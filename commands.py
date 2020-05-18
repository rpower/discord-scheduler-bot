import re
import datetime
import discord
from random import randint


async def create(bot, args, message):
    add_regex = r'^.*event (.*) time (.*) attendees (.*?)(?: reminder.*|$)'
    if re.match(add_regex, message.content):
        try:
            regex_matches = re.findall(add_regex, message.content)[0]
            events_list = regex_matches[0]
            event_time_and_date = regex_matches[1]
            attendees_list = regex_matches[2]

            # Optional reminder parameter
            reminder_time_regex = r'.*reminder (\d+)'
            if re.match(reminder_time_regex, message.content):
                reminder_time = re.findall(reminder_time_regex, message.content)[0]
            else:
                # Default reminder time is 30 minutes
                reminder_time = 30

            # Format date and time
            event_date_and_time_dt = datetime.datetime.strptime(event_time_and_date, '%Y-%m-%d %H:%M')

            event_time_formatted = bot.custom_strftime('%H:%M', event_date_and_time_dt)
            event_date_formatted = bot.custom_strftime('%A, {S} of %B', event_date_and_time_dt)
            event_date_and_time_formatted = event_time_formatted + ' on ' + event_date_formatted

            # Commit to server
            unique_id = randint(1000000, 9999999)
            sql = f"""
                insert into {bot.credentials['sql_details']['table_name']} (id, event, attendees, datetime, reminder, creator, server, channel) values (%s, %s, %s, %s, %s, %s, %s, %s)
                """
            val = (unique_id, events_list, attendees_list, event_date_and_time_dt, reminder_time, message.author.id, message.guild.id, message.channel.id)
            bot.logger.info(f'Created event {unique_id} in server {message.guild.id}')
            bot.db_insert(sql, val)

            # Send confirmation to channel
            embed = discord.Embed(title = events_list, color = 2003199)
            embed.add_field(name = 'When', value = event_date_and_time_formatted, inline = False)
            embed.add_field(name = 'Attendees', value = attendees_list, inline = False)
            embed.set_author(name = message.author.name, icon_url = message.author.avatar_url)
            embed.set_thumbnail(url = bot.credentials['discord']['avatar_url'])
            embed.set_footer(text = f'Attendees will be reminded {reminder_time} minutes beforehand')
            await message.channel.send(embed = embed)
            await message.channel.send(attendees_list)
        except Exception as e:
            bot.logger.info(f'Unable to create event in server {message.guild.id}. Attempted message: "{message.content}". Error: "{e}"')
            await message.channel.send(f'Unable to create event. Error: `{e}`')
    else:
        bot.logger.info(f'Invalid arguments in server {message.guild.id}. Attempted message: "{message.content}"')
        await message.channel.send('Invalid arguments.')


async def list(bot, args, message):
    # Get server ID
    server_id = message.guild.id

    # Get list of events
    sql = f"""
    select
        id,
        event,
        attendees,
        datetime
    from
        {bot.credentials['sql_details']['table_name']}
    where
        server = %s
        and datetime > now()
    order by
        datetime
    """
    val = (server_id, )
    list_of_events = bot.db_select(sql, val)

    # Compose response
    embed = discord.Embed(title = 'Upcoming events', color = 2003199)
    embed.set_author(name = message.author.name, icon_url = message.author.avatar_url)
    embed.set_thumbnail(url = bot.credentials['discord']['avatar_url'])

    for event in list_of_events:
        embed.add_field(name = 'Event', value = event[1] + ' (' + str(event[0]) + ')')
        embed.add_field(name = 'Attendees', value = event[2].replace(" ", "\n"))
        event_time_formatted = bot.custom_strftime('%H:%M', event[3])
        event_date_formatted = bot.custom_strftime('%A, {S} of %B', event[3])
        event_date_and_time_formatted = event_time_formatted + ' on ' + event_date_formatted
        embed.add_field(name = 'Date', value = event_date_and_time_formatted)
    bot.logger.info(f'Listed upcoming events in server {message.guild.id}')
    await message.channel.send(embed = embed)


async def delete(bot, args, message):
    event_id = args[1]
    # Get information about event being deleted
    sql = f"""select creator, server from {bot.credentials['sql_details']['table_name']} where id = %s"""
    val = (event_id, )
    event_id_info = bot.db_select(sql, val)

    # Check user has admin privileges
    user_is_admin = message.author.guild_permissions.administrator
    # Check event exists
    event_exists = (len(event_id_info) == 1)
    if event_exists:
        # Check the server ID of the delete request matches the server ID of the event
        server_matches = (str(event_id_info[0][1]) == str(message.guild.id))
        # Check the author of the delete request matches the author of the event
        author_matches = (str(event_id_info[0][0]) == str(message.author.id))

    # Check if event exists
    if not event_exists:
        bot.logger.info(f'Deleted event attempt failed. Event ID {event_id} does not exist. Server: {message.guild.id}')
        await message.channel.send(f'Could not delete event {event_id}. Event does not exist.')
    # Check if correct server
    elif not server_matches:
        bot.logger.info(f'Deleted event attempt failed. Incorrect server. Event created server: {event_id_info[0][1]}. Server: {message.guild.id}')
        await message.channel.send(f'Could not delete event {event_id}. Make sure you are in the same server the event was created in.')
    # Check if correct author
    elif not (author_matches or user_is_admin):
        bot.logger.info(
            f'Deleted event attempt failed. Incorrect user. Event created user: {event_id_info[0][0]}. User: {message.author.id}. Server: {message.guild.id}')
        await message.channel.send(f'Could not delete event {event_id}. Make sure you are creator of the event.')
    # Finally delete event
    elif event_exists and server_matches and (author_matches or user_is_admin):
        await message.channel.send(f'Event {event_id} deleted.')
        sql = f"""delete from {bot.credentials['sql_details']['table_name']} where server = %s and id = %s"""
        val = (message.guild.id, event_id)
        bot.logger.info(f'Deleted event {event_id} from server {message.guild.id}')
        bot.db_insert(sql, val)


async def help(bot, args, message):
    help_message = (':book: **Event Scheduler Commands**\n\n'
        'Add an event to the schedule:\n'
        '`!schedule add event [event_name] time [YYYY-MM-DD HH:MM] attendees [attendees]`\n\n'
        'Replace:\n'
        '`[event_name]` with the name of your event\n'
        '`[YYYY-MM-DD HH:MM]` should be the date and 24 hour time of the event you are creating\n'
        '`[attendees]` with at list of attendees from the server\n\n'
        'List all upcoming events: `!schedule list`\n\n'
        'Remove an upcoming event: `!schedule delete [event_id]`\n'
        'More information: https://github.com/rpower/discord-scheduler-bot')
    bot.logger.info(f'Listed help message in server {message.guild.id}')
    await message.channel.send(help_message)

commands_list = {
    'add': create,
    'list': list,
    'delete': delete,
    'help': help
}