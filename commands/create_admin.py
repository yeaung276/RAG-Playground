import asyncio
import getpass

from app.db.session import async_session_maker
from app.services.admin.admin_service import AdminService


def add_arguments(parser):
    parser.add_argument("--username", help="admin username (prompted if omitted)")


def run(args):
    asyncio.run(_run(args))


async def _run(args):
    username = args.username or input("Username: ")
    password = getpass.getpass("Password: ")
    if password != getpass.getpass("Password (again): "):
        raise SystemExit("Error: passwords do not match")
    if not password:
        raise SystemExit("Error: password cannot be empty")

    async with async_session_maker() as db:
        svc = AdminService(db)
        if await svc.get_by_username(username):
            raise SystemExit(f"Error: admin '{username}' already exists")
        admin = await svc.create(username, password)

    print(f"Created admin '{admin.username}'")
