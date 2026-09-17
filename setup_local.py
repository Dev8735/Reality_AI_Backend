"""
Local development setup script.
Usage:  .venv\Scripts\python.exe setup_local.py
"""
from dotenv import load_dotenv
load_dotenv()

from sqlalchemy import text, inspect
from app.core.database import engine, Base
import app.models  # noqa: registers all ORM models

# ── 1. Enable extensions ──────────────────────────────────────────────────────
print("Enabling extensions...")
with engine.connect() as conn:
    conn.execute(text("CREATE EXTENSION IF NOT EXISTS postgis;"))
    conn.commit()
    print("  postgis ... OK")
    try:
        conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector;"))
        conn.commit()
        print("  pgvector ... OK")
        PGVECTOR_IN_DB = True
    except Exception:
        conn.rollback()
        print("  pgvector ... SKIPPED (not installed in PostgreSQL - OK for dev)")
        PGVECTOR_IN_DB = False

# ── 2. Create tables in dependency order ──────────────────────────────────────
insp = inspect(engine)
existing = set(insp.get_table_names())
print(f"Existing tables: {existing or '(none)'}")
meta = Base.metadata

def create_table_if_missing(table_name):
    if table_name not in existing:
        meta.tables[table_name].create(bind=engine, checkfirst=True)
        print(f"  {table_name} ... Created")
    else:
        print(f"  {table_name} ... Already exists")

print("Creating tables in dependency order...")

# broker (no FK deps)
create_table_if_missing("broker")

# customer (no FK deps)
create_table_if_missing("customer")

# listing (FK -> broker) — created via raw SQL to dodge pgvector type
if "listing" not in existing:
    embed_col = "embedding VECTOR(384)," if PGVECTOR_IN_DB else "embedding JSONB,"
    with engine.connect() as conn:
        conn.execute(text(f"""
            CREATE TABLE IF NOT EXISTS listing (
                id            SERIAL PRIMARY KEY,
                broker_id     INTEGER NOT NULL REFERENCES broker(id),
                title         VARCHAR(200) NOT NULL,
                description   TEXT,
                price         NUMERIC(12,2) NOT NULL,
                property_type VARCHAR NOT NULL,
                location      geometry(POINT,4326) NOT NULL,
                carpet_area   NUMERIC,
                built_up_area NUMERIC,
                plot_area     NUMERIC,
                floor_number  INTEGER,
                rooms         JSONB,
                {embed_col}
                amenities     JSONB,
                created_at    TIMESTAMPTZ NOT NULL DEFAULT now(),
                CONSTRAINT ck_listing_property_type
                    CHECK (property_type IN ('flat', 'house_land'))
            );
        """))
        conn.commit()
    print("  listing ... Created")
else:
    print("  listing ... Already exists")

# conversation (FK -> customer)
create_table_if_missing("conversation")

# lead (FK -> listing, customer)
create_table_if_missing("lead")

# ── 3. Stamp alembic version ──────────────────────────────────────────────────
print("Stamping alembic_version...")
with engine.connect() as conn:
    conn.execute(text(
        "CREATE TABLE IF NOT EXISTS alembic_version "
        "(version_num VARCHAR(32) NOT NULL PRIMARY KEY)"
    ))
    exists = conn.execute(
        text("SELECT 1 FROM alembic_version WHERE version_num = '001_gist_index'")
    ).fetchone()
    if not exists:
        conn.execute(
            text("INSERT INTO alembic_version (version_num) VALUES ('001_gist_index')")
        )
    conn.commit()
print("  Alembic stamped at 001_gist_index")

# ── 4. GiST index on listing.location ────────────────────────────────────────
print("Ensuring GiST index on listing.location...")
try:
    with engine.connect() as conn:
        conn.execute(text(
            "CREATE INDEX IF NOT EXISTS ix_listing_location "
            "ON listing USING gist (location);"
        ))
        conn.commit()
    print("  GiST index ... OK")
except Exception as e:
    print(f"  GiST index skipped: {e}")

print("\n Setup complete!")
print("  Start the server:  .venv\\Scripts\\uvicorn.exe app.main:app --reload --host 0.0.0.0 --port 8000")
