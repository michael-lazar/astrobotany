from typing import Iterable

from .art import colorize
from .models import Plant


class Leaderboard:
    name: str = ""

    medal_colors = {
        1: 205,  # Gold
        2: 231,  # Silver
        3: 115,  # Bronze
    }

    def __init__(self, count: int = 10):
        self.count = count

    def list_top_items(self) -> Iterable:
        raise NotImplementedError

    def render(self, ansi_enabled: bool = False, width: int = 63) -> str:
        title = f"Daily Leaderboard - {self.name}"
        table = [
            "╔" + "═" * (width - 2) + "╗",
            "║" + title.center(width - 2) + "║",
            "╠" + "═" * 25 + "╤" + "═" * (width - 28) + "╣",
        ]

        items = list(self.list_top_items())
        while len(items) < self.count:
            items.append(["", ""])

        for i, (col1, col2) in enumerate(items, start=1):
            name = f"{i:>2}. {col1[:19]:<19}"
            if ansi_enabled:
                if col1 and i in self.medal_colors:
                    name = colorize(name, fg=self.medal_colors[i])
            row = f"║ {name} │ {col2:<{width - 30}} ║"
            table.append(row)

        table.append("╚" + "═" * 25 + "╧" + "═" * (width - 28) + "╝")
        return "\n".join(table)


class HighScore(Leaderboard):
    name = "Highest Score"

    def list_top_items(self):
        plants = Plant.all_active().order_by(Plant.score.desc())
        for plant in plants.limit(self.count):
            yield plant.user.username, f"{plant.score} points"


# TODO: Add more rotating leaderboards. Oldest plant, newest flowers, most
#       recently watered, most neighborly, etc.
