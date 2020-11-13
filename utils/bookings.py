from utils import dictionaries
from string import capwords
from utils.pricing import set_rating_price, one_win_price, hourly_price
from utils.response_types import react_message, react
from utils.utils import base_embed, get_logger
from utils.dictionaries import spec_emotes
from utils import exceptions

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

    """Represents a user created booking for a 2v2 or 3v3 boost, this class is used to store all information on a boost.
    Statuses: compiling = 0, posted = 1, pending (not uploaded) = 2, pending = 3, refund = 4, partial refund = 5, complete = 6"""
    instances, post_channel, request_channel = [], None, None

    def __init__(self, bracket, author: discord.User):
        self.__class__.instances.append(self)
        self._author = author
        self.bracket = bracket
        self.status = 0
        self.id = str(uuid.uuid1().int)[:10]
        self.type = None
        self.buyer_name = None
        self.buyer_realm = None
        self.faction = None
        self.buyer_class = None
        self.buyer_spec = None
        self.rating = None
        self.price_recommendation = 0
        self.price = 0
        self.booster = None
        self.booster_2 = 'N/A'
        self.boost_cut = 0
        self.boost_cut_2 = 0
        self.ad_cut = 0
        self.management_cut = 0
        self.attachment = 'Pending booking completion'
        self.gold_realms = 'N/A'
        self.notes = None
        self.post_message = None

    @classmethod
    async def load(cls, client):

        """Gets the channels responsible for creating / posting bookings and loads the booking cache from data/bookings.json.
        This function must be called on bot startup"""

        cls.client = client
        if cls.request_channel is None:
            cls.request_channel = commands.Bot.get_channel(cls.client, cls.client.config["request_booking_channel_id"])
        if cls.post_channel is None:
            cls.post_channel = commands.Bot.get_channel(cls.client, cls.client.config["post_booking_channel_id"])
        if not cls.request_channel or not cls.post_channel:
            raise exceptions.ChannelNotFound
        try:
            await cls.request_channel.fetch_message(cls.client.config["request_booking_message_id"])
        except discord.NotFound:
            # both channels have been found since ChannelNotFound was not raised, they can be passed to the load retry in main
            raise exceptions.MessageNotFound
        with open("data/bookings.json", "r") as f:
            cache = json.load(f)
            for instance in cache.values():
                instance = jsonpickle.decode(instance)
                instance.__class__.instances.append(instance)
            logger.info(f"{len(cls.instances)} booking(s) have been loaded from the cache")

    @property
    def author(self) -> discord.User:

        """Gets the owner of the booking instance. if the instance is from the cache it will be an int so will be converted to discord.User
        :returns: discord.User"""

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

        """Gets the user ID without unnecessarily fetching discord.User version"""

        if isinstance(self._author, discord.User):
            return self._author.id
        return self._author

    @classmethod
    def get(cls, bookingid):

        """Gets the instance of a booking from ID
        :returns: utils.bookings.Booking"""

        for instance in cls.instances:
            if instance.id == bookingid:
                return instance
        raise exceptions.RequestFailed(f"No booking was found with ID ``{bookingid}``")

    async def compile(self):

        """DMs the booking instance author questions about the booking they are creating,
         functions recursively call themselves unit a valid input is given"""

        await self.get_boost_type()
        await self.get_name_faction_class()
        await self.get_spec(self.buyer_class)
        await self.get_rating_range(self.type)
        await self.get_price(self.type, self.price_recommendation)
        await self.get_notes()

    async def post(self) -> discord.Embed:

        """Posts the compiled booking in the post bookings channel"""

        embed = discord.Embed(
            title='New {} booking'.format(self.bracket),
            description='**ID:** ``{}``'.format(self.id),
            colour=discord.Colour.purple())
        embed.set_author(name=self.author.display_name, icon_url=self.author.avatar_url)
        embed.add_field(name='Buyer Name', value=f'[{self.buyer_name}-{self.buyer_realm}](https://check-pvp.fr/eu/{self.buyer_realm}/{self.buyer_name})')
        embed.add_field(name='Boost type', value=f"``{self.type}``")
        embed.add_field(name='Booster cut', value=f"``{round(self.boost_cut):,}g``")
        embed.add_field(name='Buyer faction', value=f"{self.client.config[self.faction.lower()+'_emoji']}``{self.faction}``")
        embed.add_field(name='Boost rating', value=f"``{self.rating}``")
        embed.add_field(name='Buyer Spec', value=f'{dictionaries.spec_emotes[self.buyer_class][self.buyer_spec]}``{self.buyer_spec} {self.buyer_class}``')
        embed.add_field(name='Notes', value=f"``{self.notes}``")
        embed.set_footer(text=f"Winner will be picked in {self.client.config['post_wait_time']} seconds")
        self.post_message = await self.post_channel.send(embed=embed)
        await self.author.send(embed=base_embed(
            f'Booking has been sent! booking ID is: ``{self.id}``.\n If the booking is taken,'
            ' you will be required to input the realm(s) the gold was taken on, '
            'booking will cancel if no users sign up'))
        await self.post_message.add_reaction(self.client.config["take_emoji"])
        await self.post_message.add_reaction(self.client.config["schedule_emoji"])
        self.status = 1
        return embed

    async def pick_winner(self, embed):

        """Chooses the booster of the booking based on who reacted to the message, users who react with `now` will always be prioritized.
        In 3v3 boosts, the winner will be chosen and will have to mention their teammate,
        if they fail to do so before the configured timout, the booking will re rerolled"""

        if self.status == 1:
            await asyncio.sleep(self.client.config["post_wait_time"])
            await self._recache_message()
            reactions = await [i.users() for i in self.post_message.reactions if str(i.emoji) == self.client.config["take_emoji"]][0].flatten()
            reactions = {"users": [str(i.id) for i in reactions if i.bot is False], "time": "now"}

            if not reactions["users"]:
                reactions = await [i.users() for i in self.post_message.reactions if str(i.emoji) == self.client.config["schedule_emoji"]][0].flatten()
                reactions = {"users": [str(i.id) for i in reactions if i.bot is False], "time": "schedule"}

                if not reactions["users"]:
                    await self.post_channel.send(embed=base_embed(f'No users signed up to booking ``{self.id}``'))
                    await self.cancel()

            weight_file = json.load(open(f'data/userweights.json', 'r'))
            user_weights = weight_file[self.bracket]
            for user in list(set(user_weights.keys()).difference(set(reactions["users"]))):
                user_weights[user] = 1

            self.booster = random.choices(
                population=reactions["users"],
                weights=[0.1 if user_weights[x] < 0 else user_weights[x] for x in reactions["users"]])[0]

            weight_file[self.bracket] = user_weights
            json.dump(weight_file, open(f'data/userweights.json', 'w'), indent=4)
            mention = ', **please mention your teammate**' \
                      f' within {round(self.client.config["teammate_pick_timeout"] / 60)} minutes or the booking will be rerolled' if self.bracket == '3v3' else ''
            await self.post_channel.send(
                f"<@{self.booster}> was picked for {self.author.display_name}'s "
                f"``{self.bracket} {self.type} {self.rating}`` boost ({reactions['time']}){mention}")

        else:
            return False

        if self.bracket == '3v3' and self.booster:
            def mention_check(message) -> bool:
                return message.author == winner_user and message.mentions

            winner_user = commands.Bot.get_user(self.client, int(self.booster))
            try:
                winner_message = await commands.Bot.wait_for(self.client, event='message', check=mention_check, timeout=self.client.config["teammate_pick_timeout"])

            except asyncio.TimeoutError:
                embed.title = f"Rerolled {self.bracket} Bookings"
                self.post_message = await self.post_channel.send(embed=embed)
                await self.post_message.add_reaction(self.client.config["take_emoji"])
                await self.post_message.add_reaction(self.client.config["schedule_emoji"])
                return await self.pick_winner(embed)

            self.booster_2, self.boost_cut, self.boost_cut_2 = winner_message.mentions[0].id, self.boost_cut / 2, self.boost_cut / 2
            await self.post_channel.send(embed=base_embed(f"<@{self.booster_2}> has been picked as {winner_user.mention}'s teammate"))

        if self.boost_cut > 100000:
            for key, value in user_weights.items():
                if key == self.booster:
                    user_weights[key] = round(user_weights[key] - (self.boost_cut * 0.0000001), 2)

                else:
                    user_weights[key] = round(user_weights[key] + (self.boost_cut * 0.0000001), 2)
        self.status = 2

    async def upload(self):

        """Uploads the booking instance to the external google sheet"""

        if self.status == 2:
            await self.get_gold_realms()
            await self.client.sheets.add_pending_booking([
                'pending', self.id, self.gold_realms, self.booster, self.boost_cut,
                self.booster_2, self.boost_cut_2, str(self.author.id), str(self.ad_cut),
                str(self.price), str(self.author), 'Pending booking completion'])

            self.status = 3

    async def update_sheet(self) -> bool:

        """Finds the booking instance by ID and updates the fields to the current instance attributes"""
        sheet_booking = await self.client.sheets.get_pending_booking(self)
        fields = [
            statuses[self.status], self.id, self.gold_realms, self.booster, self.boost_cut,
            self.booster_2, self.boost_cut_2, str(self.author.id), str(self.ad_cut),
            str(self.price), str(self.author)]

        for i, item in enumerate(fields):
            sheet_booking[i].value = item

        await self.client.sheets.update_booking(sheet_booking)

    async def cancel(self):

        """Cancels a booking, can be due to user request or timeout"""

        await self.author.send(embed=base_embed(f"Bookings ``{self.id}`` has been cancelled"))
        self.delete()
        raise exceptions.CancelBooking

    async def refund(self, amount):

        """Either partially or fully refunds a booking, partial refunds require buyer's rating at refund issue
        and will accordingly update how much payment is required (only applies to set rating boosts)"""

        if amount == 'partial':
            if self.type != 'set rating':
                raise exceptions.RequestFailed("Only set rating boosts can be partially refunded")
            refund_modifier = await self.refund_rating()
            self.price /= refund_modifier
            self.boost_cut /= refund_modifier
            self.boost_cut_2 /= refund_modifier
            self.ad_cut /= refund_modifier
            self.management_cut /= refund_modifier
            self.attachment = await self.get_attachment_link()

        else:
            self.status = 4

        await self.update_sheet()
        self.cache()
        await self._status_update()
        self.delete()

    async def complete(self):

        """Flags a booking as completed, once this happens it is no longer required
         to be stored in the interal booking cache"""

        try:
            assert self.status == 3, "Booking status must be pending to complete"
            assert await self.get_attachment_link(), "Request timed out"
            self.status = 6
            await self._status_update()
            await self.update_sheet()
            self.delete()
        except AssertionError as e:
            raise exceptions.RequestFailed(str(e))

    def cache(self):

        """Saves a booking instance to the cache file at data/bookings.json,
         all attributes that are a Class are converted into integers or removed as they cannot be stored easily"""

        with open("data/bookings.json", "r") as f:
            data = json.load(f)
        with open("data/bookings.json", "w") as f:
            author, channel, message = self.author, self.post_channel, self.post_message
            # author and post message could be integers so fetching them just to get their id is pointless
            self._author = self._author if isinstance(self._author, int) else self._author.id
            Booking.post_channel = None
            self.post_message = self.post_message if isinstance(self.post_message, int) else self.post_message.id
            data[str(self.id)] = jsonpickle.encode(self)
            json.dump(data, f, indent=4)
            self._author, Booking.post_channel, self.post_message = author, channel, message

    def delete(self):
        if self.status not in range(2):
            with open("data/bookings.json", "r") as f:
                data = json.load(f)
            with open("data/bookings.json", "w") as f:
                del data[str(self.id)]
                json.dump(data, f, indent=4)
        for i, o in enumerate(self.instances):
            if o.id == self.id:
                del self.instances[i]

    async def get_boost_type(self):
        fields = '\n'.join(dictionaries.boost_types)
        boost_type = await react_message(
            self, f"the **boost type**, accepted respones:\n"
            f" {fields}\nor react with ❌ to cancel the booking", '❌')
        if boost_type.capitalize() in dictionaries.boost_types:
            self.type = boost_type.capitalize()

        else:
            await self.author.send('Boost type not recognised, please try again.')
            await self.get_boost_type()

    async def get_name_faction_class(self):
        buyer_name = await react_message(
            self, '**buyers character name** (e.g. Mystikdruldk)'
                  '\nor react with ❌ to cancel the booking', '❌')
        buyer_realm = await react_message(
            self, '**buyers realm** (e.g. Ravencrest)'
            '\nor react with ❌ to cancel the booking', '❌')

        if self.client.config["auto_faction_class_input"]:
            response = await self.client.request.get(
                f'https://eu.api.blizzard.com/profile/wow/character/{buyer_realm}/{buyer_name}?namespace=profile-eu&locale=en_GB', token=True)
            if response['status'] == 200:
                self.faction, self.buyer_class = response['body']['faction']['name'], response['body']['character_class']['name']
                self.buyer_name = capwords(buyer_name)
                self.buyer_realm = capwords(buyer_realm)

            elif response['status'] == 404:
                character_not_found_response = await react(
                    self, [self.client.config['choose_faction_emoji'], '🔁'],
                    "**No character was found with that name-realm**,"
                    " you can either input the buyers faction and class manually "
                    f"{self.client.config['choose_faction_emoji']}, "
                    "re-enter the name (🔁), or cancel the booking (❌).")

                if str(character_not_found_response) == self.client.config["choose_faction_emoji"]:
                    self.faction = await react(
                        self, [self.client.config["horde_emoji"], self.client.config["alliance_emoji"]],
                        'React with the **buyers faction**\n'
                        'or react with ❌ to cancel the booking')
                    await self.manual_class_input()

                if str(character_not_found_response) == '🔁':
                    await self.get_name_faction_class()

            else:
                await self.author.send(embed=base_embed(
                    "**Unexpected error occoured trying to find a player with that name-realm**,"
                    " you can either input the buyers faction and class manually "
                    f"{self.client.config['choose_faction_emoji']}, or cancel the booking (❌)."))
                self.faction = await react(
                    self, [self.client.config["horde_emoji"], self.client.config["alliance_emoji"]],
                    'React with the **buyers faction**\n'
                    'or react with ❌ to cancel the booking')
                await self.manual_class_input()
        else:
            self.faction = await react(
                self, [self.client.config["horde_emoji"], self.client.config["alliance_emoji"]],
                'React with the **buyers faction**\n'
                'or react with ❌ to cancel the booking')
            await self.manual_class_input()

    async def manual_class_input(self):
        fields = '\n'.join(dictionaries.class_emotes)
        buyer_class = await react_message(
            self, f'the **buyers class**, accepted responses:\n {fields}\n'
            'or react with ❌ to cancel the booking', '❌')
        if capwords(buyer_class) in dictionaries.spec_emotes.keys():
            self.buyer_name = capwords(self.buyer_name)
            self.buyer_realm = capwords(self.buyer_realm)
            self.faction = capwords(self.faction)
            self.buyer_class = capwords(buyer_class)
        else:
            await self.author.send('Class not recognised, please try again.')
            await self.manual_class_input()

    async def get_spec(self, buyer_class):
        accepted_inputs_string = ''
        for i in spec_emotes[buyer_class].keys():
            accepted_inputs_string += spec_emotes[buyer_class][i] + i + '\n'
        buyer_spec = await react_message(
            self, f'the **buyers spec**,'
            f' accepted respones:\n {accepted_inputs_string}', '❌')

        if capwords(buyer_spec) not in dictionaries.spec_emotes[buyer_class].keys() and capwords(buyer_spec) not in list(dictionaries.class_specs_abbreviations[buyer_class].keys()):
            await self.author.send('Spec not recognised, please try again.')
            await self.get_spec(buyer_class)

        else:
            # translates spec abbreivation to proper class name if it is used
            if capwords(buyer_spec) in list(dictionaries.class_specs_abbreviations[buyer_class].keys()):
                buyer_spec = dictionaries.class_specs_abbreviations[buyer_class][capwords(buyer_spec)]

            self.buyer_spec = capwords(buyer_spec)

    async def get_rating_range(self, boost_type):

        if boost_type == 'Set rating':
            boost_rating_format_string = 'the **buyers start-desired rating**, (e.g. 1049-1800)'

        else:
            boost_rating_format_string = 'the **buyers current rating (e.g. 1687)'

        boost_rating = await react_message(
            self, boost_rating_format_string
            + '\nor react with ❌ to cancel the booking**', '❌')

        try:
            rating_format_check = \
                len(boost_rating.split("-")) == 2 \
                and int(boost_rating.split("-")[0]) in range(0, 2401) \
                and int(boost_rating.split("-")[1]) in range(0, 2401)

            if boost_type == 'Set rating' and rating_format_check:
                start_rating, end_rating = int(boost_rating.split("-")[0]), int(boost_rating.split("-")[1])
                self.rating = boost_rating
                self.price_recommendation = set_rating_price(self.bracket, start_rating, end_rating)

            elif int(boost_rating) in range(0, 3501):
                if boost_type == '1 win':
                    self.rating = boost_rating
                    self.price_recommendation = one_win_price(self.bracket, int(boost_rating))

                else:
                    self.rating = boost_rating
                    self.price_recommendation = hourly_price(self.bracket, int(boost_rating))

            else:
                await self.author.send("Rating format not recognised, please check your format and try again")
                await self.get_rating_range(boost_type)

        except ValueError:
            await self.author.send("Rating format not recognised, please check your format and try again")
            await self.get_rating_range(boost_type)

    async def get_price(self, boost_type, price_recommendation):
        format_recommendation = f"{price_recommendation:,}"
        boost_price = await react_message(
            self, f'the **boost price**,\n recommended price: **{format_recommendation}**g ({boost_type})\n'
                  'or react with ❌ to cancel the booking', '❌')
        boost_price = boost_price.replace(",", "").replace(".", "")

        try:
            assert boost_price.isnumeric(), 'Boost price must be a number, please try again.'
            assert int(boost_price) > 0, 'Boost price cannot be negative, please try again.'
            boost_price = int(boost_price)
            self.price = boost_price
            self.boost_cut = boost_price * self.client.config["booster_cut"]
            self.ad_cut = boost_price * self.client.config["advertiser_cut"]
            self.management_cut = boost_price * self.client.config["management_cut"]

        except AssertionError:
            await self.author.send('Boost price cannot be negative, please try again.')
            await self.get_price(boost_type, price_recommendation)

    async def get_notes(self):
        self.notes = await react_message(
            self, '**any additional notes** about the buyer, react with ⏩ to skip\n'
            'or react with ❌ to cancel the booking', ['⏩', '❌'])
        self.notes = 'N/A' if self.notes == '⏩' else self.notes

    async def get_gold_realms(self):
        self.gold_realms = await react_message(
            self, 'the **realm the gold was collected on**\n'
            'if gold was collected on multiple realms, specify all of them seperated by commas\n'
            '(e.g. Draenor, TarrenMill, Kazzak)', '')
        send_gold_string, gold_realms_list = 'Gold realm(s) registered, do not send gold until the booking is complete\n', self.gold_realms.replace(" ", "").split(',')

        # iterate through the user-entered realm seperated by commas
        for realm in gold_realms_list:
            # iterate through connected realm groups (1 group is a list of its own)
            for x in dictionaries.connected_realms:
                # if one of the inputted realms matches a realm
                if capwords(realm) in dictionaries.realm_abbreviations.keys():
                    realm = dictionaries.realm_abbreviations[capwords(realm)]

                else:
                    realm = capwords(realm)

                if realm in x:
                    # always uses the name of the first realm in the list (where the bank character is)
                    send_gold_string += f"send **{realm}** gold to " \
                                        f"**{dictionaries.bank_characters[x[0]].format('<:Horde:753970203452506132>', '<:Alliance:753970203402174494>')}**\n"
                    break

        send_gold_string += f"When the booking is done, type ``!done {self.id}`` to register the booking as complete " \
                            "(you will be required to provide a screenshot of you sending the gold)"
        await self.author.send(embed=base_embed(send_gold_string))

    async def refund_rating(self):
        await self.author.send(embed=base_embed(
            'Please respond with **the rating the buyer was at when the refund was issued**,\n'
            'request will timeout in 5 minutes'))
        try:

            current_rating = await commands.Bot.wait_for(self.client, event='message', check=self._msg_check_wrapper(), timeout=300)
            current_rating = current_rating.content
            if current_rating.isnumeric():
                price_recommendation = self.price - set_rating_price(self.bracket, self.rating.split("-")[0], int(current_rating))
                await self.refund_price(price_recommendation)

            else:
                await self.refund_rating()

        except asyncio.TimeoutError:
            await self.author.send(embed=base_embed("Request timed out"))

    async def refund_price(self, price_recommendation) -> int:
        recommendation = f"{price_recommendation:,}"
        await self.author.send(embed=base_embed(
            'Please respond with **how much the buyer is getting refunded**,\n'
            f'recommendation: **{recommendation}**g\n reqest will timout in 5 minutes'))
        try:
            refund_amount = await commands.Bot.wait_for(self.client, event='message', check=self._msg_check_wrapper(), timeout=300)
            refund_amount = refund_amount.content.replace(",", "").replace(".", "")

            if refund_amount.isnumeric() and int(refund_amount) in range(0, self.price):
                return (self.price - int(refund_amount)) / self.price

            else:
                raise ValueError

        except ValueError:
            await self.refund_price(price_recommendation)

        except asyncio.TimeoutError:
            await self.author.send(embed=base_embed("Request timed out"))

    async def get_attachment_link(self):
        def attachment_check(message) -> bool:
            return message.channel.id == self.author.dm_channel.id and message.author == self.author and message.attachments

        await self.author.send(embed=base_embed(
            "Please upload a **screenshot of payment being send to the bank character**,\n"
            "request will timeout in 5 minutes"))
        try:
            attachment_message = await commands.Bot.wait_for(self.client, event='message', check=attachment_check, timeout=300)
            self.attachment = attachment_message.attachments[0].url
            return True

        except TimeoutError:
            await self.author.send(embed=base_embed("Request timed out"))

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
