import os
import typing
from functools import lru_cache

import emoji
import jinja2
from jetforce import JetforceApplication, Request, Response, Status
from jetforce.app.base import EnvironDict, RouteHandler, RoutePattern

from astrobotany.models import Certificate, User
from astrobotany.utils import ordinal_format

TEMPLATE_DIR = os.path.join(os.path.dirname(__file__), "templates")
STATIC_DIR = os.path.join(os.path.dirname(__file__), "static")


def setup_template_environment():
    template_env = jinja2.Environment(
        loader=jinja2.FileSystemLoader(TEMPLATE_DIR),
        undefined=jinja2.StrictUndefined,
        trim_blocks=True,
        lstrip_blocks=True,
    )

    def datetime_format(value, fmt="%A, %B %d, %Y %-I:%M:%S %p"):
        return value.strftime(fmt)

    def number_format(value):
        return f"{value:,}"

    def humanize_timedelta(value):
        minutes = int(value.total_seconds() // 60)
        if minutes == 1:
            return "1 minute"
        elif minutes < 60:
            return f"{minutes} minutes"

        hours = minutes // 60
        if hours == 1:
            return "1 hour"
        else:
            return f"{hours} hours"

    template_env.filters["datetime"] = datetime_format
    template_env.filters["number"] = number_format
    template_env.filters["ordinal"] = ordinal_format
    template_env.filters["humanize_timedelta"] = humanize_timedelta

    return template_env


_template_env = setup_template_environment()


@lru_cache(2048)
def load_session(session_id: str) -> dict:
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
    return _template_env.get_template(name).render(*args, **kwargs)


class AuthenticatedRequest(Request):
    """
    Request class that includes
    """

    user: User
    session: dict
    cert: Certificate

    def __init__(self, environ: EnvironDict, cert: Certificate):
        super().__init__(environ)
        self.cert = cert
        self.user = cert.user
        self.session = load_session(cert.user.user_id)

    def render_template(self, name: str, *args, **kwargs) -> str:
        kwargs["request"] = self
        text = render_template(name, *args, **kwargs)
        if self.cert.emoji_mode == 1:
            text = emoji.demojize(text)
        elif self.cert.emoji_mode == 2:
            text = emoji.replace_emoji(text)  # type: ignore
        return text


def authenticated_route(func: RouteHandler) -> RouteHandler:
    """
    Wraps a route method to ensure that the request is authenticated.
    """

    def wrapped(request: Request, **kwargs) -> Response:
        if "REMOTE_USER" not in request.environ:
            msg = "Attach your client certificate to continue."
            return Response(Status.CLIENT_CERTIFICATE_REQUIRED, msg)

        if request.environ["TLS_CLIENT_AUTHORISED"]:
            # Old-style verified certificate
            serial_number = request.environ["TLS_CLIENT_SERIAL_NUMBER"]
            fingerprint = f"{serial_number:032X}"  # Convert to hex
        else:
            # New-style self signed certificate
            fingerprint = typing.cast(str, request.environ["TLS_CLIENT_HASH_B64"])

        cert = User.login(fingerprint)
        if cert is None:
            body = render_template(
                "register.gmi",
                request=request,
                fingerprint=fingerprint,
                cert=request.environ["client_certificate"],
            )
            return Response(Status.SUCCESS, "text/gemini", body)

        request = AuthenticatedRequest(request.environ, cert)
        response = func(request, **kwargs)
        return response

    return wrapped


class AstrobotanyApplication(JetforceApplication):
    def auth_route(self, path: str = ".*") -> typing.Callable[[RouteHandler], RouteHandler]:
        """
        Jetforce route decorator with an added authentication layer.
        """
        route_pattern = RoutePattern(path)

        def wrap(func: RouteHandler) -> RouteHandler:
            authenticated_func = authenticated_route(func)
            app.routes.append((route_pattern, authenticated_func))
            return func

        return wrap


app = AstrobotanyApplication()

import astrobotany.views  # noqa
