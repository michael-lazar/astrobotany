#!/usr/bin/env python3
import argparse
from datetime import datetime, timedelta

from peewee import BlobField, BooleanField, DateTimeField, IntegerField, TextField
from playhouse import migrate

from astrobotany import items, settings
from astrobotany.models import Certificate, ItemSlot, Plant, User, gen_user_id, init_db


def add_setting_ansi_enabled(migrator):
    migrate.migrate(migrator.add_column("user", "ansi_enabled", BooleanField(default=False)))


def alter_user_id_type(migrator):
    migrate.migrate(
        migrator.alter_column_type("user", "user_id", TextField(unique=True, index=True))
    )


def add_item_paperclip(migrator):
    for user in User.select():
        ItemSlot.get_or_create(user=user, item_id=items.paperclip.item_id, defaults={"quantity": 1})


def add_item_fertilizer(migrator):
    for user in User.select():
        ItemSlot.get_or_create(
            user=user, item_id=items.fertilizer.item_id, defaults={"quantity": 5}
        )


def add_plant_fertilized_at(migrator):
    dt = datetime.now() - timedelta(days=4)
    migrate.migrate(migrator.add_column("plant", "fertilized_at", DateTimeField(default=dt)))


def add_user_password_field(migrator):
    migrate.migrate(migrator.add_column("user", "password", BlobField(null=True)))


def migrate_certificates(migrator):
    users = list(User.select())

    active_users = {}
    for user in users:
        active_users.setdefault(user.username, user)
        watered_at = active_users[user.username].plant.watered_at
        if user.plant.watered_at > watered_at:
            active_users[user.username] = user

    for user in users:
        active_user = active_users[user.username]
        Certificate.create(
            user=active_user,
            authorised=not user.user_id.endswith("="),
            fingerprint=user.user_id,
            cn=user.username,
        )
        if user == active_user:
            user.user_id = gen_user_id()
            user.save()
        else:
            user.delete_instance()


def move_ansi_enabled(migrator):
    migrate.migrate(migrator.add_column("certificate", "ansi_enabled", BooleanField(default=False)))

    for user in User.select():
        for cert in user.certificates:
            cert.ansi_enabled = user.ansi_enabled
            cert.save()


def add_shaken_at(migrator):
    migrate.migrate(migrator.add_column("plant", "shaken_at", IntegerField(default=False)))

    for plant in Plant.select():
        plant.shaken_at = plant.score
        plant.save()


def add_inbox_item(migrator):
    migrate.migrate(migrator.add_column("inbox", "item_id", IntegerField(null=True, default=None)))


def add_santa(migrator):
    User.create(username="santa")


def add_badge_id(migrator):
    migrate.migrate(migrator.add_column("user", "badge_id", IntegerField(null=True, default=None)))


def add_emoji_mode(migrator):
    migrate.migrate(migrator.add_column("certificate", "emoji_mode", IntegerField(default=0)))


def add_pond(migrator):
    migrate.migrate(migrator.add_column("user", "karma", IntegerField(default=0)))
    migrate.migrate(migrator.add_column("event", "count", IntegerField(default=0)))


def add_garden_coordinates(migrator):
    migrate.migrate(migrator.add_column("user", "garden_coordinates", TextField(null=True, default=None)))


MIGRATIONS = locals()


def main():
    parser = argparse.ArgumentParser(
        description="Apply a named migration to the astrobotany database"
    )
    parser.add_argument("migration")
    parser.add_argument("--db", default=settings.db)
    args = parser.parse_args()

    db = init_db(args.db)
    migrator = migrate.SqliteMigrator(db)

    print(f"Running migration {args.migration}...")
    MIGRATIONS[args.migration](migrator)
    print(f"Success!")


if __name__ == "__main__":
    main()
