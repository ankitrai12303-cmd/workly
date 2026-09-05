# Workly: Cooperative Gig Services Platform
**Smart India Hackathon 2026 — Problem Statement 26089**

Worklry is a worker-centric digital marketplace connecting customers with verified cooperative service providers through fair matching, intelligent workforce planning, welfare support, and democratic cooperative governance.

---

## 🌟 Core Differentiators (Why SkillBridge is NOT an Urban Company clone)
1. **Cooperative Ownership**: Workers are verified members of registered labour cooperatives, retaining 90% direct earnings while 5% is pooled into a member health & emergency welfare fund.
2. **FairMatch Engine (PRD §10)**: Multi-factor explainable worker allocation combining Skill (35%), Availability (20%), Distance (15%), Rating (10%), Workload (10%), and an **Opportunity Fairness Boost (10%)** to prevent gig monopolies and worker burnout.
3. **AI Demand Forecasting & Workforce Planning (PRD §11)**: Scikit-learn Random Forest model predicting 24-hour hourly and 7-day demand by service trade and zone, generating proactive capacity gap alerts and dispatch recommendations.
4. **Worker Welfare & Health Shield (PRD §7)**: Comprehensive cashless health cover, accidental transit insurance, and education grants funded directly by cooperative gig collections.
5. **Democratic Cooperative Governance (PRD §7 & §12)**: One member, one vote policy resolutions on commission rates, emergency funds, and tool loans.
6. **SIH 2026 Guided Demo Story (PRD §21)**: One-click interactive presenter tour demonstrating the complete emergency plumbing flow from customer to worker to cooperative admin.

---

## 🚀 How to Run the Platform

### 1. Start the Server
```bash
python main.py
```
Open your browser at:
👉 **[http://127.0.0.1:8000](http://127.0.0.1:8000)**

### 2. Run Automated Integration Tests
```bash
python -m pytest tests/test_system.py -v
```

---

## 📱 User Portals & Features
- **Customer Portal**:
  - Browse verified trades (Plumbing, Electrical, Carpentry, Appliances, Cleaning, Painting).
  - 🚨 **Emergency Service Toggle**: Prioritizes rapid 45-minute dispatch.
  - **FairMatch Explanation Badge**: Transparently displays why each worker was recommended.
  - Live Booking Lifecycle: `REQUESTED` &rarr; `ASSIGNED` &rarr; `ACCEPTED` &rarr; `ON THE WAY` &rarr; `IN PROGRESS` &rarr; `COMPLETED` &rarr; `PAID` &rarr; `RATED`.
  - Digital Payment Simulation & Printable Official Cooperative Tax Invoice (with GST & Coop Reg #).
  - 5-Star post-service rating and review.
- **Worker Portal**:
  - Live Duty Toggle (Available / On Job / Offline).
  - Incoming Gig Alerts with real-time Accept/Reject.
  - Active Job Progression buttons: [Start Trip] &rarr; [Arrived] &rarr; [Mark Completed].
  - Earnings Dashboard with transparent 5% welfare deductions.
  - Welfare claim submission modal.
  - Democratic cooperative voting on active proposals.
- **Cooperative Admin Portal**:
  - Executive Overview (Total Bookings, GMV, Pooled Welfare Reserve, Emergency Requests).
  - Worker Verification Queue (Approve / Reject / Review ITI & NSDC certifications).
  - FairMatch Algorithmic Weight Sliders (Live community parameter adjustment).
  - AI Demand Forecast curves (Chart.js) and Workforce Deficit Gap alerts.
  - Proposal creation & voting turnout monitors.
- **SIH 2026 Demo Story Mode**:
  - Top bar button **"SIH Demo Story"** or auto-run button to walk through Section 21 of the PRD seamlessly with an event stream logger!

---

## 🛠️ Tech Stack
- **Backend**: Python 3.13, FastAPI, Uvicorn, SQLite.
- **AI/ML**: Scikit-Learn (RandomForestRegressor), Pandas, NumPy.
- **Frontend**: Responsive Single-Page App with Tailwind CSS, Lucide Icons, Chart.js.
