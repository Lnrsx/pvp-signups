## PvP-Signups
 PvP-Signups is a discord bot designed for managing PvP bookings in World of Warcraft
 
 ## Features
* **User-friendly booking creation**
    * Automatic buyer faction and class input
    * Recommends auto-calculated boost price from customizable price list
* **Random booster selection**
    * Each user starts with a weight of 1, each boost they win or lose will +/- their weight at a rate of 0.1 per 1,000,000g
* **Automatic uploading of bookings to an external google sheet**
    * By default, this includes the discord IDs of the booster(s) and advertise, along with their cuts, the realm(s) the gold was collected on and a screenshot of the gold being sent to the bank character
* **If a list of bank characters and their realms can also be provided, advertisers will be told which characters to send the gold to after specifying the boosts collected gold realms**
 ## Commands
 
 * **Booking Commands** (Requires booking author)
    * `!refund <amount> <booking id>` (Requires booking author)<br />
    Flags a booking as refunded `<amount>` can either be `full` or `partial`.
    * `!done <booking id>` (Requires booking author)<br />
    Flags a booking as completed
    * `!setgoldrealm <booking id>` (Requires booking author)<br />
    Changes the listed gold realms of a booking
 * **Admin BLP Commands** (Requires Administrator)
    * `!blp <user>`<br />
    Displays the 2v2 and 3v3 bad luck protection values for the user
    * `!setblp <user> <bracket: 2v2> <value: 1>`<br />
    Sets the back luck protection value of the user
    * `!blplist <bracket>`<br />
    Lists the bad luck protection values of all users
 * **Admin Booking Commands** (Requires Administrator)
    * `!bookings`<br />
    Lists all currently active bookings
    * `!validate`<br />
    Checks the sheet vs the interal booking cache for any abnormalities
    * `!transferbooking <booking id> <user>`<br />
    Transfers a booking to the given user
 
  ## Installation
  
  Clone the repo:
  
  ```console
  $ git clone https://github.com/lnrsx/pvp-signups
  $ cd pvp-signups
  ```
    
  Install requirements:
  ```console
  $ pip install requirements.txt
  ```

  ## Setup
  Once the bot and the necessary dependencies have been installed, find `config.json.example` in the root directory and remove the `.example`,
  then fill in the following fields **without removing any speech marks in the config file**:
  * `discord_token` -
    The token for your discord application, it can be found [**here**](https://discord.com/developers/applications/)
    (instructions on creating an application can be found [**here**](https://discordpy.readthedocs.io/en/latest/discord.html))
  * `wowapi_id` -
    The ID for your blizzard API client - they can be created [**here**](https://develop.battle.net/access/clients)
  * `wowapi_secret` -
    The blizzard API secret is found under the client ID
  * `guild_id` -
    The ID for the server the bot will be operating in
  * `post_booking_channel_id` -
    The ID for the channel that bookings will be posted in
  * `request_booking_channel_id` -
    The ID for the channel that will contain the message used to create bookings
  * `request_booking_message_id` -
    The ID for the message that will advertisers will react to to create a booking 
    *if you do not provide one the bot will automatically create a message and save the ID*
  * `horde_emoji, alliance_emoji, choose_faction_emoji` -
    Emojis the bot will use, if you want to use unicode emojis, provide the C/C++/Java source code versions.
    If you want, you can message me on discord at `Lunarus#0936` for an invite to the server that has all the emojis the bot uses
  * `google_sheet_id` -
    The ID for the google sheet that bookings will be posted to ([**this**](https://i.imgur.com/Hs9xxQw.png) bit)
  * `worksheet_index` -
    Which worksheet the bookings will be posted to (starting from 0) 
    *make sure you check this or the bot could start posting bookings in the wrong sheet*