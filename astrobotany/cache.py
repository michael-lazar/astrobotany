import copy
import json
import typing


class Cache:
    # TODO : Add file locking

    DEFAULT = {"daily_badge": {"number": 1, "price": 500}}

    data: dict
    filename: str

    def init(self, filename: str) -> "Cache":
        self.filename = filename
        self.refresh()
        return self

    def get(self, key: str) -> typing.Any:
        return self.data[key]

    def set(self, key: str, value: typing.Any) -> None:
        self.data[key] = value

    def refresh(self) -> None:
        data = copy.deepcopy(self.DEFAULT)
        try:
            with open(self.filename, "r") as fp:
                data.update(json.load(fp))
        except (OSError, json.JSONDecodeError):
            pass

        self.data = data

    def save(self) -> None:
        with open(self.filename, "w") as fp:
            json.dump(self.data, fp)


cache = Cache()

# Alias
init_cache = cache.init
