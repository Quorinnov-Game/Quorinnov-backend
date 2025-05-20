from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from dotenv import load_dotenv
import os

load_dotenv()  # <== DÒNG NÀY GIÚP ĐỌC FILE .env

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://postgres:abc123@localhost:5432/quorinov")

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()