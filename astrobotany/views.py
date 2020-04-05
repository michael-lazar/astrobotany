import os

import jetforce
import jinja2
from jetforce import Response, Status

from .models import Message, Plant, User

TEMPLATE_DIR = os.path.join(os.path.abspath(os.path.dirname(__file__)), "templates")

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


class AstrobotanyVirtualHost:
    """
    An extendable "vhost" application for a jetforce gemini server.

    It is designed so that it can be hooked into a existing jetforce server
    application under a separate route, like this:

    >>> from astrobotany import vhost
    >>>
    >>> app = StaticDirectoryApplication(...)
    >>> app.route(hostname="astrobotany.mozz.us")(vhost)

    The following features have also been added:
        - Automatically loading the user from the environment.
        - Automatically loading/saving the user's active plant.
        - Adding an authenticated=True argument to the route decorator to
          to support authenticated-only routes.
        - Capturing regex groups in paths and passing them as arguments to
          wrapped function.
    """

    def __init__(self):
        self.routes: list = []

    def __call__(self, request):
        request.user = None
        request.plant = None

        if "REMOTE_USER" in request.environ:
            request.user, _ = User.get_or_create(
                user_id=request.environ["TLS_CLIENT_SERIAL_NUMBER"],
                username=request.environ["REMOTE_USER"],
            )
            request.plant = request.user.plant

        for route_pattern, callback, authenticated in self.routes[::-1]:
            match = route_pattern.match(request)
            if match:
                kwargs = match.groupdict()
                break
        else:
            callback, authenticated, kwargs = self.default_callback, False, {}

        if authenticated and request.user is None:
            msg = "You must have an account to view this page!"
            return Response(Status.AUTHORISED_CERTIFICATE_REQUIRED, msg)

        if request.plant:
            request.plant.refresh()
            response = callback(request, **kwargs)
            request.plant.save()
        else:
            response = callback(request, **kwargs)

        return response

    def route(self, path, strict_trailing_slash=True, authenticated=False):
        route_pattern = jetforce.RoutePattern(
            path, strict_trailing_slash=strict_trailing_slash, strict_hostname=False,
        )

        def wrap(func):
            self.routes.append((route_pattern, func, authenticated))
            return func

        return wrap

    def default_callback(self, request, **kwargs):
        return Response(Status.PERMANENT_FAILURE, "Not Found")


vhost = AstrobotanyVirtualHost()


@vhost.route("", strict_trailing_slash=False)
def index(request):
    body = render_template("index.gmi")
    return Response(Status.SUCCESS, "text/gemini", body)


@vhost.route("/register")
def register(request):
    body = render_template("register.gmi")
    return Response(Status.SUCCESS, "text/gemini", body)


@vhost.route("/message-board")
def message_board(request):
    messages = Message.select().limit(20).order_by(Message.created_at.desc())
    body = render_template("message_board.gmi", request=request, messages=messages)
    return Response(Status.SUCCESS, "text/gemini", body)


@vhost.route("/message-board/post", authenticated=True)
def message_board_post(request):
    if not request.query:
        return Response(Status.INPUT, "What would you like to say? ")

    message = Message(user=request.user, text=request.query)
    message.save()
    return Response(Status.REDIRECT_TEMPORARY, "/message-board")


@vhost.route("/plant", authenticated=True)
def plant(request):
    body = render_template("plant.gmi", request=request, plant=request.plant)
    return Response(Status.SUCCESS, "text/gemini", body)


@vhost.route("/plant/water", authenticated=True)
def water(request):
    info = request.plant.water()
    body = render_template("water.gmi", request=request, plant=request.plant, info=info)
    return Response(Status.SUCCESS, "text/gemini", body)


@vhost.route("/plant/observe", authenticated=True)
def observe(request):
    body = render_template("observe.gmi", request=request, plant=request.plant)
    return Response(Status.SUCCESS, "text/gemini", body)


@vhost.route("/plant/harvest", authenticated=True)
def harvest(request):
    if not request.plant.stage == 5 and not request.plant.dead:
        return Response(Status.TEMPORARY_FAILURE, "You shouldn't be here")

    if request.query == "confirm":
        request.plant.harvest()
        return Response(Status.REDIRECT_TEMPORARY, "/plant")

    body = render_template("harvest.gmi", request=request, plant=request.plant)
    return Response(Status.SUCCESS, "text/gemini", body)


@vhost.route("/directory")
def directory(request):
    plants = Plant.filter(Plant.user_active.is_null(False))
    plants = plants.join(User).order_by(User)
    body = render_template("directory.gmi", request=request, plants=plants)
    return Response(Status.SUCCESS, "text/gemini", body)


@vhost.route("/directory/(?P<user_id>[0-9A-F]+)")
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


@vhost.route("/directory/(?P<user_id>[0-9A-F]+)/water")
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
