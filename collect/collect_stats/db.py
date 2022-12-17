from contextlib import contextmanager
from typing import Iterator
from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker, scoped_session, Session


engine = create_engine('postgresql+pg8000://user:@localhost:5432/template3')
Base = declarative_base(bind=engine)

Ses = scoped_session(sessionmaker(bind=engine))


@contextmanager
def get_db() -> Iterator[Session]:
    with Ses() as session:
        yield session
