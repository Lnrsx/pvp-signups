import discord
from discord.ext import commands
from utils.booking import Booking
from utils import exceptions
from utils.config import cfg
from utils.misc import base_embed, get_logger

logger = get_logger("PvpSignups")


class Bookings(commands.Cog):

    """Public commands related to advertisers creating and managing bookings"""

    def __init__(self, client):
        self.client = client

    @commands.Cog.listener()
    async def on_raw_reaction_add(self, reaction):
        cond1 = reaction.channel_id == cfg.settings["request_booking_channel_id"]
        cond2 = reaction.message_id == cfg.settings["request_booking_message_id"]
        cond3 = reaction.emoji.name in [cfg.settings["twos_emoji"], cfg.settings["threes_emoji"]]
        cond4 = reaction.user_id != self.client.user.id
        if cond1 and cond2 and cond3 and cond4:
            author = commands.Bot.get_user(self.client, reaction.user_id)
            bracket = '2v2' if reaction.emoji.name == cfg.settings["twos_emoji"] else '3v3'
            booking = Booking(bracket, author)
            message = await Booking.request_channel.fetch_message(cfg.settings["request_booking_message_id"])
            await message.remove_reaction(reaction.emoji, author)
            try:
                logger.info(f"Booking being created by {author.display_name}")
                await booking.create()
            except exceptions.BookingUntaken:
                pass

    @commands.command(description="Take an untaken boost, must be in the untaken boosts channel")
    async def take(self, ctx, booking_id, partner: discord.User = None):
        if not ctx.channel == Booking.untaken_channel:
            return

        await ctx.message.delete()
        booking = Booking.get(booking_id)
        if booking.status != 7:
            await ctx.message.author.send(embed=base_embed("That booking is not Untaken"))
            return
        booking.booster.prim = ctx.message.author.id
        if booking.bracket == "3v3":
            if partner:
                booking.booster.sec = partner.id
            else:
                await ctx.message.author.send(embed=base_embed("You must mention a teammate for a 3v3 booking"))
                return
        await booking.author.send(embed=base_embed(f"You booking with ID ``{booking.id}`` for ``{booking.buyer.name}-{booking.buyer.realm} {booking.bracket} {booking.type} {booking.buyer.rating}``"
                                                   f"\n has been claimed by {ctx.message.author.display_name}"))
        await ctx.message.author.send(embed=base_embed(f"You have claimed booking with ID ``{booking.id}`` for ``{booking.buyer.name}-{booking.buyer.realm}`` ``{booking.bracket} {booking.type} {booking.buyer.rating}``"))
        logger.info(f"Booking {booking.id} has been claimed by {booking.booster.prim}")
        booking.status = 3
        await Booking.update_untaken_boosts()

    @commands.command(description="Marks a booking as complete")
    async def done(self, ctx, booking_id):
        booking = Booking.get(booking_id)
        booking.authorized(ctx.message.author.id)
        await booking.complete()

    @commands.command(description="Marks a booking as partially or fully refunded")
    async def refund(self, ctx, amount, booking_id):
        if amount.lower() not in ['full', 'partial']:
            raise exceptions.RequestFailed("Booking refund amount must be 'full' or 'partial'")
        booking = Booking.get(booking_id)
        booking.authorized(ctx.message.author.id)
        await booking.refund(full=True if amount == 'full' else False)

    @commands.command(description="Changes the registered gold realms of a booking")
    async def setgoldrealm(self, ctx, booking_id):
        booking = Booking.get(booking_id)
        booking.authorized(ctx.message.author.id)
        await booking.get_gold_realms()
        if booking.status in range(3, 8):
            await booking.update_sheet()


def setup(client):
    client.add_cog(Bookings(client))
