from discord.ext import commands
from utils.booking import Booking
from utils import exceptions
from utils.config import cfg
from utils.misc import base_embed, get_logger

import discord

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
        if ctx.channel != Booking.untaken_channel["2v2"] and ctx.channel != Booking.untaken_channel["3v3"]:
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

    @commands.command()
    async def rebook(self, ctx, message_id: int):
        message = None
        for bracket, channel in zip(["2v2", "3v3", "3v3"], [Booking.post_channel_2v2, Booking.post_channel_3v3, Booking.post_channel_glad]):
            try:
                message = await channel.fetch_message(message_id)
                break
            except discord.NotFound:
                pass
        if not message:
            await ctx.send(embed=base_embed("No booking message found with that ID, it was probably deleted"))
            return
        fields = message.embeds[0].fields
        b = Booking(bracket, ctx.message.author)
        b.status = 7
        b.type = fields[1].value.replace("``", "")
        b.buyer.name, b.buyer.realm = fields[0].value[fields[0].value.find("[") + 1:fields[0].value.find("]")].split("-")
        b.buyer.faction = fields[3].value[fields[3].value.find("``")+2:fields[3].value.rfind("``")]
        b.buyer.rating = fields[4].value[fields[4].value.find("``")+2:fields[4].value.rfind("``")]
        spec_emote = fields[5].value[fields[5].value.find("<"):fields[5].value.find(">")+1]
        b.buyer.spec, b.buyer.class_ = cfg.spec_from_emote(spec_emote)
        price_str = fields[2].value[fields[2].value.find("``") + 2:fields[2].value.rfind("``")].replace(",", "").replace("g", "")
        if price_str.isnumeric():
            b.ad_price_estimate = int(price_str) / cfg.settings["booster_cut"]
        else:
            b.ad_price_estimate = 0
        b.notes = fields[6].value[fields[6].value.find("``") + 2:fields[6].value.rfind("``")]
        b.post_message = message_id
        b.cache()
        await Booking.update_untaken_boosts()
        await ctx.send(embed=base_embed(f"Booking has been reposted with new ID: ``{b.id}``"))


def setup(client):
    client.add_cog(Bookings(client))
