from textwrap import dedent
from typing import Dict, List

from . import constants


class Item:
    def __init__(self, price: int, name: str, description: str, for_sale: bool = False) -> None:
        self.item_id = len(registry) + 1
        self.price = price
        self.name = name
        self.description = dedent(description).strip()
        self.for_sale = for_sale

        registry[self.item_id] = self


registry: Dict[int, Item] = {}


paperclip = Item(
    price=0,
    name="paper clip",
    description=r"""
    A length of wire bent into flat loops that is used to hold papers together.
    
    ✨ 📎 ✨
    
    Origin unknown.
    """,
)


fertilizer = Item(
    price=75,
    name="ez-grow fertilizer",
    description="""
    A bottle of EZ-Grow™ premium plant fertilizer.
    
    When applied, will increase plant growth rate by 1.5x for 3 days.    
    """,
    for_sale=True,
)


petals: Dict[str, Item] = {}
for color in constants.COLORS_PLAIN:
    if color in ["orange", "indigo"]:
        description = f"an {color}"
    else:
        description = f"a {color}"

    petals[color] = Item(
        price=0,
        name=f"flower petal [{color}]",
        description=f"""
        A single flower petal from {description} plant.

        Graceful, delicate, and reserved.
        """,
    )

coin = Item(
    price=1,
    name="coin",
    description="""
    A copper coin with a portrait of a long-dead cosmonaut on it.
    
    Go buy yourself something shiny.
    """,
)


class Postcard(Item):

    postcards: List["Postcard"] = []

    def __init__(self, border, **kwargs):
        super().__init__(**kwargs)
        self.border = border

        sample_letter = self.format_message(
            "I think that I shall never see",
            "A poem lovely as a tree.",
            "A tree whose hungry mouth is prest",
            "Against the earth’s sweet flowing breast;",
        )
        self.description += "\n\nExample:\n\n" + sample_letter

        self.postcards.append(self)

    def format_message(self, *lines):
        message = [self.border[0], *(f"> {line}" for line in lines), self.border[1]]
        return "\n".join(message)


plain_postcard = Postcard(
    price=50,
    name="plain postcard",
    border=constants.BORDERS["plain"],
    description="""
    A blank postcard that can be mailed to another user.
    """,
    for_sale=True,
)

fancy_postcard = Postcard(
    price=125,
    name="fancy postcard",
    border=constants.BORDERS["fancy"],
    description="""
    A fancy postcard with an intricate design.
    """,
    for_sale=True,
)

cool_postcard = Postcard(
    price=125,
    name="cool postcard",
    border=constants.BORDERS["cool"],
    description="""
    A rad postcard with a picture of a bird on it.
    """,
    for_sale=True,
)

romantic = Postcard(
    price=125,
    name="romantic postcard",
    border=constants.BORDERS["romantic"],
    description="""
    A romantic postcard with sparkling hearts on it.
    """,
    for_sale=True,
)

christmas_cheer = Item(
    price=0,
    name="bottle of christmas cheer",
    description="""
    A bottle of distilled christmas cheer.
    
    An inscription on the back reads...
    
    > Instructions: Single use application only.
    > To activate, mix with water and sprinkle over plant.
    > For best results, hum along to the tune of "O Christmas Tree".
    """,
    for_sale=False,
)
