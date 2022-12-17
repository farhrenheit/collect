from db import Base
from sqlalchemy import Column, ForeignKey, DateTime, String, Integer


class GameStratzSchema(Base):
    __tablename__ = "game_stats"

    id = Column(Integer, primary_key=True, nullable=False)
    radiant_score = Column(String, nullable=True)
    dire_score = Column(String, nullable=True)
    gameMinute = Column(String, nullable=True)
    timestamp = Column(DateTime, nullable=False)

'''class PageSchema(Base):
    __tablename__ = "page_info"
    timestamp = Column(DateTime, nullable=False)
    height_pxl = Column(Integer, nullable=False)'''
    