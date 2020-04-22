import math
import random
from datetime import date, datetime, timedelta
from typing import List, Optional

from faker import Faker
from peewee import (
    BooleanField,
    DateTimeField,
    ForeignKeyField,
    IntegerField,
    Model,
    SqliteDatabase,
    TextField,
)

from . import constants
from .art import render_art, colorize


fake = Faker()


def init_db(filename: str = ":memory:") -> SqliteDatabase:
    """
    Bind an SQLite database to the Peewee ORM models.
    """
    models = [User, Message, Plant]
    db = SqliteDatabase(filename)
    db.bind(models)
    db.create_tables(models)
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


class User(Model):
    """
    A user account corresponding to a TLS client certificate.
    """

    user_id = IntegerField(unique=True, index=True)
    username = TextField()
    created_at = DateTimeField(default=datetime.now)
    ansi_enabled = BooleanField(default=False)

    @property
    def plant(self) -> "Plant":
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


class Message(Model):
    """
    A public message posted to the community message board.
    """

    user = ForeignKeyField(User, backref="messages")
    created_at = DateTimeField(default=datetime.now)
    text = TextField()


class Plant(Model):
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
    def water_supply_percent(self) -> int:
        """
        The percentage of water supply remaining, as an integer from 0 to 100.
        """
        seconds_per_day = 24 * 60 * 60
        elapsed_seconds = (datetime.now() - self.watered_at).total_seconds()
        remaining_water = max(0.0, 1 - (elapsed_seconds / seconds_per_day))
        return math.ceil(remaining_water * 100)

    def get_water_gauge(self, ansi_enabled=False) -> str:
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

    def get_ascii_art(self, ansi_enabled=False) -> str:
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

    def get_observation(self) -> str:
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

    def water(self, user_id: str = None) -> str:
        """
        Attempt to water the plant.

        Args:
            user_id: The user watering the plant, if not the plant's owner.

        Returns: A string with a description of the resulting action.
        """
        if self.dead:
            return "There's no point in watering a dead plant."
        elif self.water_supply_percent == 100:
            return "The soil is already damp."

        self.watered_at = datetime.now()
        if user_id is not None:
            self.watered_by = user_id
            info = f"You water {self.user.username}'s plant for them."
        else:
            self.watered_by = None
            info = "You sprinkle some water over your plant."

        return info

    def harvest(self) -> "Plant":
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
