"""Reference: async SQLAlchemy 2.0 setup + a CRUD service.

Pattern to mimic: an async engine + session factory, a declarative model with the
2.0 Mapped/mapped_column style, and a service that takes an AsyncSession and does
create/get with select()/commit()/refresh(). Adapt names to your spec.
"""
from sqlalchemy import String, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

DATABASE_URL = "sqlite+aiosqlite:///./app.db"      # 'aiosqlite' driver = async sqlite

engine = create_async_engine(DATABASE_URL, echo=False)
async_session_factory = async_sessionmaker(engine, expire_on_commit=False)


class Base(DeclarativeBase):
    pass


class User(Base):
    __tablename__ = "users"
    id: Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[str] = mapped_column(String, unique=True, index=True)
    hashed_password: Mapped[str] = mapped_column(String)


async def init_models() -> None:
    """Create tables (call once on startup)."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def get_session():
    """FastAPI dependency: yield a session and close it after the request."""
    async with async_session_factory() as session:
        yield session


class UserService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create(self, email: str, hashed_password: str) -> User:
        user = User(email=email, hashed_password=hashed_password)
        self.session.add(user)
        await self.session.commit()
        await self.session.refresh(user)
        return user

    async def get_by_email(self, email: str):
        result = await self.session.execute(select(User).where(User.email == email))
        return result.scalar_one_or_none()

    async def get_by_id(self, user_id: int):
        return await self.session.get(User, user_id)
