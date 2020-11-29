import aiohttp
import json
from time import time
from datetime import datetime
from utils import exceptions
from utils.misc import get_logger
from utils.config import cfg

logger = get_logger('PvpSignups')


class Request(object):
    """Asynchronous handler for HTTP requests

    Attributes
    -----------
    client: :class:`PvpSignups`
        The client of the bot.
    token_cache: :class:`dict`
        The cache for access tokens, before any access token request the cache is checked to see
        if the last token retrieved is still valid and that one is used instead.
    fields: :class:`dict`
        A dictionary containing all of the URLs for any server that access tokens need to be gotten from,
         currently only being used for the blizzard api server.
    """
    def __init__(self, client):
        self.client = client
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
