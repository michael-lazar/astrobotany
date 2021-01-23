import argparse
import typing

from astrobotany import items, settings
from astrobotany.models import Inbox, User, init_db

parser = argparse.ArgumentParser()
parser.add_argument("filename")
parser.add_argument("user_from")
parser.add_argument("--item")
parser.add_argument("--db", default=settings.db)
args = parser.parse_args()

init_db(args.db)

user_from = User.select().where(User.username == args.user_from)
users = User.select()

subject, body = Inbox.load_mail_file(args.filename)

item_id: typing.Optional[int]

if args.item:
    item = items.search(args.item)
    if not item:
        raise ValueError(f"Item not found: {args.item}")
    item_id = item.item_id
else:
    item_id = None

for user in users:
    print(f"Sending {args.filename} to {user.username}")
    Inbox.create(
        user_from=user_from,
        user_to=user,
        item_id=item_id,
        subject=subject,
        body=body.format(user=user),
    )
