#!/usr/bin/env python3
"""
Generate fake plant data for testing.
"""
import argparse
import random
from datetime import datetime, timedelta

import faker

from astrobotany import init_db
from astrobotany.models import Plant, User

parser = argparse.ArgumentParser()
parser.add_argument("count", type=int)
parser.add_argument("--db-file", default="astrobotany.sqlite")
args = parser.parse_args()

fake = faker.Faker()

init_db(args.db_file)

for _ in range(args.count):
    age = random.randrange(int(timedelta(days=50).total_seconds()))
    user = User.create(
        user_id="".join(random.choices("0123456789ABCDEF", k=16)), username=fake.name().lower(),
    )
    plant = Plant(
        user=user,
        user_active=user,
        score=random.randrange(age // 2, age),
        created_at=datetime.now() - timedelta(seconds=age),
        watered_at=datetime.now() - timedelta(seconds=random.randrange(2 * 24 * 60 * 60)),
    )
    plant.refresh()
    plant.save()
    print(f"Generated {user.username}'s {plant.description}")
