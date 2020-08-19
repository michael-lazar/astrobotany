from textwrap import dedent
from typing import Dict

from . import constants


def for_sale():
    return sorted((i for i in registry.values() if i.for_sale), key=lambda i: i.price)


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
    price=35,
    name="EZ-Grow fertilizer",
    description="""
    A bottle of plant fertilizer.
    
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
    A copper coin.
     
    Can be used to purchase items at the shop.
    
    ```
                 ██████████          
         ██████      ███████      
       ████    ░░░░░░░░░░████      
       ██  ░░░░      ██░░░░████  ░░
     ████  ░░░░  ░░░░██░░░░████    
     ██  ░░░░░░  ░░░░██░░░░░░████  
     ██  ░░░░░░  ░░░░██░░░░░░████  
     ██  ░░░░░░  ░░░░██░░░░░░████  
     ██  ░░░░░░  ░░░░██░░░░░░████  
     ██  ░░░░░░  ░░░░██░░░░░░████  
     ██  ░░░░░░  ░░░░██░░░░░░████  
     ████  ░░░░  ░░░░██░░░░████  ░░
       ██  ░░░░████████░░░░████    
       ████  ░░░░░░░░░░░░████      
         ██████░░░░░░████████      
         ██████▓▓░░▓▓████░
    ```     
    """,
)
