from sqlalchemy import create_engine, Column, Integer, String, DateTime, JSON
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

Base = declarative_base()

class ContentHistory(Base):
    __tablename__ = 'content_history'
    id = Column(Integer, primary_key=True)
    content = Column(String)
    platform = Column(String)
    posted_at = Column(DateTime)
    performance_metrics = Column(JSON) 