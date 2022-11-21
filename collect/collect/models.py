from db import Base
from sqlalchemy import Column, ForeignKey, DateTime, String, Boolean
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
    w_one = Column(String, nullable=True)
    draw = Column(String, nullable=True)
    w_two = Column(String, nullable=True)
    plus = Column(String, nullable=True)
    dupl = Column(Boolean, nullable=True)
    timestamp = Column(DateTime, nullable=False)
    

'''class PageSchema(Base):
    __tablename__ = "page_info"
    timestamp = Column(DateTime, nullable=False)
    height_pxl = Column(Integer, nullable=False)'''
    