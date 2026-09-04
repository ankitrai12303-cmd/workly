import hashlib
import uuid
import datetime
from fastapi import APIRouter, HTTPException, Depends, Query
from typing import Optional, List, Dict, Any

from backend.database import get_db_connection
from backend.models import (
    RegisterRequest, LoginRequest, BookingCreateRequest,
    JobStatusUpdateRequest, PaymentCreateRequest, RatingCreateRequest,
    VoteCreateRequest, ProposalCreateRequest, WorkerVerifyRequest,
    FairMatchWeightsRequest, ServiceCreateRequest
)
from backend.fairmatch import run_fairmatch, get_fairmatch_weights, update_fairmatch_weights
from backend.ai_engine import get_demand_forecast, get_workforce_recommendations, train_demand_model

router = APIRouter(prefix="/api")

def hash_pw(pw: str) -> str:
    return hashlib.sha256(pw.encode()).hexdigest()

# ==========================================
# 1. AUTHENTICATION & USERS
# ==========================================

@router.post("/auth/register")
def register(req: RegisterRequest):
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("""
        INSERT INTO users (name, phone, email, password_hash, role, address)
        VALUES (?, ?, ?, ?, ?, ?)
        """, (req.name, req.phone, req.email, hash_pw(req.password), req.role, req.address))
        user_id = cursor.lastrowid

        if req.role == "worker":
            cursor.execute("""
            INSERT INTO workers (user_id, cooperative_id, experience_years, verification_status, availability_status)
            VALUES (?, ?, ?, 'pending', 'available')
            """, (user_id, req.cooperative_id or 1, req.experience_years or 2))
            worker_id = cursor.lastrowid
            if req.skill_id:
                cursor.execute("""
                INSERT INTO worker_skills (worker_id, skill_id, certification, verification_status)
                VALUES (?, ?, 'Applicant Certified', 'pending')
                """, (worker_id, req.skill_id))

        conn.commit()
        return {"status": "success", "user_id": user_id, "role": req.role, "message": "User registered successfully"}
    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=400, detail=str(e))
    finally:
        conn.close()

@router.post("/auth/login")
def login(req: LoginRequest):
    conn = get_db_connection()
    user = conn.execute("""
    SELECT user_id, name, phone, email, role, address FROM users 
    WHERE email = ? AND password_hash = ?
    """, (req.email, hash_pw(req.password))).fetchone()
    
    if not user:
        conn.close()
        raise HTTPException(status_code=401, detail="Invalid credentials")

    user_dict = dict(user)
    if user["role"] == "worker":
        worker = conn.execute("""
        SELECT w.*, c.name as cooperative_name 
        FROM workers w 
        JOIN cooperatives c ON w.cooperative_id = c.cooperative_id 
        WHERE w.user_id = ?
        """, (user["user_id"],)).fetchone()
        if worker:
            user_dict["worker_profile"] = dict(worker)

    conn.close()
    return {"status": "success", "user": user_dict, "token": f"demo-jwt-{user['user_id']}"}

@router.get("/auth/users")
def list_demo_users():
    """Returns quick switcher users for convenient SIH demo switching."""
    conn = get_db_connection()
    users = conn.execute("""
    SELECT u.user_id, u.name, u.email, u.role, u.phone,
           w.worker_id, w.verification_status, w.rating, w.availability_status
    FROM users u
    LEFT JOIN workers w ON u.user_id = w.user_id
    ORDER BY u.user_id ASC
    """).fetchall()
    conn.close()
    return [dict(u) for u in users]

# ==========================================
# 2. SERVICES CATALOG (Customer / Admin)
# ==========================================

@router.get("/services")
def get_services(category: Optional[str] = None):
    conn = get_db_connection()
    query = """
    SELECT s.*, sk.skill_name 
    FROM services s 
    JOIN skills sk ON s.required_skill_id = sk.skill_id
    """
    params = []
    if category and category != "All":
        query += " WHERE s.category = ?"
        params.append(category)
    rows = conn.execute(query, params).fetchall()
    conn.close()
    return [dict(r) for r in rows]

@router.get("/services/{service_id}")
def get_service_details(service_id: int):
    conn = get_db_connection()
    row = conn.execute("""
    SELECT s.*, sk.skill_name 
    FROM services s 
    JOIN skills sk ON s.required_skill_id = sk.skill_id 
    WHERE s.service_id = ?
    """, (service_id,)).fetchone()
    conn.close()
    if not row:
        raise HTTPException(status_code=404, detail="Service not found")
    return dict(row)

# ==========================================
# 3. FAIRMATCH & MATCHING ENGINE
# ==========================================

@router.post("/matching/find-workers")
def find_workers(
    service_id: int = Query(...),
    latitude: float = Query(12.9784),
    longitude: float = Query(77.6408),
    is_emergency: bool = Query(False)
):
    result = run_fairmatch(
        service_id=service_id,
        customer_lat=latitude,
        customer_lon=longitude,
        is_emergency=is_emergency
    )
    return result

@router.get("/matching/config")
def get_matching_weights():
    return get_fairmatch_weights()

@router.post("/matching/config")
def set_matching_weights(req: FairMatchWeightsRequest):
    return update_fairmatch_weights(req.dict())

# ==========================================
# 4. BOOKINGS (Customer & Worker)
# ==========================================

@router.post("/bookings")
def create_booking(req: BookingCreateRequest):
    """
    Creates a new booking following lifecycle:
    REQUESTED -> MATCHING -> ASSIGNED.
    Uses FairMatch to find optimal cooperative worker if preferred_worker_id not supplied.
    """
    conn = get_db_connection()
    cursor = conn.cursor()

    service = conn.execute("SELECT * FROM services WHERE service_id = ?", (req.service_id,)).fetchone()
    if not service:
        conn.close()
        raise HTTPException(status_code=404, detail="Service not found")

    amount = float(service["base_price"])
    if req.is_emergency and service["emergency_supported"]:
        amount *= float(service["emergency_multiplier"])

    # FairMatch selection
    matched_worker_id = req.preferred_worker_id
    fairness_note = ""

    fairmatch_res = run_fairmatch(
        service_id=req.service_id,
        customer_lat=req.latitude,
        customer_lon=req.longitude,
        is_emergency=req.is_emergency
    )

    if not matched_worker_id:
        if fairmatch_res["recommended_worker"]:
            rec = fairmatch_res["recommended_worker"]
            matched_worker_id = rec["worker_id"]
            fairness_note = rec["explanation"]
        else:
            # Fallback to any verified worker with skill if none within strict radius
            alt = conn.execute("""
            SELECT w.worker_id FROM workers w
            JOIN worker_skills ws ON w.worker_id = ws.worker_id
            WHERE ws.skill_id = ? AND w.verification_status = 'verified'
            LIMIT 1
            """, (service["required_skill_id"],)).fetchone()
            if alt:
                matched_worker_id = alt["worker_id"]
                fairness_note = "Assigned via cooperative roster fallback"
            else:
                matched_worker_id = 1
                fairness_note = "Assigned to duty lead worker"
    else:
        # User explicitly chose or demo picked
        for w in fairmatch_res.get("all_ranked_workers", []):
            if w["worker_id"] == matched_worker_id:
                fairness_note = w["explanation"]
                break
        if not fairness_note:
            fairness_note = "Selected by customer from recommended cooperative roster"

    initial_status = "ASSIGNED"

    cursor.execute("""
    INSERT INTO bookings (customer_id, worker_id, service_id, location, latitude, longitude, scheduled_time, is_emergency, status, amount, fairness_notes)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        req.customer_id, matched_worker_id, req.service_id, req.location,
        req.latitude, req.longitude, req.scheduled_time, 1 if req.is_emergency else 0,
        initial_status, round(amount, 2), fairness_note
    ))
    booking_id = cursor.lastrowid
    conn.commit()
    conn.close()

    return {
        "status": "success",
        "booking_id": booking_id,
        "booking_status": initial_status,
        "amount": round(amount, 2),
        "assigned_worker_id": matched_worker_id,
        "fairness_notes": fairness_note,
        "fairmatch_breakdown": fairmatch_res.get("recommended_worker")
    }

@router.get("/bookings")
def get_bookings(customer_id: Optional[int] = None, worker_id: Optional[int] = None):
    conn = get_db_connection()
    query = """
    SELECT 
        b.*,
        s.service_name, s.category, s.icon,
        u_cust.name as customer_name, u_cust.phone as customer_phone,
        u_work.name as worker_name, u_work.phone as worker_phone,
        w.rating as worker_rating,
        c.name as cooperative_name,
        p.transaction_status as payment_status, p.payment_method,
        r.rating as given_rating, r.feedback as given_feedback
    FROM bookings b
    JOIN services s ON b.service_id = s.service_id
    JOIN users u_cust ON b.customer_id = u_cust.user_id
    LEFT JOIN workers w ON b.worker_id = w.worker_id
    LEFT JOIN users u_work ON w.user_id = u_work.user_id
    LEFT JOIN cooperatives c ON w.cooperative_id = c.cooperative_id
    LEFT JOIN payments p ON b.booking_id = p.booking_id
    LEFT JOIN ratings r ON b.booking_id = r.booking_id
    """
    clauses = []
    params = []
    if customer_id:
        clauses.append("b.customer_id = ?")
        params.append(customer_id)
    if worker_id:
        clauses.append("b.worker_id = ?")
        params.append(worker_id)
    if clauses:
        query += " WHERE " + " AND ".join(clauses)

    query += " ORDER BY b.booking_id DESC"
    rows = conn.execute(query, params).fetchall()
    conn.close()
    return [dict(r) for r in rows]

@router.get("/bookings/{booking_id}")
def get_booking_by_id(booking_id: int):
    conn = get_db_connection()
    row = conn.execute("""
    SELECT 
        b.*,
        s.service_name, s.category, s.estimated_duration, s.base_price, s.emergency_multiplier,
        u_cust.name as customer_name, u_cust.phone as customer_phone, u_cust.address as customer_address,
        u_work.name as worker_name, u_work.phone as worker_phone,
        w.rating as worker_rating, w.experience_years,
        c.name as cooperative_name, c.registration_number, c.contact as cooperative_contact,
        p.payment_id, p.transaction_status as payment_status, p.payment_method, p.transaction_reference,
        p.worker_payout, p.cooperative_welfare_cut, p.platform_fee,
        r.rating as given_rating, r.feedback as given_feedback
    FROM bookings b
    JOIN services s ON b.service_id = s.service_id
    JOIN users u_cust ON b.customer_id = u_cust.user_id
    LEFT JOIN workers w ON b.worker_id = w.worker_id
    LEFT JOIN users u_work ON w.user_id = u_work.user_id
    LEFT JOIN cooperatives c ON w.cooperative_id = c.cooperative_id
    LEFT JOIN payments p ON b.booking_id = p.booking_id
    LEFT JOIN ratings r ON b.booking_id = r.booking_id
    WHERE b.booking_id = ?
    """, (booking_id,)).fetchone()
    conn.close()
    if not row:
        raise HTTPException(status_code=404, detail="Booking not found")
    return dict(row)

# ==========================================
# 5. WORKER ACTIONS & JOBS
# ==========================================

@router.get("/workers/profile")
def get_worker_profile(worker_id: int = Query(1)):
    conn = get_db_connection()
    worker = conn.execute("""
    SELECT w.*, u.name, u.phone, u.email, u.address,
           c.name as cooperative_name, c.registration_number, c.welfare_fund_balance
    FROM workers w
    JOIN users u ON w.user_id = u.user_id
    JOIN cooperatives c ON w.cooperative_id = c.cooperative_id
    WHERE w.worker_id = ?
    """, (worker_id,)).fetchone()

    if not worker:
        conn.close()
        raise HTTPException(status_code=404, detail="Worker not found")

    skills = conn.execute("""
    SELECT ws.*, s.skill_name, s.category 
    FROM worker_skills ws 
    JOIN skills s ON ws.skill_id = s.skill_id 
    WHERE ws.worker_id = ?
    """, (worker_id,)).fetchall()

    welfare = conn.execute("SELECT * FROM welfare WHERE worker_id = ?", (worker_id,)).fetchall()
    conn.close()

    res = dict(worker)
    res["skills"] = [dict(s) for s in skills]
    res["welfare_benefits"] = [dict(w) for w in welfare]
    return res

@router.put("/workers/availability")
def toggle_availability(worker_id: int = Query(...), status: str = Query(...)):
    if status not in ["available", "busy", "offline"]:
        raise HTTPException(status_code=400, detail="Invalid availability status")
    conn = get_db_connection()
    conn.execute("UPDATE workers SET availability_status = ? WHERE worker_id = ?", (status, worker_id))
    conn.commit()
    conn.close()
    return {"status": "success", "worker_id": worker_id, "availability_status": status}

@router.get("/workers/jobs")
def get_worker_jobs(worker_id: int = Query(1)):
    return get_bookings(worker_id=worker_id)

@router.post("/workers/jobs/{booking_id}/accept")
def accept_job(booking_id: int, worker_id: int = Query(1)):
    conn = get_db_connection()
    conn.execute("""
    UPDATE bookings 
    SET status = 'ACCEPTED' 
    WHERE booking_id = ? AND (worker_id = ? OR worker_id IS NULL)
    """, (booking_id, worker_id))
    conn.commit()
    conn.close()
    return {"status": "success", "booking_id": booking_id, "job_status": "ACCEPTED"}

@router.post("/workers/jobs/{booking_id}/reject")
def reject_job(booking_id: int, worker_id: int = Query(1), reason: str = "Unavailable at requested slot"):
    conn = get_db_connection()
    # Reassign or set to MATCHING
    conn.execute("""
    UPDATE bookings 
    SET status = 'MATCHING', worker_id = NULL, cancellation_reason = ? 
    WHERE booking_id = ?
    """, (reason, booking_id))
    conn.commit()
    conn.close()
    return {"status": "success", "booking_id": booking_id, "job_status": "MATCHING", "message": "Job rejected and routed back to FairMatch queue"}

@router.put("/workers/jobs/{booking_id}/status")
def update_job_status(booking_id: int, req: JobStatusUpdateRequest):
    allowed = ["ASSIGNED", "ACCEPTED", "ON THE WAY", "IN PROGRESS", "COMPLETED", "PAID", "RATED"]
    if req.status not in allowed:
        raise HTTPException(status_code=400, detail=f"Status must be one of {allowed}")

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("UPDATE bookings SET status = ? WHERE booking_id = ?", (req.status, booking_id))

    # If completed, increment worker job count
    if req.status == "COMPLETED":
        booking = conn.execute("SELECT worker_id, amount FROM bookings WHERE booking_id = ?", (booking_id,)).fetchone()
        if booking and booking["worker_id"]:
            cursor.execute("""
            UPDATE workers 
            SET completed_jobs_count = completed_jobs_count + 1,
                weekly_jobs_count = weekly_jobs_count + 1,
                weekly_earnings = weekly_earnings + (? * 0.90),
                total_earnings = total_earnings + (? * 0.90)
            WHERE worker_id = ?
            """, (booking["amount"], booking["amount"], booking["worker_id"]))

    conn.commit()
    conn.close()
    return {"status": "success", "booking_id": booking_id, "new_status": req.status}

@router.get("/workers/earnings")
def get_worker_earnings(worker_id: int = Query(1)):
    conn = get_db_connection()
    worker = conn.execute("SELECT * FROM workers WHERE worker_id = ?", (worker_id,)).fetchone()
    if not worker:
        conn.close()
        raise HTTPException(status_code=404, detail="Worker not found")

    payments = conn.execute("""
    SELECT p.*, b.service_id, s.service_name, b.location, b.created_at as job_date
    FROM payments p
    JOIN bookings b ON p.booking_id = b.booking_id
    JOIN services s ON b.service_id = s.service_id
    WHERE b.worker_id = ? AND p.transaction_status = 'success'
    ORDER BY p.created_at DESC
    """, (worker_id,)).fetchall()
    conn.close()

    total_gross = sum(p["amount"] for p in payments)
    total_payout = sum(p["worker_payout"] for p in payments)
    total_welfare_contrib = sum(p["cooperative_welfare_cut"] for p in payments)

    return {
        "worker_id": worker_id,
        "completed_jobs": worker["completed_jobs_count"],
        "weekly_jobs": worker["weekly_jobs_count"],
        "weekly_earnings": round(worker["weekly_earnings"], 2),
        "total_earnings": round(worker["total_earnings"] or total_payout, 2),
        "cooperative_welfare_contributed": round(total_welfare_contrib, 2),
        "cooperative_share_rate": "5% into Member Welfare Fund",
        "recent_transactions": [dict(p) for p in payments[:10]]
    }

# ==========================================
# 6. PAYMENTS & INVOICES
# ==========================================

@router.post("/payments/create")
def create_payment(req: PaymentCreateRequest):
    conn = get_db_connection()
    cursor = conn.cursor()

    booking = conn.execute("SELECT * FROM bookings WHERE booking_id = ?", (req.booking_id,)).fetchone()
    if not booking:
        conn.close()
        raise HTTPException(status_code=404, detail="Booking not found")

    amount = float(booking["amount"])
    # 90% goes directly to worker, 5% to cooperative welfare fund, 5% platform maintenance
    worker_payout = round(amount * 0.90, 2)
    welfare_cut = round(amount * 0.05, 2)
    platform_fee = round(amount * 0.05, 2)
    tx_ref = f"SB-PAY-{uuid.uuid4().hex[:8].upper()}"

    # Upsert payment
    cursor.execute("""
    INSERT INTO payments (booking_id, amount, worker_payout, cooperative_welfare_cut, platform_fee, payment_method, transaction_status, transaction_reference)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    ON CONFLICT(booking_id) DO UPDATE SET
        transaction_status = excluded.transaction_status,
        payment_method = excluded.payment_method,
        transaction_reference = excluded.transaction_reference
    """, (
        req.booking_id, amount, worker_payout, welfare_cut, platform_fee,
        req.payment_method, req.simulate_status, tx_ref
    ))

    # Update booking status to PAID if success
    if req.simulate_status == "success":
        cursor.execute("UPDATE bookings SET status = 'PAID' WHERE booking_id = ?", (req.booking_id,))
        # Update cooperative welfare fund balance
        worker = conn.execute("SELECT cooperative_id FROM workers WHERE worker_id = ?", (booking["worker_id"],)).fetchone()
        if worker:
            cursor.execute("""
            UPDATE cooperatives 
            SET welfare_fund_balance = welfare_fund_balance + ? 
            WHERE cooperative_id = ?
            """, (welfare_cut, worker["cooperative_id"]))

    conn.commit()
    conn.close()

    return {
        "status": "success",
        "booking_id": req.booking_id,
        "transaction_reference": tx_ref,
        "payment_status": req.simulate_status,
        "amount": amount,
        "worker_payout": worker_payout,
        "cooperative_welfare_contribution": welfare_cut
    }

@router.get("/payments/invoice/{booking_id}")
def generate_invoice(booking_id: int):
    """Generates official cooperative digital tax invoice (PRD Section 7 & 15)."""
    conn = get_db_connection()
    row = conn.execute("""
    SELECT 
        b.booking_id, b.location, b.scheduled_time, b.is_emergency, b.amount, b.created_at as booking_date,
        s.service_name, s.category, s.base_price, s.emergency_multiplier,
        u_cust.name as customer_name, u_cust.phone as customer_phone, u_cust.address as customer_address,
        u_work.name as worker_name, u_work.phone as worker_phone,
        w.rating as worker_rating,
        c.name as cooperative_name, c.registration_number, c.location as coop_address, c.contact as coop_contact,
        p.payment_id, p.payment_method, p.transaction_status, p.transaction_reference, p.created_at as payment_date,
        p.worker_payout, p.cooperative_welfare_cut, p.platform_fee
    FROM bookings b
    JOIN services s ON b.service_id = s.service_id
    JOIN users u_cust ON b.customer_id = u_cust.user_id
    LEFT JOIN workers w ON b.worker_id = w.worker_id
    LEFT JOIN users u_work ON w.user_id = u_work.user_id
    LEFT JOIN cooperatives c ON w.cooperative_id = c.cooperative_id
    LEFT JOIN payments p ON b.booking_id = p.booking_id
    WHERE b.booking_id = ?
    """, (booking_id,)).fetchone()
    conn.close()

    if not row:
        raise HTTPException(status_code=404, detail="Invoice not found for this booking")

    data = dict(row)
    base_val = float(data["base_price"])
    emergency_fee = round(data["amount"] - base_val, 2) if data["is_emergency"] else 0.0
    gst_val = round(data["amount"] * 0.05, 2)
    grand_total = data["amount"]

    invoice = {
        "invoice_number": f"SB-INV-2026-{booking_id:05d}",
        "invoice_date": data["payment_date"] or datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "cooperative": {
            "name": data["cooperative_name"] or "Bangalore Shramik Seva Cooperative Society",
            "registration_number": data["registration_number"] or "COOP/BLR/2021/8942",
            "address": data["coop_address"] or "Central Bangalore, Karnataka",
            "contact": data["coop_contact"] or "+91 80 2520 1122"
        },
        "customer": {
            "name": data["customer_name"],
            "phone": data["customer_phone"],
            "address": data["location"]
        },
        "worker": {
            "name": data["worker_name"],
            "phone": data["worker_phone"],
            "rating": data["worker_rating"]
        },
        "service_details": {
            "service_name": data["service_name"],
            "category": data["category"],
            "is_emergency": bool(data["is_emergency"]),
            "base_price": base_val,
            "emergency_surcharge": emergency_fee,
            "taxes_and_cess": gst_val,
            "total_amount": grand_total
        },
        "breakdown": {
            "worker_direct_earnings": data["worker_payout"] or round(grand_total * 0.90, 2),
            "cooperative_welfare_fund": data["cooperative_welfare_cut"] or round(grand_total * 0.05, 2),
            "platform_operations": data["platform_fee"] or round(grand_total * 0.05, 2)
        },
        "payment": {
            "method": data["payment_method"] or "UPI",
            "status": data["transaction_status"] or "PAID",
            "transaction_ref": data["transaction_reference"] or f"SB-UPI-{booking_id}"
        }
    }
    return invoice

# ==========================================
# 7. RATINGS & REVIEWS
# ==========================================

@router.post("/bookings/{booking_id}/rate")
def submit_rating(booking_id: int, req: RatingCreateRequest):
    conn = get_db_connection()
    cursor = conn.cursor()

    booking = conn.execute("SELECT worker_id, status FROM bookings WHERE booking_id = ?", (booking_id,)).fetchone()
    if not booking:
        conn.close()
        raise HTTPException(status_code=404, detail="Booking not found")

    worker_id = booking["worker_id"]
    cursor.execute("""
    INSERT INTO ratings (booking_id, customer_id, worker_id, rating, feedback, punctuality_rating, skill_rating)
    VALUES (?, ?, ?, ?, ?, ?, ?)
    ON CONFLICT(booking_id) DO UPDATE SET
        rating = excluded.rating,
        feedback = excluded.feedback
    """, (booking_id, req.customer_id, worker_id, req.rating, req.feedback, req.punctuality_rating, req.skill_rating))

    # Update booking status to RATED
    cursor.execute("UPDATE bookings SET status = 'RATED' WHERE booking_id = ?", (booking_id,))

    # Update worker aggregated rating
    ratings_agg = conn.execute("""
    SELECT AVG(rating) as avg_rating, COUNT(rating_id) as count 
    FROM ratings 
    WHERE worker_id = ?
    """, (worker_id,)).fetchone()
    
    if ratings_agg:
        cursor.execute("""
        UPDATE workers 
        SET rating = ?, total_ratings_count = ? 
        WHERE worker_id = ?
        """, (round(ratings_agg["avg_rating"], 2), ratings_agg["count"], worker_id))

    conn.commit()
    conn.close()

    return {"status": "success", "booking_id": booking_id, "worker_id": worker_id, "rating": req.rating}

# ==========================================
# 8. ADMIN DASHBOARD & WORKER VERIFICATION
# ==========================================

@router.get("/admin/dashboard")
def get_admin_dashboard():
    conn = get_db_connection()
    
    total_workers = conn.execute("SELECT COUNT(*) FROM workers").fetchone()[0]
    verified_workers = conn.execute("SELECT COUNT(*) FROM workers WHERE verification_status = 'verified'").fetchone()[0]
    pending_verifications = conn.execute("SELECT COUNT(*) FROM workers WHERE verification_status IN ('pending', 'under_review')").fetchone()[0]
    
    total_bookings = conn.execute("SELECT COUNT(*) FROM bookings").fetchone()[0]
    active_jobs = conn.execute("SELECT COUNT(*) FROM bookings WHERE status IN ('ASSIGNED', 'ACCEPTED', 'ON THE WAY', 'IN PROGRESS')").fetchone()[0]
    emergency_requests = conn.execute("SELECT COUNT(*) FROM bookings WHERE is_emergency = 1").fetchone()[0]
    
    revenue_agg = conn.execute("SELECT COALESCE(SUM(amount), 0) as total_gmv, COALESCE(SUM(cooperative_welfare_cut), 0) as welfare_total FROM payments WHERE transaction_status = 'success'").fetchone()
    
    coops = conn.execute("SELECT * FROM cooperatives").fetchall()
    fairmatch_weights = get_fairmatch_weights()

    conn.close()
    return {
        "stats": {
            "total_workers": total_workers,
            "verified_workers": verified_workers,
            "pending_verifications": pending_verifications,
            "total_bookings": total_bookings,
            "active_jobs": active_jobs,
            "emergency_requests": emergency_requests,
            "total_gmv": round(float(revenue_agg["total_gmv"]), 2),
            "welfare_fund_collected": round(float(revenue_agg["welfare_total"]), 2)
        },
        "cooperatives": [dict(c) for c in coops],
        "fairmatch_weights": fairmatch_weights
    }

@router.get("/admin/workers")
def list_admin_workers(status: Optional[str] = None):
    conn = get_db_connection()
    query = """
    SELECT 
        w.*, u.name, u.phone, u.email, u.address,
        c.name as cooperative_name,
        GROUP_CONCAT(s.skill_name || ' (' || ws.certification || ')') as skills_list
    FROM workers w
    JOIN users u ON w.user_id = u.user_id
    JOIN cooperatives c ON w.cooperative_id = c.cooperative_id
    LEFT JOIN worker_skills ws ON w.worker_id = ws.worker_id
    LEFT JOIN skills s ON ws.skill_id = s.skill_id
    """
    params = []
    if status:
        query += " WHERE w.verification_status = ?"
        params.append(status)
    query += " GROUP BY w.worker_id ORDER BY w.worker_id ASC"

    rows = conn.execute(query, params).fetchall()
    conn.close()
    return [dict(r) for r in rows]

@router.put("/admin/workers/{worker_id}/verify")
def verify_worker(worker_id: int, req: WorkerVerifyRequest):
    conn = get_db_connection()
    conn.execute("""
    UPDATE workers 
    SET verification_status = ? 
    WHERE worker_id = ?
    """, (req.verification_status, worker_id))
    
    # Also update worker_skills status
    skill_status = "verified" if req.verification_status == "verified" else "pending"
    conn.execute("UPDATE worker_skills SET verification_status = ? WHERE worker_id = ?", (skill_status, worker_id))
    
    conn.commit()
    conn.close()
    return {
        "status": "success",
        "worker_id": worker_id,
        "verification_status": req.verification_status,
        "message": f"Worker status updated to {req.verification_status}"
    }

@router.post("/admin/services")
def create_service(req: ServiceCreateRequest):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
    INSERT INTO services (service_name, category, description, base_price, estimated_duration, required_skill_id, emergency_supported, emergency_multiplier, icon)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        req.service_name, req.category, req.description, req.base_price,
        req.estimated_duration, req.required_skill_id, 1 if req.emergency_supported else 0,
        req.emergency_multiplier, req.icon
    ))
    sid = cursor.lastrowid
    conn.commit()
    conn.close()
    return {"status": "success", "service_id": sid}

# ==========================================
# 9. AI / ML DEMAND FORECAST & WORKFORCE
# ==========================================

@router.get("/ai/demand-forecast")
def demand_forecast(service_id: int = Query(1), zone: str = Query("Indiranagar")):
    return get_demand_forecast(service_id=service_id, zone=zone)

@router.get("/ai/workforce-recommendation")
def workforce_recommendations():
    return get_workforce_recommendations()

@router.post("/ai/retrain")
def retrain_ai():
    metrics = train_demand_model()
    return {"status": "success", "metrics": metrics}

# ==========================================
# 10. WELFARE & TRAINING
# ==========================================

@router.get("/welfare")
def get_welfare_programs(worker_id: Optional[int] = None):
    conn = get_db_connection()
    if worker_id:
        rows = conn.execute("""
        SELECT w.*, u.name as worker_name 
        FROM welfare w 
        JOIN workers wk ON w.worker_id = wk.worker_id 
        JOIN users u ON wk.user_id = u.user_id 
        WHERE w.worker_id = ?
        """, (worker_id,)).fetchall()
    else:
        rows = conn.execute("""
        SELECT w.*, u.name as worker_name 
        FROM welfare w 
        JOIN workers wk ON w.worker_id = wk.worker_id 
        JOIN users u ON wk.user_id = u.user_id
        """).fetchall()
    conn.close()
    return [dict(r) for r in rows]

@router.post("/welfare/claim")
def claim_welfare(welfare_id: int = Query(...), claim_amount: float = Query(...), reason: str = Query(...)):
    conn = get_db_connection()
    conn.execute("""
    UPDATE welfare 
    SET status = 'under_review', last_claim_date = CURRENT_TIMESTAMP 
    WHERE welfare_id = ?
    """, (welfare_id,))
    conn.commit()
    conn.close()
    return {
        "status": "success",
        "welfare_id": welfare_id,
        "claim_status": "under_review",
        "message": f"Claim of ₹{claim_amount} submitted to Cooperative Welfare Board for audit"
    }

# ==========================================
# 11. DEMOCRATIC GOVERNANCE & PROPOSALS
# ==========================================

@router.get("/proposals")
def get_proposals(cooperative_id: Optional[int] = None):
    conn = get_db_connection()
    query = """
    SELECT p.*, c.name as cooperative_name,
           COUNT(v.vote_id) as total_votes_cast,
           SUM(CASE WHEN v.decision = 'in_favor' THEN 1 ELSE 0 END) as votes_in_favor,
           SUM(CASE WHEN v.decision = 'against' THEN 1 ELSE 0 END) as votes_against,
           SUM(CASE WHEN v.decision = 'abstain' THEN 1 ELSE 0 END) as votes_abstain
    FROM proposals p
    JOIN cooperatives c ON p.cooperative_id = c.cooperative_id
    LEFT JOIN votes v ON p.proposal_id = v.proposal_id
    """
    params = []
    if cooperative_id:
        query += " WHERE p.cooperative_id = ?"
        params.append(cooperative_id)
    query += " GROUP BY p.proposal_id ORDER BY p.proposal_id DESC"
    rows = conn.execute(query, params).fetchall()
    conn.close()
    return [dict(r) for r in rows]

@router.get("/proposals/{proposal_id}/results")
def get_proposal_results(proposal_id: int):
    conn = get_db_connection()
    prop = conn.execute("""
    SELECT p.*, c.name as cooperative_name, c.member_count 
    FROM proposals p
    JOIN cooperatives c ON p.cooperative_id = c.cooperative_id
    WHERE p.proposal_id = ?
    """, (proposal_id,)).fetchone()
    
    if not prop:
        conn.close()
        raise HTTPException(status_code=404, detail="Proposal not found")

    votes = conn.execute("""
    SELECT v.*, u.name as member_name 
    FROM votes v
    JOIN workers w ON v.member_id = w.worker_id
    JOIN users u ON w.user_id = u.user_id
    WHERE v.proposal_id = ?
    """, (proposal_id,)).fetchall()
    conn.close()

    total_votes = len(votes)
    in_favor = sum(1 for v in votes if v["decision"] == "in_favor")
    against = sum(1 for v in votes if v["decision"] == "against")
    abstain = sum(1 for v in votes if v["decision"] == "abstain")
    member_count = prop["member_count"] or 100
    turnout_pct = round((total_votes / member_count) * 100.0, 1)

    return {
        "proposal": dict(prop),
        "total_votes_cast": total_votes,
        "turnout_percentage": turnout_pct,
        "quorum_met": turnout_pct >= prop["min_quorum_percent"],
        "in_favor": in_favor,
        "against": against,
        "abstain": abstain,
        "passed": (in_favor > against) and (turnout_pct >= prop["min_quorum_percent"]),
        "recent_votes": [dict(v) for v in votes]
    }

@router.post("/proposals/{proposal_id}/vote")
def cast_vote(proposal_id: int, req: VoteCreateRequest):
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("""
        INSERT INTO votes (proposal_id, member_id, decision, remarks)
        VALUES (?, ?, ?, ?)
        ON CONFLICT(proposal_id, member_id) DO UPDATE SET
            decision = excluded.decision,
            remarks = excluded.remarks
        """, (proposal_id, req.member_id, req.decision, req.remarks))
        conn.commit()
        return {"status": "success", "proposal_id": proposal_id, "member_id": req.member_id, "decision": req.decision}
    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=400, detail=str(e))
    finally:
        conn.close()

@router.post("/proposals")
def create_proposal(req: ProposalCreateRequest):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
    INSERT INTO proposals (cooperative_id, title, description, category, start_date, end_date, min_quorum_percent)
    VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (
        req.cooperative_id, req.title, req.description, req.category,
        req.start_date, req.end_date, req.min_quorum_percent
    ))
    pid = cursor.lastrowid
    conn.commit()
    conn.close()
    return {"status": "success", "proposal_id": pid}

# ==========================================
# 12. DEMO CONTROLLER (Reset & Tour)
# ==========================================

@router.post("/demo/reset")
def reset_demo():
    from backend.seed_data import seed_database
    seed_database()
    return {"status": "success", "message": "Demo data reset successfully to initial state"}
