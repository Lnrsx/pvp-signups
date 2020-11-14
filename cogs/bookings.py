from discord.ext import commands
from utils.bookings import Booking
from utils import exceptions


class Bookings(commands.Cog):

    """Public commands related to advertisers creating and managing bookings"""

    def __init__(self, client):
        self.client = client

    @commands.Cog.listener()
    async def on_raw_reaction_add(self, reaction):
        cond1 = reaction.channel_id == self.client.config["request_booking_channel_id"]
        cond2 = reaction.message_id == self.client.config["request_booking_message_id"]
        cond3 = reaction.emoji.name in [self.client.config["twos_emoji"], self.client.config["threes_emoji"]]
        if cond1 and cond2 and cond3:
            author = commands.Bot.get_user(self.client, reaction.user_id)
            bracket = '2v2' if reaction.emoji.name == self.client.config["twos_emoji"] else '3v3'
            booking = Booking(bracket, author)
            message = await Booking.request_channel.fetch_message(self.client.config["request_booking_message_id"])
            try:
                await message.remove_reaction(reaction.emoji, author)
                await booking.compile()
                embed = await booking.post()
                await booking.pick_winner(embed)
                await booking.upload()
                booking.cache()
            except exceptions.CancelBooking:
                pass

    @commands.command(description="Marks a booking as complete")
    async def done(self, ctx, booking_id):
        try:
            booking = Booking.get(booking_id)
            assert booking, f"No booking found with ID ``{booking_id}``"
            assert booking.authorized(ctx.message.author.id), "You do not have permission to do that"
            await booking.complete()
        except AssertionError as e:
            raise exceptions.RequestFailed(str(e))

    @commands.command(description="Marks a booking as partially or fully refunded")
    async def refund(self, ctx, amount, booking_id):
        try:
            assert amount.lower() in ['full', 'partial'], "Booking refund amount must be 'full' or 'partial'"
            booking = Booking.get(booking_id)
            assert booking, f"No booking found with ID ``{booking_id}``"
            assert booking.authorized(ctx.message.author.id), "You do not have permission to do that"
            await booking.refund(ctx.message.author.id, amount)
        except AssertionError as e:
            raise exceptions.RequestFailed(str(e))

    @commands.command(description="Changes the registered gold realms of a booking")
    async def setgoldrealm(self, ctx, booking_id):
        try:
            booking = Booking.get(booking_id)
            assert booking, f"No booking found with ID ``{booking_id}``"
            assert booking.authorized(ctx.message.author.id), "You do not have permission to do that"
            await booking.get_gold_realms()
            if booking.status in range(3, 7):
                await booking.update_sheet()
        except AssertionError as e:
            raise exceptions.RequestFailed(str(e))


def setup(client):
    client.add_cog(Bookings(client))
