import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

# Read the DATABASE_URL from environment variable (for Render)
DATABASE_URL = os.getenv("DATABASE_URL")

# Fallback to local PostgreSQL for development (optional)
if not DATABASE_URL:
    DATABASE_URL = "postgresql://silas:RUZveEbKyrFkQJsstYo5kYwBpLkejEIX@dpg-d2484f2li9vc73cf41c0-a.oregon-postgres.render.com:5432/exams_25_2jd0"

# Create the SQLAlchemy engine
engine = create_engine(DATABASE_URL)

# Create session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Base class for models
Base = declarative_base()