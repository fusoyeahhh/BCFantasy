# BCFantasy
Beyond Chaos Fantasy

**Supported emulators**
  - bizhawk

## Python Requirements

Tested on python 3.8.

```bash
$ pip install twitchio, pandas, numpy
```

## Usage

Unzip the code to a location. Open this location and in a new file named `config.json`, copy the following:

```json
{
    "irc_token":"<AUTH_TOKEN>",
    "client_id":"<CLIENT_ID>",
    "nick":"<BOT_OR_YOUR_USERNAME>",
    "prefix":"!",
    "initial_channels":["#<CHANNEL>"]
}
```

And replace the `<...>` values with their approrpriate values. To get an IRC token, see here: https://twitchapps.com/tmi/ . The initial channel is the name of the stream you're attaching to.

Load `BCF.lua` into `Tools > Lua Console` in bizhawk. This will begin writing to a log at `logfile.txt` within the same directory. Then start the bot (either by running `python3 bot.py` or with your OS associated interpreter.

You can check for bot prescence by issuing the "!hi" command in twitch chat.
