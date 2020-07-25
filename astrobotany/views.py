import math
import os
import typing
from datetime import datetime, timedelta
from functools import lru_cache

import jinja2
from jetforce import Request, Response, Status, JetforceApplication

from . import items
from .art import render_art
from .models import Message, Plant, User, Inbox
from .leaderboard import get_daily_leaderboard


UUID_RE = "[A-Za-z0-9_=-]+"
TEMPLATE_DIR = os.path.join(os.path.dirname(__file__), "templates")

template_env = jinja2.Environment(
    loader=jinja2.FileSystemLoader(TEMPLATE_DIR),
    undefined=jinja2.StrictUndefined,
    trim_blocks=True,
    lstrip_blocks=True,
)


@lru_cache(2048)
def load_session(session_id: str):
    """
    A poor man's server-side session object.

    Stores session data as a dict in memory that will be wiped on server
    restart. Mutate the dictionary to update the session. This only works
    because the server is running as a single process with shared memory.
    """
    return {}


def render_template(name: str, *args, **kwargs) -> str:
    """
    Render a gemini directory using the Jinja2 template engine.
    """
    return template_env.get_template(name).render(*args, **kwargs)


def authenticate(func: typing.Callable) -> typing.Callable:
    """
    View wrapper that handles user authentication via client certificates.
    """

    def callback(request: Request, **kwargs):
        request.user = None
        request.plant = None
        if "REMOTE_USER" in request.environ:
            if not request.environ["REMOTE_USER"]:
                msg = "The certificate must define a CN (Common Name) attribute."
                return Response(Status.CERTIFICATE_NOT_AUTHORISED, msg)

            if request.environ["TLS_CLIENT_AUTHORISED"]:
                # Old-style verified certificate
                user_id = request.environ["TLS_CLIENT_SERIAL_NUMBER"]
                user_id = f"{user_id:032X}"  # Convert to hex
            else:
                # New-style self signed certificate
                user_id = request.environ["TLS_CLIENT_HASH"]

            user = User.get_or_none(user_id=user_id)
            if user is None:
                user = User.initialize(user_id, request.environ["REMOTE_USER"])

            request.user = user
            request.plant = request.user.plant
            request.session = load_session(request.user.user_id)

        if request.user is None:
            if request.path != "/app":
                # Redirect the user to the correct "path scope" first
                return Response(Status.REDIRECT_TEMPORARY, "/app")
            else:
                msg = (
                    "This application uses TOFU client certificates for "
                    "authentication. In order to login, generate your own "
                    "self-signed certificate (the CN attribute will be your "
                    "username)."
                )
                return Response(Status.CLIENT_CERTIFICATE_REQUIRED, msg)

        if request.plant:
            request.plant.refresh()
            response = func(request, **kwargs)
            request.plant.save()
        else:
            response = func(request, **kwargs)

        return response

    return callback


app = JetforceApplication()


@app.route("", strict_trailing_slash=False)
def index(request):
    title_art = render_art("title.psci", None, False)
    leaderboard = get_daily_leaderboard().render(False)
    body = render_template("index.gmi", title_art=title_art, leaderboard=leaderboard)
    return Response(Status.SUCCESS, "text/gemini", body)


@app.route("/instructions")
def instructions(request):
    body = render_template("instructions.gmi")
    return Response(Status.SUCCESS, "text/gemini", body)


@app.route("/register")
def register(request):
    body = render_template("register.gmi")
    return Response(Status.SUCCESS, "text/gemini", body)


@app.route("/app")
@authenticate
def menu(request):
    title_art = render_art("title.psci", None, request.user.ansi_enabled)
    mailbox_count = request.user.inbox.where(Inbox.is_seen == False).count()
    body = render_template("menu.gmi", title_art=title_art, mailbox_count=mailbox_count)
    return Response(Status.SUCCESS, "text/gemini", body)


@app.route("/app/epilog/(?P<page>[0-9]+)")
@authenticate
def epilog(request, page):
    page = int(page)
    if page in (1, 2, 3, 4):
        art = render_art(f"epilog{page}.psci", None, request.user.ansi_enabled)
    else:
        art = None
    body = render_template("epilog.gmi", page=page, art=art)
    return Response(Status.SUCCESS, "text/gemini", body)


@app.route("/app/message-board")
@app.route("/app/message-board/(?P<page>[0-9]+)")
@authenticate
def message_board(request, page=1):
    page = int(page)
    paginate_by = 10
    page_count = int(math.ceil(Message.select().count() / paginate_by))
    page_count = max(page_count, 1)
    if page > page_count:
        return Response(Status.NOT_FOUND, "Invalid page number")

    items = Message.by_date().paginate(page, paginate_by)

    body = render_template(
        "message_board.gmi",
        request=request,
        items=items,
        page=page,
        page_count=page_count,
    )
    return Response(Status.SUCCESS, "text/gemini", body)


@app.route("/app/message-board/submit")
@authenticate
def message_board_submit(request):
    if not request.query:
        return Response(Status.INPUT, "What would you like to say? ")

    message = Message(user=request.user, text=request.query)
    message.save()
    return Response(Status.REDIRECT_TEMPORARY, "/app/message-board")


@app.route("/app/settings")
@authenticate
def settings(request):
    body = render_template("settings.gmi", request=request)
    return Response(Status.SUCCESS, "text/gemini", body)


@app.route("/app/settings/update/(?P<field>[A-Za-z_]+)")
@authenticate
def settings_update(request, field):
    if field not in ("ansi_enabled",):
        return Response(Status.NOT_FOUND, "Invalid setting")

    if not request.query:
        prompt = f"Enter a new value for {field}, [T]rue/[F]alse:"
        return Response(Status.INPUT, prompt)

    answer = request.query.strip().lower()

    if answer in ("t", "true"):
        value = True
    elif answer in ("f", "false"):
        value = False
    else:
        return Response(Status.BAD_REQUEST, f"Invalid query value: {request.query}")

    setattr(request.user, field, value)
    request.user.save()

    return Response(Status.REDIRECT_TEMPORARY, "/app/settings")


@app.route("/app/mailbox")
@authenticate
def mailbox(request):
    messages = request.user.inbox.order_by(Inbox.id.desc())
    body = render_template("mailbox.gmi", request=request, messages=messages)
    return Response(Status.SUCCESS, "text/gemini", body)


@app.route("/app/mailbox/(?P<message_id>[0-9]+)")
@authenticate
def mailbox_view(request, message_id):
    message = Inbox.get_or_none(id=message_id, user_to=request.user)
    if message is None:
        return Response(Status.BAD_REQUEST, "You shouldn't be here!")

    message.is_seen = True
    message.save()

    body = render_template("mailbox_view.gmi", request=request, message=message)
    return Response(Status.SUCCESS, "text/gemini", body)


@app.route("/app/plant")
@authenticate
def plant(request):
    alert = request.session.pop("alert", None)
    if alert is None:
        alert = request.plant.get_observation(request.user.ansi_enabled)

    body = render_template(
        "plant.gmi", request=request, plant=request.plant, alert=alert,
    )
    return Response(Status.SUCCESS, "text/gemini", body)


@app.route("/app/plant/water")
@authenticate
def water(request):
    request.session["alert"] = request.plant.water()
    return Response(Status.REDIRECT_TEMPORARY, "/app/plant")


@app.route("/app/plant/fertilize")
@authenticate
def fertilize(request):
    request.session["alert"] = request.plant.fertilize()
    return Response(Status.REDIRECT_TEMPORARY, "/app/plant")


@app.route("/app/plant/inspect")
@authenticate
def inspect(request):
    request.session["alert"] = "\n".join(
        [
            f"Generation: {request.plant.generation}",
            f"Growth Rate: {request.plant.growth_rate}",
        ]
    )
    return Response(Status.REDIRECT_TEMPORARY, "/app/plant")


@app.route("/app/plant/petal")
@authenticate
def petal(request):
    if request.plant.dead or request.plant.stage_str != "flowering":
        return Response(Status.BAD_REQUEST, "You shouldn't be here!")

    request.session["alert"] = request.plant.pick_petal()
    return Response(Status.REDIRECT_TEMPORARY, "/app/plant")


@app.route("/app/plant/harvest")
@app.route("/app/plant/harvest/confirm")
@authenticate
def harvest(request):
    if request.path.endswith("/confirm"):
        if request.query.strip() == f"Goodbye {request.plant.name}":
            request.plant.harvest()
            return Response(Status.REDIRECT_TEMPORARY, "/app/epilog/1")
        elif request.query:
            return Response(Status.REDIRECT_TEMPORARY, "/app/plant/harvest")
        else:
            msg = f'Type "Goodbye {request.plant.name}" to send off your plant.'
            return Response(Status.INPUT, msg)

    body = render_template("plant_harvest.gmi", request=request, plant=request.plant)
    return Response(Status.SUCCESS, "text/gemini", body)


@app.route("/app/plant/name")
@authenticate
def name(request):
    if not request.query:
        return Response(Status.INPUT, "Enter a new nickname for your plant:")

    request.plant.name = request.query[:40]
    msg = f'Your plant shall henceforth be known as "{request.plant.name}".'
    request.session["alert"] = msg
    return Response(Status.REDIRECT_TEMPORARY, "/app/plant")


@app.route("/app/visit")
@authenticate
def visit(request):
    plants = (
        Plant.all_active()
        .filter(
            Plant.score > 0, Plant.watered_at >= datetime.now() - timedelta(days=8),
        )
        .order_by(Plant.score.desc())
    )

    body = render_template("visit.gmi", request=request, plants=plants)
    return Response(Status.SUCCESS, "text/gemini", body)


@app.route(f"/app/visit/(?P<user_id>{UUID_RE})")
@authenticate
def visit_plant(request, user_id):
    user = User.get_or_none(user_id=user_id)
    if user is None:
        return Response(Status.NOT_FOUND, "User not found")
    elif request.user == user:
        return Response(Status.REDIRECT_TEMPORARY, "/app/plant")

    user.plant.refresh()
    user.plant.save()

    alert = request.session.pop("alert", None)
    body = render_template(
        "visit_plant.gmi", request=request, plant=user.plant, alert=alert,
    )
    return Response(Status.SUCCESS, "text/gemini", body)


@app.route(f"/app/visit/(?P<user_id>{UUID_RE})/water")
@authenticate
def visit_plant_water(request, user_id):
    user = User.get_or_none(user_id=user_id)
    if user is None:
        return Response(Status.NOT_FOUND, "User not found")
    elif request.user == user:
        return Response(Status.REDIRECT_TEMPORARY, "/app/plant")

    user.plant.refresh()
    request.session["alert"] = user.plant.water(request.user)
    user.plant.save()

    return Response(Status.REDIRECT_TEMPORARY, f"/app/visit/{user_id}")


@app.route(f"/app/visit/(?P<user_id>{UUID_RE})/petal")
@authenticate
def visit_plant_petal(request, user_id):
    user = User.get_or_none(user_id=user_id)
    if user is None:
        return Response(Status.NOT_FOUND, "User not found")
    elif request.user == user:
        return Response(Status.REDIRECT_TEMPORARY, "/app/plant")

    if user.plant.dead or user.plant.stage_str != "flowering":
        return Response(Status.BAD_REQUEST, "You shouldn't be here!")

    user.plant.refresh()
    request.session["alert"] = user.plant.pick_petal(request.user)
    user.plant.save()

    return Response(Status.REDIRECT_TEMPORARY, f"/app/visit/{user_id}")


@app.route("/app/inventory")
@authenticate
def inventory(request):
    body = render_template("inventory.gmi", request=request)
    return Response(Status.SUCCESS, "text/gemini", body)


@app.route("/app/inventory/(?P<item_id>[0-9]+)")
@authenticate
def view_item(request, item_id):
    item = items.registry[int(item_id)]
    body = render_template("item.gmi", request=request, item=item)
    return Response(Status.SUCCESS, "text/gemini", body)
