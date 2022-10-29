from db import Base
from sqlalchemy import Column, ForeignKey, DateTime, String
from sqlalchemy.dialects.postgresql import UUID as UUID_FIELD


class GameSchema(Base):
    __tablename__ = "game"

    id = Column(UUID_FIELD(as_uuid=True), primary_key=True, nullable=False)
    team_one = Column(String, nullable=False)
    team_two = Column(String, nullable=False)


class CoeffSchema(Base):
    __tablename__ = "coef_by_game"

    id = Column(UUID_FIELD(as_uuid=True), primary_key=True, nullable=False)
    game_id = Column(UUID_FIELD(as_uuid=True), ForeignKey("game.id"), nullable=False)
    w_one = Column(String, nullable=False)
    t = Column(String, nullable=True)
    w_two = Column(String, nullable=False)
    timestamp = Column(DateTime, nullable=False)
