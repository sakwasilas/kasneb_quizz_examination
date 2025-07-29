import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, scoped_session, declarative_base

DATABASE_URL = os.getenv("DATABASE_URL")  

engine = create_engine(
    DATABASE_URL,
    pool_size=10,
    max_overflow=20,
    pool_timeout=30,
    pool_recycle=1800,
)

Session = scoped_session(sessionmaker(bind=engine))
SessionLocal = Session

Base = declarative_base()