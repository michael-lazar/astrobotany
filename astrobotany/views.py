import math
import mimetypes
import os
import pathlib
import typing
from datetime import datetime, timedelta
from functools import lru_cache

import emoji
import jinja2
from jetforce import JetforceApplication, Request, Response, Status
from jetforce.app.base import EnvironDict, RateLimiter, RouteHandler, RoutePattern

from . import items
from .art import render_art
from .models import Certificate, Inbox, ItemSlot, Message, Plant, User

TEMPLATE_DIR = os.path.join(os.path.dirname(__file__), "templates")
STATIC_DIR = os.path.join(os.path.dirname(__file__), "static")

template_env = jinja2.Environment(
    loader=jinja2.FileSystemLoader(TEMPLATE_DIR),
    undefined=jinja2.StrictUndefined,
    trim_blocks=True,
    lstrip_blocks=True,
)


def datetime_format(value, fmt="%A, %B %d, %Y %-I:%M:%S %p"):
    return value.strftime(fmt)


def number_format(value):
    return "{:,}".format(value)


def ordinal_format(value):
    # https://stackoverflow.com/a/50992575
    n = int(value)
    suffix = ["th", "st", "nd", "rd", "th"][min(n % 10, 4)]
    if 11 <= (n % 100) <= 13:
        suffix = "th"
    return str(n) + suffix


template_env.filters["datetime"] = datetime_format
template_env.filters["number"] = number_format
template_env.filters["ordinal"] = ordinal_format

mimetypes.add_type("text/gemini", ".gmi")

password_failed_rate_limiter = RateLimiter("10/5m")
new_account_rate_limiter = RateLimiter("2/4h")
message_rate_limiter = RateLimiter("3/h")


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
    return template_env.get_template(name).render(*args, **kwargs)


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


def load_plant(func: RouteHandler) -> RouteHandler:
    """
    Wraps an route method to handle loading / refreshing the specified user's plant.
    """

    def wrapped(
        request: AuthenticatedRequest, user_id: typing.Optional[str] = None, **kwargs
    ) -> Response:
        if user_id:
            user = User.get_or_none(User.user_id == user_id)
            if user is None:
                return Response(Status.NOT_FOUND, "Not Found")
            elif user == request.user:
                return Response(Status.REDIRECT_TEMPORARY, "/app/plant")
            kwargs["user"] = user
            plant = user.plant
        else:
            plant = request.user.plant

        try:
            plant.refresh()
            response = func(request, plant, **kwargs)
        finally:
            plant.save()

        return response

    return wrapped


app = AstrobotanyApplication()


class PostcardData:
    def __init__(self):
        self.user = None
        self.subject = None
        self.item = None
        self.lines = ["", "", "", ""]

    @classmethod
    def from_request(cls, request):
        return request.session.setdefault("postcard", cls())

    @classmethod
    def delete(cls, request):
        request.session.pop("postcard", None)


@app.route("")
def index_view(request):
    title_art = render_art("title.psci")

    query = (
        Plant.all_active()
        .where(Plant.watered_by.is_null(True))
        .order_by(Plant.watered_at.desc())
        .limit(10)
    )

    activity = []
    for plant in query:
        dt = (datetime.now() - plant.watered_at).total_seconds() // 60
        activity.append(f"{plant.user.username} watered their plant {dt:0.0f} minutes ago")

    total = User.select().count()
    body = render_template("index.gmi", title_art=title_art, activity=activity, total=total)
    return Response(Status.SUCCESS, "text/gemini", body)


@app.route("/news")
def news_view(request):
    files = []
    for filename in os.listdir(os.path.join(STATIC_DIR, "changes")):
        files.append(os.path.splitext(filename)[0])

    files.sort(reverse=True)

    body = render_template("news.gmi", files=files)
    return Response(Status.SUCCESS, "text/gemini", body)


@app.route("/app/register-new")
def register_new_view(request):
    if "REMOTE_USER" not in request.environ:
        msg = "Attach your client certificate to continue."
        return Response(Status.CLIENT_CERTIFICATE_REQUIRED, msg)

    fingerprint = request.environ["TLS_CLIENT_HASH_B64"]
    if Certificate.select().where(Certificate.fingerprint == fingerprint).exists():
        msg = "This certificate has already been linked to an account."
        return Response(Status.CERTIFICATE_NOT_AUTHORISED, msg)

    username = request.query
    if not username:
        msg = "Enter your desired username (US-ASCII characters only)"
        return Response(Status.INPUT, msg)

    if not username.isascii():
        msg = f"The username '{username}' contains invalid characters, try again"
        return Response(Status.INPUT, msg)

    if len(username) > 30:
        msg = f"The username '{username}' is too long, try again"
        return Response(Status.INPUT, msg)

    if User.select().where(User.username == username).exists():
        msg = f"the username '{username}' is already taken, try again"
        return Response(Status.INPUT, msg)

    rate_limit_resp = new_account_rate_limiter.check(request)
    if rate_limit_resp:
        return rate_limit_resp

    cert = request.environ["client_certificate"]

    user = User.initialize(username)
    Certificate.create(
        user=user,
        fingerprint=fingerprint,
        subject=cert.subject.rfc4514_string(),
        not_valid_before_utc=cert.not_valid_before,
        not_valid_after_utc=cert.not_valid_after,
    )

    return Response(Status.REDIRECT_TEMPORARY, "/app")


@app.route("/app/register-existing")
@app.route("/app/register-existing/(?P<user_id>[0-9]+)")
def register_existing_view(request, user_id=None):
    if "REMOTE_USER" not in request.environ:
        msg = "Attach your client certificate to continue."
        return Response(Status.CLIENT_CERTIFICATE_REQUIRED, msg)

    fingerprint = request.environ["TLS_CLIENT_HASH_B64"]
    if Certificate.select().where(Certificate.fingerprint == fingerprint).exists():
        msg = "This certificate has already been linked to an account."
        return Response(Status.CERTIFICATE_NOT_AUTHORISED, msg)

    if user_id is None:
        username = request.query
        if not username:
            msg = "Enter your existing username"
            return Response(Status.INPUT, msg)

        try:
            user = User.select().where(User.username == username).get()
        except User.DoesNotExist:
            msg = f"No existing user was found with the name '{username}'."
            return Response(Status.BAD_REQUEST, msg)

        return Response(Status.REDIRECT_TEMPORARY, f"/app/register-existing/{user.id}")

    user = User.get_by_id(int(user_id))
    if not user.password:
        msg = "Unable to add a certificate because this account does not have a password set."
        return Response(Status.BAD_REQUEST, msg)

    password = request.query
    if not password:
        msg = "Enter your password"
        return Response(Status.SENSITIVE_INPUT, msg)

    rate_limit_resp = password_failed_rate_limiter.check(request)
    if rate_limit_resp:
        return rate_limit_resp

    if not user.check_password(password):
        msg = "Invalid password, try again"
        return Response(Status.SENSITIVE_INPUT, msg)

    cert = request.environ["client_certificate"]
    Certificate.create(
        user=user,
        fingerprint=fingerprint,
        subject=cert.subject.rfc4514_string(),
        not_valid_before_utc=cert.not_valid_before,
        not_valid_after_utc=cert.not_valid_after,
    )

    return Response(Status.REDIRECT_TEMPORARY, "/app")


@app.route("/static/(?P<path>.*)")
def static_view(request, path):
    url_path = pathlib.Path(path.strip("/"))

    filename = pathlib.Path(os.path.normpath(str(url_path)))
    if filename.is_absolute() or str(filename).startswith(".."):
        # Guard against breaking out of the directory
        return Response(Status.NOT_FOUND, "Not Found")

    filepath = STATIC_DIR / filename
    if not filepath.exists():
        return Response(Status.NOT_FOUND, "Not Found")

    mime, encoding = mimetypes.guess_type(str(filename))
    if encoding:
        mimetype = f"{mime}; charset={encoding}"
    else:
        mimetype = mime or "application/octet-stream"

    body = filepath.read_bytes()
    return Response(Status.SUCCESS, mimetype, body)


@app.auth_route("/app")
def app_view(request):
    title_art = render_art("title.psci", ansi_enabled=request.cert.ansi_enabled)
    mailbox_count = request.user.inbox.where(Inbox.is_seen == False).count()
    now = datetime.now()
    body = request.render_template(
        "menu.gmi", title_art=title_art, mailbox_count=mailbox_count, now=now
    )
    return Response(Status.SUCCESS, "text/gemini", body)


@app.auth_route("/app/epilog/(?P<page>[0-9]+)")
def epilog_view(request, page):
    page = int(page)
    if page == 5:
        art_number = 4
    else:
        art_number = page
    art = render_art(f"epilog{art_number}.psci", ansi_enabled=request.cert.ansi_enabled)
    body = request.render_template("epilog.gmi", page=page, art=art)
    return Response(Status.SUCCESS, "text/gemini", body)


@app.auth_route("/app/message-board")
@app.auth_route("/app/message-board/(?P<page>[0-9]+)")
def message_board_view(request, page=1):
    page = int(page)
    paginate_by = 20
    page_count = int(math.ceil(Message.select().count() / paginate_by))
    page_count = max(page_count, 1)
    if page > page_count:
        return Response(Status.NOT_FOUND, "Invalid page number")

    messages = Message.by_date().paginate(page, paginate_by)

    body = request.render_template(
        "message_board.gmi",
        items=messages,
        page=page,
        page_count=page_count,
    )
    return Response(Status.SUCCESS, "text/gemini", body)


@app.auth_route("/app/message-board/submit")
def message_board_submit_view(request):
    if not request.query:
        return Response(Status.INPUT, "What would you like to say? ")

    rate_limit_resp = message_rate_limiter.check(request)
    if rate_limit_resp:
        return rate_limit_resp

    last = Message.select().order_by(Message.id.desc()).first()
    if last and (last.user, last.text) == (request.user, request.query):
        # Almost definitely an accidental double-post by the user
        return Response(Status.REDIRECT_TEMPORARY, "/app/message-board")

    message = Message(user=request.user, text=request.query)
    message.save()
    return Response(Status.REDIRECT_TEMPORARY, "/app/message-board")


@app.auth_route("/app/settings")
def settings_view(request):
    body = request.render_template("settings.gmi")
    return Response(Status.SUCCESS, "text/gemini", body)


@app.auth_route("/app/settings/password")
def settings_password_view(request):
    new_password = request.session.pop("new_password", None)

    if not request.query:
        prompt = f"Enter your new password:"
        return Response(Status.SENSITIVE_INPUT, prompt)

    if not new_password:
        request.session["new_password"] = request.query
        prompt = f"Confirm your new password (enter it again):"
        return Response(Status.SENSITIVE_INPUT, prompt)

    if new_password != request.query:
        return Response(Status.BAD_REQUEST, "Passwords did not match!")

    request.user.set_password(new_password)
    request.user.save()

    message = "Password successfully updated!\n\n=>/app/settings back"
    return Response(Status.SUCCESS, "text/gemini", message)


@app.auth_route("/app/settings/ansi_enabled")
def settings_ansi_enabled_view(request):
    if not request.query:
        prompt = f"Enable ANSI support for colors? [T]rue / [F]alse"
        return Response(Status.INPUT, prompt)

    answer = request.query.strip().lower()

    if answer in ("t", "true"):
        request.cert.ansi_enabled = True
        request.cert.save()
    elif answer in ("f", "false"):
        request.cert.ansi_enabled = False
        request.cert.save()
    else:
        return Response(Status.BAD_REQUEST, f"Invalid query value: {request.query}")

    return Response(Status.REDIRECT_TEMPORARY, "/app/settings")


@app.auth_route("/app/settings/emoji_mode")
def settings_emoji_mode_view(request):
    if not request.query:
        prompt = f"Set emoji display mode (0/1/2): "
        return Response(Status.INPUT, prompt)

    answer = request.query.strip()

    if answer in ("0", "1", "2"):
        request.cert.emoji_mode = int(answer)
        request.cert.save()
    else:
        return Response(Status.BAD_REQUEST, f"Invalid query value: {request.query}")

    return Response(Status.REDIRECT_TEMPORARY, "/app/settings")


@app.auth_route("/app/badges")
def badges_view(request):
    badges = []
    for item_slot in request.user.inventory:
        if isinstance(item_slot.item, items.Badge):
            badges.append(item_slot.item)

    body = request.render_template(
        "badges.gmi",
        badges=badges,
    )
    return Response(Status.SUCCESS, "text/gemini", body)


@app.auth_route("/app/badges/equip/(?P<badge_id>[0-9]+)")
def badges_equip_view(request, badge_id):
    badge_id = int(badge_id)

    try:
        item_slot = request.user.inventory.where(ItemSlot.item_id == badge_id).get()
    except ItemSlot.DoesNotExist:
        return Response(Status.BAD_REQUEST, "You shouldn't be here!")

    badge = item_slot.item
    if not isinstance(badge, items.Badge):
        return Response(Status.BAD_REQUEST, "You shouldn't be here!")

    request.user.badge_id = badge.item_id
    request.user.save()
    return Response(Status.REDIRECT_TEMPORARY, "/app/badges")


@app.auth_route("/app/badges/remove")
def badges_remove_view(request):
    request.user.badge_id = None
    request.user.save()
    return Response(Status.REDIRECT_TEMPORARY, "/app/badges")


@app.auth_route("/app/settings/certificates")
def settings_certificates_view(request):
    certificates = (
        Certificate.select().where(Certificate.user == request.user).order_by(Certificate.last_seen)
    )

    body = request.render_template(
        "settings_certificates.gmi",
        certificates=certificates,
    )
    return Response(Status.SUCCESS, "text/gemini", body)


@app.auth_route("/app/settings/certificates/(?P<certificate_id>[0-9]+)/delete")
def settings_certificates_delete_view(request, certificate_id):
    cert = Certificate.get_or_none(id=certificate_id)
    if cert is None:
        msg = "Certificate not found"
        return Response(Status.BAD_REQUEST, msg)
    elif cert.user != request.user:
        msg = "Certificate not found"
        return Response(Status.BAD_REQUEST, msg)
    elif cert == request.cert:
        msg = "You cannot delete your active certificate"
        return Response(Status.BAD_REQUEST, msg)
    elif not request.query:
        msg = (
            f"Are you sure you want to delete certificate {cert.fingerprint[:10]}? "
            f'Type "confirm" to continue.'
        )
        return Response(Status.INPUT, msg)
    elif request.query.lower() != "confirm":
        return Response(Status.BAD_REQUEST, "Action cancelled")

    cert.delete_instance()
    return Response(Status.REDIRECT_TEMPORARY, "/app/settings/certificates")


@app.auth_route("/app/store")
def store_view(request):
    for_sale = ItemSlot.store_view(request.user)
    coins = request.user.get_item_quantity(items.coin)
    body = request.render_template("store.gmi", for_sale=for_sale, coins=coins)
    return Response(Status.SUCCESS, "text/gemini", body)


@app.auth_route("/app/store/(?P<item_id>[0-9]+)")
def store_item_view(request, item_id):
    item = items.Item.lookup(item_id)
    if item is None:
        return Response(Status.NOT_FOUND, "Item was not found")
    if not item.can_buy(request.user):
        return Response(Status.NOT_FOUND, "Item is not for sale")

    try:
        item_slot = request.user.inventory.where(ItemSlot.item_id == item.item_id).get()
    except ItemSlot.DoesNotExist:
        item_slot = ItemSlot(user=request.user, item_id=item.item_id)

    description = item_slot.item.get_store_description(request.user)
    coins = request.user.get_item_quantity(items.coin)
    body = request.render_template(
        "store_view.gmi", item_slot=item_slot, coins=coins, description=description
    )
    return Response(Status.SUCCESS, "text/gemini", body)


@app.auth_route("/app/store/(?P<item_id>[0-9]+)/purchase/(?P<amount>[0-9]+)")
def store_purchase_view(request, item_id, amount):
    amount = int(amount)

    item = items.Item.lookup(item_id)
    if item is None:
        return Response(Status.NOT_FOUND, "Item was not found")
    if not item.can_buy(request.user):
        return Response(Status.NOT_FOUND, "Item is not for sale")

    price = item.get_price(request.user) * amount
    if not request.query:
        msg = f"Confirm: purchase {amount} {item.name} for {price} coins. [Y]es/[N]o."
        return Response(Status.INPUT, msg)

    if request.query.strip().lower() in ("y", "yes"):
        if request.user.remove_item(items.coin, quantity=price):
            request.user.add_item(item, quantity=amount)
        else:
            return Response(Status.BAD_REQUEST, "Insufficient funds")

    return Response(Status.REDIRECT_TEMPORARY, "/app/store")


@app.auth_route("/app/mailbox")
def mailbox_view(request):
    messages = (
        Inbox.select()
        .where((Inbox.user_to == request.user) | (Inbox.user_from == request.user))
        .order_by(Inbox.id.desc())
    )
    mailbox_art = render_art("mailbox.psci", ansi_enabled=request.cert.ansi_enabled)
    body = request.render_template("mailbox.gmi", messages=messages, mailbox_art=mailbox_art)
    return Response(Status.SUCCESS, "text/gemini", body)


@app.auth_route("/app/mailbox/outgoing")
def mailbox_outgoing_view(request):
    postcards = []
    for postcard in items.Postcard.postcards:
        quantity = request.user.get_item_quantity(postcard)
        if quantity:
            postcards.append((postcard, quantity))

    body = request.render_template("mailbox_outgoing.gmi", postcards=postcards)
    return Response(Status.SUCCESS, "text/gemini", body)


@app.auth_route("/app/mailbox/outgoing/(?P<postcard_id>[0-9]+)")
def mailbox_compose_view(request, postcard_id):
    postcard = items.Postcard.lookup(postcard_id)
    if postcard is None:
        return Response(Status.NOT_FOUND, "Postcard was not found")

    data = PostcardData.from_request(request)
    body = request.render_template("mailbox_compose.gmi", postcard=postcard, data=data)
    return Response(Status.SUCCESS, "text/gemini", body)


@app.auth_route("/app/mailbox/outgoing/(?P<postcard_id>[0-9]+)/to")
def mailbox_compose_to_view(request, postcard_id):
    username = request.query
    if not username:
        return Response(
            Status.INPUT, "Enter a username to address this letter to (case sensitive):"
        )

    try:
        user = User.select().where(User.username == username).get()
    except User.DoesNotExist:
        msg = f"No user was found with the name '{username}'."
        return Response(Status.BAD_REQUEST, msg)

    data = PostcardData.from_request(request)
    data.user = user
    return Response(Status.REDIRECT_TEMPORARY, f"/app/mailbox/outgoing/{postcard_id}")


@app.auth_route("/app/mailbox/outgoing/(?P<postcard_id>[0-9]+)/subject")
def mailbox_compose_subject_view(request, postcard_id):
    subject = request.query
    if not subject:
        return Response(Status.INPUT, f"Enter subject:")

    data = PostcardData.from_request(request)
    data.subject = subject
    return Response(Status.REDIRECT_TEMPORARY, f"/app/mailbox/outgoing/{postcard_id}")


@app.auth_route("/app/mailbox/outgoing/(?P<postcard_id>[0-9]+)/line/(?P<line_number>[0-9]+)")
def mailbox_compose_line_view(request, postcard_id, line_number):
    line = request.query
    if not line:
        return Response(
            Status.INPUT, f"Enter message line {line_number} (or submit a blank space to erase):"
        )

    data = PostcardData.from_request(request)
    data.lines[int(line_number) - 1] = line.rstrip()
    return Response(Status.REDIRECT_TEMPORARY, f"/app/mailbox/outgoing/{postcard_id}")


@app.auth_route("/app/mailbox/outgoing/(?P<postcard_id>[0-9]+)/item")
@app.auth_route("/app/mailbox/outgoing/(?P<postcard_id>[0-9]+)/item/(?P<item_id>[0-9]+)")
def mailbox_compose_item_view(request, postcard_id, item_id=None):
    postcard = items.Postcard.lookup(postcard_id)
    if postcard is None:
        return Response(Status.NOT_FOUND, "Postcard was not found")

    if item_id is None:
        item_slots = [slot for slot in request.user.inventory if slot.item.can_gift(request.user)]
        item_slots.sort(key=lambda x: x.item.name)
        body = request.render_template("mailbox_item.gmi", postcard=postcard, item_slots=item_slots)
        return Response(Status.SUCCESS, "text/gemini", body)

    data = PostcardData.from_request(request)
    data.item = items.Item.lookup(item_id)
    return Response(Status.REDIRECT_TEMPORARY, f"/app/mailbox/outgoing/{postcard_id}")


@app.auth_route("/app/mailbox/outgoing/(?P<postcard_id>[0-9]+)/clear")
def mailbox_compose_clear_view(request, postcard_id):
    PostcardData.delete(request)
    return Response(Status.REDIRECT_TEMPORARY, f"/app/mailbox/outgoing/{postcard_id}")


@app.auth_route("/app/mailbox/outgoing/(?P<postcard_id>[0-9]+)/preview")
def mailbox_preview_view(request, postcard_id):
    postcard = items.Postcard.lookup(postcard_id)
    if postcard is None:
        return Response(Status.NOT_FOUND, "Postcard was not found")

    data = PostcardData.from_request(request)
    if data.user is None:
        return Response(Status.BAD_REQUEST, "Cannot proceed without a user defined")
    if not data.subject:
        return Response(Status.BAD_REQUEST, "Cannot proceed without a subject defined")

    body = request.render_template("mailbox_preview.gmi", postcard=postcard, data=data)
    return Response(Status.SUCCESS, "text/gemini", body)


@app.auth_route("/app/mailbox/outgoing/(?P<postcard_id>[0-9]+)/send")
def mailbox_send_view(request, postcard_id):
    postcard = items.Postcard.lookup(postcard_id)
    if postcard is None:
        return Response(Status.NOT_FOUND, "Postcard was not found")

    data = PostcardData.from_request(request)
    if data.user is None:
        return Response(Status.BAD_REQUEST, "Can't proceed without adding a recipient")
    if not data.subject:
        return Response(Status.BAD_REQUEST, "Cannot proceed without a subject defined")

    if not request.query:
        msg = f"Confirm: send postcard to {data.user.username}. [Y]es/[N]o."
        return Response(Status.INPUT, msg)

    if request.query.strip().lower() not in ("y", "yes"):
        return Response(Status.SUCCESS, "text/gemini", "Action cancelled.")

    if data.item:
        if not data.item.can_gift(request.user):
            return Response(Status.BAD_REQUEST, "Whoops, it looks like you can't send that item!")
        elif not request.user.get_item_quantity(data.item):
            return Response(Status.BAD_REQUEST, "Whoops, it looks like you can't send that item!")

    if not request.user.remove_item(postcard):
        return Response(Status.BAD_REQUEST, "Whoops, it looks like you're all out of postcards!")

    if data.item:
        request.user.remove_item(data.item)

    body = postcard.format_message(*data.lines)
    item_id = data.item.item_id if data.item else None
    Inbox.create(
        user_from=request.user, user_to=data.user, subject=data.subject, body=body, item_id=item_id
    )
    PostcardData.delete(request)

    body = request.render_template("mailbox_send.gmi")
    return Response(Status.SUCCESS, "text/gemini", body)


@app.auth_route("/app/mailbox/(?P<message_id>[0-9]+)")
def mailbox_message_view(request, message_id):
    message = Inbox.get_or_none(id=message_id)
    if message is None:
        return Response(Status.BAD_REQUEST, "You shouldn't be here!")

    new_item_slot = None
    if message.user_to == request.user:
        if not message.is_seen:
            if message.item:
                new_item_slot = request.user.add_item(message.item, quantity=1)
            message.is_seen = True
            message.save()
    elif message.user_from == request.user:
        pass
    else:
        return Response(Status.BAD_REQUEST, "You shouldn't be here!")

    body = request.render_template("mailbox_view.gmi", message=message, new_item_slot=new_item_slot)
    return Response(Status.SUCCESS, "text/gemini", body)


@app.auth_route("/app/visit")
def garden_view(request):
    plants = (
        Plant.all_active()
        .filter(Plant.score > 0, Plant.watered_at >= datetime.now() - timedelta(days=8))
        .order_by(Plant.score.desc())
    )

    garden_art = render_art("trees.psci", ansi_enabled=request.cert.ansi_enabled)
    body = request.render_template("garden.gmi", plants=plants, garden_art=garden_art)
    return Response(Status.SUCCESS, "text/gemini", body)


@app.auth_route("/app/plant")
@app.auth_route("/app/visit/(?P<user_id>[0-9a-f]{32})")
@load_plant
def plant_view(request, plant: Plant, user: typing.Optional[User] = None):
    alert = request.session.pop("alert", None)
    if alert is None:
        alert = plant.get_observation(request.cert.ansi_enabled)

    template = "visit.gmi" if user else "plant.gmi"
    body = request.render_template(template, plant=plant, alert=alert)
    return Response(Status.SUCCESS, "text/gemini", body)


@app.auth_route("/app/plant/water")
@app.auth_route("/app/visit/(?P<user_id>[0-9a-f]{32})/water")
@load_plant
def water_view(request, plant: Plant, user: typing.Optional[User] = None):
    if not plant.can_water():
        return Response(Status.BAD_REQUEST, "You shouldn't be here!")

    request.session["alert"] = plant.water(user=user)

    endpoint = f"/app/visit/{user.user_id}" if user else "/app/plant"
    return Response(Status.REDIRECT_TEMPORARY, endpoint)


@app.auth_route("/app/plant/fertilize")
@app.auth_route("/app/visit/(?P<user_id>[0-9a-f]{32})/fertilize")
@load_plant
def fertilize_view(request, plant: Plant, user: typing.Optional[User] = None):
    if not plant.can_fertilize():
        return Response(Status.BAD_REQUEST, "You shouldn't be here!")

    request.session["alert"] = plant.fertilize(user=user)

    endpoint = f"/app/visit/{user.user_id}" if user else "/app/plant"
    return Response(Status.REDIRECT_TEMPORARY, endpoint)


@app.auth_route("/app/plant/xmas")
@load_plant
def xmas_view(request, plant: Plant):
    if not plant.can_use_christmas_cheer():
        return Response(Status.BAD_REQUEST, "You shouldn't be here!")

    request.session["alert"] = plant.use_christmas_cheer()
    return Response(Status.REDIRECT_TEMPORARY, "/app/plant")


@app.auth_route("/app/plant/search")
@app.auth_route("/app/visit/(?P<user_id>[0-9a-f]{32})/search")
@load_plant
def search_view(request, plant: Plant, user: typing.Optional[User] = None):
    if not plant.can_search():
        return Response(Status.BAD_REQUEST, "You shouldn't be here!")

    request.session["alert"] = plant.pick_petal(user=user)

    endpoint = f"/app/visit/{user.user_id}" if user else "/app/plant"
    return Response(Status.REDIRECT_TEMPORARY, endpoint)


@app.auth_route("/app/plant/shake")
@load_plant
def shake_view(request, plant: Plant):
    if not plant.can_shake():
        return Response(Status.BAD_REQUEST, "You shouldn't be here!")

    request.session["alert"] = plant.shake()

    return Response(Status.REDIRECT_TEMPORARY, "/app/plant")


@app.auth_route("/app/plant/harvest")
@app.auth_route("/app/plant/harvest/confirm")
@load_plant
def harvest_view(request, plant: Plant):
    if not plant.can_harvest():
        return Response(Status.BAD_REQUEST, "You shouldn't be here!")

    if request.path.endswith("/confirm"):
        if request.query.strip() == f"Goodbye {plant.name}":
            plant.harvest()
            return Response(Status.REDIRECT_TEMPORARY, "/app/epilog/1")
        elif request.query:
            return Response(Status.REDIRECT_TEMPORARY, "/app/plant/harvest")
        else:
            msg = f'Type "Goodbye {plant.name}" to send off your plant.'
            return Response(Status.INPUT, msg)

    body = request.render_template("harvest.gmi", plant=plant)
    return Response(Status.SUCCESS, "text/gemini", body)


@app.auth_route("/app/plant/rename")
@load_plant
def plant_rename_view(request, plant: Plant):
    if not request.query:
        return Response(Status.INPUT, "Enter a new nickname for your plant:")

    plant.name = request.query[:40]
    msg = f'Your plant shall henceforth be known as "{plant.name}".'
    request.session["alert"] = msg
    return Response(Status.REDIRECT_TEMPORARY, "/app/plant")


@app.auth_route("/app/inventory")
def inventory_view(request):
    inventory = sorted(request.user.inventory, key=lambda x: x.item.name)
    body = request.render_template("inventory.gmi", inventory=inventory)
    return Response(Status.SUCCESS, "text/gemini", body)


@app.auth_route("/app/inventory/(?P<item_slot_id>[0-9]+)")
def inventory_view_item(request, item_slot_id):
    item_slot_id = int(item_slot_id)
    try:
        item_slot = ItemSlot.get_by_id(item_slot_id)
    except ItemSlot.DoesNotExist:
        return Response(Status.NOT_FOUND, "Not Found")

    if not item_slot.user == request.user:
        return Response(Status.NOT_FOUND, "Not Found")

    description = item_slot.item.get_inventory_description(request.user)
    body = request.render_template(
        "inventory_view.gmi", item_slot=item_slot, description=description
    )
    return Response(Status.SUCCESS, "text/gemini", body)


@app.route("/public/(?P<user_id>[0-9a-f]{32})")
@app.route("/public/(?P<user_id>[0-9a-f]{32})/m(?P<mode>[0-9])+")
def public_view(request, user_id: str, mode: str = "0"):
    user = User.get_or_none(User.user_id == user_id)
    if user is None:
        return Response(Status.NOT_FOUND, "Not Found")

    if mode == "0":
        ansi_enabled = False
    elif mode == "1":
        ansi_enabled = True
    else:
        return Response(Status.NOT_FOUND, "Not Found")

    request.cert = Certificate(ansi_enabled=ansi_enabled)

    body = render_template("public.gmi", request=request, plant=user.plant)
    return Response(Status.SUCCESS, "text/gemini", body)
