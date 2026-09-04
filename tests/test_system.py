import pytest
from fastapi.testclient import TestClient
from main import app
from backend.seed_data import seed_database
from backend.fairmatch import run_fairmatch, get_fairmatch_weights, update_fairmatch_weights
from backend.ai_engine import get_demand_forecast, get_workforce_recommendations

client = TestClient(app)

@pytest.fixture(autouse=True)
def setup_db():
    seed_database()

def test_fairmatch_engine_recommendations():
    """Verify FairMatch hard filters, multi-factor scoring, and explainability."""
    # Indiranagar emergency plumbing
    result = run_fairmatch(service_id=1, customer_lat=12.9784, customer_lon=77.6408, is_emergency=True)
    assert result["candidates_evaluated"] >= 1
    assert result["recommended_worker"] is not None
    rec = result["recommended_worker"]
    
    # Hero worker Ramesh Sharma should be top recommendation
    assert rec["worker_name"] == "Ramesh Sharma"
    assert rec["scores"]["total_score"] > 80.0
    assert "explanation" in rec
    assert "Recommended because" in rec["explanation"]
    assert "fairness boost" in rec["explanation"] or "assignments" in rec["explanation"]

def test_ai_demand_forecasting():
    """Verify AI demand forecasting model output and peak hours."""
    forecast = get_demand_forecast(service_id=1, zone="Indiranagar")
    assert "hourly_forecast" in forecast
    assert len(forecast["hourly_forecast"]) == 14
    assert "peak_hour" in forecast
    assert forecast["metrics"]["r2_score"] > 0.60
    assert forecast["metrics"]["is_synthetic_dataset"] is True

def test_workforce_capacity_alerts():
    """Verify capacity deficit gap alerts for workforce planning."""
    wf = get_workforce_recommendations()
    assert wf["total_active_alerts"] >= 2
    assert wf["high_priority_gaps"] >= 1
    plumbing_alert = next((a for a in wf["alerts"] if a["service_category"] == "Plumbing"), None)
    assert plumbing_alert is not None
    assert plumbing_alert["capacity_gap"] < 0
    assert "recommendation" in plumbing_alert

def test_full_emergency_booking_and_governance_lifecycle():
    """Verify complete SIH 2026 demo story lifecycle via REST API."""
    # 1. Health check
    res_health = client.get("/api/health")
    assert res_health.status_code == 200
    assert res_health.json()["status"] == "healthy"

    # 2. Get services
    res_srv = client.get("/api/services")
    assert res_srv.status_code == 200
    services = res_srv.json()
    assert len(services) >= 6

    # 3. Create Emergency Booking
    res_book = client.post("/api/bookings", json={
        "customer_id": 2,
        "service_id": 1,
        "location": "Indiranagar 100ft Road, Bangalore",
        "latitude": 12.9784,
        "longitude": 77.6408,
        "is_emergency": True,
        "scheduled_time": "Immediate Priority"
    })
    assert res_book.status_code == 200
    book_data = res_book.json()
    booking_id = book_data["booking_id"]
    assert book_data["booking_status"] == "ASSIGNED"
    assert book_data["assigned_worker_id"] == 1

    # 4. Worker accepts job
    res_acc = client.post(f"/api/workers/jobs/{booking_id}/accept?worker_id=1")
    assert res_acc.status_code == 200
    assert res_acc.json()["job_status"] == "ACCEPTED"

    # 5. Worker transitions: ON THE WAY -> IN PROGRESS -> COMPLETED
    for st in ["ON THE WAY", "IN PROGRESS", "COMPLETED"]:
        res_st = client.put(f"/api/workers/jobs/{booking_id}/status", json={"status": st})
        assert res_st.status_code == 200
        assert res_st.json()["new_status"] == st

    # 6. Customer pays (UPI simulated)
    res_pay = client.post("/api/payments/create", json={
        "booking_id": booking_id,
        "payment_method": "UPI (GooglePay)",
        "simulate_status": "success"
    })
    assert res_pay.status_code == 200
    pay_data = res_pay.json()
    assert pay_data["payment_status"] == "success"
    assert pay_data["cooperative_welfare_contribution"] > 0

    # 7. Generate cooperative Tax Invoice
    res_inv = client.get(f"/api/payments/invoice/{booking_id}")
    assert res_inv.status_code == 200
    inv = res_inv.json()
    assert "SB-INV-2026-" in inv["invoice_number"]
    assert inv["cooperative"]["registration_number"] is not None
    assert inv["breakdown"]["cooperative_welfare_fund"] > 0

    # 8. Rate worker
    res_rate = client.post(f"/api/bookings/{booking_id}/rate", json={
        "booking_id": booking_id,
        "customer_id": 2,
        "rating": 5,
        "feedback": "Prompt emergency arrival and spotless leak fix!",
        "punctuality_rating": 5,
        "skill_rating": 5
    })
    assert res_rate.status_code == 200

    # 9. Verify worker earnings updated
    res_earn = client.get("/api/workers/earnings?worker_id=1")
    assert res_earn.status_code == 200
    earn = res_earn.json()
    assert earn["weekly_earnings"] > 2800.0

    # 10. Cooperative Democratic Governance: Cast Vote
    res_vote = client.post("/api/proposals/1/vote", json={
        "member_id": 1,
        "decision": "in_favor",
        "remarks": "Strongly support 5% monsoon reserve"
    })
    assert res_vote.status_code == 200

    # 11. Check proposal results
    res_res = client.get("/api/proposals/1/results")
    assert res_res.status_code == 200
    assert res_res.json()["in_favor"] >= 1

    # 12. Admin dashboard reflects update
    res_admin = client.get("/api/admin/dashboard")
    assert res_admin.status_code == 200
    adm = res_admin.json()
    assert adm["stats"]["total_bookings"] >= 3
    assert adm["stats"]["welfare_fund_collected"] > 0
