import aiohttp
import json
from time import time
from datetime import datetime
from utils import exceptions
from utils.utils import get_logger

logger = get_logger('PvpSignups')


class Request(object):
    def __init__(self, client):
        self.client = client
        self.token_cache = json.load(open("data/token.json", "r"))
        self.fields = {'wowapi': f"https://{self.client.config['wowapi_id']}:{self.client.config['wowapi_secret']}@eu.battle.net/oauth/token"}
    
    def clearcache(self):
        self.token_cache = {}
        json.dump({}, open("data/token.json", "w"))

    async def token(self, field):
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
