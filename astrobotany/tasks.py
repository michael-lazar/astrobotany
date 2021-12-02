"""
Recurring astrobotany tasks.

This script is intended to be invoked from a cron file like this...

0 * * * * jetforce-user /usr/bin/python3 -m astrobotany-tasks hourly
0 0 * * * jetforce-user /usr/bin/python3 -m astrobotany-tasks daily
"""

import argparse

from . import settings
from .garden import rebuild_garden
from .models import Plant, init_db


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
