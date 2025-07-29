import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

# Read the DATABASE_URL from environment variable
DATABASE_URL = os.getenv("DATABASE_URL")

# Fallback if env variable is not found
if not DATABASE_URL:
    raise ValueError("No DATABASE_URL set in environment variables.")

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(bind=engine)
Base = declarative_base()