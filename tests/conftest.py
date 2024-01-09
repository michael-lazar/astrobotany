from datetime import datetime

import pytest
from freezegun import freeze_time

from astrobotany import init_db


@pytest.fixture(autouse=True)
def db():
    return init_db(":memory:")


@pytest.fixture()
def frozen_time():
    with freeze_time() as frozen_time:
        yield frozen_time


@pytest.fixture()
def now(frozen_time):
    return datetime.now()
