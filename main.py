from utils.misc import get_logger, base_embed
from utils.request import Request
from utils.booking import Booking
from utils import exceptions
from utils.config import cfg

from discord.ext import commands
import discord

import os
import sys
import traceback
import json

logger = get_logger('PvpSignups')


class PvpSignups(commands.Bot):
    """Represent the client used to access discord

    Attributes
    -----------
    intents: :class:`discord.Intents`
        The intents used by the clients, set to discord's default intents settings.
    request: :class:`Request`
        The class used to make HTTP requests, currently only being used to get a
         player's ingame faction and class from the blizzard API servers
    """
    def __init__(self):
        intents = discord.Intents.default()
        super().__init__(command_prefix=cfg.settings['command_prefix'], intents=intents)
        self.request = Request(self)
        self.startup()

    async def on_ready(self):
        try:
            await Booking.load(self)

            if cfg.settings['auto_faction_class_input']:
                await self.request.token('wowapi')
            else:
                logger.info("Automatic faction and class input is disabled")

        except exceptions.ChannelNotFound:
            logger.error("Bot failed to find the post and request channels from ID, check them in config.json")
            exit()

        except exceptions.MessageNotFound:
            logger.warning("No valid request message was found in the request booking channel, automatically creating...")
            request_message = await Booking.request_channel.send(f"React with {cfg.settings['twos_emoji']} to create a 2v2 booking or {cfg.settings['threes_emoji']} to create a 3v3 booking")
            await request_message.add_reaction(cfg.settings['twos_emoji'])
            await request_message.add_reaction(cfg.settings['threes_emoji'])
            cfg.set("request_booking_message_id", request_message.id)
            await Booking.load(self)
        except exceptions.InvalidTokenResponse:
            cfg.set("auto_faction_class_input", False)
            logger.warning("Bot could not get a blizzard API access token, automatic faction/class input has been disabled")

        logger.info("Bot is ready")

    def startup(self):
        """Performs the necessary checks on file integrity and loads cogs, must be called or the bot will not have any commands"""
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
        bot.run(cfg.settings['discord_token'])
    except discord.LoginFailure:
        logger.error("Bot failed to log in, check discord token is valid in config.json")


if __name__ == '__main__':
    main()
