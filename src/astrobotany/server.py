import argparse

from jetforce import GeminiServer

from astrobotany import __version__
from astrobotany.views import app


def build_argument_parser():
    parser = argparse.ArgumentParser(
        prog="astrobotany",
        description="🌱 A community garden over the Gemini protocol",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument(
        "-V",
        "--version",
        action="version",
        version="astrobotany " + __version__,
    )
    parser.add_argument(
        "--host",
        help="Server address to bind to",
        default="127.0.0.1",
    )
    parser.add_argument(
        "--port",
        help="Server port to bind to",
        type=int,
        default=1965,
    )
    parser.add_argument(
        "--hostname",
        help="Server hostname",
        default="localhost",
    )
    return parser


def main():
    parser = build_argument_parser()
    args = parser.parse_args()

    server = GeminiServer(
        app,
        host=args.host,
        port=args.port,
        hostname=args.hostname,
    )
    server.run()


if __name__ == "__main__":
    main()
