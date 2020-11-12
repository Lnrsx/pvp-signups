from discord.ext import commands
from utils.utils import base_embed
from utils.bookings import Booking, statuses
from inspect import Parameter


class AdminTools(commands.Cog):

    """General commands for admin use related to managing bookings"""

    def __init__(self, client):
        self.client = client

    @commands.command(description='Lists currently active bookings')
    @commands.has_permissions(administrator=True)
    async def bookings(self, ctx):
        # TODO add pages when bookings are >10
        embed = base_embed("**Currently active bookings:**")
        for b in Booking.instances:
            booking_string = ''
            booking_string += f'Author: <@{b.authorid}> Status: ``{statuses[b.status]}``\n Boost info: '
            if b.status != 'compiling':
                booking_string += f'``{b.bracket} {b.type} {b.rating}``\n'
                if b.status != 'posted':
                    booking_string += f'{"Boosters" if b.bracket == "3v3" else "Booster"}: '
                    booking_string += f'<@{b.booster}> {f"and <@{b.booster_2}>" if b.bracket == "3v3" else ""}\n\u200b'
                else:
                    booking_string += 'Booster: ``N/A``\n'
            else:
                booking_string += '``N/A``\nBooster: ``N/A``\n'
            embed.add_field(name=f"ID: ``{b.id}``", value=booking_string, inline=False)
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
                if param.default is not Parameter.empty:
                    if param.default is not None:
                        command_string += f": {param.default}> "
                        continue
                command_string += '> '

            command_string += f'**\n{command.description}' if command.description else ''
            embed.add_field(name='\u200b', value=command_string, inline=False)
        embed.set_footer(text="A colon in a parameter represents the default if no argument is given")
        await ctx.send(embed=embed)


def setup(client):
    client.add_cog(AdminTools(client))
