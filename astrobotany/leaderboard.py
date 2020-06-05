from typing import Iterable, Dict
from datetime import datetime

from .art import colorize
from .models import Plant


class Leaderboard:
    name: str = ""
    medal_colors: Dict[int, int] = {
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


class OldestPlant(Leaderboard):
    name = "Oldest Plant"

    def list_top_items(self):
        query = Plant.all_active()
        query = query.order_by(Plant.created_at.asc())
        query = query.limit(self.count)
        for plant in query:
            yield plant.user.username, f"{plant.age} days"


class PrettyFlowers(Leaderboard):
    name = "Prettiest Flowers"

    def list_top_items(self):
        query = Plant.all_active()
        query = query.where(Plant.stage == 4)
        query = query.order_by(Plant.score.desc())
        query = query.limit(self.count)
        for plant in query:
            yield plant.user.username, f"{plant.color_str} {plant.species_str}"


class RecentlyWatered(Leaderboard):
    name = "Most Recently Watered"

    def list_top_items(self):
        query = Plant.all_active()
        query = query.where(Plant.watered_by.is_null(True))
        query = query.order_by(Plant.watered_at.desc())
        query = query.limit(self.count)
        for plant in query:
            dt = (datetime.now() - plant.watered_at).total_seconds() // 60
            yield plant.user.username, f"{dt:0.0f} minutes ago"


class MostNeighborly(Leaderboard):
    name = "Most Neighborly"

    def list_top_items(self):
        query = Plant.all_active()
        query = query.where(Plant.watered_by.is_null(False))
        query = query.order_by(Plant.watered_at.desc())
        query = query.limit(self.count)
        for plant in query:
            yield plant.watered_by.username, f"visited {plant.user.username}"


_leaderboards = [HighScore, OldestPlant, PrettyFlowers, RecentlyWatered, MostNeighborly]


def get_daily_leaderboard():
    offset = (datetime.now() - datetime(1970, 1, 1)).days
    return _leaderboards[offset % len(_leaderboards)]()
