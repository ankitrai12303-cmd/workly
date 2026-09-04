// SkillBridge Client-Side Single Page Application
// Compatible with SIH 2026 Problem Statement 26089 PRD

const API_BASE = "/api";

// Global State
let currentRole = "customer"; // 'customer' | 'worker' | 'admin' | 'tour'
let currentUser = {
    user_id: 2,
    name: "Rajesh Mehta",
    email: "customer@example.com",
    role: "customer"
};
let currentWorkerId = 1; // Ramesh Sharma (Hero Plumber)
let currentSelectedServiceId = 1; // Emergency Pipe Leak
let activeBooking = null; // latest active booking
let allServices = [];
let demandChartInstance = null;
let currentRatingValue = 5;

// Locations dictionary
const LOCATIONS = {
    "Indiranagar": { lat: 12.9784, lng: 77.6408, label: "Indiranagar 100ft Rd" },
    "Koramangala": { lat: 12.9340, lng: 77.6200, label: "Koramangala 4th Block" },
    "Jayanagar": { lat: 12.9250, lng: 77.5938, label: "Jayanagar 4th T Block" },
    "HSR Layout": { lat: 12.9121, lng: 77.6446, label: "HSR Layout Sector 2" },
    "Whitefield": { lat: 12.9698, lng: 77.7500, label: "Whitefield Main Rd" }
};

// ==========================================
// INITIALIZATION
// ==========================================
document.addEventListener("DOMContentLoaded", async () => {
    lucide.createIcons();
    await loadInitialData();
    // Periodic refresh for active booking updates
    setInterval(pollActiveBooking, 4000);
});

async function loadInitialData() {
    await loadCustomerServices();
    await loadCustomerBookingHistory();
    await loadWorkerDashboard();
    await loadAdminDashboard();
    await loadAIDemandForecast();
    initDemoStoryMilestones();
    lucide.createIcons();
}

// ==========================================
// ROLE SWITCHING & NAVIGATION
// ==========================================
function switchRole(role) {
    currentRole = role;

    // Tab buttons
    ['customer', 'worker', 'admin', 'tour'].forEach(r => {
        const btn = document.getElementById(`tab-${r}`);
        const portal = document.getElementById(`portal-${r}`);
        if (r === role) {
            btn.className = "flex items-center space-x-1.5 px-3.5 py-1.5 rounded-lg transition-all bg-white text-slate-900 shadow-sm font-bold border border-slate-200";
            portal.classList.remove("hidden");
        } else {
            btn.className = "flex items-center space-x-1.5 px-3.5 py-1.5 rounded-lg transition-all text-slate-600 hover:text-slate-900 font-medium";
            portal.classList.add("hidden");
        }
    });

    const nameEl = document.getElementById("current-user-name");
    const roleEl = document.getElementById("current-user-role-badge");

    if (role === "customer") {
        nameEl.innerText = "Rajesh Mehta";
        roleEl.innerText = "Customer (Indiranagar)";
        loadCustomerBookingHistory();
    } else if (role === "worker") {
        nameEl.innerText = "Ramesh Sharma";
        roleEl.innerText = "Verified Plumber (Coop #1)";
        loadWorkerDashboard();
    } else if (role === "admin") {
        nameEl.innerText = "Ramesh Kumar";
        roleEl.innerText = "Cooperative Executive Admin";
        loadAdminDashboard();
    } else if (role === "tour") {
        nameEl.innerText = "SIH 2026 Presenter";
        roleEl.innerText = "Interactive Demo Story Mode";
    }

    lucide.createIcons();
}

function switchWorkerSubtab(tab) {
    ['earnings', 'welfare', 'governance'].forEach(t => {
        const btn = document.getElementById(`worker-subtab-${t}`);
        const panel = document.getElementById(`worker-panel-${t}`);
        if (t === tab) {
            btn.className = "px-5 py-3 border-b-2 border-coop-600 text-coop-700 bg-emerald-50/50 flex items-center space-x-2";
            panel.classList.remove("hidden");
        } else {
            btn.className = "px-5 py-3 border-b-2 border-transparent text-slate-600 hover:text-slate-900 flex items-center space-x-2";
            panel.classList.add("hidden");
        }
    });
    lucide.createIcons();
}

function switchAdminSubtab(tab) {
    ['ai', 'workers', 'fairmatch', 'governance'].forEach(t => {
        const btn = document.getElementById(`admin-subtab-${t}`);
        const panel = document.getElementById(`admin-panel-${t}`);
        if (t === tab) {
            btn.className = "px-5 py-3 border-b-2 border-coop-600 text-coop-700 bg-emerald-50/50 flex items-center space-x-2 whitespace-nowrap";
            panel.classList.remove("hidden");
        } else {
            btn.className = "px-5 py-3 border-b-2 border-transparent text-slate-600 hover:text-slate-900 flex items-center space-x-2 whitespace-nowrap";
            panel.classList.add("hidden");
        }
    });
    if (tab === 'ai') loadAIDemandForecast();
    lucide.createIcons();
}

// ==========================================
// 1. CUSTOMER PORTAL LOGIC
// ==========================================

async function loadCustomerServices() {
    try {
        const res = await fetch(`${API_BASE}/services`);
        allServices = await res.json();
        
        const countLabel = document.getElementById("service-count-label");
        countLabel.innerText = `${allServices.length} verified trade services`;

        // Render category filters
        const categories = ["All", ...new Set(allServices.map(s => s.category))];
        const catContainer = document.getElementById("cust-category-filters");
        catContainer.innerHTML = categories.map((cat, idx) => `
            <button onclick="filterCustomerServices('${cat}')" class="cat-pill px-3 py-1 text-xs font-semibold rounded-lg transition ${idx === 0 ? 'bg-emerald-600 text-white' : 'bg-slate-100 text-slate-600 hover:bg-slate-200'}">
                ${cat}
            </button>
        `).join("");

        renderServiceCards(allServices);
    } catch (err) {
        console.error("Error loading services:", err);
    }
}

function filterCustomerServices(category) {
    document.querySelectorAll(".cat-pill").forEach(el => {
        if (el.innerText.trim() === category) {
            el.className = "cat-pill px-3 py-1 text-xs font-semibold rounded-lg transition bg-emerald-600 text-white";
        } else {
            el.className = "cat-pill px-3 py-1 text-xs font-semibold rounded-lg transition bg-slate-100 text-slate-600 hover:bg-slate-200";
        }
    });

    const filtered = (category === "All") ? allServices : allServices.filter(s => s.category === category);
    renderServiceCards(filtered);
}

function renderServiceCards(services) {
    const isEmergency = document.getElementById("cust-emergency")?.checked || false;
    const grid = document.getElementById("cust-services-grid");

    grid.innerHTML = services.map(srv => {
        const price = isEmergency && srv.emergency_supported ? Math.round(srv.base_price * srv.emergency_multiplier) : srv.base_price;
        const iconName = srv.icon || "wrench";
        return `
        <div class="bg-white rounded-xl p-5 border border-slate-200 shadow-sm hover:shadow-md transition-all flex flex-col justify-between group">
            <div>
                <div class="flex items-start justify-between">
                    <div class="w-10 h-10 rounded-xl bg-emerald-50 text-emerald-700 flex items-center justify-center group-hover:bg-emerald-600 group-hover:text-white transition">
                        <i data-lucide="${iconName}" class="w-5 h-5"></i>
                    </div>
                    ${srv.emergency_supported ? '<span class="text-[10px] font-bold px-2 py-0.5 rounded-full bg-red-100 text-red-700 border border-red-200">Emergency 24x7</span>' : '<span class="text-[10px] font-semibold px-2 py-0.5 rounded-full bg-slate-100 text-slate-600">Standard</span>'}
                </div>
                <h3 class="font-bold text-sm text-slate-900 mt-3 group-hover:text-emerald-700 transition">${srv.service_name}</h3>
                <p class="text-xs text-slate-500 mt-1 line-clamp-2">${srv.description}</p>
            </div>

            <div class="mt-4 pt-3 border-t border-slate-100 flex items-center justify-between">
                <div>
                    <span class="text-xs text-slate-400 block">${srv.estimated_duration} mins</span>
                    <span class="text-base font-extrabold text-slate-900">₹${price}</span>
                </div>
                <button onclick="openBookingWithFairMatch(${srv.service_id})" class="px-3 py-1.5 bg-coop-600 hover:bg-coop-700 text-white rounded-lg text-xs font-bold transition flex items-center space-x-1 shadow-sm">
                    <i data-lucide="sparkles" class="w-3.5 h-3.5"></i>
                    <span>FairMatch Book</span>
                </button>
            </div>
        </div>
        `;
    }).join("");
    lucide.createIcons();
}

async function openBookingWithFairMatch(serviceId) {
    currentSelectedServiceId = serviceId;
    const isEmergency = document.getElementById("cust-emergency")?.checked || false;
    const locKey = document.getElementById("cust-location").value;
    const loc = LOCATIONS[locKey] || LOCATIONS["Indiranagar"];

    logDemoEvent(`Customer clicked 'FairMatch Book' for Service #${serviceId} at ${locKey}. Running algorithmic matching...`);

    // Call FairMatch API
    try {
        const res = await fetch(`${API_BASE}/matching/find-workers?service_id=${serviceId}&latitude=${loc.lat}&longitude=${loc.lng}&is_emergency=${isEmergency}`, {
            method: "POST"
        });
        const matchData = await res.json();
        
        // Immediately create booking with recommended worker
        const bookRes = await fetch(`${API_BASE}/bookings`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
                customer_id: currentUser.user_id,
                service_id: serviceId,
                location: `${locKey}, Bangalore`,
                latitude: loc.lat,
                longitude: loc.lng,
                is_emergency: isEmergency,
                scheduled_time: isEmergency ? "Immediate Priority" : "Today, 11:00 AM"
            })
        });
        const created = await bookRes.json();
        activeBooking = await (await fetch(`${API_BASE}/bookings/${created.booking_id}`)).json();
        
        renderActiveCustomerBooking();
        logDemoEvent(`Booking #${activeBooking.booking_id} created in state 'ASSIGNED' to ${activeBooking.worker_name}.`);

        // Check if incoming notification indicator on worker tab should flash
        const badge = document.getElementById("worker-job-badge");
        badge.classList.remove("hidden");

    } catch (err) {
        console.error("Booking error:", err);
    }
}

function renderActiveCustomerBooking() {
    const container = document.getElementById("cust-active-booking-container");
    if (!activeBooking || ["RATED"].includes(activeBooking.status)) {
        container.classList.add("hidden");
        return;
    }

    container.classList.remove("hidden");
    const b = activeBooking;

    // Steps definition
    const steps = ["REQUESTED", "ASSIGNED", "ACCEPTED", "ON THE WAY", "IN PROGRESS", "COMPLETED", "PAID"];
    const currentStepIdx = steps.indexOf(b.status);

    const stepItems = steps.map((s, idx) => {
        let stateClass = "text-slate-400 border-slate-200 bg-white";
        let iconHtml = `<span class="text-xs font-bold">${idx + 1}</span>`;
        if (idx < currentStepIdx) {
            stateClass = "text-emerald-700 border-emerald-500 bg-emerald-50 font-bold";
            iconHtml = `<i data-lucide="check" class="w-3.5 h-3.5 text-emerald-600"></i>`;
        } else if (idx === currentStepIdx) {
            stateClass = "text-emerald-800 border-emerald-600 bg-emerald-600 text-white font-extrabold shadow-md ring-2 ring-emerald-200";
            iconHtml = `<span class="text-xs text-white">${idx + 1}</span>`;
        }
        return `
            <div class="flex-1 flex flex-col items-center text-center">
                <div class="w-7 h-7 rounded-full border-2 flex items-center justify-center transition-all ${stateClass}">
                    ${iconHtml}
                </div>
                <span class="text-[10px] uppercase tracking-tight font-bold mt-1.5 ${idx <= currentStepIdx ? 'text-emerald-800' : 'text-slate-400'}">${s}</span>
            </div>
        `;
    }).join("");

    // Action button depending on status
    let actionBtn = "";
    if (b.status === "COMPLETED") {
        actionBtn = `
            <button onclick="openPaymentModal(${b.booking_id}, ${b.amount})" class="px-5 py-2.5 bg-emerald-600 hover:bg-emerald-700 text-white rounded-xl text-xs font-bold transition flex items-center space-x-2 shadow-md shadow-emerald-600/20">
                <i data-lucide="credit-card" class="w-4 h-4"></i>
                <span>Proceed to Payment (₹${b.amount})</span>
            </button>
        `;
    } else if (b.status === "PAID") {
        actionBtn = `
            <div class="flex items-center space-x-2">
                <button onclick="openInvoiceModal(${b.booking_id})" class="px-4 py-2 bg-slate-800 hover:bg-slate-900 text-white rounded-xl text-xs font-bold transition flex items-center space-x-1.5">
                    <i data-lucide="file-text" class="w-4 h-4"></i>
                    <span>View Tax Invoice</span>
                </button>
                <button onclick="openRatingModal(${b.booking_id})" class="px-4 py-2 bg-amber-500 hover:bg-amber-600 text-white rounded-xl text-xs font-bold transition flex items-center space-x-1.5">
                    <i data-lucide="star" class="w-4 h-4 fill-white"></i>
                    <span>Rate Worker</span>
                </button>
            </div>
        `;
    }

    container.innerHTML = `
        <div class="bg-white rounded-2xl p-6 shadow-md border-2 border-emerald-500/40 relative overflow-hidden">
            <div class="flex flex-col md:flex-row md:items-center justify-between pb-4 border-b border-slate-100 gap-3">
                <div class="flex items-center space-x-3">
                    <div class="w-10 h-10 rounded-xl bg-emerald-600 text-white flex items-center justify-center shadow-sm">
                        <i data-lucide="activity" class="w-5 h-5"></i>
                    </div>
                    <div>
                        <div class="flex items-center space-x-2">
                            <h3 class="font-extrabold text-base text-slate-900">Active Booking #${b.booking_id}: ${b.service_name}</h3>
                            ${b.is_emergency ? '<span class="text-[10px] font-bold px-2 py-0.5 bg-red-100 text-red-700 rounded-full border border-red-200">EMERGENCY RUSH</span>' : ''}
                        </div>
                        <p class="text-xs text-slate-500">${b.location} • Scheduled: <b>${b.scheduled_time}</b></p>
                    </div>
                </div>
                <div class="flex items-center space-x-3">
                    <span class="text-sm font-bold text-slate-800">Total: ₹${b.amount}</span>
                    ${actionBtn}
                </div>
            </div>

            <!-- Stepper -->
            <div class="flex items-center justify-between pt-6 pb-2 relative">
                ${stepItems}
            </div>

            <!-- FairMatch Worker Recommendation Card -->
            <div class="mt-5 p-4 rounded-xl bg-emerald-50/60 border border-emerald-200 flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
                <div class="flex items-center space-x-3">
                    <div class="w-12 h-12 rounded-xl bg-emerald-700 text-white flex items-center justify-center font-bold text-lg">
                        ${b.worker_name ? b.worker_name.split(' ').map(n=>n[0]).join('') : 'WK'}
                    </div>
                    <div>
                        <div class="flex items-center space-x-2">
                            <h4 class="font-bold text-sm text-slate-900">${b.worker_name || "Cooperative Technician"}</h4>
                            <span class="text-xs font-bold text-amber-700 flex items-center"><i data-lucide="star" class="w-3.5 h-3.5 fill-amber-400 mr-0.5"></i> ${b.worker_rating || '4.92'}</span>
                        </div>
                        <p class="text-xs text-slate-600">${b.cooperative_name || 'Bangalore Shramik Seva Cooperative'}</p>
                    </div>
                </div>

                <!-- Explainability Box (PRD Section 10 & 11) -->
                <div class="flex-1 sm:max-w-md bg-white p-2.5 rounded-lg border border-emerald-300 text-xs text-slate-700 shadow-sm">
                    <span class="text-[10px] uppercase tracking-wider font-extrabold text-emerald-800 block mb-0.5 flex items-center">
                        <i data-lucide="shield-check" class="w-3.5 h-3.5 mr-1"></i>
                        Why FairMatch Picked This Worker:
                    </span>
                    <p class="italic text-[11px] text-slate-600 leading-tight">${b.fairness_notes || 'Verified cooperative member with certified skill, close proximity, and fair opportunity quota balance.'}</p>
                </div>
            </div>
        </div>
    `;
    lucide.createIcons();
}

async function loadCustomerBookingHistory() {
    try {
        const res = await fetch(`${API_BASE}/bookings?customer_id=${currentUser.user_id}`);
        const bookings = await res.json();
        const historyContainer = document.getElementById("cust-booking-history");

        if (!bookings.length) {
            historyContainer.innerHTML = `<div class="py-4 text-center text-xs text-slate-400">No previous bookings found.</div>`;
            return;
        }

        historyContainer.innerHTML = bookings.map(b => `
            <div class="py-3.5 flex items-center justify-between">
                <div class="flex items-center space-x-3">
                    <div class="w-8 h-8 rounded-lg bg-slate-100 flex items-center justify-center text-slate-600">
                        <i data-lucide="${b.icon || 'check-circle'}" class="w-4 h-4"></i>
                    </div>
                    <div>
                        <span class="font-bold text-xs text-slate-900 block">${b.service_name}</span>
                        <span class="text-[11px] text-slate-500">${b.location} • Worker: ${b.worker_name || 'Assigned'}</span>
                    </div>
                </div>
                <div class="flex items-center space-x-3 text-xs">
                    <span class="px-2 py-0.5 rounded text-[10px] font-bold ${b.status === 'RATED' ? 'bg-emerald-100 text-emerald-800' : 'bg-slate-100 text-slate-700'}">${b.status}</span>
                    <span class="font-bold text-slate-800">₹${b.amount}</span>
                    <button onclick="openInvoiceModal(${b.booking_id})" class="text-coop-600 hover:text-coop-800 font-bold flex items-center space-x-1">
                        <i data-lucide="file-text" class="w-3.5 h-3.5"></i>
                        <span>Invoice</span>
                    </button>
                </div>
            </div>
        `).join("");
        lucide.createIcons();
    } catch (err) {
        console.error("Error loading history:", err);
    }
}

// ==========================================
// 2. WORKER PORTAL LOGIC
// ==========================================

async function loadWorkerDashboard() {
    try {
        // Fetch profile
        const profRes = await fetch(`${API_BASE}/workers/profile?worker_id=${currentWorkerId}`);
        const prof = await profRes.json();

        document.getElementById("worker-card-name").innerText = prof.name;
        document.getElementById("worker-card-coop").innerText = `${prof.cooperative_name} • Reg: ${prof.registration_number}`;
        document.getElementById("worker-card-rating").innerText = prof.rating;
        document.getElementById("worker-card-exp").innerText = `${prof.experience_years} Years Experience`;
        document.getElementById("worker-card-jobs").innerText = `${prof.completed_jobs_count} Jobs Completed`;

        // Availability selector
        const availSel = document.getElementById("worker-avail-select");
        availSel.value = prof.availability_status;
        document.getElementById("worker-avail-text").innerText = prof.availability_status === 'available' ? 'Available for Dispatch' : 'Not Accepting Gigs';

        // Load Earnings
        const earnRes = await fetch(`${API_BASE}/workers/earnings?worker_id=${currentWorkerId}`);
        const earn = await earnRes.json();
        document.getElementById("worker-stat-weekly-earn").innerText = `₹${earn.weekly_earnings.toFixed(2)}`;
        document.getElementById("worker-stat-total-earn").innerText = `₹${earn.total_earnings.toFixed(2)}`;
        document.getElementById("worker-stat-welfare-contrib").innerText = `₹${earn.cooperative_welfare_contributed.toFixed(2)}`;

        const payoutList = document.getElementById("worker-payouts-list");
        if (earn.recent_transactions.length) {
            payoutList.innerHTML = earn.recent_transactions.map(p => `
                <div class="py-2.5 flex justify-between text-xs">
                    <div>
                        <span class="font-bold text-slate-800 block">${p.service_name}</span>
                        <span class="text-[11px] text-slate-400">${p.job_date} • Ref: ${p.transaction_reference}</span>
                    </div>
                    <div class="text-right">
                        <span class="font-bold text-emerald-700 block">+₹${p.worker_payout.toFixed(2)}</span>
                        <span class="text-[10px] text-slate-400">Coop Welfare: -₹${p.cooperative_welfare_cut.toFixed(2)}</span>
                    </div>
                </div>
            `).join("");
        } else {
            payoutList.innerHTML = `<div class="py-3 text-xs text-slate-400">No settled payouts yet today.</div>`;
        }

        // Load Welfare Cards
        const welfareRes = await fetch(`${API_BASE}/welfare?worker_id=${currentWorkerId}`);
        const welfareItems = await welfareRes.json();
        const welfareGrid = document.getElementById("worker-welfare-cards");
        welfareGrid.innerHTML = welfareItems.map(w => `
            <div class="bg-slate-50 p-4 rounded-xl border border-slate-200">
                <div class="flex items-center justify-between">
                    <span class="text-xs font-bold text-slate-800">${w.benefit_type}</span>
                    <span class="text-[10px] font-extrabold px-2 py-0.5 bg-emerald-100 text-emerald-800 rounded-full uppercase">${w.status}</span>
                </div>
                <div class="text-xl font-black text-slate-900 mt-2">₹${w.coverage_amount.toLocaleString()}</div>
                <p class="text-[11px] text-slate-500 mt-1">${w.description}</p>
                <div class="mt-3 text-[10px] text-coop-700 font-medium">Eligibility: ${w.eligibility}</div>
            </div>
        `).join("");

        // Load Proposals
        await loadWorkerProposals();

        // Check for incoming or active jobs for this worker
        await checkWorkerJobQueue();

    } catch (err) {
        console.error("Error loading worker dashboard:", err);
    }
}

async function checkWorkerJobQueue() {
    const res = await fetch(`${API_BASE}/workers/jobs?worker_id=${currentWorkerId}`);
    const jobs = await res.json();

    const incomingAlert = document.getElementById("worker-incoming-alert");
    const activeJobContainer = document.getElementById("worker-active-job-container");
    const badge = document.getElementById("worker-job-badge");

    // Check if any job is ASSIGNED (waiting for worker acceptance)
    const assignedJob = jobs.find(j => j.status === "ASSIGNED");
    if (assignedJob) {
        badge.classList.remove("hidden");
        incomingAlert.classList.remove("hidden");
        incomingAlert.innerHTML = `
            <div class="bg-gradient-to-r from-amber-500 to-orange-600 text-white p-5 rounded-2xl shadow-lg animate-pulse flex flex-col md:flex-row items-start md:items-center justify-between gap-4">
                <div class="flex items-center space-x-3">
                    <div class="w-12 h-12 rounded-xl bg-white/20 flex items-center justify-center">
                        <i data-lucide="bell-ring" class="w-6 h-6 text-white"></i>
                    </div>
                    <div>
                        <div class="flex items-center space-x-2">
                            <span class="text-xs font-black uppercase tracking-wider px-2 py-0.5 rounded bg-black/20">🚨 New Assignment Alert</span>
                            <span class="text-xs font-bold">${assignedJob.is_emergency ? 'EMERGENCY RUSH' : 'STANDARD GIG'}</span>
                        </div>
                        <h3 class="text-lg font-black">${assignedJob.service_name} • ₹${assignedJob.amount}</h3>
                        <p class="text-xs text-amber-100">${assignedJob.customer_name} • ${assignedJob.location}</p>
                    </div>
                </div>
                <div class="flex items-center space-x-3">
                    <button onclick="acceptIncomingJob(${assignedJob.booking_id})" class="px-5 py-2.5 bg-white text-orange-700 hover:bg-amber-50 rounded-xl text-xs font-extrabold transition shadow-md">
                        Accept Job
                    </button>
                    <button onclick="rejectIncomingJob(${assignedJob.booking_id})" class="px-4 py-2.5 bg-black/20 hover:bg-black/30 text-white rounded-xl text-xs font-semibold transition">
                        Reject
                    </button>
                </div>
            </div>
        `;
    } else {
        badge.classList.add("hidden");
        incomingAlert.classList.add("hidden");
    }

    // Check if any active job in progress (ACCEPTED, ON THE WAY, IN PROGRESS)
    const ongoingJob = jobs.find(j => ["ACCEPTED", "ON THE WAY", "IN PROGRESS"].includes(j.status));
    if (ongoingJob) {
        activeJobContainer.classList.remove("hidden");
        
        let nextBtn = "";
        if (ongoingJob.status === "ACCEPTED") {
            nextBtn = `<button onclick="updateJobStep(${ongoingJob.booking_id}, 'ON THE WAY')" class="px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white text-xs font-bold rounded-xl transition flex items-center space-x-1.5"><i data-lucide="navigation" class="w-4 h-4"></i><span>Start Trip (On the Way)</span></button>`;
        } else if (ongoingJob.status === "ON THE WAY") {
            nextBtn = `<button onclick="updateJobStep(${ongoingJob.booking_id}, 'IN PROGRESS')" class="px-4 py-2 bg-amber-600 hover:bg-amber-700 text-white text-xs font-bold rounded-xl transition flex items-center space-x-1.5"><i data-lucide="wrench" class="w-4 h-4"></i><span>Arrived (Start Work)</span></button>`;
        } else if (ongoingJob.status === "IN PROGRESS") {
            nextBtn = `<button onclick="updateJobStep(${ongoingJob.booking_id}, 'COMPLETED')" class="px-4 py-2 bg-emerald-600 hover:bg-emerald-700 text-white text-xs font-bold rounded-xl transition flex items-center space-x-1.5"><i data-lucide="check-circle" class="w-4 h-4"></i><span>Mark Work Completed</span></button>`;
        }

        activeJobContainer.innerHTML = `
            <div class="bg-white p-5 rounded-2xl border-2 border-coop-500 shadow-sm flex flex-col md:flex-row items-start md:items-center justify-between gap-4">
                <div>
                    <span class="text-xs font-extrabold uppercase tracking-wide text-emerald-700">Active Job Execution</span>
                    <h3 class="text-base font-black text-slate-900">${ongoingJob.service_name} (Booking #${ongoingJob.booking_id})</h3>
                    <p class="text-xs text-slate-500">Customer: <b>${ongoingJob.customer_name}</b> (${ongoingJob.customer_phone}) • ${ongoingJob.location}</p>
                </div>
                <div class="flex items-center space-x-3">
                    <span class="text-xs font-extrabold px-3 py-1 rounded-full bg-emerald-100 text-emerald-800">State: ${ongoingJob.status}</span>
                    ${nextBtn}
                </div>
            </div>
        `;
    } else {
        activeJobContainer.classList.add("hidden");
    }

    lucide.createIcons();
}

async function acceptIncomingJob(bookingId) {
    await fetch(`${API_BASE}/workers/jobs/${bookingId}/accept?worker_id=${currentWorkerId}`, { method: "POST" });
    logDemoEvent(`Worker Ramesh accepted Booking #${bookingId}. State is now 'ACCEPTED'.`);
    await loadWorkerDashboard();
    pollActiveBooking();
}

async function rejectIncomingJob(bookingId) {
    await fetch(`${API_BASE}/workers/jobs/${bookingId}/reject?worker_id=${currentWorkerId}`, { method: "POST" });
    logDemoEvent(`Worker Ramesh rejected Booking #${bookingId}. Re-routed to FairMatch queue.`);
    await loadWorkerDashboard();
}

async function updateJobStep(bookingId, nextStatus) {
    await fetch(`${API_BASE}/workers/jobs/${bookingId}/status`, {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ status: nextStatus })
    });
    logDemoEvent(`Worker updated Job #${bookingId} status to '${nextStatus}'.`);
    await loadWorkerDashboard();
    pollActiveBooking();
}

async function toggleWorkerAvailability() {
    const sel = document.getElementById("worker-avail-select").value;
    await fetch(`${API_BASE}/workers/availability?worker_id=${currentWorkerId}&status=${sel}`, { method: "PUT" });
    document.getElementById("worker-avail-text").innerText = sel === 'available' ? 'Available for Dispatch' : 'Not Accepting Gigs';
}

async function loadWorkerProposals() {
    const res = await fetch(`${API_BASE}/proposals`);
    const proposals = await res.json();
    const list = document.getElementById("worker-proposals-list");
    list.innerHTML = proposals.map(p => `
        <div class="bg-slate-50 p-5 rounded-xl border border-slate-200">
            <div class="flex items-start justify-between">
                <div>
                    <span class="text-[10px] font-extrabold uppercase px-2 py-0.5 rounded bg-purple-100 text-purple-800">${p.category}</span>
                    <h5 class="font-bold text-sm text-slate-900 mt-1">${p.title}</h5>
                    <p class="text-xs text-slate-600 mt-1">${p.description}</p>
                </div>
                <span class="text-xs font-bold text-slate-500">Votes: ${p.total_votes_cast}</span>
            </div>
            <div class="mt-4 pt-3 border-t border-slate-200 flex items-center justify-between">
                <div class="text-[11px] text-slate-500">
                    Democratic Tally: <b class="text-emerald-700">${p.votes_in_favor} For</b> | <b class="text-red-700">${p.votes_against} Against</b>
                </div>
                <div class="flex items-center space-x-2">
                    <button onclick="castMemberVote(${p.proposal_id}, 'in_favor')" class="px-3 py-1 bg-emerald-600 hover:bg-emerald-700 text-white rounded text-xs font-bold transition">Vote In Favor</button>
                    <button onclick="castMemberVote(${p.proposal_id}, 'against')" class="px-3 py-1 bg-red-600 hover:bg-red-700 text-white rounded text-xs font-bold transition">Vote Against</button>
                    <button onclick="castMemberVote(${p.proposal_id}, 'abstain')" class="px-2 py-1 bg-slate-200 hover:bg-slate-300 text-slate-700 rounded text-xs font-semibold transition">Abstain</button>
                </div>
            </div>
        </div>
    `).join("");
}

async function castMemberVote(proposalId, decision) {
    await fetch(`${API_BASE}/proposals/${proposalId}/vote`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
            member_id: currentWorkerId,
            decision: decision,
            remarks: "Voted via Worker Mobile Portal"
        })
    });
    logDemoEvent(`Member Ramesh cast vote '${decision}' on Proposal #${proposalId}. Democratic tally updated.`);
    await loadWorkerProposals();
}

// ==========================================
// 3. ADMIN PORTAL LOGIC
// ==========================================

async function loadAdminDashboard() {
    try {
        const res = await fetch(`${API_BASE}/admin/dashboard`);
        const data = await res.json();

        document.getElementById("admin-stat-bookings").innerText = data.stats.total_bookings;
        document.getElementById("admin-stat-active-jobs").innerText = `${data.stats.active_jobs} Active Jobs`;
        document.getElementById("admin-stat-gmv").innerText = `₹${data.stats.total_gmv.toLocaleString()}`;
        document.getElementById("admin-stat-welfare").innerText = `₹${data.stats.welfare_fund_collected.toLocaleString()}`;
        document.getElementById("admin-stat-workers").innerText = data.stats.verified_workers;
        document.getElementById("admin-stat-pending-workers").innerText = `${data.stats.pending_verifications} Pending Approval`;
        document.getElementById("admin-stat-emergencies").innerText = data.stats.emergency_requests;

        // Pending count badge
        document.getElementById("admin-badge-pending-workers").innerText = data.stats.pending_verifications;

        // Populate FairMatch sliders from backend
        const w = data.fairmatch_weights;
        document.getElementById("slider-weight-skill").value = Math.round(w.weight_skill * 100);
        document.getElementById("slider-weight-avail").value = Math.round(w.weight_availability * 100);
        document.getElementById("slider-weight-dist").value = Math.round(w.weight_distance * 100);
        document.getElementById("slider-weight-rating").value = Math.round(w.weight_rating * 100);
        document.getElementById("slider-weight-workload").value = Math.round(w.weight_workload * 100);
        document.getElementById("slider-weight-fairness").value = Math.round(w.weight_fairness * 100);
        document.getElementById("slider-max-radius").value = w.max_service_radius_km;
        updateWeightDisplay();

        // Load workers for queue
        await filterAdminWorkers('pending');

    } catch (err) {
        console.error("Error loading admin dashboard:", err);
    }
}

async function filterAdminWorkers(filter) {
    const res = await fetch(`${API_BASE}/admin/workers`);
    const workers = await res.json();
    const list = document.getElementById("admin-worker-queue-list");

    const filtered = (filter === 'all') ? workers : workers.filter(w => {
        if (filter === 'pending') return ['pending', 'under_review'].includes(w.verification_status);
        if (filter === 'verified') return w.verification_status === 'verified';
        return true;
    });

    if (!filtered.length) {
        list.innerHTML = `<div class="py-4 text-xs text-slate-400">No worker applications matching filter '${filter}'.</div>`;
        return;
    }

    list.innerHTML = filtered.map(w => `
        <div class="py-4 flex flex-col md:flex-row items-start md:items-center justify-between gap-4">
            <div>
                <div class="flex items-center space-x-2">
                    <span class="font-bold text-sm text-slate-900">${w.name}</span>
                    <span class="text-[10px] font-bold px-2 py-0.5 rounded-full ${w.verification_status === 'verified' ? 'bg-emerald-100 text-emerald-800' : 'bg-amber-100 text-amber-800'} uppercase">${w.verification_status}</span>
                </div>
                <p class="text-xs text-slate-500">${w.cooperative_name} • ${w.experience_years} yrs exp • Phone: ${w.phone}</p>
                <p class="text-[11px] text-coop-700 mt-0.5">Certifications: ${w.skills_list || 'Trade certification on file'}</p>
            </div>
            <div class="flex items-center space-x-2">
                ${w.verification_status !== 'verified' ? `
                    <button onclick="adminSetWorkerVerify(${w.worker_id}, 'verified')" class="px-3 py-1.5 bg-emerald-600 hover:bg-emerald-700 text-white rounded-lg text-xs font-bold transition flex items-center space-x-1">
                        <i data-lucide="check" class="w-3.5 h-3.5"></i>
                        <span>Approve & Verify</span>
                    </button>
                    <button onclick="adminSetWorkerVerify(${w.worker_id}, 'rejected')" class="px-3 py-1.5 bg-red-100 hover:bg-red-200 text-red-700 rounded-lg text-xs font-bold transition">
                        Reject
                    </button>
                ` : `
                    <span class="text-xs font-bold text-emerald-700 flex items-center"><i data-lucide="shield-check" class="w-4 h-4 mr-1"></i> Active Member</span>
                `}
            </div>
        </div>
    `).join("");
    lucide.createIcons();
}

async function adminSetWorkerVerify(workerId, status) {
    await fetch(`${API_BASE}/admin/workers/${workerId}/verify`, {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ verification_status: status })
    });
    logDemoEvent(`Admin updated Worker #${workerId} verification status to '${status}'.`);
    await loadAdminDashboard();
}

// FairMatch Sliders
function updateWeightDisplay() {
    document.getElementById("val-weight-skill").innerText = `${document.getElementById("slider-weight-skill").value}%`;
    document.getElementById("val-weight-avail").innerText = `${document.getElementById("slider-weight-avail").value}%`;
    document.getElementById("val-weight-dist").innerText = `${document.getElementById("slider-weight-dist").value}%`;
    document.getElementById("val-weight-rating").innerText = `${document.getElementById("slider-weight-rating").value}%`;
    document.getElementById("val-weight-workload").innerText = `${document.getElementById("slider-weight-workload").value}%`;
    document.getElementById("val-weight-fairness").innerText = `${document.getElementById("slider-weight-fairness").value}%`;
    document.getElementById("val-max-radius").innerText = `${document.getElementById("slider-max-radius").value} km`;
}

async function saveFairMatchWeights() {
    const payload = {
        weight_skill: parseInt(document.getElementById("slider-weight-skill").value) / 100.0,
        weight_availability: parseInt(document.getElementById("slider-weight-avail").value) / 100.0,
        weight_distance: parseInt(document.getElementById("slider-weight-dist").value) / 100.0,
        weight_rating: parseInt(document.getElementById("slider-weight-rating").value) / 100.0,
        weight_workload: parseInt(document.getElementById("slider-weight-workload").value) / 100.0,
        weight_fairness: parseInt(document.getElementById("slider-weight-fairness").value) / 100.0,
        max_service_radius_km: parseFloat(document.getElementById("slider-max-radius").value)
    };
    await fetch(`${API_BASE}/matching/config`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload)
    });
    alert("FairMatch algorithmic weights updated successfully!");
    logDemoEvent(`Admin configured FairMatch weights: Skill=${payload.weight_skill*100}%, Fairness Boost=${payload.weight_fairness*100}%.`);
}

function resetFairMatchWeightsToDefault() {
    document.getElementById("slider-weight-skill").value = 35;
    document.getElementById("slider-weight-avail").value = 20;
    document.getElementById("slider-weight-dist").value = 15;
    document.getElementById("slider-weight-rating").value = 10;
    document.getElementById("slider-weight-workload").value = 10;
    document.getElementById("slider-weight-fairness").value = 10;
    document.getElementById("slider-max-radius").value = 15;
    updateWeightDisplay();
    saveFairMatchWeights();
}

// AI Demand Forecasting & Chart.js
async function loadAIDemandForecast() {
    const serviceId = document.getElementById("ai-filter-service")?.value || 1;
    const zone = document.getElementById("ai-filter-zone")?.value || "Indiranagar";

    try {
        const res = await fetch(`${API_BASE}/ai/demand-forecast?service_id=${serviceId}&zone=${zone}`);
        const data = await res.json();

        // Update metrics banner
        document.getElementById("ai-model-type").innerText = data.metrics.model_type;
        document.getElementById("ai-model-r2").innerText = data.metrics.r2_score;
        document.getElementById("ai-model-mae").innerText = data.metrics.mae;
        document.getElementById("ai-peak-hour-badge").innerText = `Peak Demand Hour: ${data.peak_hour}`;

        // Render Chart.js
        const ctx = document.getElementById("demandForecastChart").getContext("2d");
        const labels = data.hourly_forecast.map(h => h.hour_label);
        const forecastValues = data.hourly_forecast.map(h => h.forecasted_demand);
        const capacityValues = data.hourly_forecast.map(h => 8); // baseline capacity

        if (demandChartInstance) {
            demandChartInstance.destroy();
        }

        demandChartInstance = new Chart(ctx, {
            type: "line",
            data: {
                labels: labels,
                datasets: [
                    {
                        label: "AI Forecasted Demand (Bookings)",
                        data: forecastValues,
                        borderColor: "#059669",
                        backgroundColor: "rgba(5, 150, 105, 0.12)",
                        borderWidth: 3,
                        tension: 0.35,
                        fill: true
                    },
                    {
                        label: "Available Cooperative Worker Capacity",
                        data: capacityValues,
                        borderColor: "#94a3b8",
                        borderDash: [5, 5],
                        borderWidth: 2,
                        pointRadius: 0,
                        fill: false
                    }
                ]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: { position: "top", labels: { boxWidth: 12, font: { size: 11 } } },
                    tooltip: { mode: "index", intersect: false }
                },
                scales: {
                    y: { beginAtZero: true, grid: { color: "#f1f5f9" } },
                    x: { grid: { display: false } }
                }
            }
        });

        // 7-day outlook
        const weeklyContainer = document.getElementById("ai-weekly-outlook");
        weeklyContainer.innerHTML = data.weekly_forecast.map(d => `
            <div class="flex items-center justify-between p-2 rounded-lg ${d.is_peak ? 'bg-amber-50 border border-amber-200' : 'bg-slate-50'} text-xs">
                <div>
                    <span class="font-bold text-slate-800">${d.day_name} (${d.date.slice(5)})</span>
                    ${d.is_peak ? '<span class="text-[9px] font-extrabold text-amber-700 ml-1">WEEKEND SURGE</span>' : ''}
                </div>
                <span class="font-extrabold text-slate-900">${d.total_demand} jobs</span>
            </div>
        `).join("");

        // Workforce capacity alerts
        const recRes = await fetch(`${API_BASE}/ai/workforce-recommendation`);
        const recData = await recRes.json();
        const alertsGrid = document.getElementById("ai-workforce-alerts-grid");

        alertsGrid.innerHTML = recData.alerts.map(a => `
            <div class="p-4 rounded-xl border ${a.severity === 'HIGH' ? 'bg-red-50/70 border-red-200' : 'bg-amber-50/70 border-amber-200'} flex flex-col justify-between">
                <div>
                    <div class="flex items-center justify-between">
                        <span class="text-[10px] font-extrabold px-2 py-0.5 rounded-full ${a.severity === 'HIGH' ? 'bg-red-600 text-white' : 'bg-amber-600 text-white'}">${a.severity} DEFICIT GAP</span>
                        <span class="text-xs font-bold text-slate-500">${a.zone}</span>
                    </div>
                    <h5 class="font-extrabold text-sm text-slate-900 mt-2">${a.service_name}</h5>
                    <p class="text-xs text-slate-700 mt-1">Expected: <b>${a.forecasted_demand_jobs} jobs</b> | Capacity: <b>${a.active_worker_capacity} workers</b></p>
                    <div class="mt-2 text-xs font-semibold ${a.severity === 'HIGH' ? 'text-red-800' : 'text-amber-800'}">Deficit Gap: ${a.capacity_gap} workers</div>
                </div>
                <div class="mt-3 pt-2 border-t border-slate-200 text-[11px] text-slate-600">
                    <b>Action:</b> ${a.recommendation}
                </div>
            </div>
        `).join("");

    } catch (err) {
        console.error("AI forecast error:", err);
    }
}

async function retrainAIModel() {
    logDemoEvent("Retraining AI Demand Model on latest historical patterns...");
    const res = await fetch(`${API_BASE}/ai/retrain`, { method: "POST" });
    const data = await res.json();
    alert(`Model retrained successfully! New R²: ${data.metrics.r2_score}, MAE: ${data.metrics.mae}`);
    await loadAIDemandForecast();
}

// ==========================================
// 4. SIH 2026 GUIDED DEMO STORY (PRD Section 21)
// ==========================================
const DEMO_MILESTONES = [
    {
        id: 1,
        title: "1. Customer Emergency Call",
        role: "customer",
        desc: "Customer selects Emergency Pipe Leak repair in Indiranagar.",
        actionName: "Trigger Emergency Request",
        run: async () => {
            document.getElementById("cust-emergency").checked = true;
            await openBookingWithFairMatch(1);
            switchRole("customer");
        }
    },
    {
        id: 2,
        title: "2. FairMatch Explainable Ranking",
        role: "customer",
        desc: "FairMatch algorithm ranks Ramesh Sharma #1 (92.1 score) with fairness explanation.",
        actionName: "Inspect FairMatch Explanation",
        run: async () => {
            switchRole("customer");
            document.getElementById("cust-active-booking-container").scrollIntoView({ behavior: "smooth" });
        }
    },
    {
        id: 3,
        title: "3. Worker Receives Alert & Accepts",
        role: "worker",
        desc: "Switch to Worker view. Ramesh inspects job and clicks 'Accept Job'.",
        actionName: "Worker Accepts Job",
        run: async () => {
            switchRole("worker");
            if (activeBooking) {
                await acceptIncomingJob(activeBooking.booking_id);
            }
        }
    },
    {
        id: 4,
        title: "4. Worker Starts Trip & Arrives",
        role: "worker",
        desc: "Worker transitions through 'ON THE WAY' to 'IN PROGRESS'.",
        actionName: "Start Work Trip",
        run: async () => {
            switchRole("worker");
            if (activeBooking) {
                await updateJobStep(activeBooking.booking_id, "ON THE WAY");
                setTimeout(async () => {
                    await updateJobStep(activeBooking.booking_id, "IN PROGRESS");
                }, 1200);
            }
        }
    },
    {
        id: 5,
        title: "5. Work Completed",
        role: "worker",
        desc: "Ramesh finishes emergency pipe fix. State changes to 'COMPLETED'.",
        actionName: "Mark Service Completed",
        run: async () => {
            if (activeBooking) {
                await updateJobStep(activeBooking.booking_id, "COMPLETED");
            }
            switchRole("customer");
        }
    },
    {
        id: 6,
        title: "6. Payment Simulation (UPI)",
        role: "customer",
        desc: "Customer simulates UPI payment. 5% allocated to cooperative welfare reserve.",
        actionName: "Complete Payment",
        run: async () => {
            switchRole("customer");
            if (activeBooking) {
                await executeSimulatedPayment("success");
            }
        }
    },
    {
        id: 7,
        title: "7. Tax Invoice & 5★ Review",
        role: "customer",
        desc: "Customer downloads official Cooperative Tax Invoice and leaves a 5-star rating.",
        actionName: "Inspect Invoice & Submit Rating",
        run: async () => {
            switchRole("customer");
            if (activeBooking) {
                await openInvoiceModal(activeBooking.booking_id);
                await submitCustomerRatingDirect(activeBooking.booking_id);
            }
        }
    },
    {
        id: 8,
        title: "8. Admin Revenue & Governance Vote",
        role: "admin",
        desc: "Admin monitors updated GMV, AI demand surge peak, and casts democratic ballot.",
        actionName: "Review Cooperative Admin Ops",
        run: async () => {
            switchRole("admin");
            await loadAdminDashboard();
            await loadAIDemandForecast();
            logDemoEvent("SIH 2026 Demo Story completed: End-to-end cooperative cycle demonstrated!");
        }
    }
];

function initDemoStoryMilestones() {
    const grid = document.getElementById("demo-milestones-grid");
    if (!grid) return;
    grid.innerHTML = DEMO_MILESTONES.map(m => `
        <div class="bg-slate-800/80 p-4 rounded-xl border border-slate-700 text-slate-200 flex flex-col justify-between">
            <div>
                <span class="text-[10px] uppercase font-bold text-purple-400">Step ${m.id}</span>
                <h4 class="font-bold text-sm text-white mt-1">${m.title}</h4>
                <p class="text-xs text-slate-400 mt-1">${m.desc}</p>
            </div>
            <button onclick="DEMO_MILESTONES[${m.id - 1}].run()" class="mt-4 w-full py-2 bg-purple-600 hover:bg-purple-700 text-white rounded-lg text-xs font-bold transition shadow">
                ${m.actionName}
            </button>
        </div>
    `).join("");
}

async function runAutoDemoStory() {
    logDemoEvent("Beginning Automated SIH 2026 Presentation Story (PRD Section 21)...");
    for (let i = 0; i < DEMO_MILESTONES.length; i++) {
        logDemoEvent(`>>> Executing Milestone ${i+1}: ${DEMO_MILESTONES[i].title}`);
        await DEMO_MILESTONES[i].run();
        await new Promise(r => setTimeout(r, 2200));
    }
    logDemoEvent("All 8 milestones completed successfully!");
}

function logDemoEvent(msg) {
    const logBox = document.getElementById("demo-live-log");
    if (!logBox) return;
    const timeStr = new Date().toLocaleTimeString();
    const row = document.createElement("div");
    row.className = "text-slate-300";
    row.innerHTML = `<span class="text-emerald-400">[${timeStr}]</span> ${msg}`;
    logBox.appendChild(row);
    logBox.scrollTop = logBox.scrollHeight;
}

// ==========================================
// 5. MODALS & PAYMENT SIMULATION
// ==========================================
function openPaymentModal(bookingId, amount) {
    document.getElementById("modal-pay-amount").innerText = `₹${amount.toFixed(2)}`;
    document.getElementById("modal-pay-worker").innerText = `₹${(amount * 0.90).toFixed(2)}`;
    document.getElementById("modal-pay-welfare").innerText = `₹${(amount * 0.05).toFixed(2)}`;
    document.getElementById("modal-pay-fee").innerText = `₹${(amount * 0.05).toFixed(2)}`;
    document.getElementById("modal-payment").classList.remove("hidden");
    lucide.createIcons();
}

async function executeSimulatedPayment(status) {
    if (!activeBooking) return;
    const res = await fetch(`${API_BASE}/payments/create`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
            booking_id: activeBooking.booking_id,
            payment_method: "UPI (Simulated)",
            simulate_status: status
        })
    });
    const data = await res.json();
    closeModal("modal-payment");

    if (status === "success") {
        logDemoEvent(`Payment of ₹${data.amount} succeeded (Ref: ${data.transaction_reference}). 5% allocated to Cooperative Welfare Fund.`);
        pollActiveBooking();
    } else {
        alert("Payment simulation failed. Try again.");
    }
}

async function openInvoiceModal(bookingId) {
    const res = await fetch(`${API_BASE}/payments/invoice/${bookingId}`);
    const inv = await res.json();

    document.getElementById("inv-number").innerText = inv.invoice_number;
    document.getElementById("inv-date").innerText = inv.invoice_date.slice(0, 10);
    document.getElementById("inv-coop-name").innerText = inv.cooperative.name;
    document.getElementById("inv-coop-reg").innerText = `Reg No: ${inv.cooperative.registration_number}`;
    document.getElementById("inv-cust-name").innerText = inv.customer.name;
    document.getElementById("inv-cust-addr").innerText = inv.customer.address;
    document.getElementById("inv-cust-phone").innerText = inv.customer.phone;
    document.getElementById("inv-worker-name").innerText = inv.worker.name;
    document.getElementById("inv-worker-rating").innerText = `Rating: ${inv.worker.rating}★`;
    document.getElementById("inv-item-name").innerText = inv.service_details.service_name;
    document.getElementById("inv-item-base").innerText = `₹${inv.service_details.base_price.toFixed(2)}`;
    
    const emergRow = document.getElementById("inv-emergency-row");
    if (inv.service_details.is_emergency) {
        emergRow.classList.remove("hidden");
        document.getElementById("inv-item-emergency").innerText = `₹${inv.service_details.emergency_surcharge.toFixed(2)}`;
    } else {
        emergRow.classList.add("hidden");
    }

    document.getElementById("inv-worker-share").innerText = `₹${inv.breakdown.worker_direct_earnings.toFixed(2)}`;
    document.getElementById("inv-welfare-share").innerText = `₹${inv.breakdown.cooperative_welfare_fund.toFixed(2)}`;
    document.getElementById("inv-tax-share").innerText = `₹${inv.breakdown.platform_operations.toFixed(2)}`;
    document.getElementById("inv-grand-total").innerText = `₹${inv.service_details.total_amount.toFixed(2)}`;
    document.getElementById("inv-pay-method").innerText = inv.payment.method;
    document.getElementById("inv-txn-ref").innerText = inv.payment.transaction_ref;

    document.getElementById("modal-invoice").classList.remove("hidden");
    lucide.createIcons();
}

function openRatingModal(bookingId) {
    if (activeBooking) {
        document.getElementById("rate-worker-name").innerText = activeBooking.worker_name || "Ramesh Sharma";
    }
    setStarRating(5);
    document.getElementById("modal-rating").classList.remove("hidden");
    lucide.createIcons();
}

function setStarRating(val) {
    currentRatingValue = val;
    const labels = ["1.0 - Poor", "2.0 - Fair", "3.0 - Good", "4.0 - Very Good", "5.0 - Outstanding Cooperative Quality"];
    document.getElementById("star-rating-label").innerText = labels[val - 1];
    
    document.querySelectorAll(".star-btn").forEach((btn, idx) => {
        const svg = btn.querySelector("svg");
        if (idx < val) {
            svg.setAttribute("fill", "#f59e0b");
            svg.setAttribute("stroke", "#f59e0b");
        } else {
            svg.setAttribute("fill", "none");
            svg.setAttribute("stroke", "#cbd5e1");
        }
    });
}

async function submitCustomerRating() {
    if (!activeBooking) return;
    const feedback = document.getElementById("rate-feedback-text").value || "Rapid emergency response and courteous professional service.";
    await fetch(`${API_BASE}/bookings/${activeBooking.booking_id}/rate`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
            booking_id: activeBooking.booking_id,
            customer_id: currentUser.user_id,
            rating: currentRatingValue,
            feedback: feedback
        })
    });
    closeModal("modal-rating");
    logDemoEvent(`Customer submitted ${currentRatingValue}★ review: "${feedback}". Worker reputation updated.`);
    activeBooking.status = "RATED";
    renderActiveCustomerBooking();
    await loadCustomerBookingHistory();
}

async function submitCustomerRatingDirect(bookingId) {
    await fetch(`${API_BASE}/bookings/${bookingId}/rate`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
            booking_id: bookingId,
            customer_id: currentUser.user_id,
            rating: 5,
            feedback: "Outstanding emergency plumbing repair. Arrived in 15 mins!"
        })
    });
    logDemoEvent("5★ rating and feedback recorded for Booking #" + bookingId);
}

function closeModal(id) {
    document.getElementById(id).classList.add("hidden");
}

function openWelfareClaimModal() {
    document.getElementById("modal-welfare").classList.remove("hidden");
}

async function submitWelfareClaim() {
    const claimType = document.getElementById("welfare-claim-type").value;
    const amount = document.getElementById("welfare-claim-amount").value;
    const reason = document.getElementById("welfare-claim-reason").value;

    await fetch(`${API_BASE}/welfare/claim?welfare_id=${claimType}&claim_amount=${amount}&reason=${encodeURIComponent(reason)}`, {
        method: "POST"
    });
    closeModal("modal-welfare");
    alert("Welfare claim submitted to Cooperative Committee!");
    logDemoEvent(`Worker Ramesh filed ₹${amount} welfare claim.`);
    await loadWorkerDashboard();
}

function openNewProposalModal() {
    document.getElementById("modal-proposal").classList.remove("hidden");
}

async function submitNewProposal() {
    const title = document.getElementById("prop-title").value;
    const category = document.getElementById("prop-category").value;
    const desc = document.getElementById("prop-desc").value;

    await fetch(`${API_BASE}/proposals`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
            cooperative_id: 1,
            title: title,
            category: category,
            description: desc,
            start_date: "2026-09-04",
            end_date: "2026-09-25",
            min_quorum_percent: 40.0
        })
    });
    closeModal("modal-proposal");
    alert("New cooperative proposal published!");
    logDemoEvent(`New proposal created: "${title}".`);
    await loadAdminDashboard();
}

async function resetDemoState() {
    if (confirm("Reset SkillBridge database to initial state?")) {
        await fetch(`${API_BASE}/demo/reset`, { method: "POST" });
        activeBooking = null;
        logDemoEvent("Database reset to initial demo state.");
        await loadInitialData();
        alert("SkillBridge demo reset complete!");
    }
}

// Background polling for real-time status update
async function pollActiveBooking() {
    if (!activeBooking || activeBooking.status === "RATED") return;
    try {
        const res = await fetch(`${API_BASE}/bookings/${activeBooking.booking_id}`);
        if (res.ok) {
            const updated = await res.json();
            if (updated.status !== activeBooking.status) {
                logDemoEvent(`Booking #${activeBooking.booking_id} status updated to '${updated.status}'.`);
            }
            activeBooking = updated;
            renderActiveCustomerBooking();
        }
    } catch (err) {
        // silent catch
    }
}

function onCustomerLocationChange() {
    logDemoEvent("Customer changed location to: " + document.getElementById("cust-location").value);
}
