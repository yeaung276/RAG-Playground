import argparse
import os
import subprocess


def run_dev(args):
    from dotenv import dotenv_values

    env = {**os.environ, **dotenv_values(".env")}

    # `yarn dev` is `vite build --watch`: it rebuilds admin/dist (console +
    # widget.js) on change, and uvicorn --reload serves that tree.
    subprocess.run(["yarn", "--cwd", "admin", "install", "--frozen-lockfile"], check=True)
    watchers = [subprocess.Popen(["yarn", "--cwd", "admin", "dev"])]
    try:
        subprocess.run(
            ["uv", "run", "uvicorn", "app.app:app", "--reload",
             "--timeout-graceful-shutdown", "5"],
            env=env,
        )
    finally:
        for watcher in watchers:
            watcher.terminate()


def run_migrate(args):
    from alembic.config import main as alembic_main

    alembic_main(argv=args.alembic_args, prog="main.py migrate")


def build_parser():
    parser = argparse.ArgumentParser(prog="main.py")
    sub = parser.add_subparsers(dest="command", required=True)

    dev = sub.add_parser("dev", help="run api + watch-build the front-end")
    dev.set_defaults(func=run_dev)

    migrate = sub.add_parser(
        "migrate",
        help="run alembic db migrations",
        description="Forwards its arguments to alembic (see 'migrate <cmd> -h').",
        epilog=(
            "common commands:\n"
            "  upgrade head              apply all pending migrations\n"
            "  downgrade -1              revert the last migration\n"
            "  revision --autogenerate -m \"msg\"   generate a migration from model changes\n"
            "  current                   show the current db revision\n"
            "  history                   list the migration history\n"
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    migrate.add_argument("alembic_args", nargs=argparse.REMAINDER,
                         help="args forwarded to alembic, e.g. upgrade head")
    migrate.set_defaults(func=run_migrate)

    return parser


def main():
    args = build_parser().parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
