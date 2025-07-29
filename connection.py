from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, scoped_session, declarative_base

# MySQL connection details
username = "root"
password = "2480"
database = "exams_25"

# SQLAlchemy database URL
path = f"mysql+mysqldb://{username}:{password}@localhost/{database}?charset=utf8mb4"

# Create engine with connection pool settings
engine = create_engine(
    path,
    pool_size=10,
    max_overflow=20,
    pool_timeout=30,
    pool_recycle=1800,
)

# Use scoped_session to handle threads automatically
Session = scoped_session(sessionmaker(bind=engine))
SessionLocal = Session  # Alias for compatibility

Base = declarative_base()