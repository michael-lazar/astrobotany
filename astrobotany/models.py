from __future__ import annotations

import math
import os
import random
import uuid
from datetime import date, datetime, timedelta
from typing import Iterable, List, Optional, Tuple, Type

import bcrypt
from faker import Faker
from peewee import (
    JOIN,
    BlobField,
    BooleanField,
    DateTimeField,
    ForeignKeyField,
    IntegerField,
    Model,
    SqliteDatabase,
    TextField,
)

from . import constants, items
from .art import colorize, render_art

fake = Faker()


MAIL_DIR = os.path.join(os.path.dirname(__file__), "mail")


def init_db(filename: str = ":memory:") -> SqliteDatabase:
    """
    Bind an SQLite database to the Peewee ORM models.
    """
    db = SqliteDatabase(filename)
    db.bind(BaseModel.model_registry)
    db.create_tables(BaseModel.model_registry)
    return db


def _default_rarity() -> int:
    """
    Rarity calculator for plants.
    """
    if random.random() < 0.66:
        return 0
    elif random.random() < 0.5:
        return 1
    elif random.random() < 0.5:
        return 2
    elif random.random() < 0.5:
        return 3
    else:
        return 4


def gen_user_id() -> str:
    return uuid.uuid4().hex


class BaseModel(Model):
    model_registry: List[Type[BaseModel]] = []

    @classmethod
    def validate_model(cls):
        if cls.__name__ != "BaseModel":
            cls.model_registry.append(cls)
        return super().validate_model()


class User(BaseModel):
    """
    A user account corresponding to a TLS client certificate.
    """

    user_id = TextField(unique=True, index=True, default=gen_user_id)
    username = TextField()
    created_at = DateTimeField(default=datetime.now)
    ansi_enabled = BooleanField(default=False)  # TODO: Delete this field
    password = BlobField(null=True)

    @classmethod
    def admin(cls) -> User:
        user, _ = cls.get_or_create(user_id="0" * 32, username="admin")
        return user

    @classmethod
    def initialize(cls, username: str) -> User:
        """
        Register a new player.
        """
        user = cls.create(username=username)
        user.add_item(items.paperclip)
        user.add_item(items.fertilizer, quantity=1)

        subject, body = Inbox.load_mail_file("welcome.txt")
        body = body.format(user=user)
        Inbox.create(
            user_from=User.admin(), user_to=user, subject=subject, body=body,
        )
        return user

    @classmethod
    def login(cls, fingerprint: str) -> Optional[Certificate]:
        """
        Load a user from their certificate fingerprint.

        Join on the active_plant to avoid making an extra query, since we will
        almost always access the user's plant later.
        """
        query = (
            Certificate.select()
            .join(User, on=Certificate.user == User.id)
            .join(Plant, JOIN.LEFT_OUTER, on=Plant.user_active == User.id)
            .where(Certificate.fingerprint == fingerprint)
        )

        try:
            cert = query.get()
            cert.update(last_seen=datetime.now())
            cert.save()
        except Certificate.DoesNotExist:
            cert = None

        return cert

    @property
    def plant(self) -> Plant:
        """
        Return the user's current "active" plant, or generate a new one.

        This is cached locally to avoid unnecessary DB lookups.
        """
        if not hasattr(self, "_plant"):
            try:
                self._plant = self.active_plants.get()
            except Plant.DoesNotExist:
                self._plant = Plant.create(user=self, user_active=self)

        return self._plant

    def set_password(self, password: str) -> None:
        self.password = bcrypt.hashpw(password.encode(), bcrypt.gensalt())

    def check_password(self, password: str) -> bool:
        if not self.password:
            return False
        return bcrypt.checkpw(password.encode(), self.password)

    def add_item(self, item: items.Item, quantity: int = 1) -> ItemSlot:
        """
        Add an item to the user's inventory.
        """
        item_slot, _ = ItemSlot.get_or_create(user=self, item_id=item.item_id)
        item_slot.quantity += quantity
        item_slot.save()
        return item_slot

    def remove_item(self, item: items.Item, quantity: int = 1) -> bool:
        """
        Remove an item from the user's inventory.

        Returns True if the item was successfully removed.
        """
        item_slot = ItemSlot.get_or_none(user=self, item_id=item.item_id)
        if not item_slot:
            return False

        if item_slot.quantity < quantity:
            return False

        if item_slot.quantity == quantity:
            item_slot.delete_instance()
            return True

        item_slot.quantity -= quantity
        item_slot.save()
        return True

    def get_item_quantity(self, item: items.Item) -> int:
        """
        Return the number of items in the user's inventory.
        """
        item_slot = ItemSlot.get_or_none(user=self, item_id=item.item_id)
        if item_slot:
            return item_slot.quantity

        return 0


class Certificate(BaseModel):
    """
    A client certificate used for user authentication.
    """

    user = ForeignKeyField(User, backref="certificates")
    authorised = BooleanField(default=False)
    fingerprint = TextField(unique=True, index=True)
    subject = TextField(null=True)
    not_valid_before_utc = DateTimeField(null=True)
    not_valid_after_utc = DateTimeField(null=True)
    first_seen = DateTimeField(default=datetime.now)
    last_seen = DateTimeField(default=datetime.now)
    ansi_enabled = BooleanField(default=False)


class Message(BaseModel):
    """
    A public message posted to the community message board.
    """

    user = ForeignKeyField(User, backref="messages")
    created_at = DateTimeField(default=datetime.now)
    text = TextField()

    @classmethod
    def by_date(cls):
        return cls.select().order_by(cls.created_at.desc())


class ItemSlot(BaseModel):
    """
    Mapping table between users and the items that they possess.
    """

    user: User = ForeignKeyField(User, backref="inventory")
    item_id: int = IntegerField()
    quantity: int = IntegerField(default=0)

    @property
    def item(self) -> items.Item:
        return items.registry[self.item_id]

    @classmethod
    def store_view(cls, user: User) -> Iterable[ItemSlot]:
        item_slots = {item_slot.item_id: item_slot for item_slot in user.inventory}
        for item_id, item in items.registry.items():
            if item.for_sale:
                item_slot = item_slots.get(item_id)
                if not item_slot:
                    item_slot = ItemSlot(user=user, item_id=item_id)
                yield item_slot


class Event(BaseModel):
    """
    Table for tracking generic events for users.
    """

    PICK_PETAL = "pick_petal"

    user = ForeignKeyField(User, backref="events")
    created_at = DateTimeField(default=datetime.now)
    event_type = TextField(index=True)
    target = TextField(index=True)


class Inbox(BaseModel):
    r"""
    A private message sent between users.

    This should probably be merged with the message table. ¯\_(ツ)_/¯
    """

    user_from = ForeignKeyField(User, backref="outbox")
    user_to = ForeignKeyField(User, backref="inbox")
    created_at: datetime = DateTimeField(default=datetime.now)
    subject = TextField()
    body = TextField()
    is_seen = BooleanField(default=False)
    parent = ForeignKeyField("self", null=True, backref="children")

    @property
    def date_str(self) -> str:
        return self.created_at.strftime("%Y-%M-%d")

    @property
    def datetime_str(self) -> str:
        return self.created_at.strftime("%A, %B %d, %Y %-I:%M:%S %p (EST)")

    @classmethod
    def load_mail_file(cls, filename: str) -> Tuple[str, str]:
        with open(os.path.join(MAIL_DIR, filename)) as fp:
            subject = fp.readline().strip()
            body = fp.read().strip()
        return subject, body


class Plant(BaseModel):
    """
    A plant, i.e. the whole purpose of this application.
    """

    user = ForeignKeyField(User, backref="plants")
    user_active = ForeignKeyField(User, null=True, unique=True, backref="active_plants")
    created_at = DateTimeField(default=datetime.now)
    updated_at = DateTimeField(default=datetime.now)
    watered_at = DateTimeField(default=lambda: datetime.now() - timedelta(days=1))
    watered_by = ForeignKeyField(User, null=True)
    generation = IntegerField(default=1)
    score = IntegerField(default=0)
    stage = IntegerField(default=0)
    species = IntegerField(default=lambda: random.randrange(len(constants.SPECIES)))
    rarity = IntegerField(default=_default_rarity)
    color = IntegerField(default=lambda: random.randrange(len(constants.COLORS)))
    mutation = IntegerField(null=True)
    dead = BooleanField(default=False)
    name = TextField(default=fake.first_name)
    fertilized_at = DateTimeField(default=lambda: datetime.now() - timedelta(days=4))
    shaken_at = IntegerField(default=0)

    @classmethod
    def all_active(cls):
        return cls.filter(cls.user_active.is_null(False)).join(User)

    @property
    def color_str(self) -> str:
        return constants.COLORS[self.color]

    @property
    def stage_str(self) -> str:
        return constants.STAGES[self.stage]

    @property
    def species_str(self) -> str:
        return constants.SPECIES[self.species]

    @property
    def rarity_str(self) -> str:
        return constants.RARITIES[self.rarity]

    @property
    def mutation_str(self) -> Optional[str]:
        if self.mutation is not None:
            return constants.MUTATIONS[self.mutation]
        else:
            return None

    @property
    def description(self) -> str:
        """
        A single-line description of the plant and all of its attributes.
        """
        words: List[str] = []
        if self.stage > 2:
            words.append(self.rarity_str)
        if self.mutation_str is not None:
            words.append(self.mutation_str)
        if self.stage > 3:
            words.append(self.color_str)
        words.append(self.stage_str)
        if self.stage > 1:
            words.append(self.species_str)
        if self.dead:
            words.append("(deceased)")
        return " ".join(words)

    @property
    def age(self) -> int:
        """
        The plant's age in days.
        """
        return (datetime.now() - self.created_at).days

    @property
    def growth_rate(self) -> float:
        """
        A growth multiplier based on the plant's generation.
        """
        return 1 + 0.2 * (self.generation - 1)

    @property
    def is_wilted(self) -> bool:
        """
        Is the plant close to death?
        """
        if self.dead:
            return False
        else:
            return self.watered_at < datetime.now() - timedelta(days=3)

    @property
    def water_supply_percent(self) -> int:
        """
        The percentage of water supply remaining, as an integer from 0 to 100.
        """
        seconds_per_day = 24 * 60 * 60
        elapsed_seconds = (datetime.now() - self.watered_at).total_seconds()
        remaining_water = max(0.0, 1 - (elapsed_seconds / seconds_per_day))
        return math.ceil(remaining_water * 100)

    @property
    def fertilizer_percent(self) -> int:
        """
        The percentage of fertilizer remaining, as an integer from 0 to 100.
        """
        seconds_per_day = 3 * 24 * 60 * 60
        elapsed_seconds = (datetime.now() - self.fertilized_at).total_seconds()
        remaining_fertilizer = max(0.0, 1 - (elapsed_seconds / seconds_per_day))
        return math.ceil(remaining_fertilizer * 100)

    def can_fertilize(self) -> bool:
        """
        Return if the user can apply fertilizer to the plant.
        """
        if self.dead:
            return False
        elif self.fertilizer_percent:
            return False
        elif not self.user_active.get_item_quantity(items.fertilizer):
            return False
        else:
            return True

    def get_water_gauge(self, ansi_enabled: bool = False) -> str:
        """
        Build an ascii graph that displays the plant's remaining water supply.
        """
        if self.dead:
            return "N/A"

        percent = self.water_supply_percent
        bar = ("█" * (percent // 10)).ljust(10)
        if ansi_enabled:
            # Make the water blue
            bar = colorize(bar, fg=12)
        return f"|{bar}| {percent}%"

    def get_fertilizer_gauge(self, ansi_enabled: bool = False) -> str:
        """
        Build an ascii graph that displays the plant's remaining fertilizer.
        """
        if self.dead:
            return "N/A"

        percent = self.fertilizer_percent
        bar = ("▞" * (percent // 10)).ljust(10)
        if ansi_enabled:
            # Make the fertilizer purple
            bar = colorize(bar, fg=40)
        return f"|{bar}| {percent}%"

    def get_ascii_art(self, ansi_enabled: bool = False) -> str:
        """
        Build an ascii-art picture based on the plant's generation and species.
        """
        today = date.today()
        if self.dead:
            filename = "rip.psci"
        elif (today.month, today.day) == (10, 31):
            filename = "jackolantern.psci"
        elif self.stage == 0:
            filename = "seed.psci"
        elif self.stage == 1:
            filename = "seedling.psci"
        elif self.stage == 2:
            filename = f"{self.species_str.replace(' ', '')}1.psci"
        elif self.stage in (3, 5):
            filename = f"{self.species_str.replace(' ', '')}2.psci"
        elif self.stage == 4:
            filename = f"{self.species_str.replace(' ', '')}3.psci"
        else:
            raise ValueError("Unknown stage")

        return render_art(filename, self.color_str, ansi_enabled)

    def get_observation(self, ansi_enabled: bool = False) -> str:
        """
        A long-form description of the plant.

        This includes a random observations and other specific details about
        the plant's current stage.
        """
        observation = []

        stage = 99 if self.dead else self.stage

        desc = random.choice(constants.STAGE_DESCRIPTIONS[stage])
        desc = desc.format(color=self.color_str, species=self.species_str)
        observation.append(desc)

        if stage < len(constants.STAGES) - 2:
            last_cutoff = constants.STAGE_CUTOFFS[stage]
            next_cutoff = constants.STAGE_CUTOFFS[stage + 1]
            if (self.score - last_cutoff) > 0.8 * (next_cutoff - last_cutoff):
                observation.append("You notice your plant looks different.")

        if stage == 1:
            choices = [
                constants.SPECIES[self.species],
                constants.SPECIES[(self.species - 3) % len(constants.SPECIES)],
                constants.SPECIES[(self.species + 3) % len(constants.SPECIES)],
            ]
            random.shuffle(choices)
            hint = f"It could be a(n) {choices[0]}, {choices[1]}, or {choices[2]}."
            observation.append(hint)

        elif stage == 2:
            if self.rarity > 0:
                observation.append("You feel like your plant is special.")

        elif stage == 3:
            choices = [
                constants.COLORS[self.color],
                constants.COLORS[(self.color - 3) % len(constants.COLORS)],
                constants.COLORS[(self.color + 3) % len(constants.COLORS)],
            ]
            random.shuffle(choices)
            hint = f"You can see the first hints of {choices[0]}, {choices[1]}, or {choices[2]}."
            observation.append(hint)

        return "\n".join(observation)

    def refresh(self) -> None:
        """
        Update the internal state of the plant.

        This will recompute the plant's score, remaining water supply,
        mutations, any evolutions that should be happening, etc...
        """
        last_updated = self.updated_at
        self.updated_at = datetime.now()

        # If it has been >5 days since watering, sorry plant is dead :(
        if self.updated_at - self.watered_at >= timedelta(days=5):
            self.dead = True
            return

        # Add a tick for every second since we last updated, up to 24 hours
        # after the last time the plant was watered
        min_time = max((self.watered_at, last_updated))
        max_time = min((self.watered_at + timedelta(days=1), self.updated_at))
        ticks = max((0, (max_time - min_time).total_seconds()))

        # Add a multiplier for fertilizer, up to 3 days after the last time
        # that the plant was fertilized
        min_time = max((self.fertilized_at, last_updated, self.watered_at))
        max_time = min(
            (
                self.fertilized_at + timedelta(days=3),
                self.watered_at + timedelta(days=1),
                self.updated_at,
            )
        )
        bonus_ticks = max((0, (max_time - min_time).total_seconds()))
        ticks += bonus_ticks * 0.5

        ticks *= self.growth_rate
        ticks = int(ticks)
        self.score += ticks

        # Roll for a new mutation
        if self.mutation is None:
            coefficient = 200_000
            if random.random() > ((coefficient - 1) / coefficient) ** ticks:
                self.mutation = random.randrange(len(constants.MUTATIONS))

        # Evolutions
        while self.stage < len(constants.STAGES) - 1:
            if self.score >= constants.STAGE_CUTOFFS[self.stage + 1]:
                self.stage += 1
            else:
                break

    def water(self, user: User = None) -> str:
        """
        Attempt to water the plant.

        Args:
            user: The user watering the plant, if not the plant's owner.

        Returns: A string with a description of the resulting action.
        """
        if self.dead:
            return "There's no point in watering a dead plant."
        elif self.water_supply_percent == 100:
            return "The soil is already damp."

        if user is None:
            self.watered_at = datetime.now()
            self.watered_by = None
            return "You sprinkle some water over your plant."

        query = Plant.select().where(
            Plant.watered_by == user, Plant.watered_at >= datetime.now() - timedelta(hours=8),
        )
        if query.exists():
            return "Your watering can is empty, try again later!"

        self.watered_at = datetime.now()
        self.watered_by = user
        info = f"You water {self.user.username}'s plant for them."

        return info

    def pick_petal(self, user: User = None) -> str:
        """
        Pick a petal from a flowering plant.

        Args:
            user: The user picking the petal, if not the plant's owner.

        Returns: A string with a description of the resulting action.
        """
        if self.dead:
            return "You shouldn't be here!"
        elif self.stage_str != "flowering":
            return "You shouldn't be here!"

        if user is None:
            user = self.user

        target = f"plant_{self.id}"

        last_event = Event.select().where(
            Event.user == user,
            Event.created_at >= datetime.now() - timedelta(days=1),
            Event.event_type == Event.PICK_PETAL,
            Event.target == target,
        )
        if last_event.exists():
            return "The ground around this plant is bare, come back tomorrow!"

        Event.create(user=user, event_type=Event.PICK_PETAL, target=target)

        if self.color_str == "rainbow":
            petal_color = random.choice(constants.COLORS_PLAIN)
        else:
            petal_color = self.color_str

        user.add_item(items.petals[petal_color])

        lines = (
            f"You spot a [{petal_color} petal] lying on the ground nearby.",
            "You pick it up and stick it in your backpack.",
        )
        return "\n".join(lines)

    def shake(self) -> str:
        """
        Shake the user's own plant to get money.

        Coins are accumulated at a rate of 1 coin per 3600 points, which is
        equal to 1 un-adjusted hour of watered plant time.
        """
        multiplier = 3600

        coins = (self.score - self.shaken_at) // multiplier

        # Leave fractional coins unclaimed
        self.shaken_at += coins * multiplier

        # Hard-cap to encourage users to shake every once and a while
        coins = min(coins, 100)

        if coins:
            self.user.add_item(items.coin, quantity=coins)

        if coins < 1:
            msg = "but nothing happens."
        elif coins < 2:
            msg = "and you hear the plink of a single coin."
        elif coins < 5:
            msg = "and a few coins come loose from the leaves."
        elif coins < 25:
            msg = "and a handful of coins sprinkle down."
        elif coins < 99:
            msg = "and coins shower down all around."
        else:
            msg = "and a golden nugget clonks you on the head."

        return f"You shake your plant, {msg}\n(+{coins} coins)"

    def fertilize(self) -> str:
        """
        Attempt to fertilize the plant.

        Returns: A string with a description of the resulting action.
        """
        if self.dead:
            return "It's time to let go."
        elif self.fertilizer_percent:
            return "The soil is still rich with nutrients."

        if not self.user.remove_item(items.fertilizer):
            return "You don't have any fertilizer to apply."

        self.fertilized_at = datetime.now()
        return "You apply a bottle of fertilizer to your plant."

    def harvest(self) -> Plant:
        """
        Harvest the plant and generate a new active plant for the user.
        """
        if self.stage == 5:
            new_generation = self.generation + 1
        else:
            new_generation = 1

        self.dead = True
        self.user_active = None
        self.save()

        return self.__class__.create(
            user=self.user, user_active=self.user, generation=new_generation
        )
