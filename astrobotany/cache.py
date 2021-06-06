import copy
import json


class Cache:

    DEFAULT = {}

    data: dict

    def __init__(self, filename: str):
        self.filename = filename
        self.refresh()

    def refresh(self):
        data = copy.deepcopy(self.DEFAULT)
        try:
            with open(self.filename, "r") as fp:
                data.update(json.load(fp))
        except (OSError, json.JSONDecodeError):
            pass

        self.data = data

    def save(self):
        with open(self.filename, "w") as fp:
            json.dump(self.data, fp)
