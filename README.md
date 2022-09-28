# Discord Scheduler Bot

A self-hosted [disnake](https://github.com/DisnakeDev/disnake) bot written in Python that allows people to schedule simple events in their Discord server and have the attendees mentioned when the event is about to begin.

## Installation

1. Clone this repository using `git clone https://github.com/rpower/discord-scheduler-bot`
2. Install required packages using `pip install -r requirements.txt`
3. Create two environment variables:
   1. `BOT_TOKEN` - containing the API token for your Discord bot
   2. `AVATAR_URL` - a URL containing the avatar image you want to use for your bot's posts

## Commands

All commands start with `/schedule`:

| Command            | Description                               |
|--------------------|-------------------------------------------|
| `/schedule help`   | List all the commands available           |
| `/schedule add`    | Create a new event                        |
| `/schedule delete` | Delete an event                           |
| `/schedule list`   | Get a list of all upcoming events and IDs |

**Example:**

Creating an event on New Years Day at 2pm with a reminder 5 minutes beforehand:

`/schedule add event_name Celebrating New Years Day date_time 2021-01-01 14:00 attendees @my_friend1 @my_friend2 @my_friend3`

#### Other notes:

* The `list` command will only show upcoming events
* The `delete` command can only be used by the person who created the event **or** users with admin rights in a server
* This server only works in UK time for the time being
* Adding yourself as an attendee when using the `add` command is optional, you will be reminded either way