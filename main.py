from utils.utils import get_logger, base_embed
from utils.request import Request
from utils.bookings import Booking
from utils import exceptions
from utils.config import ConfigManager
from utils.sheets import SheetManager

from discord.ext import commands
import discord

import os
import sys
import traceback
import json

logger = get_logger('PvpSignups')


class PvpSignups(commands.Bot):
    def __init__(self):
        self.config_manager = ConfigManager()
        self.config = self.config_manager.settings
        intents = discord.Intents.default()
        super().__init__(command_prefix=self.config['command_prefix'], intents=intents)
        self.request = Request(self)
        self.sheets = SheetManager(self)
        self.startup()

    async def on_ready(self):
        try:
            await Booking.load(self)

            if self.config['auto_faction_class_input']:
                await self.request.token('wowapi')
            else:
                logger.info("Automatic faction and class input is disabled")

        except exceptions.ChannelNotFound:
            logger.error("Bot failed to find the post and request channels from ID, check them in config.json")
            exit()

        except exceptions.MessageNotFound:
            logger.warning("No valid request message was found in the request booking channel, automatically creating...")
            request_message = await Booking.request_channel.send(f"React with {self.config['twos_emoji']} to create a 2v2 booking or {self.config['threes_emoji']} to create a 3v3 booking")
            await request_message.add_reaction(self.config['twos_emoji'])
            await request_message.add_reaction(self.config['threes_emoji'])
            self.config.set("request_booking_message_id", request_message.id)
            await Booking.load(self)
        except exceptions.InvalidTokenResponse:
            self.config.set("auto_faction_class_input", False)
            logger.warning("Bot could not get a blizzard API access token, automatic faction/class input has been disabled")

        logger.info("Bot is ready")

    def startup(self):
        if not os.path.isdir('data'):
            os.mkdir("data")
        for file in ['bookings.json', 'token.json']:
            if not os.path.isfile(f'data/{file}'):
                with open(f"data/{file}", "w") as f:
                    json.dump({}, f)
        if not os.path.isfile("data/serviceacct_spreadsheet.json"):
            logger.error(
                "No google service account creds detected,"
                " go to https://gspread.readthedocs.io/en/latest/oauth2.html#for-bots-using-service-account and follow the instructions")
            exit()
        self.remove_command("help")
        for filename in os.listdir('./cogs'):
            if filename.endswith('.py'):
                self.load_extension(f'cogs.{filename[:-3]}')

    async def on_command_error(self, ctx, error):
        if hasattr(ctx.command, 'on_error'):
            return

        ignored_exceptions = (commands.CommandNotFound, exceptions.CancelBooking, commands.MissingPermissions)
        error = getattr(error, 'original', error)

        if isinstance(error, ignored_exceptions):
            return

        if isinstance(error, commands.MissingRequiredArgument):
            await ctx.send("Missing Argument")

        elif isinstance(error, commands.BadArgument):
            await ctx.send("Invalid Argument")

        elif isinstance(error, exceptions.RequestFailed):
            await ctx.send(embed=base_embed(str(error)))

        else:
            await ctx.send(error)
            logger.error(error)
            traceback.print_exception(type(error), error, error.__traceback__, file=sys.stderr)


def main():
    bot = PvpSignups()
    try:
        bot.run(bot.config['discord_token'])
    except discord.LoginFailure:
        logger.error("Bot failed to log in, check discord token is valid in config.json")


if __name__ == '__main__':
    main()
