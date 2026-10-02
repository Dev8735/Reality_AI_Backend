"""Synthetic data seeder — generates realistic test data for Surat, Gujarat.

Usage:
    python -m app.db.seed_synthetic_data              # default counts
    python -m app.db.seed_synthetic_data --force      # overwrite existing rows
    python -m app.db.seed_synthetic_data -n 200       # custom listing count
"""

import argparse
import random
import sys

from faker import Faker
from geoalchemy2.elements import WKTElement

from app.core.database import SessionLocal
from app.core.security import hash_password
from app.models.broker import Broker
from app.models.customer import Customer
from app.models.listing import Listing
from app.models.lead import Lead
from app.models.conversation import Conversation

fake = Faker("en_IN")

# ---------------------------------------------------------------------------
# Real Surat, Gujarat coordinates across actual neighbourhoods.
# This is the ONE city the whole project uses — do not substitute another.
# ---------------------------------------------------------------------------
REAL_CITY_COORDS: list[tuple[float, float]] = [
    # (lat, lng) — actual points in named Surat areas
    (21.1702, 72.8311),   # Adajan
    (21.1550, 72.7716),   # Vesu
    (21.1612, 72.7890),   # Citylight
    (21.1480, 72.7780),   # Piplod
    (21.1590, 72.8200),   # Athwa
    (21.2150, 72.8830),   # Varachha
    (21.1950, 72.8190),   # Nanpura
    (21.1850, 72.8370),   # Majura Gate
    (21.2050, 72.8580),   # Udhna
    (21.2280, 72.8640),   # Katargam
    (21.1900, 72.8020),   # Chauta Bazaar
    (21.1750, 72.8080),   # Ghod Dod Road
    (21.1650, 72.7950),   # Pal
    (21.1420, 72.7680),   # VIP Road
    (21.1350, 72.7850),   # Dumas Road
    (21.2100, 72.8400),   # Sagrampura
    (21.2200, 72.8950),   # Kapodra
    (21.2320, 72.8520),   # Limbayat
    (21.1780, 72.8150),   # Ring Road
    (21.1680, 72.8260),   # Parle Point
    (21.1560, 72.8100),   # Parvat Patia
    (21.1990, 72.8300),   # Khatodara
    (21.2400, 72.8700),   # Sachin
    (21.1450, 72.7750),   # Althan
    (21.1630, 72.8400),   # Rander
]


def _jitter(coord: tuple[float, float], metres: float = 300) -> tuple[float, float]:
    """Add small random offset (~*metres* in each direction)."""
    # ~0.000009 degrees per metre at Surat's latitude
    delta = metres * 0.000009
    return (
        coord[0] + random.uniform(-delta, delta),
        coord[1] + random.uniform(-delta, delta),
    )


def _plausible_price(prop_type: str, area: float) -> float:
    """Generate a price loosely correlated with property type and area."""
    if prop_type == "flat":
        rate_per_sqft = random.uniform(3500, 8000)
    else:  # house_land
        rate_per_sqft = random.uniform(2000, 5500)
    return round(rate_per_sqft * area, 2)


def _make_rooms(prop_type: str) -> dict:
    """Generate room data matching property type."""
    if prop_type == "flat":
        bedrooms = random.choice([1, 2, 3, 4])
        return {
            "bedrooms": bedrooms,
            "bathrooms": max(1, bedrooms - 1),
            "balconies": random.choice([0, 1, 2]),
            "hall": 1,
            "kitchen": 1,
        }
    else:
        bedrooms = random.choice([3, 4, 5, 6])
        return {
            "bedrooms": bedrooms,
            "bathrooms": max(2, bedrooms - 1),
            "balconies": random.choice([1, 2, 3]),
            "hall": random.choice([1, 2]),
            "kitchen": 1,
            "garden": random.choice([0, 1]),
        }


def seed(
    n_listings: int = 500,
    n_brokers: int = 10,
    n_customers: int = 30,
) -> None:
    """Seed the database with synthetic data.

    Leaves ``embedding`` and ``amenities`` as NULL — those columns are
    populated by Person 1's AI pipelines, not this script.
    """
    db = SessionLocal()
    try:
        # ── Brokers ──────────────────────────────────────────────
        brokers: list[Broker] = []
        dummy_hash = hash_password("password123")
        for _ in range(n_brokers):
            broker = Broker(
                name=fake.name(),
                email=fake.unique.email(),
                phone_hash=hash_password(fake.phone_number()),
                password_hash=dummy_hash,
            )
            db.add(broker)
            brokers.append(broker)
        db.flush()
        print(f"  Created {len(brokers)} brokers")

        # ── Customers ───────────────────────────────────────────
        customers: list[Customer] = []
        for _ in range(n_customers):
            customer = Customer(
                name=fake.name(),
                email=fake.unique.email(),
                password_hash=dummy_hash,
            )
            db.add(customer)
            customers.append(customer)
        db.flush()
        print(f"  Created {len(customers)} customers")

        # ── Listings ────────────────────────────────────────────
        listings: list[Listing] = []
        for i in range(n_listings):
            prop_type = random.choice(["flat", "house_land"])
            base_coord = random.choice(REAL_CITY_COORDS)
            lat, lng = _jitter(base_coord)

            if prop_type == "flat":
                carpet = random.uniform(400, 2000)
                built_up = carpet * random.uniform(1.1, 1.3)
                plot = None
                floor = random.randint(1, 25)
            else:
                carpet = None
                built_up = random.uniform(800, 4000)
                plot = built_up * random.uniform(1.2, 2.0)
                floor = None

            listing = Listing(
                broker_id=random.choice(brokers).id,
                title=fake.sentence(nb_words=6).rstrip("."),
                description=fake.paragraph(nb_sentences=3),
                price=_plausible_price(prop_type, built_up or carpet or 1000),
                property_type=prop_type,
                location=WKTElement(f"POINT({lng} {lat})", srid=4326),
                carpet_area=round(carpet, 2) if carpet else None,
                built_up_area=round(built_up, 2),
                plot_area=round(plot, 2) if plot else None,
                floor_number=floor,
                rooms=_make_rooms(prop_type),
            )
            db.add(listing)
            listings.append(listing)

        db.flush()
        print(f"  Created {n_listings} listings")

        # ── Leads ───────────────────────────────────────────────
        leads_count = 0
        for customer in customers:
            # Randomly associate customer with 1-3 listings as leads
            sample_listings = random.sample(listings, k=random.randint(1, 3))
            for l in sample_listings:
                db.add(Lead(listing_id=l.id, customer_id=customer.id))
                leads_count += 1
        db.flush()
        print(f"  Created {leads_count} leads")

        # ── Conversations ──────────────────────────────────────
        conv_count = 0
        for customer in customers[:10]:
            conv = Conversation(
                customer_id=customer.id,
                messages=[
                    {"role": "user", "content": "Looking for 2BHK flats in Adajan", "timestamp": "2026-10-01T10:00:00Z"},
                    {"role": "assistant", "content": "[PLACEHOLDER MODE] Here are top properties in Adajan", "timestamp": "2026-10-01T10:00:02Z", "listing_ids": [listings[0].id]}
                ]
            )
            db.add(conv)
            conv_count += 1
        print(f"  Created {conv_count} sample conversations")

        db.commit()
        print(f"\nSeed complete: {n_brokers} brokers, {n_customers} customers, {n_listings} listings, {leads_count} leads, {conv_count} conversations")

    finally:
        db.close()


def main() -> None:
    parser = argparse.ArgumentParser(description="Seed Reality AI database with synthetic data")
    parser.add_argument("-n", "--n-listings", type=int, default=500, help="Number of listings")
    parser.add_argument("--n-brokers", type=int, default=10, help="Number of brokers")
    parser.add_argument("--n-customers", type=int, default=30, help="Number of customers")
    parser.add_argument(
        "--force",
        action="store_true",
        help="Proceed even if tables already contain data",
    )
    args = parser.parse_args()

    db = SessionLocal()
    try:
        existing = db.query(Listing).count()
        if existing > 0 and not args.force:
            print(
                f"Database already has {existing} listings. "
                "Use --force to seed anyway (will add more rows, not replace)."
            )
            sys.exit(1)
    finally:
        db.close()

    print("Seeding database...")
    seed(
        n_listings=args.n_listings,
        n_brokers=args.n_brokers,
        n_customers=args.n_customers,
    )


if __name__ == "__main__":
    main()
