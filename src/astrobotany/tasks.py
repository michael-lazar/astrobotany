"""
Recurring astrobotany tasks.

This script is intended to be invoked from a cron file like this...

0 * * * * jetforce-user /usr/bin/python3 -m astrobotany-tasks hourly
0 0 * * * jetforce-user /usr/bin/python3 -m astrobotany-tasks daily
"""

import argparse
from datetime import datetime, timedelta

from astrobotany import settings
from astrobotany.garden import rebuild_garden
from astrobotany.models import Event, Plant, init_db


class Schedule:
    def __init__(self):
        self.daily_tasks = []
        self.hourly_tasks = []

    def daily(self, func):
        self.daily_tasks.append(func)
        return func

    def hourly(self, func):
        self.hourly_tasks.append(func)
        return func


schedule = Schedule()


@schedule.hourly
def refresh_all_plants():
    """
    Refresh plants every hour to keep the garden page up to date.
    """
    for plant in Plant.all_active():
        plant.refresh()
        plant.save()


@schedule.hourly
def refresh_garden_art():
    """
    Rebuild the generated garden art, this is computationally expensive so
    we run it periodically and save the art to the database instead of
    regenerating it with every gemini request.
    """
    rebuild_garden(update_users=True)


@schedule.daily
def prune_database():
    """
    Delete rows that the application will never look at again, so the
    database doesn't grow unbounded.

    - Dead plants that have been harvested are unreachable; every query
      goes through user_active or the active plant's id.
    - Petal picks are only checked against the current day, to enforce the
      one-pick-per-plant daily limit. Keep a 2-day buffer to be safe.
    """
    plant_count = (
        Plant.delete()
        .where(
            Plant.user_active.is_null(),
            Plant.dead == True,
        )
        .execute()
    )
    event_count = (
        Event.delete()
        .where(
            Event.event_type == Event.PICK_PETAL,
            Event.created_at < datetime.now() - timedelta(days=2),
        )
        .execute()
    )
    print(f"Pruned {plant_count} dead plants and {event_count} old petal picks")


@schedule.daily
def optimize_database():
    """
    Keep the query planner statistics up to date, otherwise sqlite makes
    poor index choices. Runs after prune_database so the statistics reflect
    the pruned tables.
    """
    Plant._meta.database.execute_sql("PRAGMA optimize")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("type", choices=["hourly", "daily"])
    parser.add_argument("--db", default=settings.db)
    args = parser.parse_args()

    init_db(args.db)

    if args.type == "hourly":
        tasks = schedule.hourly_tasks
    elif args.type == "daily":
        tasks = schedule.daily_tasks
    else:
        raise ValueError("Invalid type")

    print(f"Running <{args.type}> astrobotany tasks...")
    for task in tasks:
        print(f"Starting task: {task.__name__}()")
        task()
        print(f"Finished task: {task.__name__}()")
    print(f"Completed <{args.type}> astrobotany tasks!")


if __name__ == "__main__":
    main()
