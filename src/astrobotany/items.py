from __future__ import annotations

import random
import time
from collections.abc import Iterable
from textwrap import dedent
from typing import TYPE_CHECKING, Any, TypeVar

from astrobotany import constants

if TYPE_CHECKING:
    from astrobotany.models import User


# https://stackoverflow.com/questions/44640479
T = TypeVar("T", bound="Item")


def get_date() -> int:
    return int(time.time() // 86400)


def get_store_items(user: User) -> Iterable[Item]:
    for item in Item.registry.values():
        if item.can_buy(user):
            yield item


def search(name: str) -> Item | None:
    for item in Item.registry.values():
        if item.name == name:
            return item
    return None


class Item:
    registry: dict[int, Item] = {}

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
    def lookup(cls: type[T], item_id: str | int) -> T | None:
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
    petals: dict[str, Petal] = {}

    def __init__(self, color: str):
        name = f"flower petal ({color})"
        description = f"""
        A fallen petal from a plant with {color} blooming flowers.

        Graceful, delicate, and reserved.
        """
        super().__init__(name, description, giftable=True)
        self.color = color
        self.petals[color] = self


class Postcard(Item):
    postcards: list[Postcard] = []

    def __init__(
        self,
        name: str,
        description: str,
        price: int,
        border: tuple[str, str],
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
    ACTIVE_SERIES = 3

    _badges: list[Badge] = []
    _cache: dict[str, Any] = {}
    _cache_date_offset: int = 50

    def __init__(self, name: str, series: int, number: int, symbol: str):
        self.badge_name = name
        self.badge_series = series
        self.badge_number = number
        self.badge_symbol = symbol

        name = f"badge #{self.badge_number}, series {self.badge_series} - {self.badge_symbol}"
        description = f"""
        A collectable badge that can be displayed next to your name.

        Once purchased, go to the astrobotany settings page to turn it on/off.

        Picture     : {self.badge_symbol}
        Description : "{self.badge_name}"
        Collection  : Series {self.badge_series}, number {self.badge_number} of 100
        """
        super().__init__(name, description, giftable=True)
        if self.badge_series == self.ACTIVE_SERIES:
            self._badges.append(self)

    @classmethod
    def load_cache(cls) -> dict:
        date_key = get_date()
        if cls._cache.get("date") != date_key:
            badge_index = (date_key + cls._cache_date_offset) % len(cls._badges)
            badge = cls._badges[badge_index]
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
    description="A copper coin with a portrait of a long-dead cosmonaut on it.",
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

badge_1 = Badge("safety pin", series=1, number=1, symbol="🧷")
badge_2 = Badge("books", series=1, number=2, symbol="📚")
badge_3 = Badge("beach with umbrella", series=1, number=3, symbol="🏖")
badge_4 = Badge("snowman without snow", series=1, number=4, symbol="⛄")
badge_5 = Badge("sunrise over mountains", series=1, number=5, symbol="🌄")
badge_6 = Badge("locomotive", series=1, number=6, symbol="🚂")
badge_7 = Badge("peach", series=1, number=7, symbol="🍑")
badge_8 = Badge("high-heeled shoe", series=1, number=8, symbol="👠")
badge_9 = Badge("green apple", series=1, number=9, symbol="🍏")
badge_10 = Badge("toolbox", series=1, number=10, symbol="🧰")
badge_11 = Badge("vertical traffic light", series=1, number=11, symbol="🚦")
badge_12 = Badge("sleeping face", series=1, number=12, symbol="😴")
badge_13 = Badge("clapper board", series=1, number=13, symbol="🎬")
badge_14 = Badge("eye", series=1, number=14, symbol="👁")
badge_15 = Badge("sailboat", series=1, number=15, symbol="⛵")
badge_16 = Badge("butterfly", series=1, number=16, symbol="🦋")
badge_17 = Badge("castle", series=1, number=17, symbol="🏰")
badge_18 = Badge("drop of blood", series=1, number=18, symbol="🩸")
badge_19 = Badge("microscope", series=1, number=19, symbol="🔬")
badge_20 = Badge("tongue", series=1, number=20, symbol="👅")
badge_21 = Badge("sun behind rain cloud", series=1, number=21, symbol="🌦")
badge_22 = Badge("crossed fingers", series=1, number=22, symbol="🤞")
badge_23 = Badge("raccoon", series=1, number=23, symbol="🦝")
badge_24 = Badge("tent", series=1, number=24, symbol="⛺")
badge_25 = Badge("garlic", series=1, number=25, symbol="🧄")
badge_26 = Badge("poodle", series=1, number=26, symbol="🐩")
badge_27 = Badge("cityscape at dusk", series=1, number=27, symbol="🌆")
badge_28 = Badge("carp streamer", series=1, number=28, symbol="🎏")
badge_29 = Badge("raised hand", series=1, number=29, symbol="✋")
badge_30 = Badge("heart with ribbon", series=1, number=30, symbol="💝")
badge_31 = Badge("leopard", series=1, number=31, symbol="🐆")
badge_32 = Badge("rabbit", series=1, number=32, symbol="🐇")
badge_33 = Badge("blowfish", series=1, number=33, symbol="🐡")
badge_34 = Badge("meat on bone", series=1, number=34, symbol="🍖")
badge_35 = Badge("face with tongue", series=1, number=35, symbol="😛")
badge_36 = Badge("loudly crying face", series=1, number=36, symbol="😭")
badge_37 = Badge("volcano", series=1, number=37, symbol="🌋")
badge_38 = Badge("smiling face with halo", series=1, number=38, symbol="😇")
badge_39 = Badge("sign of the horns", series=1, number=39, symbol="🤘")
badge_40 = Badge("lizard", series=1, number=40, symbol="🦎")
badge_41 = Badge("tired face", series=1, number=41, symbol="😫")
badge_42 = Badge("beverage box", series=1, number=42, symbol="🧃")
badge_43 = Badge("ribbon", series=1, number=43, symbol="🎀")
badge_44 = Badge("level slider", series=1, number=44, symbol="🎚")
badge_45 = Badge("ice cream", series=1, number=45, symbol="🍨")
badge_46 = Badge("bento box", series=1, number=46, symbol="🍱")
badge_47 = Badge("oncoming taxi", series=1, number=47, symbol="🚖")
badge_48 = Badge("carousel horse", series=1, number=48, symbol="🎠")
badge_49 = Badge("flexed biceps", series=1, number=49, symbol="💪")
badge_50 = Badge("cowboy hat face", series=1, number=50, symbol="🤠")
badge_51 = Badge("direct hit", series=1, number=51, symbol="🎯")
badge_52 = Badge("wolf face", series=1, number=52, symbol="🐺")
badge_53 = Badge("peanuts", series=1, number=53, symbol="🥜")
badge_54 = Badge("bacon", series=1, number=54, symbol="🥓")
badge_55 = Badge("man dancing", series=1, number=55, symbol="🕺")
badge_56 = Badge("person biking", series=1, number=56, symbol="🚴")
badge_57 = Badge("ogre", series=1, number=57, symbol="👹")
badge_58 = Badge("baseball", series=1, number=58, symbol="⚾")
badge_59 = Badge("oncoming automobile", series=1, number=59, symbol="🚘")
badge_60 = Badge("crayon", series=1, number=60, symbol="🖍")
badge_61 = Badge("magnet", series=1, number=61, symbol="🧲")
badge_62 = Badge("cup with straw", series=1, number=62, symbol="🥤")
badge_63 = Badge("tooth", series=1, number=63, symbol="🦷")
badge_64 = Badge("zzz", series=1, number=64, symbol="💤")
badge_65 = Badge("test tube", series=1, number=65, symbol="🧪")
badge_66 = Badge("deciduous tree", series=1, number=66, symbol="🌳")
badge_67 = Badge("goat", series=1, number=67, symbol="🐐")
badge_68 = Badge("hammer and wrench", series=1, number=68, symbol="🛠")
badge_69 = Badge("police car light", series=1, number=69, symbol="🚨")
badge_70 = Badge("hot pepper", series=1, number=70, symbol="🌶")
badge_71 = Badge("woozy face", series=1, number=71, symbol="🥴")
badge_72 = Badge("bouquet", series=1, number=72, symbol="💐")
badge_73 = Badge("sports medal", series=1, number=73, symbol="🏅")
badge_74 = Badge("satellite", series=1, number=74, symbol="🛰")
badge_75 = Badge("unicorn face", series=1, number=75, symbol="🦄")
badge_76 = Badge("cat face", series=1, number=76, symbol="🐱")
badge_77 = Badge("cocktail glass", series=1, number=77, symbol="🍸")
badge_78 = Badge("skier", series=1, number=78, symbol="⛷")
badge_79 = Badge("canoe", series=1, number=79, symbol="🛶")
badge_80 = Badge("fox face", series=1, number=80, symbol="🦊")
badge_81 = Badge("ghost", series=1, number=81, symbol="👻")
badge_82 = Badge("motorcycle", series=1, number=82, symbol="🏍")
badge_83 = Badge("barber pole", series=1, number=83, symbol="💈")
badge_84 = Badge("grinning face with big eyes", series=1, number=84, symbol="😃")
badge_85 = Badge("cut of meat", series=1, number=85, symbol="🥩")
badge_86 = Badge("anchor", series=1, number=86, symbol="⚓")
badge_87 = Badge("Japanese bargain button", series=1, number=87, symbol="🉐")
badge_88 = Badge("sport utility vehicle", series=1, number=88, symbol="🚙")
badge_89 = Badge("american football", series=1, number=89, symbol="🏈")
badge_90 = Badge("banana", series=1, number=90, symbol="🍌")
badge_91 = Badge("cactus", series=1, number=91, symbol="🌵")
badge_92 = Badge("circus tent", series=1, number=92, symbol="🎪")
badge_93 = Badge("credit card", series=1, number=93, symbol="💳")
badge_94 = Badge("Statue of Liberty", series=1, number=94, symbol="🗽")
badge_95 = Badge("crescent moon", series=1, number=95, symbol="🌙")
badge_96 = Badge("winking face", series=1, number=96, symbol="😉")
badge_97 = Badge("squid", series=1, number=97, symbol="🦑")
badge_98 = Badge("ringed planet", series=1, number=98, symbol="🪐")
badge_99 = Badge("eggplant", series=1, number=99, symbol="🍆")
badge_100 = Badge("money bag", series=1, number=100, symbol="💰")

audio_synthesizer = Item(
    name="Audio Synthesizer",
    description="An audio synth that can be programmed to play a musical jingle for your plant.",
    price=300,
    buyable=True,
    giftable=True,
)

badge_101 = Badge("bikini", series=2, number=1, symbol="👙")
badge_102 = Badge("high voltage", series=2, number=2, symbol="⚡")
badge_103 = Badge("dog face", series=2, number=3, symbol="🐶")
badge_104 = Badge("kite", series=2, number=4, symbol="🪁")
badge_105 = Badge("soft ice cream", series=2, number=5, symbol="🍦")
badge_106 = Badge("smiling face with sunglasses", series=2, number=6, symbol="😎")
badge_107 = Badge("drum", series=2, number=7, symbol="🥁")
badge_108 = Badge("birthday cake", series=2, number=8, symbol="🎂")
badge_109 = Badge("computer disk", series=2, number=9, symbol="💽")
badge_110 = Badge("violin", series=2, number=10, symbol="🎻")
badge_111 = Badge("green salad", series=2, number=11, symbol="🥗")
badge_112 = Badge("kangaroo", series=2, number=12, symbol="🦘")
badge_113 = Badge("crystal ball", series=2, number=13, symbol="🔮")
badge_114 = Badge("person fencing", series=2, number=14, symbol="🤺")
badge_115 = Badge("camera", series=2, number=15, symbol="📷")
badge_116 = Badge("canned food", series=2, number=16, symbol="🥫")
badge_117 = Badge("bat", series=2, number=17, symbol="🦇")
badge_118 = Badge("bone", series=2, number=18, symbol="🦴")
badge_119 = Badge("mouth", series=2, number=19, symbol="👄")
badge_120 = Badge("vulcan salute", series=2, number=20, symbol="🖖")
badge_121 = Badge("rooster", series=2, number=21, symbol="🐓")
badge_122 = Badge("articulated lorry", series=2, number=22, symbol="🚛")
badge_123 = Badge("baguette bread", series=2, number=23, symbol="🥖")
badge_124 = Badge("couple with heart", series=2, number=24, symbol="💑")
badge_125 = Badge("lipstick", series=2, number=25, symbol="💄")
badge_126 = Badge("bomb", series=2, number=26, symbol="💣")
badge_127 = Badge("pie", series=2, number=27, symbol="🥧")
badge_128 = Badge("money with wings", series=2, number=28, symbol="💸")
badge_129 = Badge("bird", series=2, number=29, symbol="🐦")
badge_130 = Badge("revolving hearts", series=2, number=30, symbol="💞")
badge_131 = Badge("joystick", series=2, number=31, symbol="🕹")
badge_132 = Badge("genie", series=2, number=32, symbol="🧞")
badge_133 = Badge("potato", series=2, number=33, symbol="🥔")
badge_134 = Badge("sauropod", series=2, number=34, symbol="🦕")
badge_135 = Badge("penguin", series=2, number=35, symbol="🐧")
badge_136 = Badge("face blowing a kiss", series=2, number=36, symbol="😘")
badge_137 = Badge("skull", series=2, number=37, symbol="💀")
badge_138 = Badge("person surfing", series=2, number=38, symbol="🏄")
badge_139 = Badge("right-facing fist", series=2, number=39, symbol="🤜")
badge_140 = Badge("fairy", series=2, number=40, symbol="🧚")
badge_141 = Badge("racing car", series=2, number=41, symbol="🏎")
badge_142 = Badge("diving mask", series=2, number=42, symbol="🤿")
badge_143 = Badge("performing arts", series=2, number=43, symbol="🎭")
badge_144 = Badge("hot face", series=2, number=44, symbol="🥵")
badge_145 = Badge("dog", series=2, number=45, symbol="🐕")
badge_146 = Badge("potted plant", series=2, number=46, symbol="🪴")
badge_147 = Badge("desert", series=2, number=47, symbol="🏜")
badge_148 = Badge("bread", series=2, number=48, symbol="🍞")
badge_149 = Badge("rabbit face", series=2, number=49, symbol="🐰")
badge_150 = Badge("red apple", series=2, number=50, symbol="🍎")
badge_151 = Badge("people with bunny ears", series=2, number=51, symbol="👯")
badge_152 = Badge("moai", series=2, number=52, symbol="🗿")
badge_153 = Badge("roller skate", series=2, number=53, symbol="🛼")
badge_154 = Badge("mage", series=2, number=54, symbol="🧙")
badge_155 = Badge("burrito", series=2, number=55, symbol="🌯")
badge_156 = Badge("mate", series=2, number=56, symbol="🧉")
badge_157 = Badge("purse", series=2, number=57, symbol="👛")
badge_158 = Badge("cupcake", series=2, number=58, symbol="🧁")
badge_159 = Badge("person juggling", series=2, number=59, symbol="🤹")
badge_160 = Badge("eyes", series=2, number=60, symbol="👀")
badge_161 = Badge("mosquito", series=2, number=61, symbol="🦟")
badge_162 = Badge("middle finger", series=2, number=62, symbol="🖕")
badge_163 = Badge("flamingo", series=2, number=63, symbol="🦩")
badge_164 = Badge("soccer ball", series=2, number=64, symbol="⚽")
badge_165 = Badge("octopus", series=2, number=65, symbol="🐙")
badge_166 = Badge("baby chick", series=2, number=66, symbol="🐤")
badge_167 = Badge("jack-o-lantern", series=2, number=67, symbol="🎃")
badge_168 = Badge("lady beetle", series=2, number=68, symbol="🐞")
badge_169 = Badge("face screaming in fear", series=2, number=69, symbol="😱")
badge_170 = Badge("winking face with tongue", series=2, number=70, symbol="😜")
badge_171 = Badge("honeybee", series=2, number=71, symbol="🐝")
badge_172 = Badge("pile of poo", series=2, number=72, symbol="💩")
badge_173 = Badge("dolphin", series=2, number=73, symbol="🐬")
badge_174 = Badge("cooking", series=2, number=74, symbol="🍳")
badge_175 = Badge("woman’s hat", series=2, number=75, symbol="👒")
badge_176 = Badge("piñata", series=2, number=76, symbol="🪅")
badge_177 = Badge("four leaf clover", series=2, number=77, symbol="🍀")
badge_178 = Badge("sunrise", series=2, number=78, symbol="🌅")
badge_179 = Badge("dove", series=2, number=79, symbol="🕊")
badge_180 = Badge("pool 8 ball", series=2, number=80, symbol="🎱")
badge_181 = Badge("gem stone", series=2, number=81, symbol="💎")
badge_182 = Badge("taco", series=2, number=82, symbol="🌮")
badge_183 = Badge("guitar", series=2, number=83, symbol="🎸")
badge_184 = Badge("water pistol", series=2, number=84, symbol="🔫")
badge_185 = Badge("woman dancing", series=2, number=85, symbol="💃")
badge_186 = Badge("dna", series=2, number=86, symbol="🧬")
badge_187 = Badge("desert island", series=2, number=87, symbol="🏝")
badge_188 = Badge("wine glass", series=2, number=88, symbol="🍷")
badge_189 = Badge("otter", series=2, number=89, symbol="🦦")
badge_190 = Badge("fishing pole", series=2, number=90, symbol="🎣")
badge_191 = Badge("rosette", series=2, number=91, symbol="🏵")
badge_192 = Badge("hamburger", series=2, number=92, symbol="🍔")
badge_193 = Badge("alien", series=2, number=93, symbol="👽")
badge_194 = Badge("floppy disk", series=2, number=94, symbol="💾")
badge_195 = Badge("pineapple", series=2, number=95, symbol="🍍")
badge_196 = Badge("rice ball", series=2, number=96, symbol="🍙")
badge_197 = Badge("bubble tea", series=2, number=97, symbol="🧋")
badge_198 = Badge("swan", series=2, number=98, symbol="🦢")
badge_199 = Badge("speaker high volume", series=2, number=99, symbol="🔊")
badge_200 = Badge("lollipop", series=2, number=100, symbol="🍭")

fence = Item(
    name="garden fence",
    description="""
    A short garden fence that can be placed around your flowerbed.

    Erecting a fence will prevent visiting players from watering and fertilizing
    your plant. You can tear it down at any time, but doing so will destroy the
    fence.

    > "Solitary trees, if they grow at all, grow strong." - Winston Churchill
    """,
    price=300,
    buyable=True,
    giftable=True,
)

badge_201 = Badge("zany face", series=3, number=1, symbol="🤪")
badge_202 = Badge("hippopotamus", series=3, number=2, symbol="🦛")
badge_203 = Badge("blossom", series=3, number=3, symbol="🌼")
badge_204 = Badge("sunflower", series=3, number=4, symbol="🌻")
badge_205 = Badge("sushi", series=3, number=5, symbol="🍣")
badge_206 = Badge("softball", series=3, number=6, symbol="🥎")
badge_207 = Badge("cheese wedge", series=3, number=7, symbol="🧀")
badge_208 = Badge("key", series=3, number=8, symbol="🔑")
badge_209 = Badge("brick", series=3, number=9, symbol="🧱")
badge_210 = Badge("dizzy", series=3, number=10, symbol="💫")
badge_211 = Badge("laptop", series=3, number=11, symbol="💻")
badge_212 = Badge("satellite antenna", series=3, number=12, symbol="📡")
badge_213 = Badge("clipboard", series=3, number=13, symbol="📋")
badge_214 = Badge("cherry blossom", series=3, number=14, symbol="🌸")
badge_215 = Badge("T-Rex", series=3, number=15, symbol="🦖")
badge_216 = Badge("spider", series=3, number=16, symbol="🕷")
badge_217 = Badge("disco ball", series=3, number=17, symbol="🪩")
badge_218 = Badge("compass", series=3, number=18, symbol="🧭")
badge_219 = Badge("snowboarder", series=3, number=19, symbol="🏂")
badge_220 = Badge("merperson", series=3, number=20, symbol="🧜")
badge_221 = Badge("mouse face", series=3, number=21, symbol="🐭")
badge_222 = Badge("shopping cart", series=3, number=22, symbol="🛒")
badge_223 = Badge("butter", series=3, number=23, symbol="🧈")
badge_224 = Badge("brain", series=3, number=24, symbol="🧠")
badge_225 = Badge("man in tuxedo", series=3, number=25, symbol="🤵")
badge_226 = Badge("lion face", series=3, number=26, symbol="🦁")
badge_227 = Badge("money mouth face", series=3, number=27, symbol="🤑")
badge_228 = Badge("syringe", series=3, number=28, symbol="💉")
badge_229 = Badge("star-struck face", series=3, number=29, symbol="🤩")
badge_230 = Badge("turtle", series=3, number=30, symbol="🐢")
badge_231 = Badge("scorpion", series=3, number=31, symbol="🦂")
badge_232 = Badge("computer mouse", series=3, number=32, symbol="🖱")
badge_233 = Badge("curling stone", series=3, number=33, symbol="🥌")
badge_234 = Badge("magic wand", series=3, number=34, symbol="🪄")
badge_235 = Badge("abacus", series=3, number=35, symbol="🧮")
badge_236 = Badge("military medal", series=3, number=36, symbol="🎖")
badge_237 = Badge("snowflake", series=3, number=37, symbol="❄️")
badge_238 = Badge("globe showing Europe-Africa", series=3, number=38, symbol="🌍")
badge_239 = Badge("globe showing Americas", series=3, number=39, symbol="🌎")
badge_240 = Badge("crab", series=3, number=40, symbol="🦀")
badge_241 = Badge("lobster", series=3, number=41, symbol="🦞")
badge_242 = Badge("vampire", series=3, number=42, symbol="🧛‍")
badge_243 = Badge("clown face", series=3, number=43, symbol="🤡")
badge_244 = Badge("palm tree", series=3, number=44, symbol="🌴")
badge_245 = Badge("coconut", series=3, number=45, symbol="🥥")
badge_246 = Badge("grapes", series=3, number=46, symbol="🍇")
badge_247 = Badge("strawberry", series=3, number=47, symbol="🍓")
badge_248 = Badge("cherries", series=3, number=48, symbol="🍒")
badge_249 = Badge("watermelon", series=3, number=49, symbol="🍉")
badge_250 = Badge("tennis", series=3, number=50, symbol="🎾")
badge_251 = Badge("milk", series=3, number=51, symbol="🥛")
badge_252 = Badge("person rowing boat", series=3, number=52, symbol="🚣")
badge_253 = Badge("ear of corn", series=3, number=53, symbol="🌽")
badge_254 = Badge("tractor", series=3, number=54, symbol="🚜")
badge_255 = Badge("scissors", series=3, number=55, symbol="✂️")
badge_256 = Badge("fire engine", series=3, number=56, symbol="🚒")
badge_257 = Badge("hedgehog", series=3, number=57, symbol="🦔")
badge_258 = Badge("boomerang", series=3, number=58, symbol="🪃")
badge_259 = Badge("flashlight", series=3, number=59, symbol="🔦")
badge_260 = Badge("lotus", series=3, number=60, symbol="🪷")
badge_261 = Badge("thermometer", series=3, number=61, symbol="🌡")
badge_262 = Badge("trident emblem", series=3, number=62, symbol="🔱")
badge_263 = Badge("mountain", series=3, number=63, symbol="⛰")
badge_264 = Badge("glasses", series=3, number=64, symbol="👓")
badge_265 = Badge("ninja", series=3, number=65, symbol="🥷")
badge_266 = Badge("beaver", series=3, number=66, symbol="🦫")
badge_267 = Badge("spoon", series=3, number=67, symbol="🥄")
badge_268 = Badge("hole", series=3, number=68, symbol="🕳")
badge_269 = Badge("toilet", series=3, number=69, symbol="🚽")
badge_270 = Badge("robot face", series=3, number=70, symbol="🤖")
badge_271 = Badge("superhero", series=3, number=71, symbol="🦸")
badge_272 = Badge("bug", series=3, number=72, symbol="🐛")
badge_273 = Badge("carrot", series=3, number=73, symbol="🥕")
badge_274 = Badge("mushroom", series=3, number=74, symbol="🍄")
badge_275 = Badge("adhesive bandage", series=3, number=75, symbol="🩹")
badge_276 = Badge("drop of water", series=3, number=76, symbol="💧")
badge_277 = Badge("bowl with spoon", series=3, number=77, symbol="🥣")
badge_278 = Badge("safety vest", series=3, number=78, symbol="🦺")
badge_279 = Badge("one-piece swimsuit", series=3, number=79, symbol="🩱")
badge_280 = Badge("pancakes", series=3, number=80, symbol="🥞")
badge_281 = Badge("shopping bags", series=3, number=81, symbol="🛍")
badge_282 = Badge("firecracker", series=3, number=82, symbol="🧨")
badge_283 = Badge("carpentry saw", series=3, number=83, symbol="🪚")
badge_284 = Badge("petri dish", series=3, number=84, symbol="🧫")
badge_285 = Badge("hook", series=3, number=85, symbol="🪝")
badge_286 = Badge("feather", series=3, number=86, symbol="🪶")
badge_287 = Badge("placard", series=3, number=87, symbol="🪧")
badge_288 = Badge("toothbrush", series=3, number=88, symbol="🪥")
badge_289 = Badge("hourglass", series=3, number=89, symbol="⏳")
badge_290 = Badge("yo-yo", series=3, number=90, symbol="🪀")
badge_291 = Badge("factory", series=3, number=91, symbol="🏭")
badge_292 = Badge("white flower", series=3, number=92, symbol="💮")
badge_293 = Badge("bookmark", series=3, number=93, symbol="🔖")
badge_294 = Badge("tangerine", series=3, number=94, symbol="🍊")
badge_295 = Badge("clinking beer mugs", series=3, number=95, symbol="🍻")
badge_296 = Badge("spade suit", series=3, number=96, symbol="♠️")
badge_297 = Badge("tulip", series=3, number=97, symbol="🌷")
badge_298 = Badge("herb", series=3, number=98, symbol="🌿")
badge_299 = Badge("shamrock", series=3, number=99, symbol="☘️")
badge_300 = Badge("partying face", series=3, number=100, symbol="🥳")
