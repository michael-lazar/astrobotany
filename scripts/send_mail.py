import argparse

from astrobotany.models import Inbox, User, init_db

parser = argparse.ArgumentParser()
parser.add_argument("filename")
parser.add_argument("user_from")
parser.add_argument("user_to")
parser.add_argument("--db", default="/etc/astrobotany/astrobotany.sqlite")
args = parser.parse_args()

init_db(args.db)

user_from = User.select().where(User.username == args.user_from)
if args.user_to == "all":
    users = User.select()
else:
    users = User.select().where(User.username == args.user_to)

subject, body = Inbox.load_mail_file(args.filename)
for user in users:
    print(f"Sending {args.filename} to {user.username}")
    Inbox.create(user_from=user_from, user_to=user, subject=subject, body=body.format(user=user))
