from app.core.database import Base, engine
from app.models.database_models import MemoryRecord


def initialize_database() -> None:
    Base.metadata.create_all(bind=engine)