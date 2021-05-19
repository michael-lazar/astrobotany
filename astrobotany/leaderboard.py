import csv
import io
from typing import Iterable

from .models import Plant, User


class Leaderboard:
    key: str = ""
    name: str = ""

    def __init__(self, count: int = 10) -> None:
        self.count = count

    def list_top_items(self) -> Iterable:
        raise NotImplementedError

    def render_table(self, width: int = 50) -> str:
        title = f"Leaderboard - {self.name}"
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
            row = f"║ {name} │ {col2:<{width - 30}} ║"
            table.append(row)

        table.append("╚" + "═" * 25 + "╧" + "═" * (width - 28) + "╝")
        return "\n".join(table)

    def render_csv(self) -> str:
        buffer = io.StringIO()
        writer = csv.writer(buffer)
        writer.writerow(["rank", "username", "value"])
        for i, (username, value) in enumerate(self.list_top_items(), start=1):
            writer.writerow([str(i), username, value])
        return buffer.getvalue()


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


class MostKarma(Leaderboard):
    name = "Most Karma"

    def list_top_items(self):
        query = User.select().order_by(User.karma.desc())
        for user in query.limit(self.count):
            yield user.username, f"{user.karma} karma"


leaderboards = {
    "high_score": HighScore(),
    "oldest_plant": OldestPlant(),
    "pretty_flowers": PrettyFlowers(),
    "most_karma": MostKarma(),
}
