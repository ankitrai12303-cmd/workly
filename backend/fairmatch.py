import math
from typing import List, Dict, Any, Optional
from backend.database import get_db_connection

def haversine_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Calculate the great-circle distance between two points on the Earth in kilometers."""
    R = 6371.0  # Earth radius in kilometers
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = (math.sin(dlat / 2) ** 2 +
         math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) *
         math.sin(dlon / 2) ** 2)
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return round(R * c, 2)

def get_fairmatch_weights() -> Dict[str, float]:
    conn = get_db_connection()
    row = conn.execute("SELECT * FROM fairmatch_config WHERE config_id = 1").fetchone()
    conn.close()
    if row:
        return {
            "weight_skill": float(row["weight_skill"]),
            "weight_availability": float(row["weight_availability"]),
            "weight_distance": float(row["weight_distance"]),
            "weight_rating": float(row["weight_rating"]),
            "weight_workload": float(row["weight_workload"]),
            "weight_fairness": float(row["weight_fairness"]),
            "max_service_radius_km": float(row["max_service_radius_km"]),
        }
    return {
        "weight_skill": 0.35,
        "weight_availability": 0.20,
        "weight_distance": 0.15,
        "weight_rating": 0.10,
        "weight_workload": 0.10,
        "weight_fairness": 0.10,
        "max_service_radius_km": 15.0,
    }

def update_fairmatch_weights(weights: Dict[str, float]) -> Dict[str, float]:
    conn = get_db_connection()
    conn.execute("""
    UPDATE fairmatch_config
    SET weight_skill = ?,
        weight_availability = ?,
        weight_distance = ?,
        weight_rating = ?,
        weight_workload = ?,
        weight_fairness = ?,
        max_service_radius_km = ?,
        updated_at = CURRENT_TIMESTAMP
    WHERE config_id = 1
    """, (
        weights.get("weight_skill", 0.35),
        weights.get("weight_availability", 0.20),
        weights.get("weight_distance", 0.15),
        weights.get("weight_rating", 0.10),
        weights.get("weight_workload", 0.10),
        weights.get("weight_fairness", 0.10),
        weights.get("max_service_radius_km", 15.0)
    ))
    conn.commit()
    conn.close()
    return get_fairmatch_weights()

def run_fairmatch(
    service_id: int,
    customer_lat: float,
    customer_lon: float,
    is_emergency: bool = False,
    override_weights: Optional[Dict[str, float]] = None
) -> Dict[str, Any]:
    """
    Executes PRD Section 10 FairMatch Engine:
    1. Hard eligibility filters (Skill match, verified status, availability, within radius).
    2. Multi-factor scoring (Skill, Availability, Distance, Rating, Workload, Fairness).
    3. Explainable recommendations with transparent mathematical breakdown.
    """
    conn = get_db_connection()
    
    # Get service details
    service = conn.execute("SELECT * FROM services WHERE service_id = ?", (service_id,)).fetchone()
    if not service:
        conn.close()
        return {"error": "Service not found", "matched_workers": []}

    req_skill_id = service["required_skill_id"]
    weights = override_weights or get_fairmatch_weights()
    max_radius = weights["max_service_radius_km"]

    # Hard eligibility query:
    # - verified worker
    # - available status
    # - possesses verified skill for required_skill_id
    query = """
    SELECT 
        w.worker_id,
        w.user_id,
        w.cooperative_id,
        u.name AS worker_name,
        u.phone AS worker_phone,
        c.name AS cooperative_name,
        w.experience_years,
        w.verification_status,
        w.rating,
        w.total_ratings_count,
        w.availability_status,
        w.service_area,
        w.latitude,
        w.longitude,
        w.completed_jobs_count,
        w.weekly_jobs_count,
        w.weekly_earnings,
        ws.certification
    FROM workers w
    JOIN users u ON w.user_id = u.user_id
    JOIN cooperatives c ON w.cooperative_id = c.cooperative_id
    JOIN worker_skills ws ON w.worker_id = ws.worker_id
    WHERE ws.skill_id = ?
      AND w.verification_status = 'verified'
      AND w.availability_status = 'available'
      AND ws.verification_status = 'verified'
    """
    candidates = conn.execute(query, (req_skill_id,)).fetchall()
    conn.close()

    if not candidates:
        return {
            "service_name": service["service_name"],
            "candidates_evaluated": 0,
            "matched_workers": [],
            "message": "No verified, available workers found with the required skill within the system."
        }

    scored_workers = []
    # Benchmark average weekly jobs for fairness baseline
    avg_weekly_jobs = max(1.0, sum(c["weekly_jobs_count"] for c in candidates) / len(candidates))
    max_weekly_earnings = max([c["weekly_earnings"] for c in candidates] + [5000.0])

    for cand in candidates:
        dist_km = haversine_distance(customer_lat, customer_lon, cand["latitude"], cand["longitude"])
        
        # Hard radius filter
        if dist_km > max_radius:
            continue

        # 1. Skill Score (0 to 1.0)
        # Baseline 0.75 for verified certification + up to 0.25 based on experience years
        skill_score = min(1.0, 0.75 + (cand["experience_years"] * 0.025))

        # 2. Availability Score (0 to 1.0)
        # Emergency calls place premium on immediate availability
        avail_score = 1.0 if cand["availability_status"] == "available" else 0.0

        # 3. Distance Score (0 to 1.0)
        # Closer workers score higher: 0km -> 1.0; at max_radius -> 0.0
        dist_score = max(0.0, 1.0 - (dist_km / max_radius))

        # 4. Rating Score (0 to 1.0)
        rating_score = cand["rating"] / 5.0

        # 5. Workload Score (0 to 1.0)
        # Workers with fewer jobs this week get higher balance score
        workload_score = max(0.1, 1.0 - min(1.0, (cand["weekly_jobs_count"] / 20.0)))

        # 6. Fairness & Opportunity Equity Score (0 to 1.0)
        # Prioritizes qualified cooperative members who have lower current earnings
        # this week to distribute gig work fairly and reduce wage inequality
        fairness_score = max(0.1, 1.0 - min(0.9, (cand["weekly_earnings"] / max_weekly_earnings)))

        # Composite Weighted Score (0 to 100)
        total_score = (
            (weights["weight_skill"] * skill_score) +
            (weights["weight_availability"] * avail_score) +
            (weights["weight_distance"] * dist_score) +
            (weights["weight_rating"] * rating_score) +
            (weights["weight_workload"] * workload_score) +
            (weights["weight_fairness"] * fairness_score)
        ) * 100.0

        # Generate Explainable Narrative
        fairness_reason = ""
        if cand["weekly_jobs_count"] <= avg_weekly_jobs:
            fairness_reason = f"has received fewer recent assignments ({cand['weekly_jobs_count']} this week, granting +{int(fairness_score*100)}% fairness boost)"
        else:
            fairness_reason = f"active workload ({cand['weekly_jobs_count']} jobs completed this week)"

        explanation = (
            f"Recommended because {cand['worker_name']} has verified credentials in {service['service_name']} "
            f"({cand['experience_years']} yrs exp), is currently available, is nearby ({dist_km} km), "
            f"holds a stellar {cand['rating']:.2f}/5.0 rating, and {fairness_reason}."
        )

        scored_workers.append({
            "worker_id": cand["worker_id"],
            "worker_name": cand["worker_name"],
            "worker_phone": cand["worker_phone"],
            "cooperative_name": cand["cooperative_name"],
            "experience_years": cand["experience_years"],
            "rating": round(cand["rating"], 2),
            "total_ratings_count": cand["total_ratings_count"],
            "distance_km": dist_km,
            "certification": cand["certification"],
            "weekly_jobs_count": cand["weekly_jobs_count"],
            "weekly_earnings": cand["weekly_earnings"],
            "scores": {
                "total_score": round(total_score, 1),
                "skill_score": round(skill_score * 100, 1),
                "availability_score": round(avail_score * 100, 1),
                "distance_score": round(dist_score * 100, 1),
                "rating_score": round(rating_score * 100, 1),
                "workload_score": round(workload_score * 100, 1),
                "fairness_score": round(fairness_score * 100, 1),
            },
            "applied_weights": weights,
            "explanation": explanation,
            "is_recommended": False
        })

    # Sort candidates by total_score descending
    scored_workers.sort(key=lambda w: w["scores"]["total_score"], reverse=True)

    if scored_workers:
        scored_workers[0]["is_recommended"] = True

    return {
        "service_name": service["service_name"],
        "is_emergency": is_emergency,
        "candidates_evaluated": len(candidates),
        "eligible_within_radius": len(scored_workers),
        "weights": weights,
        "recommended_worker": scored_workers[0] if scored_workers else None,
        "all_ranked_workers": scored_workers
    }
