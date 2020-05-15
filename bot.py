import mysql.connector
import discord
import asyncio
from commands import commands_list
import json
import os
import logging


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

        # Database
        self.database = mysql.connector.connect(
            host=credentials['sql_details']['host'],
            user=credentials['sql_details']['username'],
            passwd=credentials['sql_details']['pw'],
            database=credentials['sql_details']['db_name']
        )

        super().__init__()

    async def on_ready(self):
        self.logger.info('Bot is running.')
        self.logger.info(f'Logged in as: "{self.user}"')
        for server in self.guilds:
            self.logger.info(f'Logged into server: "{server.name}" (id: {server.id}, members: {server.member_count})')
        await self.change_presence(activity=discord.Activity(type=discord.ActivityType.listening, name="!schedule help"))
        await self.check_upcoming_reminders()

    async def on_server_join(self, server):
        self.logger.info(f'Joined new server: "{server.name}" (id: {server.id}, members: {server.member_count})')

    def db_insert(self, sql, values):
        mycursor = self.database.cursor()
        mycursor.execute(f"""set @@session.time_zone = '{credentials['sql_details']['time_zone']}'""")
        mycursor.execute(sql, values)
        self.database.commit()

    def db_select(self, sql, values):
        mycursor = self.database.cursor()
        mycursor.execute(f"""set @@session.time_zone = '{credentials['sql_details']['time_zone']}'""")
        mycursor.execute(sql, values)
        return mycursor.fetchall()

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

    async def check_upcoming_reminders(self):
        self.logger.info('Checking upcoming events.')
        interval_between_checks_in_seconds = 60
        # Give ourselves a small window to remind people
        window_to_remind_in_minutes = 1

        get_upcoming_events_sql = f"""
        select
            id,
            event,
            datetime,
            creator,
            attendees,
            channel,
            reminder,
            server
        from (
            select
                id,
                event,
                attendees,
                datetime,
                creator,
                server,
                channel,
                reminder,
                timestampdiff(minute, now(), date_sub(datetime, interval reminder minute)) as time_to_reminder
            from
                {credentials['sql_details']['table_name']}
            where
                datetime > now()
                and reminded_flag = 0
        ) a
        where
            time_to_reminder <= %s; 
        """

        set_reminded_flag_sql = f"""
        update
            {credentials['sql_details']['table_name']}
        set
            reminded_flag = 1
        where
            id in (%s)
        """

        while True:
            vals = (window_to_remind_in_minutes, )
            events_to_remind = self.db_select(get_upcoming_events_sql, vals)
            event_ids_to_remind = [item[0] for item in events_to_remind]

            for event in events_to_remind:
                channel_to_remind_id = int(event[5])
                channel_to_remind = self.get_channel(channel_to_remind_id)
                time_formatted = event[2].strftime('%H:%M')
                reminder_message = f':alarm_clock: **Reminder:** {event[1]} in {event[6]} minutes with {event[4]} organised by <@{event[3]}>'
                self.logger.info(f'Sending reminder message to server {event[7]} regarding event {event[0]}')
                await channel_to_remind.send(reminder_message)

            if len(events_to_remind) > 0:
                format_event_ids_to_remind = ','.join(['%s'] * len(event_ids_to_remind))
                self.logger.info(f'Setting reminded flag for event {event[0]}')
                self.db_insert(set_reminded_flag_sql % format_event_ids_to_remind, tuple(event_ids_to_remind))

            await asyncio.sleep(interval_between_checks_in_seconds)

if os.path.isfile('credentials.json'):
    with open('credentials.json') as credentials_file:
        credentials = json.loads(credentials_file.read())
        bot = ScheduleBot()
        application = bot
        bot.run(credentials['discord']['bot_token'])
else:
    self.logger.info(f'Could not find credentials.json')

