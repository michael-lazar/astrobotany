import typing

from peewee import fn

from astrobotany.art import ArtFile, colorize
from astrobotany.items import Petal, get_date
from astrobotany.models import Event, User


def colorize_petal_text() -> typing.Dict[str, str]:
    color_map = {}
    for color in Petal.petals.keys():
        fg, _ = ArtFile.FLOWER_COLORS[color]
        color_map[color] = colorize(color, fg)
    return color_map


class Pond:
    petal_map = Petal.petals
    color_map = colorize_petal_text()

    def __init__(self, user: User):
        self.user = user

    @classmethod
    def get_blessed_color(cls, ansi_enabled: bool = False) -> str:
        index = get_date() % len(cls.petal_map)
        color = list(cls.petal_map.keys())[index]

        if ansi_enabled:
            return cls.color_map[color]
        else:
            return color

    def tribute(self, color: str) -> str:
        item = self.petal_map[color]
        amount = self.user.get_item_quantity(item)
        if not amount:
            return "Nothing happened."

        self.user.remove_item(item, amount)

        karma = amount
        if color == self.get_blessed_color():
            karma *= 3

        self.user.karma += karma
        self.user.save()

        Event.create(user=self.user, event_type=Event.TRIBUTE_PETAL, target=color, count=amount)
        msg = f"You toss {amount} {color} petal{'s' if amount > 1 else ''} into the pond. Fate smiles upon you."
        return msg

    def get_tribute_total(self) -> int:
        value = (
            Event.select(fn.SUM(Event.count))
            .where(Event.event_type == Event.TRIBUTE_PETAL)
            .scalar()
        )
        return value or 0

    def get_available_petal_data(self, ansi_enabled: bool = False) -> typing.List[dict]:
        petal_data = []
        item: Petal
        for item in Petal.petals.values():
            quantity = self.user.get_item_quantity(item)
            if not quantity:
                continue

            if ansi_enabled:
                petal_str = self.color_map[item.color]
            else:
                petal_str = item.color

            data = {"petal": item, "amount": quantity, "petal_str": petal_str, "color": item.color}
            petal_data.append(data)

        return petal_data
