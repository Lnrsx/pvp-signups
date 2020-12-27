from discord.ext import commands
import json
from discord import Member
from utils.misc import base_embed


class Blpcommands(commands.Cog):

    """Commands related to the bad luck protection weights of booster (requires admin privileges)"""

    def __init__(self, client):

        self.client = client

    @commands.command(description='Lists bad luck protection values of all users in the channel')
    @commands.has_permissions(administrator=True)
    async def blplist(self, ctx, bracket):

        if bracket not in ['2v2', '3v3']:
            raise Exception("Invalid argument, bracket must be '2v2' or '3v3'")

        members = [x for x in ctx.channel.members if x.bot is False]
        with open('data/userweights.json', 'r') as f:
            user_weights = json.load(f)[bracket]
        users = [x.display_name for x in members]
        weights = [str(round(user_weights[str(x.id)], 2)) if str(x.id) in user_weights.keys() else '1' for x in members]

        embed = base_embed('Bad luck protection values for ' + bracket)
        embed.add_field(
            name='__Name:__',
            value='\n'.join(users)
        )
        embed.add_field(
            name='__Value:__',
            value='\n'.join(weights)
        )
        await ctx.send(embed=embed)

    @commands.command(description='Displays the 2v2 and 3v3 bad luck protection values for the user')
    @commands.has_permissions(administrator=True)
    async def blp(self, ctx, user: Member = None):

        with open("data/userweights.json") as f:
            userweights = json.load(f)
        user = user if user else ctx.message.author
        weight_2 = str(round(userweights['2v2'][user.id], 2)) if user.id in userweights['2v2'].keys() else '1'
        weight_3 = str(round(userweights['3v3'][user.id], 2)) if user.id in userweights['3v3'].keys() else '1'
        await ctx.send(embed=base_embed(
            f"{user.display_name}'s bad luck protection value is "
            f"**``{weight_2}`` in 2v2** and **``{weight_3}`` in 3v3**"))

    @commands.command(description="Sets the bad luck protection value of the user")
    @commands.has_permissions(administrator=True)
    async def setblp(self, ctx, user: Member = None, bracket: str = '2v2', value: float = 1):
        if bracket not in ['2v2', '3v3'] or value < 0:
            raise commands.BadArgument

        user = user if user else ctx.message.author
        with open('data/userweights.json', 'r') as f:
            user_weights = json.load(f)
        user_weights[bracket][str(user.id)] = value
        with open('data/userweights.json', 'w') as f:
            json.dump(user_weights, f, indent=4)

        await ctx.send(embed=base_embed(f"{user.mention}'s {bracket} weight has been set to ``{value}``"))


def setup(client):
    client.add_cog(Blpcommands(client))
