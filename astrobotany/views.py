import math
import os
import typing
from datetime import datetime, timedelta

import jinja2
from jetforce import Request, Response, Status, JetforceApplication

from .art import render_art
from .models import Message, Plant, User
from .leaderboard import get_daily_leaderboard


UUID_RE = "[A-Za-z0-9_=-]+"
TEMPLATE_DIR = os.path.join(os.path.dirname(__file__), "templates")

template_env = jinja2.Environment(
    loader=jinja2.FileSystemLoader(TEMPLATE_DIR),
    undefined=jinja2.StrictUndefined,
    trim_blocks=True,
    lstrip_blocks=True,
)


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
                msg = "Invalid certificate, the subject CommonName must be specified!"
                return Response(Status.AUTHORISED_CERTIFICATE_REQUIRED, msg)

            if request.environ["TLS_CLIENT_AUTHORISED"]:
                # Old-style verified certificate
                user_id = request.environ["TLS_CLIENT_SERIAL_NUMBER"]
                user_id = f"{user_id:032X}"  # Convert to hex
            else:
                # New-style self signed certificate
                user_id = request.environ["TLS_CLIENT_HASH"]

            request.user, _ = User.get_or_create(
                user_id=user_id, username=request.environ["REMOTE_USER"],
            )
            request.plant = request.user.plant

        if request.user is None:
            if request.path != "/app":
                # Redirect the user to the correct "path scope" first
                return Response(Status.REDIRECT_TEMPORARY, "/app")
            else:
                msg = (
                    "Use a self-signed certificate to login. The CommonName "
                    "attribute will be your username. The certificate will be "
                    "linked to your account, so don't lose it!"
                )
                return Response(Status.AUTHORISED_CERTIFICATE_REQUIRED, msg)

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
    body = render_template("menu.gmi", title_art=title_art)
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


@app.route("/app/plant")
@authenticate
def plant(request):
    body = render_template("plant.gmi", request=request, plant=request.plant)
    return Response(Status.SUCCESS, "text/gemini", body)


@app.route("/app/plant/water")
@authenticate
def water(request):
    info = request.plant.water()
    body = render_template(
        "plant_water.gmi", request=request, plant=request.plant, info=info
    )
    return Response(Status.SUCCESS, "text/gemini", body)


@app.route("/app/plant/inspect")
@authenticate
def inspect(request):
    body = render_template("plant_inspect.gmi", request=request, plant=request.plant)
    return Response(Status.SUCCESS, "text/gemini", body)


@app.route("/app/plant/harvest")
@app.route("/app/plant/harvest/confirm")
@authenticate
def harvest(request):
    if request.path.endswith("/confirm"):
        if request.query.strip() == f"Goodbye {request.plant.name}":
            request.plant.harvest()
            return Response(Status.REDIRECT_TEMPORARY, "/app/plant")
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
    body = render_template("plant_name.gmi", request=request, plant=request.plant)
    return Response(Status.SUCCESS, "text/gemini", body)


@app.route("/app/visit")
@authenticate
def visit(request):
    plants = (
        Plant.all_active()
        .filter(
            Plant.score > 0, Plant.watered_at >= datetime.now() - timedelta(days=8),
        )
        .order_by(User)
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

    body = render_template("visit_plant.gmi", request=request, plant=user.plant)
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
    info = user.plant.water(request.user)
    user.plant.save()

    body = render_template(
        "visit_plant_water.gmi", request=request, plant=user.plant, info=info
    )
    return Response(Status.SUCCESS, "text/gemini", body)
