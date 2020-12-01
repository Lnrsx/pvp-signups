from discord.ext import commands
import discord
from utils.misc import base_embed
from utils import exceptions
from utils.booking import Booking, statuses
from inspect import Parameter


class AdminTools(commands.Cog):

    """General commands for admin use related to managing bookings"""

    def __init__(self, client):
        self.client = client

    @commands.command(description='Lists currently active bookings')
    @commands.has_permissions(administrator=True)
    async def bookings(self, ctx):
        embed = base_embed("**Currently active bookings:**")
        for b in Booking.instances:
            booking_string = ''
            booking_string += f'Author: <@{b.authorid}> Status: ``{statuses[b.status]}``\n Boost info: '
            if b.status != 'compiling':
                booking_string += f'``{b.bracket} {b.type} {b.rating}``\n'
                if b.status != 'posted':
                    booking_string += f'{"Boosters" if b.bracket == "3v3" else "Booster"}: '
                    booking_string += f'<@{b.booster.prim}> {f"and <@{b.booster.sec}>" if b.bracket == "3v3" else ""}'
                else:
                    booking_string += 'Booster: ``N/A``\n'
            else:
                booking_string += '``N/A``\nBooster: ``N/A``\n'
            embed.add_field(name=f"\nID: ``{b.id}``", value=booking_string, inline=False)
        if embed.fields:
            await ctx.send(embed=embed)
        else:
            await ctx.send(embed=base_embed("There are currently no active bookings"))

    @commands.command(description="Lists all available commands")
    @commands.has_permissions(administrator=True)
    async def help(self, ctx):
        embed = base_embed("", title="Commands:")
        for command in self.client.commands:
            command_string = f"**{self.client.command_prefix}{command} "
            for name, param in command.clean_params.items():
                command_string += f"<{name.replace('_', ' ')}"
                if param.default is not Parameter.empty and param.default is not None:
                    command_string += f": {param.default}> "
                    continue
                command_string += '> '
            command_string += f'**\n{command.description}' if command.description else ''
            embed.add_field(name='\u200b', value=command_string, inline=False)
        await ctx.send(embed=embed)

    @commands.command(description="Transfers ownship (the advertiser) of a booking")
    @commands.has_permissions(administrator=True)
    async def transferbooking(self, ctx, booking_id, user: discord.User):
        booking = Booking.get(booking_id)
        try:
            assert booking.status >= 3, "Booking that have not yet been posted cannot have ownership transferred"
            if booking.authorid != ctx.message.author.id:
                await booking.author.send(embed=base_embed(
                    f"Your booking with ID ``{booking.id}`` (``{booking.bracket} {booking.type} {booking.rating}``)"
                    f" has been given to {user.display_name} by {ctx.message.author.display_name}."
                    f" If this is unexpected please contact them"))
            if booking.authorid != user.id:
                await user.send(embed=base_embed(
                    f"Ownership of booking with ID ``{booking.id}`` (``{booking.bracket} {booking.type} {booking.rating}``)"
                    f" has been given to you by {ctx.message.author.display_name}. If this is unexpected please contact them"
                ))
            booking._author = user
            await ctx.send(embed=base_embed(
                f"Ownership of booking with ID ``{booking.id}`` (``{booking.bracket} {booking.type} {booking.rating}``)"
                f" has been given to {user.mention}"
                ))
            booking.cache()
            booking.update_sheet()

        except AssertionError as e:
            raise exceptions.RequestFailed(str(e))

    @commands.command()
    @commands.has_permissions(administrator=True)
    async def validate(self, ctx):
        response = await Booking.validate()
        await ctx.send(embed=base_embed(response))


def setup(client):
    client.add_cog(AdminTools(client))
