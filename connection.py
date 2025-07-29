from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, scoped_session, declarative_base

DATABASE_URL = "postgresql+psycopg2://exams_25_6cm_user:<your-password>@dpg-d24clsidbo4c73ajf8mg-a.oregon-postgres.render.com:5432/exams_25_6cmx"

engine = create_engine(DATABASE_URL)

Session = scoped_session(sessionmaker(bind=engine))
SessionLocal = Session

Base = declarative_base()