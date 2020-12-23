from __future__ import annotations

import typing
from textwrap import dedent

from . import constants

if typing.TYPE_CHECKING:
    from .models import User


# https://stackoverflow.com/questions/44640479
T = typing.TypeVar("T", bound="Item")


def get_store_items(user: User) -> typing.Iterable[Item]:
    for item in Item.registry.values():
        if item.can_buy(user):
            yield item


class Item:

    registry: typing.Dict[int, Item] = {}

    def __init__(
        self,
        item_id: int,
        name: str,
        description: str,
        price: int = 0,
        buyable: bool = False,
        usable: bool = False,
        giftable: bool = False,
    ):
        self.item_id = item_id
        self.name = name
        self.description = dedent(description).strip()
        self.price = price
        self.buyable = buyable
        self.usable = usable
        self.giftable = giftable

    @classmethod
    def register(cls: typing.Type[T], name: str, *args, **kwargs) -> T:
        item_id = len(cls.registry) + 1
        item = cls(item_id, name, *args, **kwargs)
        cls.registry[item_id] = item
        return item

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
        return self.buyable

    def can_use(self, user: User) -> bool:
        return self.usable

    def can_gift(self, user: User) -> bool:
        return self.giftable

    def get_inventory_description(self, user: User) -> str:
        return self.description

    def get_store_description(self, user: User) -> str:
        return self.description


class Petal(Item):

    petals: typing.Dict[str, Petal] = {}

    def __init__(self, item_id: int, color: str, **kwargs):
        name = f"flower petal ({color})"
        description = f"""
        A fallen petal from a plant with {color} blooming flowers.

        Graceful, delicate, and reserved.
        """
        super().__init__(item_id, name, description, **kwargs)

    @classmethod
    def register(cls, name: str, *args, **kwargs) -> Petal:
        petal = super().register(name, *args, **kwargs)
        petal = typing.cast(Petal, petal)
        cls.petals[name] = petal
        return petal


class Postcard(Item):

    postcards: typing.List[Postcard] = []

    def __init__(
        self, item_id: int, name: str, description: str, border: typing.Tuple[str, str], **kwargs
    ):
        self.border = border

        sample_letter = self.format_message(
            "I think that I shall never see",
            "A poem lovely as a tree.",
            "A tree whose hungry mouth is prest",
            "Against the earth’s sweet flowing breast;",
        )
        description += "\n\nExample:\n\n" + sample_letter
        super().__init__(item_id, name, description, **kwargs)

    @classmethod
    def register(cls, *args, **kwargs) -> Postcard:
        postcard = super().register(*args, **kwargs)
        postcard = typing.cast(Postcard, postcard)
        cls.postcards.append(postcard)
        return postcard

    def format_message(self, *lines):
        message = [self.border[0], *(f"> {line}" for line in lines), self.border[1]]
        return "\n".join(message)


paperclip = Item.register(
    name="paper clip",
    description=r"""
    A length of wire bent into flat loops that is used to hold papers together.
    
    ✨ 📎 ✨
    
    Origin unknown.
    """,
)

fertilizer = Item.register(
    name="ez-grow fertilizer",
    description="""
    A bottle of EZ-Grow™ premium plant fertilizer.
    
    When applied, will increase plant growth rate by 1.5x for 3 days.    
    """,
    price=75,
    buyable=True,
    giftable=True,
)

red_petal = Petal.register("red", giftable=True)
orange_petal = Petal.register("orange", giftable=True)
yellow_petal = Petal.register("yellow", giftable=True)
green_petal = Petal.register("green", giftable=True)
blue_petal = Petal.register("blue", giftable=True)
indigo_petal = Petal.register("indigo", giftable=True)
violet_petal = Petal.register("violet", giftable=True)
white_petal = Petal.register("white", giftable=True)
black_petal = Petal.register("black", giftable=True)
gold_petal = Petal.register("gold", giftable=True)

coin = Item.register(
    name="coin",
    description="""
    A copper coin with a portrait of a long-dead cosmonaut on it.
    
    Go buy yourself something shiny.
    """,
)

plain_postcard = Postcard.register(
    name="plain postcard",
    description="A blank postcard that can be mailed to another user.",
    border=constants.BORDERS["plain"],
    price=50,
    buyable=True,
    giftable=True,
)

fancy_postcard = Postcard.register(
    name="fancy postcard",
    description="A fancy postcard with an intricate design.",
    border=constants.BORDERS["fancy"],
    price=125,
    buyable=True,
    giftable=True,
)

cool_postcard = Postcard.register(
    name="cool postcard",
    description="A rad postcard with a picture of a bird on it.",
    border=constants.BORDERS["cool"],
    price=125,
    buyable=True,
    giftable=True,
)

romantic_postcard = Postcard.register(
    name="romantic postcard",
    description="A romantic postcard with sparkling hearts on it.",
    border=constants.BORDERS["romantic"],
    price=125,
    buyable=True,
    giftable=True,
)

christmas_cheer = Item.register(
    name="bottle of christmas cheer",
    description="""
    A bottle of distilled christmas cheer.
    
    An inscription on the back reads...
    
    > Instructions: Single use application only.
    > To activate, mix with water and sprinkle over plant.
    > For best results, hum along to the tune of "O Christmas Tree".
    """,
)
