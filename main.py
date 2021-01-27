__version__ = "1.0.0"


from utils.misc import get_logger, base_embed
from utils.request import request
from utils.booking import Booking
from utils import exceptions
from utils.config import cfg, icfg, devmode

from discord.ext import commands, tasks
import discord

import os
import sys
import traceback
from inspect import Parameter

logger = get_logger('PvpSignups')


class PvpSignups(commands.Bot):
    """Represent the client used to access discord

    Attributes
    -----------
    intents: :class:`discord.Intents`
        The intents used by the clients, set to discord's default intents settings.
    """
    def __init__(self):
        intents = discord.Intents.default()
        intents.members = True
        super().__init__(command_prefix=cfg.command_prefix if not devmode else "?", intents=intents)
        self.startup()

    async def on_ready(self):
        try:
            await Booking.load(self)
            for instname in icfg.keys():
                pass
                await Booking.update_untaken_boosts(instname)
            if cfg.auto_faction_class_input:
                await request.token('wowapi')
            else:
                logger.info("Automatic faction and class input is disabled")

        except exceptions.ChannelNotFound:
            logger.error("Bot failed to find the post, request or untaken channels from ID, check them in config.json")
            exit()

        except exceptions.InvalidTokenResponse:
            cfg.set("auto_faction_class_input", False)
            logger.warning("Bot could not get a blizzard API access token, automatic faction/class input has been disabled")
        await Booking.cleanup()
        logger.info("Bot is ready")

    def startup(self):
        """Performs the necessary checks on file integrity and loads cogs, must be called or the bot will not have any commands"""
        self.remove_command("help")
        for filename in os.listdir('./cogs'):
            if filename.endswith('.py'):
                self.load_extension(f'cogs.{filename[:-3]}')

    @staticmethod
    async def tryrestart():
        if [b for b in Booking.instances if b.status in range(0, 3)]:
            logger.warning("it is not safe to shut down")
            return False
        for booking in Booking.instances:
            if booking.status not in range(0, 3):
                booking.cache()
        logger.info("All bookings have been cached, shutting down")
        exit()

    async def on_command_error(self, ctx, error):
        if hasattr(ctx.command, 'on_error'):
            return

        ignored_exceptions = (commands.CommandNotFound, commands.MissingPermissions)
        error = getattr(error, 'original', error)

        if isinstance(error, ignored_exceptions):
            return

        if isinstance(error, commands.MissingRequiredArgument):
            await ctx.send(f"Missing Argument, usage: {self.cmd_usage_string(ctx.command)}")

        elif isinstance(error, commands.BadArgument):
            await ctx.send(f"Invalid Argument, usage: {self.cmd_usage_string(ctx.command)}")

        elif isinstance(error, exceptions.RequestFailed):
            logger.warning(f"Command request raised an exception: {error}")
            await ctx.send(embed=base_embed(str(error)))

        else:
            await ctx.send(embed=base_embed("Sorry, an unexpected error ococured please contact PvP management"))
            logger.error(error)
            traceback.print_exception(type(error), error, error.__traceback__, file=sys.stderr)

    def cmd_usage_string(self, command: discord.ext.commands.Command):
        command_string = f"{self.command_prefix}{command} "
        for name, param in command.clean_params.items():
            command_string += f"<{name.replace('_', ' ')}"
            if param.default is not Parameter.empty and param.default is not None:
                command_string += f": {param.default}> "
                continue
            command_string += '> '
        return f"**{command_string}**"

    @tasks.loop(hours=1)
    async def cleanup(self):
        await Booking.cleanup()


def main():
    bot = PvpSignups()
    try:
        bot.run(cfg.discord_token)
    except discord.LoginFailure:
        logger.error("Bot failed to log in, check discord token is valid in config.json")


if __name__ == '__main__':
    main()
