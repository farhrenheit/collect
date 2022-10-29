from contextlib import contextmanager
from typing import Iterator
from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker, scoped_session, Session
from settings import DATABSE_URL


engine = create_engine(DATABSE_URL)
Base = declarative_base(bind=engine)

Ses = scoped_session(sessionmaker(bind=engine))


@contextmanager
def get_db() -> Iterator[Session]:
    with Ses() as session:
        yield session
