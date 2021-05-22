import discord
from discord.ext import tasks
import asyncio
from commands import commands_list
import json
import os
import logging
from database import *


class ScheduleBot(discord.Client):
    def __init__(self):
        # Logging
        formatter = logging.Formatter('%(asctime)s [%(levelname)s]: %(message)s')
        handler = logging.FileHandler('bot.log')
        handler.setFormatter(formatter)
        self.logger = logging.getLogger(__name__)
        self.logger.addHandler(handler)
        self.logger.setLevel(logging.INFO)

        # Credentials
        self.credentials = credentials

        # Start upcoming events check loop
        self.check_upcoming_events.start()

        super().__init__()

    async def on_ready(self):
        self.logger.info('Bot is running.')
        self.logger.info(f'Logged in as: "{self.user}"')
        for server in self.guilds:
            self.logger.info(f'Logged into server: "{server.name}" (id: {server.id}, members: {server.member_count})')
        await self.change_presence(activity=discord.Activity(type=discord.ActivityType.listening, name="!schedule help"))

    async def on_server_join(self, server):
        self.logger.info(f'Joined new server: "{server.name}" (id: {server.id}, members: {server.member_count})')

    def suffix(self, d):
        return 'th' if 11 <= d <= 13 else {1: 'st', 2: 'nd', 3: 'rd'}.get(d % 10, 'th')

    def custom_strftime(self, format, t):
        return t.strftime(format).replace('{S}', str(t.day) + self.suffix(t.day))

    async def on_message(self, message):
        # Don't respond to message from itself
        if message.author == self.user:
            return
        # Don't respond to messages from other bots
        if message.author.bot:
            return

        bot_message_prefix = '!schedule'
        if message.content.startswith(bot_message_prefix):
            args = message.content[len(bot_message_prefix) + 1:].split(' ')
            command = commands_list.get(args[0])
            if command is not None:
                await command(self, args, message)
            else:
                bot.logger.info(f'Invalid command in server {message.guild.id}. Attempted message: "{message.content}"')

    @tasks.loop(seconds = 60.0)
    async def check_upcoming_events(self):
        events_to_remind = get_events_to_remind()
        events_to_remind = [r[0] for r in events_to_remind]

        for events in events_to_remind:
            channel_to_remind_id = int(events.channel)
            channel_to_remind = self.get_channel(channel_to_remind_id)
            reminder_period = int((events.datetime - events.reminder_time).total_seconds() / 60)

            reminder_message = f':alarm_clock: **Reminder:** {events.event} in {reminder_period} minutes with {events.attendees} organised by <@{events.creator}>'
            self.logger.info(f'Sending reminder message to server {events.server} regarding event {events.id}')
            await channel_to_remind.send(reminder_message)

            # Mark event as reminded
            mark_events_as_reminded(events.id)

    @check_upcoming_events.before_loop
    async def before_check_upcoming_events(self):
        await self.wait_until_ready()

if os.path.isfile('credentials.json'):
    with open('credentials.json') as credentials_file:
        credentials = json.loads(credentials_file.read())
        bot = ScheduleBot()
        application = bot
        bot.run(credentials['discord']['bot_token'])
else:
    self.logger.info(f'Could not find credentials.json')

