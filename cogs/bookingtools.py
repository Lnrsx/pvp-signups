from discord.ext import commands
from utils.booking import Booking
from utils import exceptions
from utils.config import cfg


class Bookings(commands.Cog):

    """Public commands related to advertisers creating and managing bookings"""

    def __init__(self, client):
        self.client = client

    @commands.Cog.listener()
    async def on_raw_reaction_add(self, reaction):
        cond1 = reaction.channel_id == cfg.settings["request_booking_channel_id"]
        cond2 = reaction.message_id == cfg.settings["request_booking_message_id"]
        cond3 = reaction.emoji.name in [cfg.settings["twos_emoji"], cfg.settings["threes_emoji"]]
        if cond1 and cond2 and cond3:
            author = commands.Bot.get_user(self.client, reaction.user_id)
            bracket = '2v2' if reaction.emoji.name == cfg.settings["twos_emoji"] else '3v3'
            booking = Booking(bracket, author)
            message = await Booking.request_channel.fetch_message(cfg.settings["request_booking_message_id"])
            try:
                await message.remove_reaction(reaction.emoji, author)
                await booking.compile()
                await booking.post()
                await booking.pick_winner()
                await booking.upload()
                booking.cache()

            except exceptions.CancelBooking:
                pass

    @commands.command(description="Marks a booking as complete")
    async def done(self, ctx, booking_id):
        try:
            booking = Booking.get(booking_id)
            assert booking.authorized(ctx.message.author.id), "You do not have permission to do that"
            await booking.complete()
        except AssertionError as e:
            raise exceptions.RequestFailed(str(e))

    @commands.command(description="Marks a booking as partially or fully refunded")
    async def refund(self, ctx, amount, booking_id):
        try:
            assert amount.lower() in ['full', 'partial'], "Booking refund amount must be 'full' or 'partial'"
            booking = Booking.get(booking_id)
            assert booking.authorized(ctx.message.author.id), "You do not have permission to do that"
            await booking.refund(ctx.message.author.id, True if amount == 'full' else False)
        except AssertionError as e:
            raise exceptions.RequestFailed(str(e))

    @commands.command(description="Changes the registered gold realms of a booking")
    async def setgoldrealm(self, ctx, booking_id):
        try:
            booking = Booking.get(booking_id)
            assert booking.authorized(ctx.message.author.id), "You do not have permission to do that"
            await booking.get_gold_realms()
            if booking.status in range(3, 7):
                await booking.update_sheet()
        except AssertionError as e:
            raise exceptions.RequestFailed(str(e))


def setup(client):
    client.add_cog(Bookings(client))
