from connection import SessionLocal
from models import User

db = SessionLocal()
users = db.query(User).all()
for user in users:
    print(f"Username: {user.username}, Password: {user.password}, Role: {user.role}")
db.close()