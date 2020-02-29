"""
Can't sleep, must write unit tests...
"""
from datetime import datetime, timedelta

import pytest
from astrobotany import init_db
from astrobotany.constants import SPECIES, STAGES
from astrobotany.models import Plant, User
from freezegun import freeze_time


@pytest.fixture
def db():
    return init_db(":memory:")


@pytest.fixture
def user(db):
    return User.create(user_id="123AF", username="mozz")


@pytest.fixture
def plant(db, user):
    return Plant.create(user=user)


def test_plant_load_ascii_art(plant):
    for species in range(len(SPECIES)):
        for stage in range(len(STAGES)):
            plant.species = species
            plant.stage = stage
            assert plant.get_ascii_art()

    plant.dead = True
    assert plant.get_ascii_art()


@freeze_time()
def test_plant_water_supply_percent(plant):
    plant.watered_at = datetime.now()
    assert plant.water_supply_percent == 100

    plant.watered_at = datetime.now() - timedelta(minutes=1)
    assert plant.water_supply_percent == 100

    plant.watered_at = datetime.now() - timedelta(hours=12)
    assert plant.water_supply_percent == 50

    plant.watered_at = datetime.now() - timedelta(hours=24)
    assert plant.water_supply_percent == 0

    plant.watered_at = datetime.now() - timedelta(hours=36)
    assert plant.water_supply_percent == 0


@freeze_time()
def test_plant_water_gauge(plant):
    plant.watered_at = datetime.now()
    assert plant.water_gauge == "|██████████| 100%"

    plant.watered_at = datetime.now() - timedelta(hours=12)
    assert plant.water_gauge == "|█████     | 50%"

    plant.watered_at = datetime.now() - timedelta(hours=24)
    assert plant.water_gauge == "|          | 0%"


def test_plant_get_observation(plant):
    plant.score = 60 * 60 * 23
    assert "You notice your plant looks different." in plant.get_observation()


@freeze_time()
def test_plant_water(plant):
    assert plant.water_supply_percent == 0
    plant.water()
    assert plant.water_supply_percent == 100


def test_plant_harvest(user, plant):
    plant.user_active = user
    plant.harvest()
    assert plant.dead
    assert plant.user_active is None
    assert plant.get(user_active=user)


@freeze_time()
def test_plant_refresh_dead(plant):
    plant.watered_at = datetime.now() - timedelta(days=6)
    plant.refresh()
    assert plant.dead
    assert plant.updated_at == datetime.now()
    assert plant.score == 0


@freeze_time()
def test_plant_refresh_12h(plant):
    plant.watered_at = datetime.now() - timedelta(hours=12)
    plant.updated_at = datetime.now() - timedelta(hours=12)

    plant.refresh()
    assert plant.updated_at == datetime.now()
    assert plant.score == 12 * 3600


@freeze_time()
def test_plant_refresh_generation_2_12h(plant):
    plant.watered_at = datetime.now() - timedelta(hours=12)
    plant.updated_at = datetime.now() - timedelta(hours=12)
    plant.generation = 2

    plant.refresh()
    assert plant.updated_at == datetime.now()
    assert plant.score == 12 * 3600 * 1.2


@freeze_time()
def test_plant_refresh_18h(plant):
    plant.watered_at = datetime.now() - timedelta(hours=18)
    plant.updated_at = datetime.now() - timedelta(hours=12)

    plant.refresh()
    assert plant.updated_at == datetime.now()
    assert plant.score == 12 * 3600


@freeze_time()
def test_plant_refresh_36h(plant):
    plant.watered_at = datetime.now() - timedelta(hours=36)
    plant.updated_at = datetime.now() - timedelta(hours=24)

    plant.refresh()
    assert plant.updated_at == datetime.now()
    assert plant.score == 12 * 3600


@freeze_time()
def test_plant_refresh_evolve(plant):
    plant.score = 1
    plant.watered_at = datetime.now() - timedelta(hours=24)
    plant.updated_at = datetime.now() - timedelta(hours=24)

    plant.refresh()
    assert plant.stage == 1
