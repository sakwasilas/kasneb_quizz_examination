import os
from connection import Base, engine, SessionLocal
from models import User, StudentProfile

# ✅ Create tables
Base.metadata.create_all(bind=engine)
print("✅ Tables created successfully!")
print("Using DB file:", os.path.abspath("exams_25.db"))

# ✅ Add default admin user
def add_admin_user():
    db = SessionLocal()
    try:
        existing_user = db.query(User).filter_by(username="admin").first()
        if existing_user:
            print("ℹ️ Admin user already exists.")
        else:
            admin = User(
                username="admin",
                password="admin123",  # You can hash this later
                role="admin"
            )
            db.add(admin)
            db.commit()
            print("✅ Admin user created! Username: admin | Password: admin123")
    finally:
        db.close()

if __name__ == "__main__":
    add_admin_user()