from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, scoped_session, declarative_base
import os

# Pull from Render environment variable
DATABASE_URL = os.environ.get("SQLALCHEMY_DATABASE_URI")

# PostgreSQL connection with SSL (important for Render)
engine = create_engine(
    DATABASE_URL,
    pool_size=10,
    max_overflow=20,
    pool_timeout=30,
    pool_recycle=1800,
    connect_args={"sslmode": "require"}  # Enforce SSL connection
)

Session = scoped_session(sessionmaker(bind=engine))
SessionLocal = Session
Base = declarative_base()