import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

# Read the DATABASE_URL from environment variable
DATABASE_URL = os.getenv("DATABASE_URL")

# Fallback if env variable is not found
DATABASE_URL = "postgresql://silas:RUZveEbKyrFkQJsstYo5kYwBpLkejEIX@dpg-d2484f2li9vc73cf41c0-a.oregon-postgres.render.com:5432/exams_25_2jd0"

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(bind=engine)
Base = declarative_base()