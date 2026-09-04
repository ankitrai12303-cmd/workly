from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any

class RegisterRequest(BaseModel):
    name: str
    phone: str
    email: str
    password: str
    role: str = "customer" # customer, worker, admin
    address: Optional[str] = "Indiranagar, Bangalore"
    cooperative_id: Optional[int] = 1
    skill_id: Optional[int] = 1
    experience_years: Optional[int] = 2

class LoginRequest(BaseModel):
    email: str
    password: str

class BookingCreateRequest(BaseModel):
    customer_id: int
    service_id: int
    location: str
    latitude: float
    longitude: float
    scheduled_time: Optional[str] = "Immediate"
    is_emergency: bool = False
    preferred_worker_id: Optional[int] = None

class JobStatusUpdateRequest(BaseModel):
    status: str # ACCEPTED, ON THE WAY, IN PROGRESS, COMPLETED

class PaymentCreateRequest(BaseModel):
    booking_id: int
    payment_method: str = "UPI"
    simulate_status: str = "success" # success, failed

class RatingCreateRequest(BaseModel):
    booking_id: int
    customer_id: int
    rating: int = Field(..., ge=1, le=5)
    feedback: Optional[str] = ""
    punctuality_rating: Optional[int] = 5
    skill_rating: Optional[int] = 5

class VoteCreateRequest(BaseModel):
    member_id: int # worker_id
    decision: str # in_favor, against, abstain
    remarks: Optional[str] = ""

class ProposalCreateRequest(BaseModel):
    cooperative_id: int
    title: str
    description: str
    category: Optional[str] = "Welfare & Operations"
    start_date: str
    end_date: str
    min_quorum_percent: Optional[float] = 40.0

class WorkerVerifyRequest(BaseModel):
    verification_status: str # verified, under_review, rejected, pending
    notes: Optional[str] = ""

class FairMatchWeightsRequest(BaseModel):
    weight_skill: float = 0.35
    weight_availability: float = 0.20
    weight_distance: float = 0.15
    weight_rating: float = 0.10
    weight_workload: float = 0.10
    weight_fairness: float = 0.10
    max_service_radius_km: float = 15.0

class ServiceCreateRequest(BaseModel):
    service_name: str
    category: str
    description: str
    base_price: float
    estimated_duration: int
    required_skill_id: int
    emergency_supported: bool = False
    emergency_multiplier: float = 1.25
    icon: str = "wrench"
