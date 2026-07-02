"""
SafeNet AI – Demo Data Seeder
Populates the database with realistic synthetic data for hackathon demo.
Run once before the demo presentation.

Usage: python scripts/seed_demo_data.py
"""
from __future__ import annotations

import asyncio
import random
import uuid
from datetime import datetime, timedelta

# ── Seed Configuration ────────────────────────────────────────────
NUM_SCAM_REPORTS = 250
NUM_COUNTERFEIT_REPORTS = 80
NUM_FRAUD_CASES = 12
SEED = 42
random.seed(SEED)

# Indian city/state data for realistic geo distribution
INDIA_CITIES = [
    ("Mumbai", "Maharashtra", 19.076, 72.877),
    ("Delhi", "Delhi", 28.704, 77.102),
    ("Bengaluru", "Karnataka", 12.972, 77.594),
    ("Hyderabad", "Telangana", 17.388, 78.474),
    ("Chennai", "Tamil Nadu", 13.083, 80.270),
    ("Kolkata", "West Bengal", 22.573, 88.364),
    ("Pune", "Maharashtra", 18.520, 73.856),
    ("Ahmedabad", "Gujarat", 23.023, 72.572),
    ("Jaipur", "Rajasthan", 26.912, 75.787),
    ("Lucknow", "Uttar Pradesh", 26.847, 80.947),
    ("Surat", "Gujarat", 21.170, 72.831),
    ("Patna", "Bihar", 25.594, 85.137),
    ("Bhopal", "Madhya Pradesh", 23.259, 77.413),
    ("Indore", "Madhya Pradesh", 22.719, 75.857),
    ("Nagpur", "Maharashtra", 21.145, 79.082),
    ("Visakhapatnam", "Andhra Pradesh", 17.688, 83.218),
    ("Coimbatore", "Tamil Nadu", 11.017, 76.956),
    ("Chandigarh", "Punjab", 30.736, 76.788),
    ("Kochi", "Kerala", 9.931, 76.267),
    ("Bhubaneswar", "Odisha", 20.296, 85.825),
]

SCAM_TYPES = [
    "digital_arrest", "digital_arrest", "digital_arrest",  # weighted more
    "kyc_update", "kyc_update",
    "investment", "investment",
    "loan_fraud",
    "lottery",
    "impersonation",
    "tech_support",
]

CALLER_PREFIXES = [
    "+911800", "+919900", "+910000", "+91800",
    "+918888", "+917777", "+916666",
]


def random_phone(prefix: str = "+91") -> str:
    return prefix + str(random.randint(7000000000, 9999999999))


def random_date(days_back: int = 60) -> datetime:
    delta = timedelta(
        days=random.randint(0, days_back),
        hours=random.randint(0, 23),
        minutes=random.randint(0, 59),
    )
    return datetime.utcnow() - delta


def jitter_coords(lat: float, lng: float, radius_deg: float = 0.3):
    """Add small random offset to coordinates for realistic spread."""
    return (
        lat + random.uniform(-radius_deg, radius_deg),
        lng + random.uniform(-radius_deg, radius_deg),
    )


async def seed_database():
    """Main seeding function."""
    # Import here to avoid circular imports at module level
    import sys
    sys.path.insert(0, ".")

    from backend.db.models import (
        AsyncSessionLocal, ScamReport, CounterfeitReport,
        FraudCase, create_tables,
    )

    print("🌱 SafeNet AI — Demo Data Seeder")
    print("=" * 50)

    await create_tables()
    print("✅ Tables created/verified")

    async with AsyncSessionLocal() as session:

        # ── Scam Reports ─────────────────────────────────────────
        print(f"\n📞 Seeding {NUM_SCAM_REPORTS} scam reports...")
        for i in range(NUM_SCAM_REPORTS):
            city, state, lat, lng = random.choice(INDIA_CITIES)
            jlat, jlng = jitter_coords(lat, lng)
            scam_type = random.choice(SCAM_TYPES)
            confidence = random.uniform(0.65, 0.98)

            patterns_map = {
                "digital_arrest": [
                    "Authority impersonation with legal threat",
                    "Secrecy / isolation instruction",
                    "Video call identity verification pressure",
                ],
                "kyc_update": [
                    "Fake KYC update urgency",
                    "OTP solicitation (never legitimate)",
                ],
                "investment": [
                    "Guaranteed returns promise",
                    "High-pressure urgency language",
                ],
                "loan_fraud": [
                    "Advance fee loan scam",
                ],
                "lottery": [
                    "Unsolicited prize / lottery win",
                    "High-pressure urgency language",
                ],
            }
            patterns = patterns_map.get(scam_type, ["High-pressure urgency language"])

            report = ScamReport(
                id=uuid.uuid4(),
                caller_number=random.choice(CALLER_PREFIXES) + str(random.randint(100000, 999999)),
                victim_number=random_phone(),
                scam_type=scam_type,
                confidence_score=round(confidence, 4),
                status=random.choices(
                    ["confirmed", "pending", "false_positive", "escalated"],
                    weights=[60, 25, 5, 10],
                )[0],
                call_duration_seconds=random.randint(45, 900),
                call_metadata={
                    "number_spoofing_detected": random.random() > 0.4,
                    "silence_ratio": round(random.uniform(0.1, 0.6), 2),
                    "speech_rate_wpm": random.randint(120, 220),
                },
                script_patterns_matched=patterns,
                location_lat=round(jlat, 6),
                location_lng=round(jlng, 6),
                city=city,
                state=state,
                created_at=random_date(60),
            )
            session.add(report)

            if (i + 1) % 50 == 0:
                await session.flush()
                print(f"  → {i + 1} scam reports added")

        # ── Counterfeit Reports ───────────────────────────────────
        print(f"\n💵 Seeding {NUM_COUNTERFEIT_REPORTS} counterfeit reports...")
        denominations = [500, 500, 500, 2000, 200, 100]
        defect_types = [
            "watermark", "security_thread", "microprint",
            "color_shift_ink", "bleed_lines",
        ]

        for i in range(NUM_COUNTERFEIT_REPORTS):
            city, state, lat, lng = random.choice(INDIA_CITIES)
            jlat, jlng = jitter_coords(lat, lng, 0.5)
            denomination = random.choice(denominations)
            verdict = random.choices(
                ["counterfeit", "genuine", "uncertain"],
                weights=[55, 30, 15],
            )[0]
            confidence = random.uniform(0.72, 0.97)
            num_defects = random.randint(1, 3) if verdict == "counterfeit" else 0
            defects = random.sample(defect_types, min(num_defects, len(defect_types)))

            report = CounterfeitReport(
                id=uuid.uuid4(),
                denomination=denomination,
                confidence_score=round(confidence, 4),
                verdict=verdict,
                defects_detected=defects,
                serial_number_valid=verdict != "counterfeit",
                microprint_score=round(random.uniform(0.2 if verdict == "counterfeit" else 0.7, 0.95), 3),
                security_thread_score=round(random.uniform(0.2 if verdict == "counterfeit" else 0.65, 0.95), 3),
                watermark_score=round(random.uniform(0.2 if verdict == "counterfeit" else 0.6, 0.95), 3),
                image_hash=uuid.uuid4().hex[:32],
                location_lat=round(jlat, 6),
                location_lng=round(jlng, 6),
                city=city,
                state=state,
                reported_to_rbi=verdict == "counterfeit",
                created_at=random_date(60),
            )
            session.add(report)

        await session.flush()
        print(f"  → {NUM_COUNTERFEIT_REPORTS} counterfeit reports added")

        # ── Fraud Cases ───────────────────────────────────────────
        print(f"\n🕸️  Seeding {NUM_FRAUD_CASES} fraud cases...")
        case_templates = [
            ("Operation CBI Ghost", "digital_arrest", "critical", 847, 127_000_000),
            ("Operation OTP Drain", "kyc_update", "high", 312, 28_000_000),
            ("Maharashtra Investment Ring", "investment", "high", 156, 45_000_000),
            ("Pan-India Lottery Network", "lottery", "medium", 89, 8_900_000),
            ("Fake Loan App Network", "loan_fraud", "high", 234, 18_000_000),
            ("WhatsApp Crypto Scam", "investment", "critical", 1247, 89_000_000),
            ("South India KYC Ring", "kyc_update", "high", 445, 35_000_000),
            ("North India Digital Arrest", "digital_arrest", "critical", 623, 93_000_000),
            ("Bengaluru Tech Support Ring", "tech_support", "medium", 78, 5_600_000),
            ("Gujarat Stock Tips Fraud", "investment", "high", 189, 34_000_000),
            ("Delhi NCR Impersonation", "impersonation", "medium", 134, 12_000_000),
            ("Cross-State Mule Network", "loan_fraud", "critical", 567, 67_000_000),
        ]

        for i, (title, fraud_type, severity, victims, loss) in enumerate(case_templates):
            states = random.sample([c[1] for c in INDIA_CITIES], random.randint(2, 5))
            case = FraudCase(
                id=uuid.uuid4(),
                case_number=f"SN-2026-{10000 + i}",
                title=title,
                fraud_type=fraud_type,
                status=random.choice(["open", "open", "investigating", "escalated"]),
                severity=severity,
                estimated_victims=victims,
                estimated_loss_inr=float(loss),
                states_involved=list(set(states)),
                network_nodes=[str(uuid.uuid4()) for _ in range(random.randint(5, 25))],
                created_at=random_date(45),
            )
            session.add(case)

        await session.flush()
        print(f"  → {NUM_FRAUD_CASES} fraud cases added")

        await session.commit()

    print("\n" + "=" * 50)
    print("✅ Demo data seeding complete!")
    print(f"   📞 Scam reports: {NUM_SCAM_REPORTS}")
    print(f"   💵 Counterfeit reports: {NUM_COUNTERFEIT_REPORTS}")
    print(f"   🕸️  Fraud cases: {NUM_FRAUD_CASES}")
    print("\n🚀 Ready for demo! Start the server:")
    print("   uvicorn backend.main:app --reload")
    print("   Open: http://localhost:8000/docs")


if __name__ == "__main__":
    asyncio.run(seed_database())
