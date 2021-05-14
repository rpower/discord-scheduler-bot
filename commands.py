import re
import discord
import pytz
from random import randint
from database import *

# Define timezones
est_time = pytz.timezone('US/Eastern')
uk_time = pytz.timezone('Europe/London')
datetime_format = '%Y-%m-%d %H:%M'


async def create(bot, args, message):
    add_regex = r'^.*event (.*) time (.*) attendees (.*?)(?: reminder.*|$)'
    if re.match(add_regex, message.content):
        try:
            regex_matches = re.findall(add_regex, message.content)[0]
            events_list = regex_matches[0]
            event_time_and_date = regex_matches[1]
            attendees_list = regex_matches[2]

            # Format date and time
            event_date_and_time_dt = datetime.datetime.strptime(event_time_and_date, '%Y-%m-%d %H:%M')

            # Format date and time to correct timezone
            # event_date_and_time_dt_est = uk_time.localize(event_date_and_time_dt).astimezone(est_time)

            # Set reminder time
            reminder_period_regex = r'.*reminder (\d+)'
            if re.match(reminder_period_regex, message.content):
                reminder_period = re.findall(reminder_period_regex, message.content)[0]
                reminder_period = int(reminder_period)
            else:
                # Default reminder time is 30 minutes
                reminder_period = 30
            reminder_time = event_date_and_time_dt - datetime.timedelta(minutes = reminder_period)

            event_time_formatted = bot.custom_strftime('%H:%M', event_date_and_time_dt)
            event_date_formatted = bot.custom_strftime('%A, {S} of %B', event_date_and_time_dt)
            event_date_and_time_formatted = event_time_formatted + ' on ' + event_date_formatted

            # Commit to server
            unique_id = randint(1000000, 9999999)
            add_new_event(
                unique_id,
                events_list,
                attendees_list,
                event_date_and_time_dt,
                reminder_time,
                message.author.id,
                message.guild.id,
                message.channel.id
            )
            bot.logger.info(f'Created event {unique_id} in server {message.guild.id}')

            # Send confirmation to channel
            embed = discord.Embed(title=events_list, color=2003199)
            embed.add_field(name='When', value=event_date_and_time_formatted, inline=False)
            embed.add_field(name='Attendees', value=attendees_list, inline=False)
            embed.set_author(name=message.author.name, icon_url=message.author.avatar_url)
            embed.set_thumbnail(url=bot.credentials['discord']['avatar_url'])
            embed.set_footer(text=f'Attendees will be reminded {reminder_period} minutes beforehand')
            await message.channel.send(embed=embed)
            await message.channel.send(attendees_list)
        except Exception as e:
            bot.logger.info(
                f'Unable to create event in server {message.guild.id}. Attempted message: "{message.content}". Error: "{e}"')
            await message.channel.send(f'Unable to create event. Error: `{e}`')
    else:
        bot.logger.info(f'Invalid arguments in server {message.guild.id}. Attempted message: "{message.content}"')
        await message.channel.send('Invalid arguments.')


async def list_upcoming_events(bot, args, message):
    # Get server ID
    server_id = message.guild.id

    # Get list of events
    list_of_events = get_upcoming_events(server_id)

    # Compose response
    embed = discord.Embed(title='Upcoming events', color=2003199)
    embed.set_author(name=message.author.name, icon_url=message.author.avatar_url)
    embed.set_thumbnail(url=bot.credentials['discord']['avatar_url'])

    for event in list_of_events:
        embed.add_field(name='Event', value=event[1] + ' (' + str(event[0]) + ')')
        embed.add_field(name='Attendees', value=event[2].replace(" ", "\n"))

        event_date_time = event[3]
        event_time_formatted = bot.custom_strftime('%H:%M', event_date_time)
        event_date_formatted = bot.custom_strftime('%A, {S} of %B', event_date_time)
        event_date_and_time_formatted = event_time_formatted + ' on ' + event_date_formatted
        embed.add_field(name='Date', value=event_date_and_time_formatted)
    bot.logger.info(f'Listed upcoming events in server {message.guild.id}')
    await message.channel.send(embed=embed)


async def delete(bot, args, message):
    event_id = args[1]
    # Check event exists
    event_id_info = check_single_event_exists(event_id, message.author.id, message.guild.id)

    if event_id_info:
        delete_single_event(event_id, message.author.id, message.guild.id)
        await message.channel.send(f'Event `{event_id}` deleted.')
        bot.logger.info(f'Deleted event {event_id} from server {message.guild.id}')
    else:
        await message.channel.send(f'Could not delete event `{event_id}`. Event does not exist.')
        bot.logger.info(f'Deleted event attempt failed. Event ID {event_id} does not exist. Server: {message.guild.id}')


async def display_help_message(bot, args, message):
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
    'list': list_upcoming_events,
    'delete': delete,
    'help': display_help_message
}
