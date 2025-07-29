
import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base


DB_URL = os.environ.get("DATABASE_URL")


DB_URL = "postgresql://postgres:yourpassword@localhost:5432/exams_25"

engine = create_engine(DB_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()