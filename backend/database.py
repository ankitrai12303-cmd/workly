import sqlite3
import os
from pathlib import Path

DB_PATH = Path(__file__).resolve().parent.parent / "skillbridge.db"

def get_db_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn

def init_db():
    conn = get_db_connection()
    cursor = conn.cursor()

    # USERS
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS users (
        user_id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        phone TEXT NOT NULL UNIQUE,
        email TEXT NOT NULL UNIQUE,
        password_hash TEXT NOT NULL,
        role TEXT NOT NULL CHECK (role IN ('customer', 'worker', 'admin')),
        address TEXT,
        city TEXT DEFAULT 'Bangalore',
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    """)

    # COOPERATIVES
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS cooperatives (
        cooperative_id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        registration_number TEXT NOT NULL UNIQUE,
        location TEXT NOT NULL,
        contact TEXT NOT NULL,
        status TEXT NOT NULL DEFAULT 'active',
        member_count INTEGER DEFAULT 0,
        welfare_fund_balance REAL DEFAULT 0.0,
        description TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    """)

    # SKILLS
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS skills (
        skill_id INTEGER PRIMARY KEY AUTOINCREMENT,
        skill_name TEXT NOT NULL UNIQUE,
        category TEXT NOT NULL,
        description TEXT
    );
    """)

    # WORKERS
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS workers (
        worker_id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL UNIQUE,
        cooperative_id INTEGER NOT NULL,
        experience_years INTEGER NOT NULL DEFAULT 1,
        verification_status TEXT NOT NULL DEFAULT 'pending' CHECK (verification_status IN ('pending', 'under_review', 'verified', 'rejected')),
        rating REAL NOT NULL DEFAULT 5.0,
        total_ratings_count INTEGER DEFAULT 0,
        availability_status TEXT NOT NULL DEFAULT 'available' CHECK (availability_status IN ('available', 'busy', 'offline')),
        service_area TEXT NOT NULL DEFAULT 'Central Bangalore',
        latitude REAL NOT NULL DEFAULT 12.9716,
        longitude REAL NOT NULL DEFAULT 77.5946,
        completed_jobs_count INTEGER DEFAULT 0,
        weekly_jobs_count INTEGER DEFAULT 0,
        weekly_earnings REAL DEFAULT 0.0,
        total_earnings REAL DEFAULT 0.0,
        cooperative_share_rate REAL DEFAULT 0.05,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (user_id) REFERENCES users (user_id) ON DELETE CASCADE,
        FOREIGN KEY (cooperative_id) REFERENCES cooperatives (cooperative_id) ON DELETE CASCADE
    );
    """)

    # WORKER_SKILLS
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS worker_skills (
        worker_id INTEGER NOT NULL,
        skill_id INTEGER NOT NULL,
        certification TEXT,
        verification_status TEXT DEFAULT 'verified' CHECK (verification_status IN ('pending', 'verified', 'rejected')),
        PRIMARY KEY (worker_id, skill_id),
        FOREIGN KEY (worker_id) REFERENCES workers (worker_id) ON DELETE CASCADE,
        FOREIGN KEY (skill_id) REFERENCES skills (skill_id) ON DELETE CASCADE
    );
    """)

    # SERVICES
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS services (
        service_id INTEGER PRIMARY KEY AUTOINCREMENT,
        service_name TEXT NOT NULL,
        category TEXT NOT NULL,
        description TEXT NOT NULL,
        base_price REAL NOT NULL,
        estimated_duration INTEGER NOT NULL, -- minutes
        required_skill_id INTEGER NOT NULL,
        service_area TEXT NOT NULL DEFAULT 'All Bangalore',
        emergency_supported INTEGER DEFAULT 0,
        emergency_multiplier REAL DEFAULT 1.25,
        icon TEXT DEFAULT 'wrench',
        FOREIGN KEY (required_skill_id) REFERENCES skills (skill_id)
    );
    """)

    # BOOKINGS
    # Lifecycle: REQUESTED -> MATCHING -> ASSIGNED -> ACCEPTED -> ON THE WAY -> IN PROGRESS -> COMPLETED -> PAID -> RATED
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS bookings (
        booking_id INTEGER PRIMARY KEY AUTOINCREMENT,
        customer_id INTEGER NOT NULL,
        worker_id INTEGER,
        service_id INTEGER NOT NULL,
        location TEXT NOT NULL,
        latitude REAL NOT NULL,
        longitude REAL NOT NULL,
        scheduled_time TEXT NOT NULL,
        is_emergency INTEGER DEFAULT 0,
        status TEXT NOT NULL DEFAULT 'REQUESTED',
        amount REAL NOT NULL,
        fairness_notes TEXT,
        cancellation_reason TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (customer_id) REFERENCES users (user_id),
        FOREIGN KEY (worker_id) REFERENCES workers (worker_id),
        FOREIGN KEY (service_id) REFERENCES services (service_id)
    );
    """)

    # PAYMENTS
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS payments (
        payment_id INTEGER PRIMARY KEY AUTOINCREMENT,
        booking_id INTEGER NOT NULL UNIQUE,
        amount REAL NOT NULL,
        worker_payout REAL NOT NULL,
        cooperative_welfare_cut REAL NOT NULL,
        platform_fee REAL NOT NULL,
        payment_method TEXT NOT NULL, -- UPI, Card, NetBanking, Cash
        transaction_status TEXT NOT NULL DEFAULT 'pending', -- pending, success, failed, refunded
        transaction_reference TEXT NOT NULL UNIQUE,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (booking_id) REFERENCES bookings (booking_id)
    );
    """)

    # RATINGS
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS ratings (
        rating_id INTEGER PRIMARY KEY AUTOINCREMENT,
        booking_id INTEGER NOT NULL UNIQUE,
        customer_id INTEGER NOT NULL,
        worker_id INTEGER NOT NULL,
        rating INTEGER NOT NULL CHECK (rating BETWEEN 1 AND 5),
        feedback TEXT,
        punctuality_rating INTEGER DEFAULT 5,
        skill_rating INTEGER DEFAULT 5,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (booking_id) REFERENCES bookings (booking_id),
        FOREIGN KEY (customer_id) REFERENCES users (user_id),
        FOREIGN KEY (worker_id) REFERENCES workers (worker_id)
    );
    """)

    # WELFARE
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS welfare (
        welfare_id INTEGER PRIMARY KEY AUTOINCREMENT,
        worker_id INTEGER NOT NULL,
        benefit_type TEXT NOT NULL, -- Health Insurance, Accidental Cover, Child Education Grant, Emergency Relief
        description TEXT NOT NULL,
        coverage_amount REAL NOT NULL,
        status TEXT NOT NULL DEFAULT 'active', -- active, under_review, claimed, expired
        eligibility TEXT NOT NULL,
        last_claim_date TEXT,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (worker_id) REFERENCES workers (worker_id)
    );
    """)

    # PROPOSALS
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS proposals (
        proposal_id INTEGER PRIMARY KEY AUTOINCREMENT,
        cooperative_id INTEGER NOT NULL,
        title TEXT NOT NULL,
        description TEXT NOT NULL,
        category TEXT NOT NULL DEFAULT 'Welfare & Benefits',
        start_date TEXT NOT NULL,
        end_date TEXT NOT NULL,
        status TEXT NOT NULL DEFAULT 'active', -- active, closed, approved, rejected
        min_quorum_percent REAL DEFAULT 40.0,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (cooperative_id) REFERENCES cooperatives (cooperative_id)
    );
    """)

    # VOTES
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS votes (
        vote_id INTEGER PRIMARY KEY AUTOINCREMENT,
        proposal_id INTEGER NOT NULL,
        member_id INTEGER NOT NULL, -- worker_id / member user_id
        decision TEXT NOT NULL CHECK (decision IN ('in_favor', 'against', 'abstain')),
        remarks TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        UNIQUE (proposal_id, member_id),
        FOREIGN KEY (proposal_id) REFERENCES proposals (proposal_id),
        FOREIGN KEY (member_id) REFERENCES workers (worker_id)
    );
    """)

    # FAIRMATCH CONFIG
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS fairmatch_config (
        config_id INTEGER PRIMARY KEY CHECK (config_id = 1),
        weight_skill REAL NOT NULL DEFAULT 0.35,
        weight_availability REAL NOT NULL DEFAULT 0.20,
        weight_distance REAL NOT NULL DEFAULT 0.15,
        weight_rating REAL NOT NULL DEFAULT 0.10,
        weight_workload REAL NOT NULL DEFAULT 0.10,
        weight_fairness REAL NOT NULL DEFAULT 0.10,
        max_service_radius_km REAL NOT NULL DEFAULT 15.0,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    """)

    cursor.execute("""
    INSERT OR IGNORE INTO fairmatch_config (config_id, weight_skill, weight_availability, weight_distance, weight_rating, weight_workload, weight_fairness, max_service_radius_km)
    VALUES (1, 0.35, 0.20, 0.15, 0.10, 0.10, 0.10, 15.0);
    """)

    conn.commit()
    conn.close()

if __name__ == "__main__":
    init_db()
    print("Database schema initialized successfully at:", DB_PATH)
