import re
import disnake
import pytz
import logging
import datetime
from random import randint
from database import add_new_event, get_upcoming_events, check_single_event_exists, delete_single_event

# Define timezones
est_time = pytz.timezone('US/Eastern')
uk_time = pytz.timezone('Europe/London')
datetime_format = '%Y-%m-%d %H:%M'

# Logging
formatter = logging.Formatter('%(asctime)s [%(levelname)s]: %(message)s')
handler = logging.FileHandler('bot.log')
handler.setFormatter(formatter)
logger = logging.getLogger(__name__)
logger.addHandler(handler)
logger.setLevel(logging.INFO)

scheduler_embed_colour = disnake.Colour.from_rgb(70, 94, 141)

# Helper functions
def generate_date_suffix(day_number):
    """
    Calculate what suffix to put on the end of a given date (e.g. 1st vs 2nd vs 3rd vs 4th)
    :param day_number: An integer representing the day of the month
    :return: A string representing the appropriate suffix
    """
    return 'th' if 11 <= day_number <= 13 else {1: 'st', 2: 'nd', 3: 'rd'}.get(day_number % 10, 'th')

def custom_strftime(datetime_formatting, event_datetime):
    """
    Append our custom date suffix to a given datetime string
    :param datetime_formatting: Datetime string format as per
    https://docs.python.org/3/library/datetime.html#strftime-and-strptime-format-codes
    :param event_datetime: The time of the event in datetime format
    :return: String with updated suffix on date
    """
    return event_datetime.strftime(datetime_formatting).replace(
        '{S}',
        str(event_datetime.day) + generate_date_suffix(event_datetime.day)
    )

async def create_event(ctx, arg, avatar_url):
    add_regex = r'^event (.*) time (.*) attendees (.*?)(?: reminder.*|$)'
    if re.match(add_regex, arg):
        try:
            regex_matches = re.findall(add_regex, arg)[0]
            events_list = regex_matches[0]
            event_time_and_date = regex_matches[1]
            attendees_list = regex_matches[2]

            # Format date and time
            event_date_and_time_dt = datetime.datetime.strptime(event_time_and_date, '%Y-%m-%d %H:%M')

            # Set reminder time
            reminder_period_regex = r'.*reminder (\d+)'
            if re.match(reminder_period_regex, arg):
                reminder_period = re.findall(reminder_period_regex, arg)[0]
                reminder_period = int(reminder_period)
            else:
                # Default reminder time is 30 minutes
                reminder_period = 30
            reminder_time = event_date_and_time_dt - datetime.timedelta(minutes = reminder_period)

            event_time_formatted = custom_strftime('%H:%M', event_date_and_time_dt)
            event_date_formatted = custom_strftime('%A, {S} of %B', event_date_and_time_dt)
            event_date_and_time_formatted = event_time_formatted + ' on ' + event_date_formatted

            # Commit to server
            unique_id = randint(1000000, 9999999)
            add_new_event(
                unique_id,
                events_list,
                attendees_list,
                event_date_and_time_dt,
                reminder_time,
                ctx.message.author.id,
                ctx.message.guild.id,
                ctx.message.channel.id
            )
            logger.info(f'Created event "{events_list}" (id: {unique_id}) '
                        f'in server "{ctx.message.guild.name}" (id: {ctx.message.guild.id}) '
                        f'for member "{ctx.message.author.name}" (id: {ctx.message.author.id})')

            # Send confirmation to channel
            embed = disnake.Embed(title=events_list, color=scheduler_embed_colour)
            embed.add_field(name='When', value=event_date_and_time_formatted, inline=False)
            embed.add_field(name='Attendees', value=attendees_list, inline=False)
            embed.set_author(name=ctx.message.author.name, icon_url=ctx.message.author.display_avatar)
            embed.set_thumbnail(url=avatar_url)
            embed.set_footer(text=f'Attendees will be reminded {reminder_period} minutes beforehand')
            await ctx.message.channel.send(embed=embed)
            await ctx.message.channel.send(attendees_list)
        except Exception as e:
            logger.info(
                f'Unable to create event in server "{ctx.message.guild.name}" (id: {ctx.message.guild.id}) '
                f'for member "{ctx.message.author.name}" (id: {ctx.message.author.id}). '
                f'Attempted message: "{ctx.message.content}". Error: "{e}"')
            await ctx.message.channel.send(f'Unable to create event. Error: `{e}`')
    else:
        logger.info(f'Invalid arguments in server "{ctx.message.guild.name}" (id: {ctx.message.guild.id}) '
                    f'for member "{ctx.message.author.name}" (id: {ctx.message.author.id}). '
                    f'Attempted message: "{ctx.message.content}"')
        await ctx.message.channel.send('Invalid arguments.')

async def create_event_slash(ctx, event_name, date_time, attendees, avatar_url):
    events_list = event_name
    event_time_and_date = date_time
    attendees_list = attendees

    # Format date and time
    event_date_and_time_dt = datetime.datetime.strptime(event_time_and_date, '%Y-%m-%d %H:%M')

    reminder_period = 30
    reminder_time = event_date_and_time_dt - datetime.timedelta(minutes=reminder_period)

    event_time_formatted = custom_strftime('%H:%M', event_date_and_time_dt)
    event_date_formatted = custom_strftime('%A, {S} of %B', event_date_and_time_dt)
    event_date_and_time_formatted = event_time_formatted + ' on ' + event_date_formatted

    # Commit to server
    unique_id = randint(1000000, 9999999)
    add_new_event(
        unique_id,
        events_list,
        attendees_list,
        event_date_and_time_dt,
        reminder_time,
        ctx.author.id,
        ctx.guild.id,
        ctx.channel.id
    )
    logger.info(f'Created event "{events_list}" (id: {unique_id}) '
                f'in server "{ctx.guild.name}" (id: {ctx.guild.id}) '
                f'for member "{ctx.author.name}" (id: {ctx.author.id})')

    # Send confirmation to channel
    embed = disnake.Embed(title=events_list, color=scheduler_embed_colour)
    embed.add_field(name='When', value=event_date_and_time_formatted, inline=False)
    embed.add_field(name='Attendees', value=attendees_list, inline=False)
    embed.set_author(name=ctx.author.name, icon_url=ctx.author.display_avatar)
    embed.set_thumbnail(url=avatar_url)
    embed.set_footer(text=f'Attendees will be reminded {reminder_period} minutes beforehand')
    await ctx.send(embed=embed)
    await ctx.send(attendees_list)

async def list_upcoming_events(ctx, avatar_url, slash_command=False):
    # Get server ID
    if slash_command:
        server_id = ctx.guild.id
    else:
        server_id = ctx.message.guild.id

    # Get list of events
    list_of_events = get_upcoming_events(server_id)

    # Compose response
    embed = disnake.Embed(title='Upcoming events', color=scheduler_embed_colour)
    if slash_command:
        embed.set_author(name=ctx.author.name, icon_url=ctx.author.display_avatar)
    else:
        embed.set_author(name=ctx.message.author.name, icon_url=ctx.message.author.display_avatar)
    embed.set_thumbnail(url=avatar_url)

    for event in list_of_events:
        embed.add_field(name='Event', value=event[1] + ' (' + str(event[0]) + ')')
        embed.add_field(name='Attendees', value=event[2].replace(" ", "\n"))

        event_date_time = event[3]
        event_time_formatted = custom_strftime('%H:%M', event_date_time)
        event_date_formatted = custom_strftime('%A, {S} of %B', event_date_time)
        event_date_and_time_formatted = event_time_formatted + ' on ' + event_date_formatted
        embed.add_field(name='Date', value=event_date_and_time_formatted)
    if slash_command:
        logger.info(f'Listed upcoming events in "{ctx.guild.name}" (id: {ctx.guild.id}) '
                    f'for member "{ctx.author.name}" (id: {ctx.author.id})')
        await ctx.send(embed=embed)
    else:
        logger.info(f'Listed upcoming events in "{ctx.message.guild.name}" (id: {ctx.message.guild.id}) '
                    f'for member "{ctx.message.author.name}" (id: {ctx.message.author.id})')
        await ctx.message.channel.send(embed=embed)


async def delete_event(ctx, event_id):
    # Check event exists
    event_id_info = check_single_event_exists(event_id, ctx.message.author.id, ctx.message.guild.id)

    if event_id_info:
        delete_single_event(event_id, ctx.message.author.id, ctx.message.guild.id)
        await ctx.message.channel.send(f'Event `{event_id}` deleted.')
        logger.info(f'Deleted event {event_id} from server "{ctx.message.guild.name}" (id: {ctx.message.guild.id}) '
                    f'for member "{ctx.message.author.name}" (id: {ctx.message.author.id})')
    else:
        await ctx.message.channel.send(f'Could not delete event `{event_id}`. Event does not exist.')
        logger.info(f'Unable to delete event {event_id} '
                    f'from server "{ctx.message.guild.name}" (id: {ctx.message.guild.id}) '
                    f'for member "{ctx.message.author.name}" (id: {ctx.message.author.id})')

async def delete_event_slash(ctx, event_id):
    # Check event exists
    event_id_info = check_single_event_exists(event_id, ctx.author.id, ctx.guild.id)

    if event_id_info:
        delete_single_event(event_id, ctx.author.id, ctx.guild.id)
        await ctx.send(f'Event `{event_id}` deleted.')
        logger.info(f'Deleted event {event_id} from server "{ctx.guild.name}" (id: {ctx.guild.id}) '
                    f'for member "{ctx.author.name}" (id: {ctx.author.id})')
    else:
        await ctx.send(f'Could not delete event `{event_id}`. Event does not exist.')
        logger.info(f'Unable to delete event {event_id} '
                    f'from server "{ctx.guild.name}" (id: {ctx.guild.id}) '
                    f'for member "{ctx.author.name}" (id: {ctx.author.id})')


async def display_help_message(ctx, slash_command=False):
    embed_title = ':alarm_clock: Event Scheduler Commands'
    embed_description = """
    **COMMANDS**
    
    **/schedule add**
    Add a new event, for example `/schedule add My Happy Event date_time 2022-09-30 15:30 attendees @Brass Beast Bot`.
    
    **/schedule list**
    List all upcoming events.
    
    **/schedule delete**
    Delete an upcoming event.
    
    More information and examples: https://github.com/rpower/discord-scheduler-bot
    """
    embed = disnake.Embed(
        title = embed_title,
        description = embed_description,
        color = scheduler_embed_colour
    )
    if slash_command:
        logger.info(f'Listed help message in server "{ctx.guild.name}" (id: {ctx.guild.id}) '
                    f'for member "{ctx.author.name}" (id: {ctx.author.id})')
        await ctx.send(embed=embed)
    else:
        logger.info(f'Listed help message in server "{ctx.message.guild.name}" (id: {ctx.message.guild.id}) '
                    f'for member "{ctx.message.author.name}" (id: {ctx.message.author.id})')
        await ctx.message.channel.send(embed = embed)
