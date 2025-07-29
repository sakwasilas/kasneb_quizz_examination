from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, scoped_session, declarative_base

DATABASE_URL ='postgresql://exams_25_6cm_user:RzZ0nHIZPHBVbWSTjgln9q2wLlEgVUE4@dpg-d24clsidbo4c73ajf8mg-a.oregon-postgres.render.com:5432/exams_25_6cmx?sslmode=require'
'

engine = create_engine(DATABASE_URL)

Session = scoped_session(sessionmaker(bind=engine))
SessionLocal = Session

Base = declarative_base()