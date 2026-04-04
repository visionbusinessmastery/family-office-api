from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
import os

# 1. Récupérer la vraie DB Render
DATABASE_URL = os.getenv("DATABASE_URL")

# Sécurité (fallback local)
if not DATABASE_URL:
    DATABASE_URL = "sqlite:///./test.db"

# 2. Créer engine APRÈS
engine = create_engine(DATABASE_URL)

# 3. Session
SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine
)

# 4. Base
Base = declarative_base()

# 5. Dependency FastAPI
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()



