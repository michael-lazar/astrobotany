import mimetypes

from astrobotany.app import app  # noqa
from astrobotany.models import init_db  # noqa

mimetypes.add_type("text/gemini", ".gmi")

__version__ = "0.0.1"
