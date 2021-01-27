from utils.misc import get_logger
from utils.booking import Booking

from discord.ext import commands

from aiohttp import web
import asyncio

logger = get_logger("PvpSignups")


class AsyncRequestHandler(commands.Cog):

    def __init__(self, client):
        self.client = client
        self.site = None

    async def requesthandler(self):
        async def handler(request):
            return web.Response(body=Booking.json_instances())

        app = web.Application()
        app.router.add_get("/", handler)
        runner = web.AppRunner(app)
        await runner.setup()
        self.site = web.TCPSite(runner, 'localhost', 8080)
        await self.client.wait_until_ready()
        await self.site.start()

    def __unload(self):
        asyncio.ensure_future(self.site.stop())


def setup(client):
    asyncrequesthandler = AsyncRequestHandler(client)
    client.add_cog(asyncrequesthandler)
    client.loop.create_task(asyncrequesthandler.requesthandler())
