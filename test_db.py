from sqlalchemy import create_engine

# Your PostgreSQL connection string
DATABASE_URL = "postgresql+psycopg2://exams_25_hax1:muCCD3uQohdUFIBe23co6fRZZJ26hE58@dpg-d24b0p8gjchc7388c5bg-a:5432/exams_25_hax1"

# Create engine
engine = create_engine(DATABASE_URL)

try:
    with engine.connect() as connection:
        result = connection.execute("SELECT version();")
        print("✅ Connected successfully!")
        print("PostgreSQL version:", result.fetchone()[0])
except Exception as e:
    print("❌ Failed to connect:")
    print(e)