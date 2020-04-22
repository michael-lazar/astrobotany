"""
Can't sleep, must write unit tests...
"""
from datetime import datetime, timedelta
import os

import pytest

from astrobotany import init_db
from astrobotany.art import ArtFile
from astrobotany.constants import SPECIES, STAGES, COLORS
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


@pytest.mark.parametrize("filename", (os.listdir(ArtFile.ART_DIR)))
def test_validate_art_files(filename: str):
    art_file = ArtFile(filename)
    for line in art_file.character_matrix:
        for tile in line:
            # The background color should never be set
            assert tile.bg is None

            # Non-empty tiles should always have a foreground color
            if tile.char != " ":
                assert tile.fg is not None

            # The char should be in the printable 7-bit ASCII range
            assert chr(32) <= tile.char < chr(128)

    assert art_file.render(ansi_enabled=False)
    assert art_file.render(ansi_enabled=True)


def test_draw_plant_dead(plant):
    plant.dead = True
    assert "R.I.P." in plant.get_ascii_art()


@pytest.mark.parametrize("species", SPECIES)
def test_draw_plant_stages(plant, species: str):
    plant.species = SPECIES.index(species)
    for stage in range(len(STAGES)):
        plant.stage = stage
        assert plant.get_ascii_art()


@pytest.mark.parametrize("color", COLORS)
def test_draw_plant_flowers(plant, color: str):
    plant.stage = 4
    plant.color = COLORS.index(color)
    assert plant.get_ascii_art(ansi_enabled=True)


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
def test_plant_get_water_gauge(plant):
    plant.watered_at = datetime.now()
    assert plant.get_water_gauge() == "|██████████| 100%"

    plant.watered_at = datetime.now() - timedelta(hours=12)
    assert plant.get_water_gauge() == "|█████     | 50%"

    plant.watered_at = datetime.now() - timedelta(hours=24)
    assert plant.get_water_gauge() == "|          | 0%"


def test_plant_get_observation(plant):
    plant.score = 60 * 60 * 23
    assert "You notice your plant looks different." in plant.get_observation()


@freeze_time()
def test_plant_water(plant):
    plant.watered_at = datetime.now() - timedelta(hours=24)
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
