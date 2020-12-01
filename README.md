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

 ## Requirements
 On top of having a discord bot application, the bot also requires a blizzard API client, and and google sheets service account
 
 Blizzard API clients can be created [**here**](https://develop.battle.net/access/clients) and
 instructions on how to create a google sheets service account can be found [**here**](https://gspread.readthedocs.io/en/latest/oauth2.html#for-bots-using-service-account)
 
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