from discord.ext import commands
from utils.bookings import Booking
from utils.utils import base_embed
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
            author = await commands.Bot.fetch_user(self.client, reaction.user_id)
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
        booking = Booking.get(booking_id)
        if booking:
            await booking.complete()
        else:
            await ctx.send(embed=base_embed(f"No booking was found with ID ``{booking_id}``"))

    @commands.command(description="Marks a booking as partially or fully refunded")
    async def refund(self, ctx, amount, booking_id):
        if amount.lower() not in ['full', 'partial']:
            raise commands.BadArgument
        booking = Booking.get(booking_id)
        if booking:
            await booking.refund(ctx.message.author.id, amount)
        else:
            await ctx.send(embed=base_embed(f"No booking found with ID ``{booking_id}``"))

    @commands.command(description="Changes the registered gold realms of a booking")
    async def setgoldrealm(self, ctx, booking_id):
        b = Booking.get(booking_id)
        if ctx.message.author.id == b.authorid:
            if b:
                b.gold_realms = await b.get_gold_realms()
                if b.status in range(3, 7):
                    await b.update_sheet()
        else:
            await ctx.send(embed=base_embed("You must be the booking author to do that"))


def setup(client):
    client.add_cog(Bookings(client))
