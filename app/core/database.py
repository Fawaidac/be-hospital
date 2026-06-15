#app/core/database.py
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from app.core.config import settings

# Main DB
engine_main = create_engine(
    settings.DATABASE_MAIN,
    pool_pre_ping=True,
)

SessionLocalMain = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine_main
)

BaseMain = declarative_base()


# PSC DB
engine_psc = create_engine(
    settings.DATABASE_PSC,
    pool_pre_ping=True,
)

SessionLocalPSC = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine_psc
)

BasePSC = declarative_base()


# Dependency
def get_db_main():
    db = SessionLocalMain()
    try:
        yield db
    finally:
        db.close()


def get_db_psc():
    db = SessionLocalPSC()
    try:
        yield db
    finally:
        db.close()