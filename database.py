from sqlalchemy import create_engine
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, sessionmaker

async_engine = create_async_engine(
    url='sqlite+aiosqlite:///cryptobot.db',
    echo=True
)

async_session = async_sessionmaker(async_engine)

sync_engine = create_engine(
    url='sqlite:///cryptobot.db',
    echo=True
)

sync_session = sessionmaker(sync_engine)


class Base(DeclarativeBase):
    pass


class UsersOrm(Base):
    __tablename__ = 'users'
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int]
    coin: Mapped[str]
    price_check: Mapped[int]
    higher = Mapped[bool]


