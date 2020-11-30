import asyncio
import discord
from discord.ext import commands
from utils.misc import base_embed
from utils import exceptions


async def react_message(booking, buyerinfo, reactions, timeout=300):
    local_embed = await booking.author.send(embed=base_embed(f'Please respond with {buyerinfo}'))

    def reaction_check(reaction, user):
        return (str(reaction.emoji) in reactions) and (booking.author.id == user.id) and (reaction.message.id == local_embed.id)

    def message_check(message):
        return message.channel.id == booking.author.dm_channel.id and message.author == booking.author

    for x in reactions:
        await local_embed.add_reaction(x)

    pending_response = [
        commands.Bot.wait_for(booking.client, event='reaction_add', check=reaction_check),
        commands.Bot.wait_for(booking.client, event='message', check=message_check)
                        ]
    done_tasks, pending_responses = await asyncio.wait(pending_response, timeout=timeout, return_when=asyncio.FIRST_COMPLETED)
    for task in pending_responses:
        task.cancel()

    if done_tasks:
        response = done_tasks.pop().result()

        if type(response) == discord.message.Message:
            return response.content.capitalize()
        elif type(response[0]) == discord.reaction.Reaction and str(response[0]) != '❌':
            return str(response[0])
    else:
        await booking.author.send(embed=base_embed(f"Booking {booking.id} has been cancelled"))
        await booking.delete()
        raise exceptions.CancelBooking


async def react(booking, reactions, description):

    def check(reaction, user):
        return (str(reaction.emoji) in reactions or ['❌']) and (booking.author.id == user.id) and (reaction.message.id == embed.id)

    embed = await booking.author.send(embed=base_embed(description))

    for x in reactions:
        await embed.add_reaction(x)
    await embed.add_reaction('❌')

    try:
        response = await commands.Bot.wait_for(booking.client, event='reaction_add', check=check)
    except asyncio.TimeoutError:
        await booking.cancel()

    if response[0].emoji != '❌':
        return response[0].emoji
    else:
        await booking.cancel()
