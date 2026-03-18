import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.db import Base, engine, ensure_runtime_schema
import app.models  # noqa: F401


def main() -> None:
    Base.metadata.create_all(bind=engine)
    ensure_runtime_schema()
    print("Database initialized.")


if __name__ == "__main__":
    main()
