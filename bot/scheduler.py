import disnake
from disnake.ext import tasks, commands
import os
import logging
from dotenv import load_dotenv
from event_commands import list_upcoming_events, create_event, delete_event, display_help_message, create_event_slash, delete_event_slash
from database import get_events_to_remind, mark_events_as_reminded

# Environment variables
load_dotenv()
BOT_TOKEN = os.getenv('BOT_TOKEN')
AVATAR_URL = os.getenv('AVATAR_URL')

# Logging
formatter = logging.Formatter('%(asctime)s [%(levelname)s]: %(message)s')
handler = logging.FileHandler('bot.log')
handler.setFormatter(formatter)
logger = logging.getLogger(__name__)
logger.addHandler(handler)
logger.setLevel(logging.INFO)

# Intents
intents = disnake.Intents.default()
intents.messages = True

bot_command_prefix = 'schedule'
bot = commands.Bot(command_prefix =f'!{bot_command_prefix} ', help_command = None, intents = intents)

@bot.event
async def on_ready():
    for guild in bot.guilds:
        logger.info(f'Logged into server: "{guild.name}" (id: {guild.id}, members: {guild.member_count})')
    await bot.change_presence(activity=disnake.Activity(
        type=disnake.ActivityType.listening,
        name=f"/{bot_command_prefix} help"
    ))

@bot.event
async def on_guild_join(guild):
    logger.info(f'Joined server: "{guild.name}" (id: {guild.id}, members: {guild.member_count})')

# Legacy commands
@bot.command()
async def list(ctx):
    await list_upcoming_events(ctx, AVATAR_URL, slash_command=False)

@bot.command()
async def add(ctx, *, arg):
    await create_event(ctx, arg, AVATAR_URL)

@bot.command()
async def delete(ctx, arg):
    await delete_event(ctx, arg)

@bot.command()
async def help(ctx):
    await display_help_message(ctx, slash_command=False)

# Slash commands
@bot.slash_command()
async def schedule(inter):
    pass

@schedule.sub_command(description='Lists upcoming events')
async def list(ctx):
    await list_upcoming_events(ctx, AVATAR_URL, slash_command=True)

@schedule.sub_command(description='Create new event')
async def add(inter: disnake.ApplicationCommandInteraction, event_name: str, date_time: str, attendees: str):
    """
    Create new event

    Parameters
    ----------
    event_name: The name of the event
    date_time: The date and time of the event in YYYY-MM-DD HH:MM format
    attendees: A list of people attending your event
    """
    await create_event_slash(inter, event_name, date_time, attendees, AVATAR_URL)

@schedule.sub_command(description='Delete event')
async def delete(inter: disnake.ApplicationCommandInteraction, event_id: int):
    """
    Create new event

    Parameters
    ----------
    event_id: The ID of the event (use /schedule list to find what these are)
    """
    await delete_event_slash(inter, event_id)

@schedule.sub_command(description='Get help on Event Scheduler commands')
async def help(ctx):
    await display_help_message(ctx, slash_command=True)

@tasks.loop(seconds = 60.0)
async def check_upcoming_events():
    events_to_remind = get_events_to_remind()
    events_to_remind = [r[0] for r in events_to_remind]

    for events in events_to_remind:
        channel_to_remind_id = int(events.channel)
        channel_to_remind = bot.get_channel(channel_to_remind_id)
        reminder_period = int((events.datetime - events.reminder_time).total_seconds() / 60)

        reminder_message = f':alarm_clock: **Reminder:** {events.event} in {reminder_period} minutes ' \
                           f'with {events.attendees} organised by <@{events.creator}>'
        logger.info(f'Sending reminder message to server {events.server} regarding event {events.id}')
        await channel_to_remind.send(reminder_message)

        # Mark event as reminded
        mark_events_as_reminded(events.id)

@check_upcoming_events.before_loop
async def before_check_upcoming_events():
    await bot.wait_until_ready()

# Start upcoming events check loop
check_upcoming_events.start()

bot.run(BOT_TOKEN)
