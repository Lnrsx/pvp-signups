from utils import pricing
from utils.misc import base_embed, get_logger
from utils.request import request
from utils import exceptions
from utils.config import cfg
from utils.sheets import sheets

from discord.ext import commands
import discord

import uuid
import asyncio
import json
import jsonpickle
import random

logger = get_logger("PvpSignups")
statuses = ['Compiling', 'Posted', 'Pending (not uploaded)', 'Pending', 'Refund', 'Partial refund', 'Complete']


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
    attachment: Optional[:class:`str`]
        The link to a discord CDN image of the advertiser sending the collected gold to the bank character,
        however since this is only collected when a booking is set to complete and completed bookings are not stored internally,
        it will almost certainly be None.
    gold_realms: Optional[:class:`str`]
        A string of comma seperated realm names that the payment for the booking was collect on. Could be None.
    notes: Optional[:class:`str`]
        Additional notes provided by the advertiser about the booking. Could be None.
    post_message: Optional[:class:`discord.Message`]
        The message that was posted about the booking in the designated post_bookings channel. Could be None.
    """
    instances, post_channel, request_channel = [], None, None

    def __init__(self, bracket, author: discord.User):
        self.__class__.instances.append(self)
        self._author = author
        self.bracket = bracket
        self.status = 0
        self.id = str(uuid.uuid1().int)[:10]
        self.type = None
        self.buyer = Buyer()
        self.price_recommendation = None
        self.price = 0
        self.booster = Booster()
        self.attachment = None
        self.gold_realms = None
        self.notes = None
        self.post_message = None

    @classmethod
    async def load(cls, client):
        """Gets the channels responsible for creating / posting bookings and loads the booking cache from data/bookings.json.
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
        if cls.post_channel is None:
            cls.post_channel = commands.Bot.get_channel(cls.client, cfg.settings["post_booking_channel_id"])
        if not cls.request_channel or not cls.post_channel:
            raise exceptions.ChannelNotFound
        try:
            await cls.request_channel.fetch_message(cfg.settings["request_booking_message_id"])
        except discord.NotFound:
            raise exceptions.MessageNotFound
        with open("data/bookings.json", "r") as f:
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
    async def validate(cls):
        """Validates all booking in the interal cache with their sheet counterparts
        
        .. note::
        If the format bookings are loaded to the sheet is changed, this function's code must be updated
        """
        sheet = await sheets.grab_sheet()
        del sheet[0]
        cachefields = [b.sheet_format() for b in cls.instances]
        not_on_sheet = [x for x in cachefields if x not in sheet and x[0] not in statuses[0:3]]
        not_in_cache = [x for x in sheet if x not in cachefields and x[0] not in statuses[4:]]
        if not_in_cache or not_on_sheet:
            response = f"Sheet check completed: {len(not_on_sheet)} booking(s) found not on sheet, {len(not_in_cache)} booking(s) found not in cache"
            logger.warning(response)
        else:
            response = "Sheet check completed: Sheet is valid"
            logger.info(response)
        return response

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

    async def compile(self):
        """DMs the booking instance author questions about the booking they are creating,
        functions recursively call themselves until a valid input is given.
        """
        await self._get_boost_type()
        await self._get_name_faction_class()
        await self._get_spec()
        await self._get_rating_range()
        await self._get_notes()

    async def post(self):
        """ `discord.Embed`: Posts the compiled booking in the post bookings channel."""
        embed = discord.Embed(
            title='New {} booking'.format(self.bracket),
            description='**ID:** ``{}``'.format(self.id),
            colour=discord.Colour.purple())
        embed.set_author(name=self.author.display_name, icon_url=self.author.avatar_url)
        embed.add_field(name='Buyer Name', value=f'[{self.buyer_name}-{self.buyer_realm}](https://check-pvp.fr/eu/{self.buyer_realm}/{self.buyer_name})')
        embed.add_field(name='Boost type', value=f"``{self.type}``")
        embed.add_field(name='Booster cut', value=self.format_price_recommendation())
        embed.add_field(name='Buyer faction', value=f"{cfg.settings[self.faction.lower() + '_emoji']}``{self.faction}``")
        embed.add_field(name='Boost rating', value=f"``{self.rating}``")
        embed.add_field(name='Buyer Spec', value=f'{cfg.data["spec_emotes"][self.buyer.class_][self.buyer_spec]}``{self.buyer_spec} {self.buyer.class_}``')
        embed.add_field(name='Notes', value=f"``{self.notes}``")
        embed.set_footer(text=f"Winner will be picked in {cfg.settings['post_wait_time']} seconds")
        self.post_message = await self.post_channel.send(embed=embed)
        await self.author.send(embed=base_embed(
            f'Booking has been sent! booking ID is: ``{self.id}``.\n If the booking is taken,'
            ' you will be required to input the realm(s) the gold was taken on, '
            'booking will cancel if no users sign up'))
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
                    await self.post_channel.send(embed=base_embed(f'No users signed up to booking ``{self.id}``'))
                    await self.author.send(embed=base_embed(f"Booking ``{self.id}`` was cancelled due to no users signing up"))
                    self.delete()
                    raise exceptions.CancelBooking

            weight_file = json.load(open(f'data/userweights.json', 'r'))
            user_weights = weight_file[self.bracket]
            for user in list(set(user_weights.keys()).difference(set(reactions["users"]))):
                user_weights[user] = 1

            self.booster.prim = random.choices(
                population=reactions["users"],
                weights=[0.1 if user_weights[x] < 0 else user_weights[x] for x in reactions["users"]])[0]

            weight_file[self.bracket] = user_weights
            json.dump(weight_file, open(f'data/userweights.json', 'w'), indent=4)
            mention = ', **please mention your teammate**' \
                      f' within {round(cfg.settings["teammate_pick_timeout"] / 60)} minutes or the booking will be rerolled' if self.bracket == '3v3' else ''
            await self.post_channel.send(
                f"<@{self.booster.prim}> was picked for {self.author.display_name}'s "
                f"``{self.bracket} {self.type} {self.rating}`` boost ({reactions['time']}){mention}")

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
            await self.post_channel.send(embed=base_embed(f"<@{self.booster.sec}> has been picked as {winner_user.mention}'s teammate"))

        # post message is no longer relevent so is removed to save space in cache
        self.post_message = None
        if self.booster.prim_cut > 100000:
            for key in user_weights.keys():
                if key == self.booster.prim:
                    user_weights[key] = round(user_weights[key] - (self.booster.prim_cut * cfg.settings["bad_luck_protection_mofifier"]), 2)

                else:
                    user_weights[key] = round(user_weights[key] + (self.booster.prim_cut * cfg.settings["bad_luck_protection_mofifier"]), 2)
        self.status = 2

    async def upload(self):
        """Uploads the booking instance to the external google sheet.

        .. note::
        If the booking is already uploaded, call :meth:`update_sheet` instead.
        """

        if self.status == 2:
            await self.get_gold_realms()
            await sheets.add_pending_booking(self.sheet_format())

            self.status = 3

    async def update_sheet(self) -> bool:
        """Finds the booking instance by ID and updates the fields to the current instance attributes

        .. note::
        If the booking does not yet exist on the sheet, call :meth:`upload` instead.
        """
        sheet_booking = await sheets.get_pending_booking(self)
        for i, item in enumerate(self.sheet_format()):
            sheet_booking[i].value = item

        await sheets.update_booking(sheet_booking)

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
                assert await self.get_attachment_link(), "Request timed out"
            except AssertionError as e:
                raise exceptions.RequestFailed(str(e))
            self.booster.update_price(self.price)
        await self.update_sheet()
        self.cache()
        await self._status_update()
        self.delete()

    async def complete(self):
        """Flags a booking as completed, once this happens it is deleted from the cache"""
        try:
            assert self.status == 3, "Booking status must be pending to complete"
            assert await self.get_attachment_link(), "Request timed out"
            assert await self._get_price(), "Request timed out"
            self.status = 6
            await self._status_update()
            await self.update_sheet()
            self.delete()
        except AssertionError as e:
            raise exceptions.RequestFailed(str(e))

    def cache(self):
        """Saves a booking instance to the cache file at data/bookings.json.

        .. note::
        All attributes of the booking that are classes are converted to `int` in ID form
         """
        with open("data/bookings.json", "r") as f:
            data = json.load(f)
        with open("data/bookings.json", "w") as f:
            temp_author = self._author
            if isinstance(self._author, discord.User):
                self._author = self._author.id
            data[str(self.id)] = jsonpickle.encode(self)
            json.dump(data, f, indent=4)
            self._author = temp_author

    def delete(self):
        """Deletes the booking from the interal instance cache and the external file at data/bookings.json"""
        if self.status not in range(2):
            with open("data/bookings.json", "r") as f:
                data = json.load(f)
            with open("data/bookings.json", "w") as f:
                del data[str(self.id)]
                json.dump(data, f, indent=4)
        for i, obj in enumerate(self.instances):
            if obj.id == self.id:
                del self.instances[i]

    async def _get_boost_type(self):
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

    async def _get_name_faction_class(self):
        buyer_name = await request.react_message(
            self, '**buyers character name** (e.g. Mystikdruldk)'
                  '\nor react with ❌ to cancel the booking', '❌')
        buyer_realm = await request.react_message(
            self, '**buyers realm** (e.g. Ravencrest)'
            '\nor react with ❌ to cancel the booking', '❌')

        if cfg.settings["auto_faction_class_input"]:
            response = await request.get(
                f'https://eu.api.blizzard.com/profile/wow/character/{buyer_realm.lower()}/{buyer_name.lower()}?namespace=profile-eu&locale=en_GB', token=True)
            if response['status'] == 200:
                self.faction, self.buyer.class_ = response['body']['faction']['name'], response['body']['character_class']['name'].capitalize()
                self.buyer_name = buyer_name
                self.buyer_realm = buyer_realm

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
                    self.faction = faction_response.name
                    await self.manual_class_input()

                if str(character_not_found_response) == '🔁':
                    await self._get_name_faction_class()

            else:
                await self.author.send(embed=base_embed(
                    "**Unexpected error occoured trying to find a player with that name-realm**,"
                    " you can either input the buyers faction and class manually "
                    f"{cfg.settings['choose_faction_emoji']}, or cancel the booking (❌)."))
                self.faction = await request.react(
                    self, [cfg.settings["horde_emoji"], cfg.settings["alliance_emoji"]],
                    'React with the **buyers faction**\n'
                    'or react with ❌ to cancel the booking')
                await self.manual_class_input()
        else:
            self.faction = await request.react(
                self, [cfg.settings["horde_emoji"], cfg.settings["alliance_emoji"]],
                'React with the **buyers faction**\n'
                'or react with ❌ to cancel the booking')
            await self.manual_class_input()

    async def manual_class_input(self):
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

    async def _get_spec(self):
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

            self.buyer_spec = buyer_spec

    async def _get_rating_range(self):
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
                and len(boost_rating.split('-')) == 2:
            start_rating, end_rating = int(boost_rating.split("-")[0]), int(boost_rating.split("-")[1])
            self.rating = boost_rating
            self.price_recommendation = pricing.set_rating(self.bracket, start_rating, end_rating)

        elif boost_rating.isnumeric() and int(boost_rating) in range(0, 3501):
            if self.type == '1 win':
                self.rating = boost_rating
                self.price_recommendation = pricing.one_win(self.bracket, int(boost_rating))

            elif self.type == 'Gladiator':
                self.rating = boost_rating
                self.price_recommendation = 'See glad pricing'

            else:
                self.rating = boost_rating
                self.price_recommendation = pricing.hourly(self.bracket)

        else:
            await self.author.send("Rating format not recognised, please check your format and try again")
            await self._get_rating_range()

    async def _get_price(self):
        if not (self.type, self.price_recommendation):
            raise exceptions.RequestFailed("Cannot get price when boost type / price recommendation are not known")
        boost_price = await request.react_message(
            self, f'the **total boost price**,\n recommended price: **{self.price_recommendation:,}**g', '')
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

    async def _get_notes(self):
        self.notes = await request.react_message(
            self, '**any additional notes** about the buyer, react with ⏩ to skip\n'
            'or react with ❌ to cancel the booking', ['⏩', '❌'])
        self.notes = 'N/A' if self.notes == '⏩' else self.notes

    async def get_gold_realms(self):
        self.gold_realms = await request.react_message(
            self, 'the **realm the gold was collected on**\n'
            'if gold was collected on multiple realms, specify all of them seperated by commas\n'
            '(e.g. Draenor, TarrenMill, Kazzak)', '', timeout=None)
        send_gold_string, gold_realms_list = 'Gold realm(s) registered, do not send gold until the booking is complete\n', self.gold_realms.replace(" ", "").split(',')

        # iterate through the user-entered realm seperated by commas
        for realm in gold_realms_list:
            # iterate through connected realm groups (1 group is a list of its own)
            for x in cfg.data['connected_realms']:
                # if one of the inputted realms matches a realm
                if realm in cfg.data['realm_abbreviations'].keys():
                    realm = cfg.data['realm_abbreviations'][realm]

                if realm in x:
                    # always uses the name of the first realm in the list (where the bank character is)
                    send_gold_string += f"send **{realm}** gold to " \
                                        f"**{cfg.data['bank_characters'][x[0]].format('<:Horde:753970203452506132>', '<:Alliance:753970203402174494>')}**\n"
                    break

        send_gold_string += f"When the booking is done, type ``!done {self.id}`` to register the booking as complete " \
                            "(you will be required to provide a screenshot of you sending the gold)"
        await self.author.send(embed=base_embed(send_gold_string))

    async def refund_price(self) -> int:
        refund_amount = await request.react_message(self, "**the price of the boost** (after refund)", "")
        refund_amount = refund_amount.replace(",", "").replace(".", "")

        if refund_amount.isnumeric():
            return int(refund_amount)

        else:
            await self.author.send("Unrecognized format, please try again")
            return await self.refund_price()

    async def get_attachment_link(self):
        def attachment_check(message) -> bool:
            return message.channel.id == self.author.dm_channel.id and message.author == self.author

        await self.author.send(embed=base_embed(
            "Please upload a **screenshot of payment being send to the bank character**,\n"
            "request will timeout in 5 minutes"))
        try:
            attachment_message = await commands.Bot.wait_for(self.client, event='message', check=attachment_check, timeout=300)
            if attachment_message.attachments:
                self.attachment = attachment_message.attachments[0].url
            else:
                self.attachment = attachment_message.content
            return True

        except TimeoutError:
            await self.author.send(embed=base_embed("Request timed out"))

    def format_price_recommendation(self):
        if self.type == "Gladiator":
            return "``See glad pricing``"
        else:
            boost_cut_recommendation = self.price_recommendation * cfg.settings['booster_cut']
            price_recommendation_string = f"{round(boost_cut_recommendation):,}g"
            if self.type == 'Hourly':
                price_recommendation_string += "/hr"
            return f"``{price_recommendation_string}``"

    async def _recache_message(self):
        """Fetch the post message of the booking instance, used when the reaction on the message need to be rechecked"""
        if self.status == 1:
            self.post_message = await self.post_channel.fetch_message(self.post_message.id)

    async def _status_update(self):
        await self.author.send(embed=base_embed(f"Booking ``{self.id}`` has been set to ``{statuses[self.status]}``"))

    def _msg_check_wrapper(self) -> bool:
        def message_check(message):
            # checks if the message is in the dm channel of the message author and is from the message author
            return message.post_channel.id == self.author.dm_channel.id and message.author == self.author
        return message_check

    def authorized(self, user_id):
        return self.authorid == user_id
    
    def sheet_format(self):
        return [
            statuses[self.status], str(self.id), self.gold_realms or "N/A", str(self.booster.prim), str(self.booster.prim_cut),
            str(self.booster.sec) or 'N/A', str(self.booster.sec_cut), str(self.author.id), str(self.booster.ad_cut),
            str(self.price), str(self.author), self.attachment or 'Pending Booking Completion']


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
