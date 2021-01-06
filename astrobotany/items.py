from __future__ import annotations

import random
import time
import typing
from textwrap import dedent

from . import constants

if typing.TYPE_CHECKING:
    from .models import User


# https://stackoverflow.com/questions/44640479
T = typing.TypeVar("T", bound="Item")


def get_date() -> int:
    return int(time.time() // 86400)


def get_store_items(user: User) -> typing.Iterable[Item]:
    for item in Item.registry.values():
        if item.can_buy(user):
            yield item


def search(name: str) -> typing.Optional[Item]:
    for item in Item.registry.values():
        if item.name == name:
            return item
    return None


class Item:

    registry: typing.Dict[int, Item] = {}

    def __init__(
        self,
        name: str,
        description: str,
        price: int = 0,
        buyable: bool = False,
        usable: bool = False,
        giftable: bool = False,
    ):
        self.item_id = len(self.registry) + 1

        self.name = name
        self._description = dedent(description).strip()
        self._price = price
        self._buyable = buyable
        self._usable = usable
        self._giftable = giftable

        self.registry[self.item_id] = self

    @classmethod
    def lookup(cls: typing.Type[T], item_id: typing.Union[str, int]) -> typing.Optional[T]:
        try:
            item = cls.registry[int(item_id)]
        except (ValueError, KeyError):
            return None

        if not isinstance(item, cls):
            # Ensure that calling lookup() from a subclass only returns items of that subclass
            return None

        return item

    def can_buy(self, user: User) -> bool:
        return self._buyable

    def can_use(self, user: User) -> bool:
        return self._usable

    def can_gift(self, user: User) -> bool:
        return self._giftable

    def get_price(self, user: User) -> int:
        return self._price

    def get_inventory_description(self, user: User) -> str:
        return self._description

    def get_store_description(self, user: User) -> str:
        return self._description


class Petal(Item):

    petals: typing.Dict[str, Petal] = {}

    def __init__(self, color: str):
        name = f"flower petal ({color})"
        description = f"""
        A fallen petal from a plant with {color} blooming flowers.

        Graceful, delicate, and reserved.
        """
        super().__init__(name, description, giftable=True)
        self.petals[color] = self


class Postcard(Item):

    postcards: typing.List[Postcard] = []

    def __init__(
        self,
        name: str,
        description: str,
        price: int,
        border: typing.Tuple[str, str],
    ):
        self.border = border
        sample_letter = self.format_message(
            "I think that I shall never see",
            "A poem lovely as a tree.",
            "A tree whose hungry mouth is prest",
            "Against the earth’s sweet flowing breast;",
        )
        description += "\n\nExample:\n\n" + sample_letter
        super().__init__(name, description, price=price, buyable=True, giftable=True)
        self.postcards.append(self)

    def format_message(self, *lines):
        message = [self.border[0], *(f"> {line}" for line in lines), self.border[1]]
        return "\n".join(message)


class Badge(Item):

    badges: typing.List[Badge] = []
    _cache: typing.Dict[str, typing.Any] = {}
    _cache_date_offset: int = 50

    def __init__(self, name: str, number: int, symbol: str):
        self.badge_name = name
        self.badge_number = number
        self.badge_symbol = symbol

        name = f"badge #{self.badge_number} - {self.badge_symbol}"
        description = f"""
        A collectable badge that can be displayed next to your name.
        
        Once purchased, go to the astrobotany settings page to turn it on/off.
        
        Picture     : {self.badge_symbol}
        Description : "{self.badge_name}"
        Collection  : Series 1, number {self.badge_number} of 100
        """
        super().__init__(name, description, giftable=True)
        self.badges.append(self)

    @classmethod
    def load_cache(cls) -> dict:
        date_key = get_date()
        if cls._cache.get("date") != date_key:
            badge_index = (date_key + cls._cache_date_offset) % len(cls.badges)
            badge = cls.badges[badge_index]
            price = random.randint(300, 800)
            cls._cache = {"date": date_key, "badge": badge, "price": price}
        return cls._cache

    def get_price(self, user: User) -> int:
        cache = self.load_cache()
        return cache["price"]

    def can_buy(self, user: User) -> bool:
        cache = self.load_cache()
        return cache["badge"] == self

    def get_store_description(self, user: User) -> str:
        minutes_remaining = int(86400 - time.time() % 86400) // 60
        hours, minutes = divmod(minutes_remaining, 60)
        extra = f"\n\nThis offer will expire in {hours} hours, {minutes} minutes."
        return self._description + extra


paperclip = Item(
    name="paper clip",
    description=r"""
    A length of wire bent into flat loops that is used to hold papers together.
    
    ✨ 📎 ✨
    
    Origin unknown.
    """,
)

fertilizer = Item(
    name="ez-grow fertilizer",
    description="""
    A bottle of EZ-Grow™ premium plant fertilizer.
    
    When applied, will increase plant growth rate by 1.5x for 3 days.    
    """,
    price=75,
    buyable=True,
    giftable=True,
)

red_petal = Petal("red")
orange_petal = Petal("orange")
yellow_petal = Petal("yellow")
green_petal = Petal("green")
blue_petal = Petal("blue")
indigo_petal = Petal("indigo")
violet_petal = Petal("violet")
white_petal = Petal("white")
black_petal = Petal("black")
gold_petal = Petal("gold")

coin = Item(
    name="coin",
    description="""
    A copper coin with a portrait of a long-dead cosmonaut on it.
    
    Go buy yourself something shiny.
    """,
)

plain_postcard = Postcard(
    name="plain postcard",
    description="A blank postcard that can be mailed to another user.",
    border=constants.BORDERS["plain"],
    price=50,
)

fancy_postcard = Postcard(
    name="fancy postcard",
    description="A fancy postcard with an intricate design.",
    border=constants.BORDERS["fancy"],
    price=125,
)

cool_postcard = Postcard(
    name="cool postcard",
    description="A rad postcard with a picture of a bird on it.",
    border=constants.BORDERS["cool"],
    price=125,
)

romantic_postcard = Postcard(
    name="romantic postcard",
    description="A romantic postcard with sparkling hearts on it.",
    border=constants.BORDERS["romantic"],
    price=125,
)

christmas_cheer = Item(
    name="bottle of christmas cheer",
    description="""
    A bottle of distilled christmas cheer.
    
    An inscription on the back reads...
    
    > Instructions: Single use application only.
    > To activate, mix with water and sprinkle over plant.
    > For best results, hum along to the tune of "O Christmas Tree".
    """,
)

badge_1 = Badge(name="safety pin", number=1, symbol="🧷")
badge_2 = Badge(name="books", number=2, symbol="📚")
badge_3 = Badge(name="beach with umbrella", number=3, symbol="🏖")
badge_4 = Badge(name="snowman without snow", number=4, symbol="⛄")
badge_5 = Badge(name="sunrise over mountains", number=5, symbol="🌄")
badge_6 = Badge(name="locomotive", number=6, symbol="🚂")
badge_7 = Badge(name="peach", number=7, symbol="🍑")
badge_8 = Badge(name="high-heeled shoe", number=8, symbol="👠")
badge_9 = Badge(name="green apple", number=9, symbol="🍏")
badge_10 = Badge(name="toolbox", number=10, symbol="🧰")
badge_11 = Badge(name="vertical traffic light", number=11, symbol="🚦")
badge_12 = Badge(name="sleeping face", number=12, symbol="😴")
badge_13 = Badge(name="clapper board", number=13, symbol="🎬")
badge_14 = Badge(name="eye", number=14, symbol="👁")
badge_15 = Badge(name="sailboat", number=15, symbol="⛵")
badge_16 = Badge(name="butterfly", number=16, symbol="🦋")
badge_17 = Badge(name="castle", number=17, symbol="🏰")
badge_18 = Badge(name="drop of blood", number=18, symbol="🩸")
badge_19 = Badge(name="microscope", number=19, symbol="🔬")
badge_20 = Badge(name="tongue", number=20, symbol="👅")
badge_21 = Badge(name="sun behind rain cloud", number=21, symbol="🌦")
badge_22 = Badge(name="crossed fingers", number=22, symbol="🤞")
badge_23 = Badge(name="raccoon", number=23, symbol="🦝")
badge_24 = Badge(name="tent", number=24, symbol="⛺")
badge_25 = Badge(name="garlic", number=25, symbol="🧄")
badge_26 = Badge(name="poodle", number=26, symbol="🐩")
badge_27 = Badge(name="cityscape at dusk", number=27, symbol="🌆")
badge_28 = Badge(name="carp streamer", number=28, symbol="🎏")
badge_29 = Badge(name="raised hand", number=29, symbol="✋")
badge_30 = Badge(name="heart with ribbon", number=30, symbol="💝")
badge_31 = Badge(name="leopard", number=31, symbol="🐆")
badge_32 = Badge(name="rabbit", number=32, symbol="🐇")
badge_33 = Badge(name="blowfish", number=33, symbol="🐡")
badge_34 = Badge(name="meat on bone", number=34, symbol="🍖")
badge_35 = Badge(name="face with tongue", number=35, symbol="😛")
badge_36 = Badge(name="loudly crying face", number=36, symbol="😭")
badge_37 = Badge(name="volcano", number=37, symbol="🌋")
badge_38 = Badge(name="smiling face with halo", number=38, symbol="😇")
badge_39 = Badge(name="sign of the horns", number=39, symbol="🤘")
badge_40 = Badge(name="lizard", number=40, symbol="🦎")
badge_41 = Badge(name="tired face", number=41, symbol="😫")
badge_42 = Badge(name="beverage box", number=42, symbol="🧃")
badge_43 = Badge(name="ribbon", number=43, symbol="🎀")
badge_44 = Badge(name="level slider", number=44, symbol="🎚")
badge_45 = Badge(name="ice cream", number=45, symbol="🍨")
badge_46 = Badge(name="bento box", number=46, symbol="🍱")
badge_47 = Badge(name="oncoming taxi", number=47, symbol="🚖")
badge_48 = Badge(name="carousel horse", number=48, symbol="🎠")
badge_49 = Badge(name="flexed biceps", number=49, symbol="💪")
badge_50 = Badge(name="cowboy hat face", number=50, symbol="🤠")
badge_51 = Badge(name="direct hit", number=51, symbol="🎯")
badge_52 = Badge(name="wolf face", number=52, symbol="🐺")
badge_53 = Badge(name="peanuts", number=53, symbol="🥜")
badge_54 = Badge(name="bacon", number=54, symbol="🥓")
badge_55 = Badge(name="man dancing", number=55, symbol="🕺")
badge_56 = Badge(name="person biking", number=56, symbol="🚴")
badge_57 = Badge(name="ogre", number=57, symbol="👹")
badge_58 = Badge(name="baseball", number=58, symbol="⚾")
badge_59 = Badge(name="oncoming automobile", number=59, symbol="🚘")
badge_60 = Badge(name="crayon", number=60, symbol="🖍")
badge_61 = Badge(name="magnet", number=61, symbol="🧲")
badge_62 = Badge(name="cup with straw", number=62, symbol="🥤")
badge_63 = Badge(name="tooth", number=63, symbol="🦷")
badge_64 = Badge(name="zzz", number=64, symbol="💤")
badge_65 = Badge(name="test tube", number=65, symbol="🧪")
badge_66 = Badge(name="deciduous tree", number=66, symbol="🌳")
badge_67 = Badge(name="goat", number=67, symbol="🐐")
badge_68 = Badge(name="hammer and wrench", number=68, symbol="🛠")
badge_69 = Badge(name="police car light", number=69, symbol="🚨")
badge_70 = Badge(name="hot pepper", number=70, symbol="🌶")
badge_71 = Badge(name="woozy face", number=71, symbol="🥴")
badge_72 = Badge(name="bouquet", number=72, symbol="💐")
badge_73 = Badge(name="sports medal", number=73, symbol="🏅")
badge_74 = Badge(name="satellite", number=74, symbol="🛰")
badge_75 = Badge(name="unicorn face", number=75, symbol="🦄")
badge_76 = Badge(name="cat face", number=76, symbol="🐱")
badge_77 = Badge(name="cocktail glass", number=77, symbol="🍸")
badge_78 = Badge(name="skier", number=78, symbol="⛷")
badge_79 = Badge(name="canoe", number=79, symbol="🛶")
badge_80 = Badge(name="fox face", number=80, symbol="🦊")
badge_81 = Badge(name="ghost", number=81, symbol="👻")
badge_82 = Badge(name="motorcycle", number=82, symbol="🏍")
badge_83 = Badge(name="barber pole", number=83, symbol="💈")
badge_84 = Badge(name="grinning face with big eyes", number=84, symbol="😃")
badge_85 = Badge(name="cut of meat", number=85, symbol="🥩")
badge_86 = Badge(name="anchor", number=86, symbol="⚓")
badge_87 = Badge(name="Japanese bargain button", number=87, symbol="🉐")
badge_88 = Badge(name="sport utility vehicle", number=88, symbol="🚙")
badge_89 = Badge(name="american football", number=89, symbol="🏈")
badge_90 = Badge(name="banana", number=90, symbol="🍌")
badge_91 = Badge(name="cactus", number=91, symbol="🌵")
badge_92 = Badge(name="circus tent", number=92, symbol="🎪")
badge_93 = Badge(name="credit card", number=93, symbol="💳")
badge_94 = Badge(name="Statue of Liberty", number=94, symbol="🗽")
badge_95 = Badge(name="crescent moon", number=95, symbol="🌙")
badge_96 = Badge(name="winking face", number=96, symbol="😉")
badge_97 = Badge(name="squid", number=97, symbol="🦑")
badge_98 = Badge(name="ringed planet", number=98, symbol="🪐")
badge_99 = Badge(name="eggplant", number=99, symbol="🍆")
badge_100 = Badge(name="money bag", number=100, symbol="💰")
