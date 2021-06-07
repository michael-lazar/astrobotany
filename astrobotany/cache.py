import copy
import json
import typing
from datetime import datetime


class Cache:
    # TODO : Add file locking

    DEFAULT = {"daily_badge": {"number": 0, "price": 500}}

    data: dict
    filename: str
    last_access: datetime

    def __init__(self, lifetime: int = 60):
        self.lifetime = lifetime

    def init(self, filename: str) -> "Cache":
        self.filename = filename
        self.refresh()
        return self

    def refresh(self) -> None:
        data = copy.deepcopy(self.DEFAULT)
        try:
            with open(self.filename, "r") as fp:
                data.update(json.load(fp))
        except (OSError, json.JSONDecodeError):
            pass

        self.last_access = datetime.now()
        self.data = data

    def get(self, key: str) -> typing.Any:
        refresh_dt = (datetime.now() - self.last_access).total_seconds()
        if refresh_dt > self.lifetime:
            self.refresh()

        return self.data[key]

    def set(self, key: str, value: typing.Any) -> None:
        self.data[key] = value

    def save(self) -> None:
        with open(self.filename, "w") as fp:
            json.dump(self.data, fp)


cache = Cache()

# Alias
init_cache = cache.init
