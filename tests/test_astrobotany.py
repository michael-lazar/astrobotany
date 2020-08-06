"""
Can't sleep, must write unit tests...
"""
import itertools
import os
from datetime import datetime, timedelta

import pytest
from freezegun import freeze_time

from astrobotany import init_db, items
from astrobotany.art import ArtFile
from astrobotany.constants import COLOR_MAP, COLORS, SPECIES, STAGES
from astrobotany.models import Plant, User


@pytest.fixture(autouse=True)
def db():
    return init_db(":memory:")


@pytest.fixture
def frozen_time():
    with freeze_time() as frozen_time:
        yield frozen_time


@pytest.fixture
def now(frozen_time):
    return datetime.now()


user_generator = itertools.count()


def user_factory(**kwargs):
    user_id = str(next(user_generator))
    return User.create(user_id=user_id, username="username" + user_id)


def plant_factory(user=None, **kwargs):
    if user is None:
        user = user_factory()
    return Plant.create(user=user, **kwargs)


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


def test_draw_plant_dead():
    plant = plant_factory(dead=True)
    assert "R.I.P." in plant.get_ascii_art()


@pytest.mark.parametrize("species", SPECIES)
def test_draw_plant_stages(species: str):
    for stage in range(len(STAGES)):
        plant = plant_factory(species=SPECIES.index(species), stage=stage)
        assert plant.get_ascii_art()


@pytest.mark.parametrize("color", COLORS)
def test_draw_plant_flowers(color: str):
    plant = plant_factory(stage=4, color=COLORS.index(color))
    assert plant.get_ascii_art(ansi_enabled=True)


def test_plant_water_supply_percent(now):
    plant = plant_factory(watered_at=now)
    assert plant.water_supply_percent == 100

    plant = plant_factory(watered_at=now - timedelta(minutes=1))
    assert plant.water_supply_percent == 100

    plant = plant_factory(watered_at=now - timedelta(hours=12))
    assert plant.water_supply_percent == 50

    plant = plant_factory(watered_at=now - timedelta(hours=24))
    assert plant.water_supply_percent == 0

    plant = plant_factory(watered_at=now - timedelta(hours=36))
    assert plant.water_supply_percent == 0


def test_plant_get_water_gauge(now):
    plant = plant_factory(watered_at=now)
    assert plant.get_water_gauge() == "|██████████| 100%"

    plant = plant_factory(watered_at=now - timedelta(hours=12))
    assert plant.get_water_gauge() == "|█████     | 50%"

    plant = plant_factory(watered_at=now - timedelta(hours=24))
    assert plant.get_water_gauge() == "|          | 0%"


def test_plant_get_fertilizer_gauge(now):
    plant = plant_factory(fertilized_at=now)
    assert plant.get_fertilizer_gauge() == "|▞▞▞▞▞▞▞▞▞▞| 100%"

    plant = plant_factory(fertilized_at=now - timedelta(hours=36))
    assert plant.get_fertilizer_gauge() == "|▞▞▞▞▞     | 50%"

    plant = plant_factory(fertilized_at=now - timedelta(hours=72))
    assert plant.get_fertilizer_gauge() == "|          | 0%"


def test_plant_get_observation():
    plant = plant_factory(score=60 * 60 * 23)
    assert "You notice your plant looks different." in plant.get_observation()


def test_plant_water(now):
    plant = plant_factory(watered_at=now - timedelta(hours=24))
    assert plant.water_supply_percent == 0
    plant.water()
    assert plant.water_supply_percent == 100


def test_plant_fertilize(now):
    plant = plant_factory()

    plant.user.add_item(items.fertilizer)
    assert plant.fertilizer_percent == 0

    plant.fertilize()
    assert plant.fertilizer_percent == 100


def test_plant_fertilize_not_empty(now):
    plant = plant_factory()
    plant.user.add_item(items.fertilizer)

    plant.fertilized_at = datetime.now() - timedelta(days=2)
    assert plant.fertilizer_percent == 34

    # This attempt should fail and not use the item
    plant.fertilize()
    assert plant.fertilizer_percent == 34


def test_plant_no_fertilizer(now):
    plant = plant_factory()
    assert plant.fertilizer_percent == 0

    plant.fertilize()
    assert plant.fertilizer_percent == 0


def test_plant_water_rate_limit(frozen_time, now):
    """
    A user can only water one neighbor's plan every 8 hours.
    """
    user1 = user_factory()
    user2 = user_factory()
    user3 = user_factory()

    plant1 = plant_factory(user=user1, watered_at=now - timedelta(hours=24))
    plant2 = plant_factory(user=user2, watered_at=now - timedelta(hours=24))

    plant1.water(user3)
    plant1.save()
    assert plant1.water_supply_percent == 100
    assert plant1.watered_by == user3

    plant2.water(user3)
    plant2.save()
    assert plant2.water_supply_percent == 0
    assert plant2.watered_by is None

    frozen_time.tick(delta=timedelta(hours=12))
    plant2.water(user3)
    plant2.save()
    assert plant2.water_supply_percent == 100
    assert plant2.watered_by == user3


def test_plant_harvest():
    """
    Harvesting should automatically create a new plant for the user.
    """
    plant = plant_factory()
    user = plant.user
    plant.user_active = user
    plant.harvest()
    assert plant.dead
    assert plant.user_active is None
    assert plant.get(user_active=user)


def test_plant_refresh_dead(now):
    plant = plant_factory(watered_at=now - timedelta(days=6))
    plant.refresh()
    assert plant.dead
    assert plant.updated_at == datetime.now()
    assert plant.score == 0


def test_plant_refresh_12h(now):
    plant = plant_factory(
        watered_at=now - timedelta(hours=12), updated_at=now - timedelta(hours=12)
    )
    plant.refresh()
    assert plant.updated_at == datetime.now()
    assert plant.score == 12 * 3600


def test_plant_refresh_12h_fertilizer(now):
    plant = plant_factory(
        watered_at=now - timedelta(hours=12),
        updated_at=now - timedelta(hours=12),
        fertilized_at=now - timedelta(hours=6),
    )
    plant.refresh()
    assert plant.updated_at == datetime.now()
    assert plant.score == 12 * 3600 + 0.5 * 6 * 3600


def test_plant_refresh_generation_2_12h(now):
    plant = plant_factory(
        watered_at=now - timedelta(hours=12),
        updated_at=now - timedelta(hours=12),
        generation=2,
    )
    plant.refresh()
    assert plant.updated_at == datetime.now()
    assert plant.score == 12 * 3600 * 1.2


def test_plant_refresh_18h(now):
    plant = plant_factory(
        watered_at=now - timedelta(hours=18), updated_at=now - timedelta(hours=12),
    )
    plant.refresh()
    assert plant.updated_at == datetime.now()
    assert plant.score == 12 * 3600


def test_plant_refresh_18h_fertilizer(now):
    plant = plant_factory(
        watered_at=now - timedelta(hours=18),
        fertilized_at=now - timedelta(hours=18),
        updated_at=now - timedelta(hours=12),
    )
    plant.refresh()
    assert plant.updated_at == datetime.now()
    assert plant.score == 12 * 3600 * 1.5


def test_plant_refresh_36h(now):
    plant = plant_factory(
        watered_at=now - timedelta(hours=36), updated_at=now - timedelta(hours=24)
    )
    plant.refresh()
    assert plant.updated_at == datetime.now()
    assert plant.score == 12 * 3600


def test_plant_refresh_36h_fertilizer(now):
    plant = plant_factory(
        watered_at=now - timedelta(hours=36),
        updated_at=now - timedelta(hours=24),
        fertilized_at=now - timedelta(hours=30),
    )
    plant.refresh()
    assert plant.updated_at == datetime.now()
    assert plant.score == 1.5 * 12 * 3600


def test_plant_refresh_36h_fertilizer_2(now):
    plant = plant_factory(
        watered_at=now - timedelta(hours=12),
        updated_at=now - timedelta(hours=36),
        fertilized_at=now - timedelta(hours=24),
    )
    plant.refresh()
    assert plant.updated_at == datetime.now()
    assert plant.score == 1.5 * 12 * 3600


def test_plant_refresh_36h_fertilizer_3(now):
    plant = plant_factory(
        watered_at=now - timedelta(hours=12),
        updated_at=now - timedelta(hours=36),
        fertilized_at=now - timedelta(hours=24),
    )
    plant.refresh()
    assert plant.updated_at == datetime.now()
    assert plant.score == 1.5 * 12 * 3600


def test_plant_refresh_evolve(now):
    plant = plant_factory(
        watered_at=now - timedelta(hours=24),
        updated_at=now - timedelta(hours=24),
        score=1,
    )
    plant.refresh()
    assert plant.stage == 1


def test_plant_pick_petal_dead():
    plant = plant_factory(stage=4, dead=True, color=COLOR_MAP["red"])
    plant.pick_petal()
    assert plant.user.get_item_quantity(items.petals["red"]) == 0


def test_plant_pick_petal_invalid_stage():
    plant = plant_factory(stage=3, color=COLOR_MAP["red"])
    plant.pick_petal()
    assert plant.user.get_item_quantity(items.petals["red"]) == 0


def test_plant_pick_petal():
    plant = plant_factory(stage=4, color=COLOR_MAP["red"])
    plant.pick_petal()
    assert plant.user.get_item_quantity(items.petals["red"]) == 1


def test_plant_pick_petal_twice():
    plant = plant_factory(stage=4, color=COLOR_MAP["red"])
    plant.pick_petal()
    plant.pick_petal()
    assert plant.user.get_item_quantity(items.petals["red"]) == 1


def test_plant_pick_petal_guest():
    plant = plant_factory(stage=4, color=COLOR_MAP["red"])
    user = user_factory()
    plant.pick_petal(user=user)

    assert user.get_item_quantity(items.petals["red"]) == 1
    assert plant.user.get_item_quantity(items.petals["red"]) == 0


def test_pick_petal_cooldown(frozen_time):
    plant = plant_factory(stage=4, color=COLOR_MAP["red"])
    plant.pick_petal()
    assert plant.user.get_item_quantity(items.petals["red"]) == 1

    frozen_time.tick(delta=timedelta(hours=25))
    plant.pick_petal()
    assert plant.user.get_item_quantity(items.petals["red"]) == 2
