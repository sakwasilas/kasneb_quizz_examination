from connection import Base, engine
from models import User, StudentProfile  

# Create all tables in the database
if __name__ == "__main__":
    Base.metadata.create_all(bind=engine)
    print("✅ Tables created successfully!")