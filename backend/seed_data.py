import sqlite3
import hashlib
from backend.database import get_db_connection, init_db

def hash_pw(password: str) -> str:
    return hashlib.sha256(password.encode()).hexdigest()

def seed_database():
    init_db()
    conn = get_db_connection()
    cursor = conn.cursor()

    # Clear existing data for a clean seed
    cursor.execute("DELETE FROM votes")
    cursor.execute("DELETE FROM proposals")
    cursor.execute("DELETE FROM welfare")
    cursor.execute("DELETE FROM ratings")
    cursor.execute("DELETE FROM payments")
    cursor.execute("DELETE FROM bookings")
    cursor.execute("DELETE FROM services")
    cursor.execute("DELETE FROM worker_skills")
    cursor.execute("DELETE FROM skills")
    cursor.execute("DELETE FROM workers")
    cursor.execute("DELETE FROM cooperatives")
    cursor.execute("DELETE FROM users")

    # 1. COOPERATIVES
    coops = [
        (
            1, "Bangalore Shramik Seva Cooperative Society", "COOP/BLR/2021/8942",
            "Indiranagar & Central Bangalore", "+91 80 2520 1122", "active", 142, 345000.0,
            "A registered democratic labour cooperative for certified home trades and maintenance technicians."
        ),
        (
            2, "Metro Craftsmen & Technicians Sahakari Union", "COOP/BLR/2019/3310",
            "Koramangala & HSR Layout", "+91 80 4110 5588", "active", 98, 210000.0,
            "Worker-owned cooperative dedicated to fair wages, pension welfare, and technical skill development."
        ),
        (
            3, "GreenCity Facility Services Sahakari", "COOP/BLR/2022/1105",
            "Jayanagar & South Bangalore", "+91 80 2663 7799", "active", 115, 280000.0,
            "Cooperative focusing on deep cleaning, environmental sanitation, and green residential care."
        )
    ]
    cursor.executemany("""
    INSERT INTO cooperatives (cooperative_id, name, registration_number, location, contact, status, member_count, welfare_fund_balance, description)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, coops)

    # 2. SKILLS
    skills = [
        (1, "Plumbing & Pipe Repair", "Plumbing", "Emergency leak repair, sanitary installation, drain unclogging"),
        (2, "Electrical Maintenance", "Electrical", "Short circuits, wiring diagnostics, MCB installation"),
        (3, "Appliance Repair", "Appliances", "AC servicing, washing machines, refrigerators, microwave repair"),
        (4, "Carpentry & Joinery", "Carpentry", "Door hinge fixing, wardrobe repair, modular woodwork"),
        (5, "Deep House Cleaning", "Cleaning", "Full kitchen, washroom, sanitization, upholstery cleaning"),
        (6, "Painting & Waterproofing", "Painting", "Interior dampness seal, texture painting, touchups")
    ]
    cursor.executemany("""
    INSERT INTO skills (skill_id, skill_name, category, description)
    VALUES (?, ?, ?, ?)
    """, skills)

    # 3. USERS
    # Admin, Customer, Workers
    admin_pw = hash_pw("admin123")
    worker_pw = hash_pw("worker123")
    customer_pw = hash_pw("customer123")

    users = [
        # Admin
        (1, "Ramesh Kumar (Cooperative Admin)", "9876500001", "admin@skillbridge.coop", admin_pw, "admin", "Cooperative Bhavan, Shivaji Nagar", "Bangalore"),
        # Customer
        (2, "Rajesh Mehta", "9845012345", "customer@example.com", customer_pw, "customer", "Flat 402, Sai Residency, 100ft Road, Indiranagar", "Bangalore"),
        (3, "Sunita Rao", "9845012346", "sunita@example.com", customer_pw, "customer", "12th Main, 4th Block, Koramangala", "Bangalore"),
        # Workers
        # Ramesh Sharma - Hero Demo Worker (Plumber)
        (4, "Ramesh Sharma", "9845110001", "ramesh.sharma@worker.coop", worker_pw, "worker", "HAL 2nd Stage, Indiranagar", "Bangalore"),
        # Suresh Gowda - Plumber with higher recent workload
        (5, "Suresh Gowda", "9845110002", "suresh.gowda@worker.coop", worker_pw, "worker", "Domlur Layout", "Bangalore"),
        # Anil Patel - Electrician
        (6, "Anil Patel", "9845110003", "anil.patel@worker.coop", worker_pw, "worker", "Tavarekere, BTM 1st Stage", "Bangalore"),
        # Farooq Ahmed - Appliance Tech
        (7, "Farooq Ahmed", "9845110004", "farooq.ahmed@worker.coop", worker_pw, "worker", "Ulsoor Lake Road", "Bangalore"),
        # Priya Sundaram - Cleaning
        (8, "Priya Sundaram", "9845110005", "priya.sundaram@worker.coop", worker_pw, "worker", "Jayanagar 4th T Block", "Bangalore"),
        # Manjunath K - Carpenter
        (9, "Manjunath K", "9845110006", "manjunath.k@worker.coop", worker_pw, "worker", "Ejipura, Koramangala", "Bangalore"),
        # Deepak Verma - Pending verification plumber
        (10, "Deepak Verma", "9845110007", "deepak.verma@worker.coop", worker_pw, "worker", "HSR Layout Sector 2", "Bangalore"),
        # Vikram Singh - Under review electrician
        (11, "Vikram Singh", "9845110008", "vikram.singh@worker.coop", worker_pw, "worker", "Whitefield Main Road", "Bangalore")
    ]
    cursor.executemany("""
    INSERT INTO users (user_id, name, phone, email, password_hash, role, address, city)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, users)

    # 4. WORKERS
    # worker_id, user_id, cooperative_id, experience, verification_status, rating, total_ratings_count, availability_status, service_area, lat, lng, completed_jobs_count, weekly_jobs_count, weekly_earnings, total_earnings
    # Indiranagar center lat: 12.9784, lng: 77.6408
    workers = [
        # Ramesh Sharma (Primary Demo Plumber - verified, available, nearby 1.6km, 4.9★, lower weekly jobs -> high fairness boost)
        (1, 4, 1, 8, "verified", 4.92, 128, "available", "Indiranagar & Central", 12.9725, 77.6385, 214, 4, 2800.0, 142000.0),
        # Suresh Gowda (Plumber - verified, available, 3.2km, 4.75★, higher weekly jobs 14 -> lower fairness boost)
        (2, 5, 1, 6, "verified", 4.75, 96, "available", "Indiranagar & Domlur", 12.9610, 77.6350, 180, 14, 8600.0, 118000.0),
        # Anil Patel (Electrician)
        (3, 6, 2, 5, "verified", 4.85, 84, "available", "Koramangala & BTM", 12.9352, 77.6245, 145, 6, 3900.0, 94000.0),
        # Farooq Ahmed (Appliances)
        (4, 7, 1, 7, "verified", 4.88, 112, "available", "Central Bangalore", 12.9800, 77.6200, 192, 7, 5200.0, 130000.0),
        # Priya Sundaram (Cleaning)
        (5, 8, 3, 4, "verified", 4.96, 140, "available", "Jayanagar & South", 12.9250, 77.5938, 230, 8, 7100.0, 158000.0),
        # Manjunath K (Carpenter)
        (6, 9, 2, 10, "verified", 4.70, 75, "available", "Koramangala", 12.9400, 77.6300, 160, 5, 3400.0, 110000.0),
        # Deepak Verma (Pending verification - for Admin action)
        (7, 10, 1, 3, "pending", 4.50, 0, "available", "HSR Layout", 12.9121, 77.6446, 0, 0, 0.0, 0.0),
        # Vikram Singh (Under review - for Admin action)
        (8, 11, 2, 2, "under_review", 4.60, 0, "available", "Whitefield", 12.9698, 77.7500, 0, 0, 0.0, 0.0)
    ]
    cursor.executemany("""
    INSERT INTO workers (worker_id, user_id, cooperative_id, experience_years, verification_status, rating, total_ratings_count, availability_status, service_area, latitude, longitude, completed_jobs_count, weekly_jobs_count, weekly_earnings, total_earnings)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, workers)

    # 5. WORKER_SKILLS
    worker_skills = [
        (1, 1, "Govt. ITI Master Plumber License #KA-9821", "verified"),
        (2, 1, "National Skill Development Corp (NSDC) Plumbing Level 4", "verified"),
        (3, 2, "Licensed Electrical Wireman #EL-4401", "verified"),
        (4, 3, "Consumer Appliance Diagnostic Certified", "verified"),
        (5, 5, "Certified Chemical & Sanitization Specialist", "verified"),
        (6, 4, "Master Woodworking & Joinery Guild Certificate", "verified"),
        (7, 1, "Apprentice Plumber Certificate", "pending"),
        (8, 2, "Vocational Wireman Training", "pending")
    ]
    cursor.executemany("""
    INSERT INTO worker_skills (worker_id, skill_id, certification, verification_status)
    VALUES (?, ?, ?, ?)
    """, worker_skills)

    # 6. SERVICES
    services = [
        (
            1, "Emergency Pipe Leak & Tap Burst Repair", "Plumbing",
            "Rapid response repair for burst pipes, high-pressure tap leaks, clogged main drainage, and bathroom flooding.",
            499.0, 45, 1, "All Bangalore", 1, 1.25, "droplet"
        ),
        (
            2, "Complete Sanitary & Bathroom Fixture Fitting", "Plumbing",
            "Installation and overhaul of shower heads, commodes, flush valves, mixers, and sink traps.",
            699.0, 60, 1, "All Bangalore", 0, 1.0, "wrench"
        ),
        (
            3, "Emergency Electrical Short Circuit & MCB Trip", "Electrical",
            "Urgent fault detection for tripped circuits, burning smells, sparks, fuse blowout, and total line blackouts.",
            549.0, 45, 2, "All Bangalore", 1, 1.30, "zap"
        ),
        (
            4, "Home Wiring & Switchboard Upgrades", "Electrical",
            "Inverter points, modular switchboard rewiring, appliance grounding and surge protector fitting.",
            449.0, 60, 2, "All Bangalore", 0, 1.0, "sliders"
        ),
        (
            5, "AC Jet Pump Deep Cleaning & Gas Inspection", "Appliances",
            "Indoor and outdoor unit pressure foam wash, cooling coil sanitization, drain tray de-clogging and gas check.",
            799.0, 60, 3, "All Bangalore", 0, 1.0, "wind"
        ),
        (
            6, "Furniture Repair, Door Alignments & Hinges", "Carpentry",
            "Hydraulic hinges replacement, wardrobe sliding rail tuning, bed creak fix, and lock installations.",
            599.0, 90, 4, "All Bangalore", 0, 1.0, "hammer"
        ),
        (
            7, "Full 2BHK/3BHK Deep House Sanitization", "Cleaning",
            "High-temperature steam sanitization, floor scrubbing machine treatment, grease degreasing for kitchens and bathrooms.",
            1699.0, 180, 5, "All Bangalore", 0, 1.0, "sparkles"
        ),
        (
            8, "Interior Wall Waterproofing & Dampness Touchup", "Painting",
            "Anti-fungal polymer coat, efflorescence treatment, putty leveling, and waterproof acrylic color coat.",
            1299.0, 120, 6, "All Bangalore", 0, 1.0, "paint-roller"
        )
    ]
    cursor.executemany("""
    INSERT INTO services (service_id, service_name, category, description, base_price, estimated_duration, required_skill_id, service_area, emergency_supported, emergency_multiplier, icon)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, services)

    # 7. WELFARE RECORDS
    welfare_records = [
        (1, 1, "Ayushman Bharat + Cooperative Top-up Shield", "Full cashless hospitalization coverage up to ₹3,00,000 for worker, spouse, and up to 2 dependent children.", 300000.0, "active", "Completed 50+ cooperative gigs & >90% on-time attendance"),
        (2, 1, "Accidental Injury & Transit Disability Fund", "Immediate disability stipend ₹25,000 + ₹5,00,000 accidental cover during active gig transit and on-site hours.", 500000.0, "active", "Active membership for 3+ months"),
        (3, 1, "Children Higher Education Scholarship", "Annual direct grant of ₹15,000 towards school/polytechnic fees for member's children with >75% attendance.", 15000.0, "active", "Minimum 100 platform jobs completed"),
        (4, 2, "Ayushman Bharat + Cooperative Top-up Shield", "Full cashless hospitalization coverage up to ₹3,00,000.", 300000.0, "active", "Eligible member"),
        (5, 3, "Tool & Protective Gear Replacement Grant", "Annual subsidy of ₹6,000 for verified diagnostic testers and insulated safety shoes.", 6000.0, "active", "Valid wireman license on file")
    ]
    cursor.executemany("""
    INSERT INTO welfare (welfare_id, worker_id, benefit_type, description, coverage_amount, status, eligibility)
    VALUES (?, ?, ?, ?, ?, ?, ?)
    """, welfare_records)

    # 8. PROPOSALS & DEMOCRATIC GOVERNANCE
    proposals = [
        (
            1, 1,
            "Allocate 5.0% of Cooperative Service Commission to Monsoon Relief Welfare Fund",
            "During the heavy monsoon season in Bangalore, outdoor and trade workers face reduced hours and transit risk. This resolution creates an automatic ₹5,00,000 contingency fund financed by an additional 1% reserve reallocation.",
            "Welfare & Benefits",
            "2026-09-01", "2026-09-15", "active", 40.0
        ),
        (
            2, 1,
            "Adopt Algorithmic Fairness Cap: Maximum 18 Jobs/Week per Technician",
            "To prevent worker burnout and ensure equitable distribution of high-value gigs among newly verified cooperative members, propose a fair cap on single-worker weekly assignment density.",
            "FairMatch Policy",
            "2026-09-02", "2026-09-20", "active", 50.0
        ),
        (
            3, 2,
            "Partnership with Electric Vehicle Cooperative for Subsidized E-Bikes",
            "Proposal to partner with Bangalore Green Mobility Union to provide zero-downpayment electric two-wheelers for cooperative technicians with 15% cooperative loan guarantee.",
            "Equipment & Logistics",
            "2026-08-15", "2026-08-30", "approved", 45.0
        )
    ]
    cursor.executemany("""
    INSERT INTO proposals (proposal_id, cooperative_id, title, description, category, start_date, end_date, status, min_quorum_percent)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, proposals)

    # 9. VOTES
    votes = [
        (1, 1, 2, "in_favor", "Crucial for rain season protection."),
        (2, 2, 2, "against", "Should be flexible during peak demand periods."),
        (3, 3, 3, "in_favor", "Will save daily fuel costs significantly.")
    ]
    cursor.executemany("""
    INSERT INTO votes (vote_id, proposal_id, member_id, decision, remarks)
    VALUES (?, ?, ?, ?, ?)
    """, votes)

    # 10. HISTORICAL COMPLETED BOOKINGS (to demonstrate ratings, invoices, and analytics)
    historical_bookings = [
        (
            1, 3, 1, 1, "100ft Road, Indiranagar", 12.9784, 77.6408, "2026-09-02 10:30", 1, "RATED", 624.0,
            "FairMatch matched Ramesh Sharma (Distance: 1.2km, Fairness boost: high, Rating: 4.9★)"
        ),
        (
            2, 2, 2, 2, "80ft Road, Koramangala", 12.9340, 77.6200, "2026-09-03 14:00", 0, "RATED", 699.0,
            "FairMatch matched Suresh Gowda (Distance: 2.1km, Rating: 4.8★)"
        )
    ]
    cursor.executemany("""
    INSERT INTO bookings (booking_id, customer_id, worker_id, service_id, location, latitude, longitude, scheduled_time, is_emergency, status, amount, fairness_notes)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, historical_bookings)

    # PAYMENTS for historical
    payments = [
        (1, 1, 624.0, 561.6, 31.2, 31.2, "UPI (GooglePay)", "success", "TXN_UPI_20260902_98124"),
        (2, 2, 699.0, 629.1, 34.95, 34.95, "UPI (PhonePe)", "success", "TXN_UPI_20260903_12093")
    ]
    cursor.executemany("""
    INSERT INTO payments (payment_id, booking_id, amount, worker_payout, cooperative_welfare_cut, platform_fee, payment_method, transaction_status, transaction_reference)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, payments)

    # RATINGS for historical
    ratings = [
        (1, 1, 3, 1, 5, "Extremely fast emergency plumbing response! Ramesh arrived in 15 mins and stopped the kitchen pipe leakage. Polite and highly skilled.", 5, 5),
        (2, 2, 2, 2, 5, "Punctual and very neat bathroom fixture overhaul. Great cooperative service.", 5, 4)
    ]
    cursor.executemany("""
    INSERT INTO ratings (rating_id, booking_id, customer_id, worker_id, rating, feedback, punctuality_rating, skill_rating)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, ratings)

    conn.commit()
    conn.close()
    print("SkillBridge database seeded with rich cooperative data successfully!")

if __name__ == "__main__":
    seed_database()
