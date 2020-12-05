import asyncio

import aiohttp
import json
from time import time
from datetime import datetime

import discord
from discord.ext import commands
from utils import exceptions
from utils.misc import get_logger, base_embed
from utils.config import cfg

logger = get_logger('PvpSignups')


class Request(object):
    """Asynchronous handler for (most) API requests

    Attributes
    -----------
    token_cache: :class:`dict`
        The cache for access tokens, before any access token request the cache is checked to see
        if the last token retrieved is still valid and that one is used instead.
    fields: :class:`dict`
        A dictionary containing all of the URLs for any server that access tokens need to be gotten from,
         currently only being used for the blizzard api server.
    """
    def __init__(self):
        self.token_cache = json.load(open("data/token.json", "r"))
        self.fields = {'wowapi': f"https://{cfg.settings['wowapi_id']}:{cfg.settings['wowapi_secret']}@eu.battle.net/oauth/token"}
    
    def clearcache(self):
        """Clears the token cache"""
        self.token_cache = {}
        json.dump({}, open("data/token.json", "w"))

    async def token(self, field):
        """:class:`str` Gets an access token for the specified field,
         the token cache will always be checked for a valid token before making a request.
         """
        if self.token_cache and time() < self.token_cache['expires_at']:
            # if cached cache exists and is valid
            return self.token_cache['body']['access_token']
        else:
            response = await self.get(self.fields[field], params={'grant_type': 'client_credentials'})
            if response['status'] == 200:
                response['expires_at'] = time() + response['body']['expires_in']
                self.token_cache = response
                json.dump(self.token_cache, open("data/token.json", "w"), indent=4)
                logger.info(f"Retrieved new {field} token, expires at {datetime.utcfromtimestamp(response['expires_at']).strftime('%Y-%m-%d %H:%M:%S')} UTC")
                return response['body']['access_token']
            else:
                raise exceptions.InvalidTokenResponse

    async def get(self, url, cache=None, params=None, token=False):
        """Makes an asynchronous HTTP request

        Parameters
        -----------
        url: :class:`str`
            The URL of the request.
        cache: :class:Optional['dict']
            If a dictionary containing a 'last_modified' key and timestamp value is given,
            a 304 request will be sent and will return the given cache body if the response is 304
        params: :class:Optional['LooseHeaders']
            The paramaters of the request
        token: class:`bool`
            Adds an access token to the URL if True
        """
        url += '&access_token=' + await self.token('wowapi') if token else ''
        headers = {"If-Modified-Since": cache['last_modified']} if cache else None
        async with aiohttp.ClientSession() as session:
            async with session.get(url, headers=headers, params=params) as response:
                if response.status == 200:
                    body = await response.json()
                    return {'body': body, 'last_modified': response.raw_headers[1][1].decode("utf-8"), 'status': response.status}
                elif response.status == 304:
                    return cache
                else:
                    return {'status': response.status}

    @staticmethod
    async def react_message(booking, buyerinfo, reactions, timeout=300, custom_message=None, custom_react=None):
        """Used to get information for the booking author in message or reaction form

        Parameters
        -----------
        booking: :class:`Booking`
            A booking object
        buyerinfo: :class:`str`
            The string the buyer will be sent, 'Please respond with' will be added to the front of the message before sending
        reactions: :class:`list`
            A list of the reactions that will be added to the message
        timeout: :class:`int`
            Time in seconds to wait for a response before raising :class:`RequestFailed` (or :class:`CancelBooking`)
        custom_message: :class:`predicate`
            A custom check for the message response
        custom_react: :class:`predicate`
            A custom check for the reaction response
        """
        local_embed = await booking.author.send(embed=base_embed(f'Please respond with {buyerinfo}'))

        def reaction_check(reaction, user):
            return (str(reaction.emoji) in reactions) and (booking.author.id == user.id) and (reaction.message.id == local_embed.id)

        def message_check(message):
            return message.channel.id == booking.author.dm_channel.id and message.author == booking.author

        for x in reactions:
            await local_embed.add_reaction(x)

        pending_response = [
            commands.Bot.wait_for(booking.client, event='reaction_add', check=custom_react or reaction_check),
            commands.Bot.wait_for(booking.client, event='message', check=custom_message or message_check)
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
        if booking.status == 0:
            await booking.author.send(embed=base_embed(f"Booking ``{booking.id}`` has been cancelled"))
            booking.delete()
            raise exceptions.CancelBooking
        else:
            raise exceptions.RequestFailed("Request timed out")

    @staticmethod
    async def react(booking, reactions, description):
        """Same function as react_message but only works with reaction, also has no timeout"""
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


request = Request()
