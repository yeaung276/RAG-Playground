from pwdlib import PasswordHash
from pwdlib.hashers.bcrypt import BcryptHasher
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.admin import Admin

_hasher = PasswordHash((BcryptHasher(),))


class AdminService:
    def __init__(self, db: AsyncSession):
        self._db = db

    async def get(self, admin_id: str) -> Admin | None:
        return await self._db.get(Admin, admin_id)

    async def get_by_username(self, username: str) -> Admin | None:
        result = await self._db.execute(
            select(Admin).where(Admin.username == username)
        )
        return result.scalar_one_or_none()

    async def create(self, username: str, password: str) -> Admin:
        admin = Admin(username=username, password_hash=_hasher.hash(password))
        self._db.add(admin)
        await self._db.commit()
        await self._db.refresh(admin)
        return admin

    async def authenticate(self, username: str, password: str) -> Admin | None:
        admin = await self.get_by_username(username)
        if admin is None or not _hasher.verify(password, admin.password_hash):
            return None
        return admin
