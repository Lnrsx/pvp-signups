from utils import pricing
from utils.misc import base_embed, get_logger
from utils.request import request
from utils import exceptions
from utils.config import cfg

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

logger = get_logger("PvpSignups")
statuses = ['Compiling', 'Posted', 'Pending (not uploaded)', 'Pending', 'Refund', 'Partial refund', 'Complete', 'Untaken']


# noinspection PyUnresolvedReferences
class Booking(object):
    """Represents a PvP Booking.

    Attributes
    -----------
    author: :class:`discord.User`
        The author of the booking.
    authorid: :class:`int`
        The user ID of the author of the booking.
    bracket: :class:`str`
        The bracket of the boost. Can be '2v2' or '3v3'
    status: :class:`int`
        Current status of the booking between 0 and 6
    id: :class:`int`
        A 10 digit unique ID of the booking.
    type: Optional[:class:`str`]
        The type of the boost. Can be 'Hourly', '1 win', 'Set rating' or 'Gladiator. Could be None.
    buyer: :class:`Buyer`
        A `Buyer` class containing information about the buyer
    price_recommendation: Optional[:class:`str`]
        The recommended price of the boost generated by utils.pricing
    price: Optional[:class:`int`]
        The real price of the boost specified by the author of the booking. Could be None.
    booster: :class:`Booster`
        A `Booster` class containing information on the boosters and the gold cuts of all members involved
    payment_hash: Optional[:class:`str`]
        The hashed return string from the mail addon
    gold_realms: Optional[:class:`str`]
        A string of comma seperated realm names that the payment for the booking was collect on. Could be None.
    notes: Optional[:class:`str`]
        Additional notes provided by the advertiser about the booking. Could be None.
    post_message: Optional[:class:`discord.Message`]
        The message that was posted about the booking in the designated post_bookings channel. Could be None.
    """
    instances = []
    untaken_messages = {"2v2": [], "3v3": []}
    client = None
    post_channel_2v2 = None
    post_channel_3v3 = None
    post_channel_glad = None
    request_channel = None
    untaken_channel = {"2v2": None, "3v3": None}

    def __init__(self, bracket, author: discord.User):
        self.__class__.instances.append(self)
        self._author = author
        self.bracket = bracket
        self.status = 0
        self.id = str(uuid.uuid1().int)[:10]
        self.type = None
        self.buyer = Buyer()
        self.price_recommendation = None
        self.ad_price_estimate = None
        self.price = 0
        self.booster = Booster()
        self.notes = None
        self.post_message = None
        self.timestamp = time.time()

    @classmethod
    async def load(cls, client):
        """Gets the channels responsible for creating / posting bookings and loads the booking cache from data/sylvanas/bookings.json.
        This function must be called on bot startup.

        Parameters
        -----------
        client: 'discord.commands.Bot`
            The client that is running the bot.

        Raises
        -------
        ChannelNorFound
            Booking and Post channels could not be found from given ID
        """
        cls.client = client
        if cls.request_channel is None:
            cls.request_channel = commands.Bot.get_channel(cls.client, cfg.settings["request_booking_channel_id"])
        if cls.post_channel_2v2 is None:
            cls.post_channel_2v2 = commands.Bot.get_channel(cls.client, cfg.settings["post_booking_2v2_channel_id"])
        if cls.post_channel_3v3 is None:
            cls.post_channel_3v3 = commands.Bot.get_channel(cls.client, cfg.settings["post_booking_3v3_channel_id"])
        if cls.post_channel_glad is None:
            cls.post_channel_glad = commands.Bot.get_channel(cls.client, cfg.settings["post_booking_glad_channel_id"])
        if cls.untaken_channel["2v2"] is None:
            cls.untaken_channel["2v2"] = commands.Bot.get_channel(cls.client, cfg.settings["untaken_boosts_channel_id_2v2"])
        if cls.untaken_channel["3v3"] is None:
            cls.untaken_channel["3v3"] = commands.Bot.get_channel(cls.client, cfg.settings["untaken_boosts_channel_id_3v3"])
        if not cls.request_channel or not cls.post_channel_2v2 or not cls.post_channel_3v3 or not cls.post_channel_glad or not cls.untaken_channel["2v2"] or not cls.untaken_channel["3v3"]:
            raise exceptions.ChannelNotFound
        try:
            await cls.request_channel.fetch_message(cfg.settings["request_booking_message_id"])
            logger.info("Successfully located request channel")
        except discord.NotFound:
            raise exceptions.MessageNotFound("request_message")
        for bracket, messages in zip(["2v2", "3v3"], [cls.untaken_messages["2v2"], cls.untaken_messages["3v3"]]):
            for message_id in cfg.settings["untaken_boosts_message_id_"+bracket]:
                try:
                    messages.append(await cls.untaken_channel[bracket].fetch_message(message_id))
                    logger.info(f"Located untaken boost message ID: {message_id}")
                except discord.NotFound:
                    cfg.settings["untaken_boosts_message_id_"+bracket].remove(message_id)
                    cfg.set("untaken_boosts_message_id_"+bracket, cfg.settings["untaken_boosts_message_id_"+bracket])
                    logger.info(f"disgarding unlocatable untaken boost message ID: {message_id}")
        with open("data/sylvanas/bookings.json", "r") as f:
            cache = json.load(f)
            for _instance in cache.values():
                instance = jsonpickle.decode(_instance)
                instance.__class__.instances.append(instance)
            logger.info(f"{len(cls.instances)} booking(s) have been loaded from the cache")

    @classmethod
    def get(cls, bookingid):
        """Optional `Booking`]: Returns the booking instance from ID if it exists, ``None`` otherwise.

        Parameters
        -----------
        bookingid: `int`
            The ID of the booking being retrieved.

        .. note::
        Bookings that have been completed/refunded are not stored in the interal instance cache.
        """
        for instance in cls.instances:
            if instance.id == bookingid:
                return instance
        raise exceptions.RequestFailed(f"No booking was found with ID ``{bookingid}``")

    @classmethod
    async def update_untaken_boosts(cls):
        embed = base_embed(f"Type ``{cfg.settings['command_prefix']}take <ID> <mention teammate if 3v3>`` to claim a boost", title="Untaken boosts")
        page_length = 10
        untaken_boosts_2v2 = [b for b in Booking.instances if b.status == 7 and b.bracket == "2v2"]
        untaken_boosts_3v3 = [b for b in Booking.instances if b.status == 7 and b.bracket == "3v3"]
        for bracket, untaken_boosts in zip(["2v2", "3v3"], [untaken_boosts_2v2, untaken_boosts_3v3]):
            untaken_boosts.sort(key=lambda b: (b.buyer.class_, b.buyer.spec))
            untaken_bookings_pages = [untaken_boosts[i:i + page_length] for i in range(0, len(untaken_boosts), page_length)]
            if len(untaken_bookings_pages) < len(cls.untaken_messages[bracket]):
                for message in cls.untaken_messages[bracket][len(untaken_bookings_pages):]:
                    try:
                        cfg.settings["untaken_boosts_message_id_"+bracket].remove(message.id)
                        cfg.update("untaken_boosts_message_id_"+bracket)
                        logger.info(f"Deleting unnecessary untaken message: {message.id}")
                        await message.delete()
                        del message
                    except ValueError:
                        logger.warning("Tried to delete untaken message that didnt exist")

            for i, page in enumerate(untaken_bookings_pages):
                for n, b in enumerate(page):
                    edit_required = False
                    booking_string = f'ID: ``{b.id}``Author: <@{b.authorid}> \n ' \
                                     f'Boost info: ``{b.bracket} {b.type} {b.buyer.rating}`` {b.format_price_estimate()}\n ' \
                                     f'Buyer info: [{b.buyer.name}-{b.buyer.realm}](https://check-pvp.fr/eu/{b.buyer.realm.replace(" ", "%20")}/{b.buyer.name}) ' \
                                     f'{cfg.settings[b.buyer.faction.lower() + "_emoji"]}' \
                                     f'{cfg.data["spec_emotes"][b.buyer.class_][b.buyer.spec]}\n' \
                                     f'Created: ``{datetime.datetime.utcfromtimestamp(b.timestamp).strftime("%d/%m %H:%M") if b.timestamp else "N/A"}`` \nNotes: ``{b.notes}``'
                    if untaken_boosts[(i * page_length) + n - 1].buyer.spec != b.buyer.spec:
                        embed_title = f"\u200b\n{cfg.data['spec_emotes'][b.buyer.class_][b.buyer.spec]}__**{b.buyer.spec} {b.buyer.class_} bookings**__"
                    else:
                        embed_title = "\u200b"
                    if not (len(cls.untaken_messages[bracket]) > i and len(cls.untaken_messages[bracket][i].embeds[0].fields) > n):
                        edit_required = True
                    elif booking_string != cls.untaken_messages[bracket][i].embeds[0].fields[n].value \
                            or embed_title != cls.untaken_messages[bracket][i].embeds[0].fields[n].name:
                        edit_required = True
                    embed.add_field(name=embed_title, value=booking_string, inline=False)
                if len(cls.untaken_messages[bracket]) >= i or len(embed.fields) != len(cls.untaken_messages[bracket][i].embeds[0].fields):
                    edit_required = True
                if not embed.fields:
                    embed.add_field(name="\u200b", value="There are currently no untaken boosts", inline=False)
                    break
                if len(cls.untaken_messages[bracket]) > 0 and len(cls.untaken_messages[bracket])-1 >= i:
                    if edit_required:
                        try:
                            await cls.untaken_messages[bracket][i].edit(embed=embed)
                            logger.info(f"Edited untaken message: {cls.untaken_messages[bracket][i].id}")
                        except discord.NotFound:
                            logger.error("Tried to edit a message that was not there")
                    else:
                        logger.info(f"Skipping editing untaken message: {cls.untaken_messages[bracket][i].id}")
                    embed = base_embed("")
                else:
                    new_untaken_page = await cls.untaken_channel[bracket].send(embed=embed)
                    logger.info(f"Created new untaken message {new_untaken_page.id}")
                    embed = base_embed("")
                    cls.untaken_messages[bracket].append(new_untaken_page)
                    cfg.settings["untaken_boosts_message_id_"+bracket].append(new_untaken_page.id)
                    cfg.update("untaken_boosts_message_id_"+bracket)

    @classmethod
    async def cleanup(cls):
        logger.info("Beginning booking cleanup...")
        ts = time.time()
        expired = []
        for i, b in enumerate(cls.instances):
            if (b.timestamp + 172800) < ts:  # 2 days in seconds
                if isinstance(b.post_message, int):
                    await b.author.send(
                        embed=base_embed(f"Your booking with ID ``{b.id}`` for ``{b.buyer.name}-{b.buyer.realm} "
                                         f""f"{b.bracket} {b.type} {b.buyer.rating}`` has expired from the expired bookings board, "
                                         f"if the buyer still wants a boost, **DM me** ``!rebook {b.post_message}``"))
                expired.append(b)
        # no idea why but it needs to be like this or it only cleans first 2 expired
        [b.delete() for b in expired]
        await Booking.update_untaken_boosts()
        logger.info("Finished booking cleanup")

    @property
    def author(self) -> discord.User:
        """ `discord.User`: Gets the owner of the booking instance."""
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
        """ `int`: Gets the user ID of the booking."""
        if isinstance(self._author, discord.User):
            return self._author.id
        return self._author

    @property
    def post_channel(self):
        if self.bracket == "2v2":
            return self.post_channel_2v2
        elif self.bracket == "3v3":
            if self.type == "Gladiator":
                return self.post_channel_glad
            else:
                return self.post_channel_3v3

    async def create(self):
        try:
            await self.compile()
            await self.post()
            await self.pick_winner()
            self.cache()

        except exceptions.CancelBooking:
            pass

    async def compile(self):
        """DMs the booking instance author questions about the booking they are creating,
        functions recursively call themselves until a valid input is given.
        """
        await self._get_boost_type()
        await self._get_name_faction_class()
        await self._get_spec()
        await self._get_rating_range()
        await self._get_price_estimate()
        await self._get_notes()

    async def post(self):
        """ `discord.Embed`: Posts the compiled booking in the post bookings channel."""
        logger.info(f"Posting {self.bracket} booking: {self.id}")
        embed = discord.Embed(
            title='New {} booking'.format(self.bracket),
            description='**ID:** ``{}``'.format(self.id),
            colour=discord.Colour.purple())
        embed.set_author(name=self.author.display_name, icon_url=self.author.avatar_url)
        embed.add_field(name='Buyer Name', value=f'[{self.buyer.name}-{self.buyer.realm}](https://check-pvp.fr/eu/{string.capwords(self.buyer.realm.replace(" ", "%20"))}/{string.capwords(self.buyer.name)})')
        embed.add_field(name='Boost type', value=f"``{self.type}``")
        embed.add_field(name='Est. booster cut', value=self.format_price_estimate())
        embed.add_field(name='Buyer faction', value=f"{cfg.settings[self.buyer.faction.lower() + '_emoji']}``{self.buyer.faction}``")
        embed.add_field(name='Boost rating', value=f"``{self.buyer.rating}``")
        embed.add_field(name='Buyer Spec', value=f'{cfg.data["spec_emotes"][self.buyer.class_][self.buyer.spec]}``{self.buyer.spec} {self.buyer.class_}``')
        embed.add_field(name='Notes', value=f"``{self.notes}``")
        embed.set_footer(text=f"Winner will be picked in {cfg.settings['post_wait_time']} seconds")
        if self.buyer.faction == "Horde":
            mention = cfg.settings["horde_role"]
        elif self.buyer.faction == "Alliance":
            mention = cfg.settings["alliance_role"]
        else:
            mention = ''
        self.post_message = await self.post_channel.send(mention, embed=embed)
        await self.author.send(embed=base_embed(
            f'Booking has been sent! booking ID is: ``{self.id}``'))
        await self.post_message.add_reaction(cfg.settings["take_emoji"])
        await self.post_message.add_reaction(cfg.settings["schedule_emoji"])
        self.status = 1

    async def pick_winner(self):
        """Chooses the booster of the booking based on who reacted to the message, users who react with `now` will always be prioritized.
        In 3v3 boosts, the winner will be chosen and will have to mention their teammate,
        if they fail to do so before the configured timout, the booking will re rerolled.

        Raises
        -------
        CancelBooking
            No users signed up to the booking.
        """

        if self.status == 1:
            await asyncio.sleep(cfg.settings["post_wait_time"])
            await self._recache_message()
            reactions = await [i.users() for i in self.post_message.reactions if str(i.emoji) == cfg.settings["take_emoji"]][0].flatten()
            reactions = {"users": [str(i.id) for i in reactions if i.bot is False], "time": "now"}
            if not reactions["users"]:
                reactions = await [i.users() for i in self.post_message.reactions if str(i.emoji) == cfg.settings["schedule_emoji"]][0].flatten()
                reactions = {"users": [str(i.id) for i in reactions if i.bot is False], "time": "schedule"}

                if not reactions["users"]:
                    untaken_message = f'No users signed up to booking ``{self.id}``, it will be moved to {self.untaken_channel[self.bracket].mention}, to claim the boost, type: ``!take {self.id}`` '
                    await self.post_message.clear_reactions()
                    if self.bracket == "3v3":
                        untaken_message += '<Mention teammate> '
                    untaken_message += f'in {self.untaken_channel[self.bracket].mention}'
                    await self.post_channel.send(embed=base_embed(untaken_message))
                    await self.author.send(embed=base_embed(f'No users signed up to booking ``{self.id}``, it will be moved to the untaken boosts board'))
                    self.status = 7
                    self.post_message = None
                    self.cache()
                    await self.update_untaken_boosts()
                    raise exceptions.BookingUntaken
            await self.post_message.clear_reactions()
            weight_file = json.load(open(f'data/sylvanas/userweights.json', 'r'))
            user_weights = weight_file[self.bracket]
            for user in [x for x in reactions["users"] if x not in user_weights.keys()]:
                user_weights[str(user)] = 1

            self.booster.prim = random.choices(
                population=reactions["users"],
                weights=[0.1 if user_weights[x] < 0 else user_weights[x] for x in reactions["users"]])[0]
            mention = ', **please mention your teammate**' \
                      f' within {round(cfg.settings["teammate_pick_timeout"] / 60)} minutes or the booking will be rerolled' if self.bracket == '3v3' else ''
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
                winner_message = await commands.Bot.wait_for(self.client, event='message', check=mention_check, timeout=cfg.settings["teammate_pick_timeout"])

            except asyncio.TimeoutError:
                embed = self.post_message.embeds[0]
                embed.title = f"Rerolled {self.bracket} Bookings"
                self.post_message = await self.post_channel.send(embed=embed)
                await self.post_message.add_reaction(cfg.settings["take_emoji"])
                await self.post_message.add_reaction(cfg.settings["schedule_emoji"])
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
                    user_weights[key] = round(user_weights[key] - (self.booster.prim_cut * cfg.settings["bad_luck_protection_mofifier"]), 5)

                else:
                    user_weights[key] = round(user_weights[key] + (self.booster.prim_cut * cfg.settings["bad_luck_protection_mofifier"]), 5)
        weight_file[self.bracket] = user_weights
        json.dump(weight_file, open(f'data/sylvanas/userweights.json', 'w'), indent=4)
        self.status = 2

    async def refund(self, full=True):
        """Either partially or fully refunds a booking and updating the sheet version with the new infomation

        .. note::
        Only `Set rating` boosts can be partially refunded
        """
        if full:
            self.status = 4
        else:
            try:
                assert self.type == 'Set rating', "Only set rating boosts can be partially refunded"
                self.price = await self.refund_price()
                assert await self.get_payment_hash(), "Request timed out"
            except AssertionError as e:
                raise exceptions.RequestFailed(str(e))
            self.booster.update_price(self.price)
        self.cache()
        await self._status_update()
        self.delete()

    async def complete(self):
        """Flags a booking as completed, once this happens it is deleted from the cache"""
        try:
            assert self.status == 3, "Booking status must be pending to complete"
            assert await self.get_payment_hash(), "Request timed out"
            assert await self._get_price(), "Request timed out"
            self.status = 6
            await self._status_update()
            self.delete()
        except AssertionError as e:
            raise exceptions.RequestFailed(str(e))

    def cache(self):
        """Saves a booking instance to the cache file at data/sylvanas/bookings.json.

        .. note::
        All attributes of the booking that are classes are converted to `int` in ID form
         """
        with open("data/sylvanas/bookings.json", "r") as f:
            data = json.load(f)
        temp_author = self._author
        if isinstance(self._author, discord.User):
            self._author = self._author.id
        data[str(self.id)] = jsonpickle.encode(self)
        json.dump(data, open("data/sylvanas/bookings.json", "w"), indent=4)
        self._author = temp_author

    def delete(self):
        """Deletes the booking from the interal instance cache and the external file at data/sylvanas/bookings.json"""
        if self.status not in range(2):
            data = json.load(open("data/sylvanas/bookings.json", "r"))
            if self.id not in data.keys():
                logger.warning("Tried to delete bookings not in cache")
            else:
                del data[self.id]
                with open("data/sylvanas/bookings.json", "w") as f:
                    json.dump(data, f, indent=4)
        for i, obj in enumerate(self.instances):
            if obj.id == self.id:
                del self.instances[i]
        logger.info(f"Booking {self.id} has been deleted")

    async def _get_boost_type(self, force=False):
        if not force and self.type:
            return
        fields = '\n'.join(cfg.data['boost_types'] + cfg.data['bracket_boost_types'][self.bracket])
        boost_type = await request.react_message(
            self, f"the **boost type**, accepted respones:\n"
            f" {fields}\nor react with ❌ to cancel the booking", '❌')
        if boost_type in cfg.data['boost_types']:
            self.type = boost_type
        elif boost_type in cfg.data['bracket_boost_types'][self.bracket]:
            self.type = boost_type
        else:
            await self.author.send('Boost type not recognised, please try again.')
            await self._get_boost_type()

    async def _get_name_faction_class(self, force=False):
        if not force and self.buyer.name and self.buyer.realm and self.buyer.faction and self.buyer.class_:
            return
        buyer_name = await request.react_message(
            self, '**buyers character name** (e.g. Mystikdruldk)'
                  '\nor react with ❌ to cancel the booking', '❌')
        buyer_realm = await request.react_message(
            self, '**buyers realm** (e.g. Ravencrest) \n**if realm name is multiple words you can use spaces**'
            '\nor react with ❌ to cancel the booking', '❌')
        self.buyer.name = buyer_name.lower()
        self.buyer.realm = buyer_realm.lower()
        if cfg.settings["auto_faction_class_input"]:
            response = await request.get(
                f'https://eu.api.blizzard.com/profile/wow/character/{self.buyer.realm.replace(" ", "-")}/{self.buyer.name}?namespace=profile-eu&locale=en_GB', token=True)
            if response['status'] == 200:
                self.buyer.faction, self.buyer.class_ = response['body']['faction']['name'], response['body']['character_class']['name'].capitalize()
                self.buyer.name = buyer_name
                self.buyer.realm = buyer_realm

            elif response['status'] == 404:
                character_not_found_response = await request.react(
                    self, [cfg.settings['choose_faction_emoji'], '🔁'],
                    "**No character was found with that name-realm**,"
                    " you can either input the buyers faction and class manually "
                    f"{cfg.settings['choose_faction_emoji']}, "
                    "re-enter the name (🔁), or cancel the booking (❌).")

                if str(character_not_found_response) == cfg.settings["choose_faction_emoji"]:
                    faction_response = await request.react(
                        self, [cfg.settings["horde_emoji"], cfg.settings["alliance_emoji"]],
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
                    f"{cfg.settings['choose_faction_emoji']}, or cancel the booking (❌)."))
                self.buyer.faction = await request.react(
                    self, [cfg.settings["horde_emoji"], cfg.settings["alliance_emoji"]],
                    'React with the **buyers faction**\n'
                    'or react with ❌ to cancel the booking')
                await self.manual_class_input()
        else:
            self.buyer.faction = await request.react(
                self, [cfg.settings["horde_emoji"], cfg.settings["alliance_emoji"]],
                'React with the **buyers faction**\n'
                'or react with ❌ to cancel the booking')
            await self.manual_class_input()

    async def manual_class_input(self, force=False):
        if not force and self.buyer.class_:
            return
        fields = '\n'.join(cfg.data['class_emotes'])
        buyer_class = await request.react_message(
            self, f'the **buyers class**, accepted responses:\n {fields}\n'
            'or react with ❌ to cancel the booking', '❌')
        if buyer_class in cfg.data['specs_abbreviations'].keys():
            self.buyer.class_ = buyer_class
        else:
            if buyer_class in cfg.data['class_abbreviations'].keys():
                self.buyer.class_ = cfg.data['class_abbreviations'][buyer_class]
            else:
                await self.author.send('Class not recognised, please try again.')
                await self.manual_class_input()

    async def _get_spec(self, force=False):
        if not force and self.buyer.spec:
            return
        if not self.buyer.class_:
            raise exceptions.RequestFailed("Cannot get spec when class is not known")
        accepted_inputs_string = ''
        for i in cfg.data['spec_emotes'][self.buyer.class_].keys():
            accepted_inputs_string += cfg.data['spec_emotes'][self.buyer.class_][i] + i + '\n'
        buyer_spec = await request.react_message(
            self, f'the **buyers spec**,'
            f' accepted respones:\n {accepted_inputs_string}', '❌')

        if buyer_spec not in cfg.data['spec_emotes'][self.buyer.class_].keys() and buyer_spec not in list(cfg.data['specs_abbreviations'][self.buyer.class_].keys()):
            await self.author.send('Spec not recognised, please try again.')
            await self._get_spec()

        else:
            # translates spec abbreivation to proper class name if it is used
            if buyer_spec in list(cfg.data['specs_abbreviations'][self.buyer.class_].keys()):
                buyer_spec = cfg.data['specs_abbreviations'][self.buyer.class_][buyer_spec]

            self.buyer.spec = buyer_spec

    async def _get_rating_range(self, force=False):
        if not force and self.buyer.rating and self.price_recommendation:
            return
        if not self.type:
            raise exceptions.RequestFailed("Cannot get rating range when boost type is not known")
        if self.type == 'Set rating':
            boost_rating_format_string = 'the **buyers start-desired rating**, (e.g. 1049-1800)'

        else:
            boost_rating_format_string = 'the **buyers current rating (e.g. 1687)'

        boost_rating = await request.react_message(
            self, boost_rating_format_string
            + '\nor react with ❌ to cancel the booking**', '❌')

        if self.type == 'Set rating'\
                and not [x for x in boost_rating.split('-') if not x.isnumeric() or int(x) not in range(0, 2401)]\
                and len(boost_rating.split('-')) == 2 and int(boost_rating.split("-")[0]) < int(boost_rating.split("-")[1]):
            start_rating, end_rating = int(boost_rating.split("-")[0]), int(boost_rating.split("-")[1])
            self.buyer.rating = boost_rating
            self.price_recommendation = pricing.set_rating(self.bracket, start_rating, end_rating)

        elif self.type != "Set rating" and boost_rating.isnumeric() and int(boost_rating) in range(0, 3501):
            if self.type == '1 win':
                self.buyer.rating = boost_rating
                self.price_recommendation = pricing.one_win(self.bracket, int(boost_rating))

            elif self.type == 'Gladiator':
                self.buyer.rating = boost_rating
                self.price_recommendation = 'See glad pricing'

            else:
                self.buyer.rating = boost_rating
                self.price_recommendation = pricing.hourly(self.bracket)

        else:
            await self.author.send("Rating format not recognised, please check your format and try again")
            await self._get_rating_range()

    async def _get_price_estimate(self):
        recommendation = f"{self.price_recommendation:,}" if self.type != "Gladiator" else "See glad pricing"
        price_estimate = await request.react_message(
            self, f"the **estimated price of the boost**, \n recommended price: **{recommendation}**\nThis is not the final price, just what is shown when the booking is posted", '❌')
        price_estimate = price_estimate.replace(",", "").replace(".", "")
        try:
            assert price_estimate.isnumeric(), 'Boost price must be a number, please try again.'
            assert int(price_estimate) > 0, 'Boost price cannot be negative, please try again.'
            self.ad_price_estimate = int(price_estimate)
            return True

        except AssertionError as e:
            await self.author.send(str(e))
            await self._get_price_estimate()

    async def _get_price(self, force=False):
        if not force and self.price:
            return
        if not self.type and self.price_recommendation:
            raise exceptions.RequestFailed("Cannot get price when boost type / price recommendation are not known")
        boost_price = await request.react_message(
            self, f'the **total boost price**,\n estimated price: **{self.ad_price_estimate:,}**g', '')
        boost_price = boost_price.replace(",", "").replace(".", "")

        try:
            assert boost_price.isnumeric(), 'Boost price must be a number, please try again.'
            assert int(boost_price) > 0, 'Boost price cannot be negative, please try again.'
            boost_price = int(boost_price)
            self.price = boost_price
            self.booster.prim_cut = round(boost_price * cfg.settings["booster_cut"])
            self.booster.ad_cut = round(boost_price * cfg.settings["advertiser_cut"])
            self.booster.mana_cut = round(boost_price * cfg.settings["management_cut"])
            return True

        except AssertionError as e:
            await self.author.send(str(e))
            await self._get_price()

    async def _get_notes(self, force=False):
        if not force and self.notes:
            return
        self.notes = await request.react_message(
            self, '**any additional notes** about the buyer, react with ⏩ to skip\n'
            'or react with ❌ to cancel the booking', ['⏩', '❌'])
        self.notes = 'N/A' if self.notes == '⏩' else self.notes

    async def refund_price(self) -> int:
        refund_amount = await request.react_message(self, "**the price of the boost** (after refund)", "")
        refund_amount = refund_amount.replace(",", "").replace(".", "")

        if refund_amount.isnumeric():
            return int(refund_amount)

        else:
            await self.author.send("Unrecognized format, please try again")
            return await self.refund_price()

    def format_price_estimate(self, modifier=cfg.settings["booster_cut"]):
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
        """Fetch the post message of the booking instance, used when the reaction on the message need to be rechecked"""
        if self.status == 1:
            self.post_message = await self.post_channel.fetch_message(self.post_message.id)

    async def _status_update(self):
        await self.author.send(embed=base_embed(f"Booking ``{self.id}`` has been set to ``{statuses[self.status]}``"))

    def authorized(self, user_id):
        if self.authorid != user_id:
            raise exceptions.RequestFailed("You are not authorized to do that")
    
    def sheet_format(self):
        return [
            statuses[self.status], str(self.id), self.gold_realms or "N/A", str(self.booster.prim), str(self.booster.prim_cut),
            str(self.booster.sec) or 'N/A', str(self.booster.sec_cut), str(self.author.id), str(self.booster.ad_cut),
            str(self.price), str(self.author), self.payment_hash or 'Pending Booking Completion']


class Buyer(object):
    """ Represents information about the buyer of a booking

    Attributes
    -----------
    name: Optional[:class:`str`]
        The buyer's name. Could be None.
    realm: Optional[:class:`str`]
        The buyer's realm. Could be None.
    faction: Optional[:class:`str`]
        The buyer's faction. Could be None.
    class_: Optional[:class:`str`]
        The buyer's class. Could be None.
    spec: Optional[:class:`str`]
        The buyer's spec. Could be None.
    rating: Optional[:class:`str`]
        The rating of the boost. Can be in format `num` or `num-num`. Could be None.
    """
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
    """ Represents information about boosters and cuts of a booking

    Attributes
    -----------
    prim: Optional[:class:`int`]
        The user ID of the primary booster. Could be None.
    sec: Optional[:class:`int`]
        The user ID of the seconary booster (for 3s bookings). Could be Nonde.
    prim_cut: :class:`int`
        The gold cut of the primary booster. Will be 0 if price is 0.
    sec_cut: :class:`int`
        The gold cut of the secondary booster. Will be 0 if price is 0.
    ad_cut: :class:`int`
        The gold cut of the advertiser (booking author). Will be 0 if price is 0.
    mana_cut: :class:`int`
        The gold cut of management. Will be 0 if price is 0.
    """
    def __init__(self):
        self.prim = None
        self.sec = None
        self.prim_cut = 0
        self.sec_cut = 0
        self.ad_cut = 0
        self.mana_cut = 0

    def update_price(self, new_price: int):
        if not self.sec:
            self.prim_cut = new_price // cfg.settings["booster_cut"]
        else:
            self.prim_cut = new_price // (cfg.settings["booster_cut"] / 2)
            self.sec_cut = new_price // (cfg.settings["booster_cut"] / 2)
        self.ad_cut = new_price // cfg.settings["advertiser_cut"]
        self.mana_cut = new_price // cfg.settings["management_cut"]
