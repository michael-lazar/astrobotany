import argparse

from playhouse import migrate
from peewee import BooleanField

from astrobotany import init_db


def add_setting_ansi_enabled(migrator):
    migrate.migrate(
        migrator.add_column("user", "ansi_enabled", BooleanField(default=False))
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Apply a named migration to the astrobotany database"
    )
    parser.add_argument("db")
    parser.add_argument("migration")
    args = parser.parse_args()

    db = init_db(args.db)
    migrator = migrate.SqliteMigrator(db)

    print(f"Running migration {args.migration}...")
    locals()[args.migration](migrator)
    print(f"Success!")
