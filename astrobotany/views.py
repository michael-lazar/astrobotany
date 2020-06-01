import math
import os
import typing

import jinja2
from jetforce import Request, Response, Status, JetforceApplication

from .art import render_art
from .models import Message, Plant, User

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


def authenticate(allow_anonymous=False):
    """
    View wrapper that handles user authentication via client certificates.
    """

    def wrapper(func: typing.Callable) -> typing.Callable:
        def callback(request: Request, **kwargs):
            request.user = None
            request.plant = None
            if "REMOTE_USER" in request.environ:
                if not request.environ["REMOTE_USER"]:
                    msg = (
                        "Invalid certificate, the subject CommonName must be specified!"
                    )
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

            if not allow_anonymous and request.user is None:
                msg = "You must have an account to view this page!"
                return Response(Status.AUTHORISED_CERTIFICATE_REQUIRED, msg)

            if request.plant:
                request.plant.refresh()
                response = func(request, **kwargs)
                request.plant.save()
            else:
                response = func(request, **kwargs)

            return response

        return callback

    return wrapper


app = JetforceApplication()


@app.route("", strict_trailing_slash=False)
@authenticate(allow_anonymous=True)
def index(request):
    ansi_enabled = request.user and request.user.ansi_enabled
    title_art = render_art("title.psci", None, ansi_enabled)
    body = render_template("index.gmi", title_art=title_art)
    return Response(Status.SUCCESS, "text/gemini", body)


@app.route("/register")
@authenticate(allow_anonymous=True)
def register(request):
    body = render_template("register.gmi")
    return Response(Status.SUCCESS, "text/gemini", body)


@app.route("/message-board")
@app.route("/message-board/(?P<page>[0-9]+)")
@authenticate()
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


@app.route("/message-board/submit")
@authenticate()
def message_board_submit(request):
    if not request.query:
        return Response(Status.INPUT, "What would you like to say? ")

    message = Message(user=request.user, text=request.query)
    message.save()
    return Response(Status.REDIRECT_TEMPORARY, "/message-board")


@app.route("/settings")
@authenticate()
def settings(request):
    body = render_template("settings.gmi", request=request)
    return Response(Status.SUCCESS, "text/gemini", body)


@app.route("/settings/update/(?P<field>[A-Za-z_]+)")
@authenticate()
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

    return Response(Status.REDIRECT_TEMPORARY, "/settings")


@app.route("/plant")
@authenticate()
def plant(request):
    body = render_template("plant.gmi", request=request, plant=request.plant)
    return Response(Status.SUCCESS, "text/gemini", body)


@app.route("/plant/water")
@authenticate()
def water(request):
    info = request.plant.water()
    body = render_template("water.gmi", request=request, plant=request.plant, info=info)
    return Response(Status.SUCCESS, "text/gemini", body)


@app.route("/plant/observe")
@authenticate()
def observe(request):
    body = render_template("observe.gmi", request=request, plant=request.plant)
    return Response(Status.SUCCESS, "text/gemini", body)


@app.route("/plant/harvest")
@authenticate()
def harvest(request):
    if not request.plant.stage == 5 and not request.plant.dead:
        return Response(Status.TEMPORARY_FAILURE, "You shouldn't be here")

    if request.query == "confirm":
        request.plant.harvest()
        return Response(Status.REDIRECT_TEMPORARY, "/plant")

    body = render_template("harvest.gmi", request=request, plant=request.plant)
    return Response(Status.SUCCESS, "text/gemini", body)


@app.route("/plant/name")
@authenticate()
def name(request):
    if not request.query:
        return Response(Status.INPUT, "Enter a new nickname for your plant:")

    request.plant.name = request.query[:40]
    body = render_template("name.gmi", request=request, plant=request.plant)
    return Response(Status.SUCCESS, "text/gemini", body)


@app.route("/directory")
@authenticate()
def directory(request):
    plants = Plant.filter(Plant.user_active.is_null(False), Plant.score > 0)
    plants = plants.join(User).order_by(User)
    body = render_template("directory.gmi", request=request, plants=plants)
    return Response(Status.SUCCESS, "text/gemini", body)


@app.route("/directory/(?P<user_id>[A-Za-z0-9_=-]+)")
@authenticate()
def visit(request, user_id):
    user = User.get_or_none(user_id=user_id)
    if user is None:
        return Response(Status.NOT_FOUND, "User not found")
    elif request.user == user:
        return Response(Status.REDIRECT_TEMPORARY, "/plant")

    user.plant.refresh()
    user.plant.save()

    body = render_template("visit.gmi", request=request, plant=user.plant)
    return Response(Status.SUCCESS, "text/gemini", body)


@app.route("/directory/(?P<user_id>[A-Za-z0-9_=-]+)/water")
@authenticate()
def visit_water(request, user_id):
    user = User.get_or_none(user_id=user_id)
    if user is None:
        return Response(Status.NOT_FOUND, "User not found")
    elif request.user == user:
        return Response(Status.REDIRECT_TEMPORARY, "/plant")

    user.plant.refresh()
    info = user.plant.water(request.user)
    user.plant.save()

    body = render_template(
        "visit_water.gmi", request=request, plant=user.plant, info=info
    )
    return Response(Status.SUCCESS, "text/gemini", body)
