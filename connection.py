from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, scoped_session, declarative_base

DATABASE_URL = "postgresql+psycopg2://exams_25_hax1:muCCD3uQohdUFIBe23co6fRZZJ26hE58@dpg-d24b0p8gjchc7388c5bg-a.oregon-postgres.render.com:5432/exams_25_hax1"

engine = create_engine(DATABASE_URL)

Session = scoped_session(sessionmaker(bind=engine))
SessionLocal = Session

Base = declarative_base()