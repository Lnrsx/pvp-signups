from utils import pricing
from utils.misc import base_embed, get_logger
from utils.request import request
from utils import exceptions
from utils.config import cfg, icfg, data

from discord.ext import commands
import discord

import string
import uuid
import asyncio
import json
import jsonpickle
import random
import time
import datetime
import itertools

logger = get_logger("PvpSignups")
statuses = ['Compiling', 'Posted', 'Pending (not uploaded)', 'Pending', 'Refund', 'Partial refund', 'Complete', 'Untaken']


# noinspection PyUnresolvedReferences
class Booking(object):
    instances = {instname: [] for instname in icfg.keys()}
    client = None
    untaken_messages = {}
    post_channels = {}
    request_channels = {}
    untaken_channels = {}

    def __init__(self, bracket, author: discord.User, instname):
        if instname not in icfg.keys():
            raise exceptions.UnsupportedInstanceType
        self.__class__.instances[instname].append(self)
        self.instance = instname
        self._author = author
        self.bracket = bracket
        self.status = 0
        self.id = str(uuid.uuid1().int)[:10]
        self.type = None
        self.buyer = Buyer()
        self.price_recommendation = None
        self.ad_price_estimate = None
        self.price = 0
        self.booster = Booster(instname)
        self.notes = None
        self.post_message = None
        self.timestamp = time.time()

    @classmethod
    async def load(cls, client):
        cls.client = client
        for instname, instconfig in icfg.items():
            logger.info(f"----- Begin loading instance {instname}: -----")

            cls.request_channels[instname] = commands.Bot.get_channel(cls.client, instconfig.request_channel)
            if cls.request_channels[instname] is None:
                raise exceptions.ChannelNotFound

            cls.post_channels[instname] = {
                "2v2": commands.Bot.get_channel(cls.client, instconfig.post_2v2),
                "3v3": commands.Bot.get_channel(cls.client, instconfig.post_3v3),
                "glad": commands.Bot.get_channel(cls.client, instconfig.post_glad)
            }
            for channel in cls.post_channels[instname].values():
                if channel is None:
                    raise exceptions.ChannelNotFound

            cls.untaken_channels[instname] = {
                "2v2": commands.Bot.get_channel(cls.client, instconfig.untaken_channels["2v2"]),
                "3v3": commands.Bot.get_channel(cls.client, instconfig.untaken_channels["3v3"])
            }
            for channel in cls.untaken_channels[instname].values():
                if channel is None:
                    raise exceptions.ChannelNotFound

            try:
                await cls.request_channels[instname].fetch_message(instconfig.request_message)
                logger.info("Successfully located request message")
            except discord.NotFound:
                logger.warning("No valid request message was found in the request booking channel, automatically creating...")
                request_message = await cls.request_channels[instname].send(f"React with {cfg.twos_emoji} to create a 2v2 booking or {cfg.threes_emoji} to create a 3v3 booking")
                await request_message.add_reaction(cfg.twos_emoji)
                await request_message.add_reaction(cfg.threes_emoji)
                instconfig.set("request_message", request_message.id)
                instconfig.update()

            cls.untaken_messages[instname] = {}
            for bracket, messages in instconfig.untaken_messages.items():
                cls.untaken_messages[instname][bracket] = []
                for message_id in messages:
                    try:
                        cls.untaken_messages[instname][bracket].append(await cls.untaken_channels[instname][bracket].fetch_message(message_id))
                        logger.info(f"Located untaken boost message ID: {message_id}")
                    except discord.NotFound:
                        instconfig.untaken_messages[bracket].remove(message_id)
                        instconfig.update()
                        logger.info(f"disgarding unlocatable untaken boost message ID: {message_id}")

            cache = json.load(open(f"{instconfig.directory}/bookings.json", "r"))
            for _instance in cache.values():
                instance = jsonpickle.decode(_instance)
                instance.__class__.instances[instname].append(instance)
            logger.info(f"{len(cls.instances[instname])} booking(s) have been loaded from the {instname} cache")
            logger.info(f"----- Finished loading instance: {instname} -----")

    @classmethod
    def get(cls, bookingid):
        for instance in cls.joined_instances():
            if instance.id == bookingid:
                return instance
        raise exceptions.RequestFailed(f"No booking was found with ID ``{bookingid}``")

    @classmethod
    async def update_untaken_boosts(cls, instname):
        if instname not in icfg.keys():
            logger.error(f"Failed to update untaken boosts for: {instname} - no instance found matching that name")
        page_length = 10
        instconfig = icfg[instname]
        logger.info(f"----- Begin updating untaken boosts for {instname} -----")
        embed = base_embed(f"Type ``{cfg.command_prefix}take <ID> <mention teammate if 3v3>`` to claim a boost", title="Untaken boosts")
        untaken_brackets = {
            "2v2": [],
            "3v3": []
            }
        for booking in Booking.instances[instname]:
            if booking.status == 7:
                if booking.bracket == "2v2":
                    untaken_brackets["2v2"].append(booking)
                elif booking.bracket == "3v3":
                    untaken_brackets["3v3"].append(booking)
        for bracket, untaken_boosts in untaken_brackets.items():
            untaken_boosts.sort(key=lambda b_sort: (b_sort.buyer.class_, b_sort.buyer.spec))
            untaken_pages = [untaken_boosts[i:i + page_length] for i in range(0, len(untaken_boosts), page_length)]
            if len(untaken_pages) < len(cls.untaken_messages[instname][bracket]):
                for message in cls.untaken_messages[instname][bracket][len(untaken_pages):]:
                    try:
                        instconfig.untaken_messages[bracket].remove(message.id)
                        instconfig.update()
                        logger.info(f"Deleting unnecessary untaken message: {message.id}")
                        await message.delete()
                        cls.untaken_messages[instname][bracket].remove(message)
                    except ValueError:
                        logger.warning("Tried to delete untaken message that didnt exist")

            for i, page in enumerate(untaken_pages):
                for n, b in enumerate(page):
                    edit_required = False
                    booking_string = f'ID: ``{b.id}``Author: <@{b.authorid}> \n ' \
                                     f'Boost info: ``{b.bracket} {b.type} {b.buyer.rating}`` {b.format_price_estimate()}\n ' \
                                     f'Buyer info: [{b.buyer.name}-{b.buyer.realm}](https://check-pvp.fr/eu/{b.buyer.realm.replace(" ", "%20")}/{b.buyer.name}) ' \
                                     f'{getattr(cfg, b.buyer.faction.lower() + "_emoji")}' \
                                     f'{data.spec_emotes[b.buyer.class_][b.buyer.spec]}\n' \
                                     f'Created: ``{datetime.datetime.utcfromtimestamp(b.timestamp).strftime("%d/%m %H:%M") if b.timestamp else "N/A"}`` \nNotes: ``{b.notes}``'
                    if untaken_boosts[(i * page_length) + n - 1].buyer.spec != b.buyer.spec:
                        embed_title = f"\u200b\n{data.spec_emotes[b.buyer.class_][b.buyer.spec]}__**{b.buyer.spec} {b.buyer.class_} bookings**__"
                    else:
                        embed_title = "\u200b"
                    if not (len(cls.untaken_messages[instname][bracket]) > i and len(cls.untaken_messages[instname][bracket][i].embeds[0].fields) > n):
                        edit_required = True
                    elif booking_string != cls.untaken_messages[instname][bracket][i].embeds[0].fields[n].value \
                            or embed_title != cls.untaken_messages[instname][bracket][i].embeds[0].fields[n].name:
                        edit_required = True
                    embed.add_field(name=embed_title, value=booking_string, inline=False)
                if len(cls.untaken_messages[instname][bracket]) >= i or len(embed.fields) != len(cls.untaken_messages[instname][bracket][i].embeds[0].fields):
                    edit_required = True
                if not embed.fields:
                    embed.add_field(name="\u200b", value="There are currently no untaken boosts", inline=False)
                    break
                if len(cls.untaken_messages[instname][bracket]) > 0 and len(cls.untaken_messages[instname][bracket])-1 >= i:
                    if edit_required:
                        try:
                            await cls.untaken_messages[instname][bracket][i].edit(embed=embed)
                            logger.info(f"Edited untaken message: {cls.untaken_messages[instname][bracket][i].id}")
                        except discord.NotFound:
                            logger.error("Tried to edit a message that was not there")
                    else:
                        logger.info(f"Skipping editing untaken message: {cls.untaken_messages[instname][bracket][i].id}")
                    embed = base_embed("")
                else:
                    new_untaken_page = await cls.untaken_channels[instname][bracket].send(embed=embed)
                    logger.info(f"Created new untaken message {new_untaken_page.id}")
                    embed = base_embed("")
                    cls.untaken_messages[instname][bracket].append(new_untaken_page)
                    instconfig.untaken_messages[bracket].append(new_untaken_page.id)
                    instconfig.update()
        logger.info(f"----- Finished updating untaken boosts for {instname} -----")

    @classmethod
    async def cleanup(cls):
        logger.info("Beginning booking cleanup...")
        ts = time.time()
        for instname, insts in cls.instances.items():
            for i, b in enumerate(insts):
                if (b.timestamp + 172800) < ts:  # 2 days in seconds
                    b.delete()
            # no idea why but it needs to be like this or it only cleans first 2 expired
            await Booking.update_untaken_boosts(instname)
        logger.info("Finished booking cleanup")

    @classmethod
    def joined_instances(cls):
        return list(itertools.chain.from_iterable(cls.instances.values()))

    @classmethod
    def json_instances(cls):
        json_instances = {}
        for b in cls.joined_instances():
            instance = b.__dict__
            if isinstance(instance["buyer"], Buyer):
                instance["buyer"] = instance["buyer"].__dict__
            if isinstance(instance["booster"], Booster):
                instance["booster"] = instance["booster"].__dict__
            if isinstance(instance["post_message"], discord.Message):
                instance["post_message"] = instance["post_message"].id
            json_instances[instance["id"]] = instance
        return json.dumps(json_instances)

    @property
    def author(self) -> discord.User:
        if isinstance(self._author, int):
            author = commands.Bot.get_user(self.client, self._author)
            if not author:
                author = commands.Bot.fetch_user(self.client, self._author)
                if not author:
                    raise exceptions.RequestFailed("The booking author cannot be found from ID, please contact management")
            self._author = author
        return self._author

    @property
    def authorid(self) -> int:
        if isinstance(self._author, discord.User):
            return self._author.id
        return self._author

    @property
    def post_channel(self):
        if self.bracket == "2v2":
            return self.post_channels[self.instance]["2v2"]
        elif self.bracket == "3v3":
            if self.type == "Gladiator":
                return self.post_channels[self.instance]["glad"]
            else:
                return self.post_channels[self.instance]["3v3"]

    async def create(self):
        try:
            await self.compile()
            await self.post()
            await self.pick_winner()
            self.cache()

        except exceptions.CancelBooking:
            pass

    async def compile(self):
        await self._get_boost_type()
        await self._get_name_faction_class()
        await self._get_spec()
        await self._get_rating_range()
        await self._get_price_estimate()
        await self._get_notes()

    async def post(self):
        logger.info(f"Posting {self.bracket} booking: {self.id}")
        embed = discord.Embed(
            title='New {} booking'.format(self.bracket),
            description='**ID:** ``{}``'.format(self.id),
            colour=discord.Colour.purple())
        embed.set_author(name=self.author.display_name, icon_url=self.author.avatar_url)
        embed.add_field(name='Buyer Name', value=f'[{self.buyer.name}-{self.buyer.realm}](https://check-pvp.fr/eu/{string.capwords(self.buyer.realm.replace(" ", "%20"))}/{string.capwords(self.buyer.name)})')
        embed.add_field(name='Boost type', value=f"``{self.type}``")
        embed.add_field(name='Est. booster cut', value=self.format_price_estimate())
        embed.add_field(name='Buyer faction', value=f"{getattr(cfg, self.buyer.faction.lower() + '_emoji')}``{self.buyer.faction}``")
        embed.add_field(name='Boost rating', value=f"``{self.buyer.rating}``")
        embed.add_field(name='Buyer Spec', value=f'{data.spec_emotes[self.buyer.class_][self.buyer.spec]}``{self.buyer.spec} {self.buyer.class_}``')
        embed.add_field(name='Notes', value=f"``{self.notes}``")
        embed.set_footer(text=f"Winner will be picked in {cfg.post_wait_time} seconds")
        if self.buyer.faction == "Horde":
            mention = icfg[self.instance].horde_role
        elif self.buyer.faction == "Alliance":
            mention = icfg[self.instance].alliance_role
        else:
            mention = ''
        self.post_message = await self.post_channel.send(mention, embed=embed)
        await self.author.send(embed=base_embed(
            f'Booking has been sent! booking ID is: ``{self.id}``'))
        await self.post_message.add_reaction(cfg.take_emoji)
        await self.post_message.add_reaction(cfg.schedule_emoji)
        self.status = 1

    async def pick_winner(self):
        if self.status == 1:
            await asyncio.sleep(cfg.post_wait_time)
            await self._recache_message()
            reactions = await [i.users() for i in self.post_message.reactions if str(i.emoji) == cfg.take_emoji][0].flatten()
            reactions = {"users": [str(i.id) for i in reactions if i.bot is False], "time": "now"}
            if not reactions["users"]:
                reactions = await [i.users() for i in self.post_message.reactions if str(i.emoji) == cfg.schedule_emoji][0].flatten()
                reactions = {"users": [str(i.id) for i in reactions if i.bot is False], "time": "schedule"}

                if not reactions["users"]:
                    untaken_message = f'No users signed up to booking ``{self.id}``, it will be moved to {self.untaken_channels[self.instance][self.bracket].mention}, to claim the boost, type: ``!take {self.id}`` '
                    await self.post_message.clear_reactions()
                    if self.bracket == "3v3":
                        untaken_message += '<Mention teammate> '
                    untaken_message += f'in {self.untaken_channels[self.instance][self.bracket].mention}'
                    await self.post_channel.send(embed=base_embed(untaken_message))
                    await self.author.send(embed=base_embed(f'No users signed up to booking ``{self.id}``, it will be moved to the untaken boosts board'))
                    self.status = 7
                    self.post_message = None
                    self.cache()
                    await self.update_untaken_boosts(self.instance)
                    raise exceptions.BookingUntaken
            await self.post_message.clear_reactions()
            weight_file = json.load(open(f'{icfg[self.instance].directory}/userweights.json', 'r'))
            user_weights = weight_file[self.bracket]
            for user in [x for x in reactions["users"] if x not in user_weights.keys()]:
                user_weights[str(user)] = 1

            self.booster.prim = random.choices(
                population=reactions["users"],
                weights=[0.1 if user_weights[x] < 0 else user_weights[x] for x in reactions["users"]])[0]
            mention = ', **please mention your teammate**' \
                      f' within {round(cfg.teammate_pick_timeout / 60)} minutes or the booking will be rerolled' if self.bracket == '3v3' else ''
            pick_message = f"<@{self.booster.prim}> was picked for {self.author.display_name}'s " \
                           f"``{self.bracket} {self.type} {self.buyer.rating}`` boost ({reactions['time']}){mention}"
            await self.post_channel.send(pick_message)
        else:
            return False

        if self.bracket == '3v3' and self.booster.prim:
            def mention_check(message) -> bool:
                return message.author == winner_user and message.mentions

            winner_user = commands.Bot.get_user(self.client, int(self.booster.prim))
            try:
                winner_message = await commands.Bot.wait_for(self.client, event='message', check=mention_check, timeout=cfg.teammate_pick_timeout)

            except asyncio.TimeoutError:
                embed = self.post_message.embeds[0]
                embed.title = f"Rerolled {self.bracket} Bookings"
                self.post_message = await self.post_channel.send(embed=embed)
                await self.post_message.add_reaction(cfg.take_emoji)
                await self.post_message.add_reaction(cfg.schedule_emoji)
                return await self.pick_winner()

            self.booster.sec, self.booster.prim_cut, self.booster.sec_cut = winner_message.mentions[0].id, self.booster.prim_cut // 2, self.booster.prim_cut // 2
            if self.type == "Gladiator":
                post_channel = self.post_channel_glad
            else:
                post_channel = self.post_channel_3v3
            await post_channel.send(embed=base_embed(f"<@{self.booster.sec}> has been picked as {winner_user.mention}'s teammate"))

        self.post_message = self.post_message.id
        if self.booster.prim_cut > 100000:
            for key in user_weights.keys():
                if key == self.booster.prim:
                    user_weights[key] = round(user_weights[key] - (self.booster.prim_cut * cfg.bad_luck_protection_mofifier), 5)

                else:
                    user_weights[key] = round(user_weights[key] + (self.booster.prim_cut * cfg.bad_luck_protection_mofifier), 5)
        weight_file[self.bracket] = user_weights
        json.dump(weight_file, open(f'{icfg[self.instance].directory}/userweights.json', 'w'), indent=4)
        self.status = 2

    def cache(self):
        with open(icfg[self.instance].directory+"/bookings.json", "r") as f:
            jsondata = json.load(f)
        temp_author = self._author
        if isinstance(self._author, discord.User):
            self._author = self._author.id
        jsondata[str(self.id)] = jsonpickle.encode(self)
        json.dump(jsondata, open(icfg[self.instance].directory+"/bookings.json", "w"), indent=4)
        self._author = temp_author

    def delete(self):
        if self.status not in range(2):
            jsondata = json.load(open(f"{icfg[self.instance].directory}/bookings.json", "r"))
            if self.id not in jsondata.keys():
                logger.warning("Tried to delete bookings not in cache")
            else:
                del jsondata[self.id]
                with open(icfg[self.instance].directory+"/bookings.json", "w") as f:
                    json.dump(jsondata, f, indent=4)
        for i, obj in enumerate(self.instances[self.instance]):
            if obj.id == self.id:
                del self.instances[self.instance][i]
        logger.info(f"Booking {self.id} has been deleted")

    async def _get_boost_type(self):
        def boost_type_check(user_input):
            return user_input in data.boost_types or user_input in data.bracket_boost_types[self.bracket]
        fields = '\n'.join(data.boost_types + data.bracket_boost_types[self.bracket])
        self.type = await request.react_message(
            self, f"the **boost type**, accepted respones:\n"
            f" {fields}\nor react with ❌ to cancel the booking", '❌', message_predicate=boost_type_check)

    async def _get_name_faction_class(self):
        buyer_name = await request.react_message(
            self, '**buyers character name** (e.g. Mystikdruldk)'
                  '\nor react with ❌ to cancel the booking', '❌')
        buyer_realm = await request.react_message(
            self, '**buyers realm** (e.g. Ravencrest) \n**if realm name is multiple words you can use spaces**'
            '\nor react with ❌ to cancel the booking', '❌')
        self.buyer.name = buyer_name.lower()
        self.buyer.realm = buyer_realm.lower()
        if cfg.auto_faction_class_input:
            response = await request.get(
                f'https://eu.api.blizzard.com/profile/wow/character/{self.buyer.realm.replace(" ", "-")}/{self.buyer.name}?namespace=profile-eu&locale=en_GB', token=True)
            if response['status'] == 200:
                self.buyer.faction, self.buyer.class_ = response['body']['faction']['name'], response['body']['character_class']['name'].capitalize()
                self.buyer.name = buyer_name
                self.buyer.realm = buyer_realm

            elif response['status'] == 404:
                character_not_found_response = await request.react(
                    self, [cfg.choose_faction_emoji, '🔁'],
                    "**No character was found with that name-realm**,"
                    " you can either input the buyers faction and class manually "
                    f"{cfg.choose_faction_emoji}, "
                    "re-enter the name (🔁), or cancel the booking (❌).")

                if str(character_not_found_response) == cfg.choose_faction_emoji:
                    faction_response = await request.react(
                        self, [cfg.horde_emoji, cfg.alliance_emoji],
                        'React with the **buyers faction**\n'
                        'or react with ❌ to cancel the booking')
                    self.buyer.faction = faction_response.name
                    await self.manual_class_input()

                if str(character_not_found_response) == '🔁':
                    await self._get_name_faction_class()

            else:
                await self.author.send(embed=base_embed(
                    "**Unexpected error occoured trying to find a player with that name-realm**,"
                    " you can either input the buyers faction and class manually "
                    f"{cfg.choose_faction_emoji}, or cancel the booking (❌)."))
                self.buyer.faction = await request.react(
                    self, [cfg.horde_emoji, cfg.alliance_emoji],
                    'React with the **buyers faction**\n'
                    'or react with ❌ to cancel the booking')
                await self.manual_class_input()
        else:
            self.buyer.faction = await request.react(
                self, [cfg.horde_emoji, cfg.alliance_emoji],
                'React with the **buyers faction**\n'
                'or react with ❌ to cancel the booking')
            await self.manual_class_input()

    async def manual_class_input(self):
        def class_input_check(user_input):
            return user_input in data.specs_abbreviations.keys() or user_input in data.class_abbreviations.keys()
        fields = '\n'.join(data.class_emotes)
        self.buyer.class_ = await request.react_message(
            self, f'the **buyers class**, accepted responses:\n {fields}\n'
            'or react with ❌ to cancel the booking', '❌', message_predicate=class_input_check)
        if buyer_class in data.class_abbreviations.keys():
            self.buyer.class_ = data.class_abbreviations[buyer_class]

    async def _get_spec(self):
        if not self.buyer.class_:
            raise exceptions.RequestFailed("Cannot get spec when class is not known")

        def spec_input_check(user_input):
            return user_input in data.spec_emotes[self.buyer.class_].keys() or user_input in list(data.specs_abbreviations[self.buyer.class_].keys())
        accepted_inputs_string = ''
        for i in data.spec_emotes[self.buyer.class_].keys():
            accepted_inputs_string += data.spec_emotes[self.buyer.class_][i] + i + '\n'
        self.buyer.spec = await request.react_message(
            self, f'the **buyers spec**,'
            f' accepted respones:\n {accepted_inputs_string}', '❌', message_predicate=spec_input_check)
        if self.buyer.spec in list(data.specs_abbreviations[self.buyer.class_].keys()):
            self.buyer.spec = data.specs_abbreviations[self.buyer.class_][buyer_spec]

    async def _get_rating_range(self):
        if not self.type:
            raise exceptions.RequestFailed("Cannot get rating range when boost type is not known")

        def rating_format_check(user_input, booking):
            return (booking.type == 'Set rating' and not [x for x in user_input.split('-') if not x.isnumeric() or int(x) not in range(0, 2401)]
                    and len(user_input.split('-')) == 2 and int(user_input.split("-")[0]) < int(user_input.split("-")[1])) \
                    or (booking.type != "Set rating" and user_input.isnumeric() and int(user_input) in range(0, 3501))
        boost_rating_format_string = 'the **buyers start-desired rating**, (e.g. 1049-1800)' if self.type == 'Set rating' else 'the **buyers current rating (e.g. 1687)'
        self.buyer.rating = await request.react_message(
            self, boost_rating_format_string
            + '\n or react with ❌ to cancel the booking**', '❌', message_predicate_binfo=rating_format_check)

        if self.type == 'Set rating':
            start_rating, end_rating = [int(i) for i in self.buyer.rating.split("-")]
            self.price_recommendation = pricing.set_rating(self.instance, self.bracket, start_rating, end_rating)
        elif self.type == '1 win':
            self.buyer.rating = int(self.buyer.rating)
            self.price_recommendation = pricing.one_win(self.instance, self.bracket, self.buyer.rating)
        elif self.type == 'Gladiator':
            self.price_recommendation = 'See glad pricing'
        elif self.type == 'Hourly':
            self.price_recommendation = pricing.hourly(self.instance, self.bracket)

    async def _get_price_estimate(self):
        def price_estimate_check(user_input):
            user_input = user_input.replace(",", "").replace(".", "")
            return user_input.isnumeric() and int(user_input) > 0
        recommendation = f"{self.price_recommendation:,}" if self.type != "Gladiator" else "See glad pricing"
        self.ad_price_estimate = await request.react_message(
            self, f"the **estimated price of the boost**, \n recommended price: **{recommendation}**\nThis is not the final price, just what is shown when the booking is posted",
            '❌', message_predicate=price_estimate_check)
        self.ad_price_estimate = int(self.ad_price_estimate.replace(",", "").replace(".", ""))

    async def _get_notes(self):
        self.notes = await request.react_message(
            self, '**any additional notes** about the buyer, react with ⏩ to skip\n'
            'or react with ❌ to cancel the booking', ['⏩', '❌'])
        self.notes = 'N/A' if self.notes == '⏩' else self.notes

    def format_price_estimate(self, modifier=None):
        modifier = icfg[self.instance].booster_cut if not modifier else modifier
        if self.type == "Gladiator":
            return "``See glad pricing``"
        else:
            if not self.ad_price_estimate:
                self.ad_price_estimate = 0
            boost_cut_recommendation = self.ad_price_estimate * modifier
            price_estimate_string = f"{round(boost_cut_recommendation):,}g"
            if self.type == 'Hourly':
                price_estimate_string += "/hr"
            return f"``{price_estimate_string}``"

    async def _recache_message(self):
        if self.status == 1:
            self.post_message = await self.post_channel.fetch_message(self.post_message.id)

    async def _status_update(self):
        await self.author.send(embed=base_embed(f"Booking ``{self.id}`` has been set to ``{statuses[self.status]}``"))

    def authorized(self, user_id):
        if self.authorid != user_id:
            raise exceptions.RequestFailed("You are not authorized to do that")


class Buyer(object):
    def __init__(self):
        self.name = None
        self.realm = None
        self.faction = None
        self.class_ = None
        self.spec = None
        self.rating = None

    def __repr__(self):
        return f"Name={self.name}-{self.realm} Faction={self.faction} Spec={self.spec} {self.class_} Rating={self.rating}"


class Booster(object):
    def __init__(self, instname):
        self.instname = instname
        self.prim = None
        self.sec = None
        self.prim_cut = 0
        self.sec_cut = 0
        self.ad_cut = 0
        self.mana_cut = 0

    def update_price(self, new_price: int):
        if not self.sec:
            self.prim_cut = new_price // icfg[self.instname].booster_cut
        else:
            self.prim_cut = new_price // (icfg[self.instname].booster_cut / 2)
            self.sec_cut = new_price // (icfg[self.instname].booster_cut / 2)
        self.ad_cut = new_price // icfg[self.instname].advertiser_cut
        self.mana_cut = new_price // icfg[self.instname].management_cut
