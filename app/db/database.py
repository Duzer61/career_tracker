from typing import Annotated

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from app.config import config as cf

DB_URL = cf.db.db_url

engine = create_async_engine(DB_URL)
AsyncLocalSession = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


async def get_session():
    async with AsyncLocalSession() as session:
        yield session


SessionDep = Annotated[AsyncSession, Depends(get_session)]
