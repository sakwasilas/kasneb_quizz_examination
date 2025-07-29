import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

# Get from environment variables (Render and local .env)
DB_URL = os.environ.get("DATABASE_URL")  # Render will set this

# Fallback for local development (optional)
if not DB_URL:
    username = "root"
    password = "2480"
    database = "exams_25"
    DB_URL = f"mysql+mysqldb://{username}:{password}@localhost/{database}?charset=utf8mb4"

engine = create_engine(DB_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()