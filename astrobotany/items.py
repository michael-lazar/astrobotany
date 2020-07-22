from textwrap import dedent


registry = {}


class Item:
    def __init__(self, item_id: int, price: int, name: str, description: str):
        self.item_id = item_id
        self.price = price
        self.name = name
        self.description = dedent(description).strip()

        registry[item_id] = self


paperclip = Item(
    item_id=1,
    price=0,
    name="Paper clip",
    description=r"""
    A length of wire bent into flat loops that is used to hold papers together.
    
    ✨ 📎 ✨
    
    Origin unknown.
    """,
)


fertilizer = Item(
    item_id=2,
    price=0,
    name="EZ-Grow Fertilizer",
    description="""
    A bottle of plant fertilizer.
    
    When applied, will increase plant growth rate by 1.5x for 3 days.    
    """,
)
