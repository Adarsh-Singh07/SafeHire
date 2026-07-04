// content.js — SafeHire AI Content Script (Clean Rewrite)
console.log("SafeHire AI: Content script loaded.");

// ─── State ───────────────────────────────────────────────────────────────────
let lastScannedUrl = "";
let scanDebounce = null;
let isScanning = false;

// ─── Utilities ───────────────────────────────────────────────────────────────
function getJobUrl() {
    const url = window.location.href;
    if (url.includes("linkedin.com/jobs")) return url;
    if (url.includes("indeed.com/viewjob")) return url;
    if (url.includes("naukri.com/job-listings") || url.includes("naukri.com/") && document.querySelector(".jd-header-title, .jd-header")) return url;
    return null;
}

function sleep(ms) {
    return new Promise(resolve => setTimeout(resolve, ms));
}

// ─── Extraction ──────────────────────────────────────────────────────────────
function extractJob() {
    const host = window.location.hostname;
    if (host.includes("linkedin.com")) return extractLinkedIn();
    if (host.includes("indeed.com")) return extractIndeed();
    if (host.includes("naukri.com")) return extractNaukri();
    return null;
}

function extractLinkedIn() {
    // Try multiple selector strategies
    const selectors = {
        desc: ["#job-details", ".jobs-description__container", ".jobs-description-content__text", ".jobs-description", "article"],
        title: [
            ".job-details-jobs-unified-top-card__job-title h1",
            ".job-details-jobs-unified-top-card__job-title",
            "h2.t-24", ".jobs-unified-top-card__job-title", "h1"
        ],
        company: [
            ".job-details-jobs-unified-top-card__primary-description a",
            ".job-details-jobs-unified-top-card__company-name",
            ".jobs-unified-top-card__company-name"
        ]
    };

    let descEl = null;
    for (const sel of selectors.desc) {
        descEl = document.querySelector(sel);
        if (descEl && descEl.innerText.trim().length > 50) break;
        descEl = null;
    }

    // Fallback: find "About the job" heading
    if (!descEl) {
        const headings = document.querySelectorAll("h2, h3");
        for (const h of headings) {
            if (h.innerText && h.innerText.includes("About the job")) {
                descEl = h.closest("section") || h.parentElement;
                break;
            }
        }
    }

    let titleEl = null;
    for (const sel of selectors.title) {
        titleEl = document.querySelector(sel);
        if (titleEl && titleEl.innerText.trim()) break;
        titleEl = null;
    }

    let companyEl = null;
    for (const sel of selectors.company) {
        companyEl = document.querySelector(sel);
        if (companyEl && companyEl.innerText.trim()) break;
        companyEl = null;
    }

    console.log(`SafeHire AI: Extraction -> title=${!!titleEl}, desc=${!!descEl}`);

    if (!titleEl || !descEl) return null;

    return {
        url: window.location.href,
        title: titleEl.innerText.trim().slice(0, 200),
        company: companyEl ? companyEl.innerText.trim().slice(0, 100) : "Unknown",
        description: descEl.innerText.trim().slice(0, 8000)
    };
}

function extractIndeed() {
    const titleEl = document.querySelector(".jobsearch-JobInfoHeader-title");
    const companyEl = document.querySelector('[data-testid="inlineHeader-companyName"]');
    const descEl = document.querySelector("#jobDescriptionText");
    if (!titleEl || !descEl) return null;
    return {
        url: window.location.href,
        title: titleEl.innerText.trim().slice(0, 200),
        company: companyEl ? companyEl.innerText.trim().slice(0, 100) : "Unknown",
        description: descEl.innerText.trim().slice(0, 8000)
    };
}

function extractNaukri() {
    // Naukri job detail page selectors
    const titleSelectors = [
        ".jd-header-title",
        "h1.title",
        "[class*='jd-header'] h1",
        ".job-tittle h1",
        "h1"
    ];
    const companySelectors = [
        ".jd-header-comp-name",
        "[class*='company-name']",
        ".comp-name",
        ".company"
    ];
    const descSelectors = [
        ".job-desc",
        "[class*='job-desc']",
        ".jd-desc",
        "[class*='jd-desc']",
        ".description__content",
        "section.job-desc"
    ];

    let titleEl = null;
    for (const sel of titleSelectors) {
        titleEl = document.querySelector(sel);
        if (titleEl && titleEl.innerText.trim()) break;
        titleEl = null;
    }

    let companyEl = null;
    for (const sel of companySelectors) {
        companyEl = document.querySelector(sel);
        if (companyEl && companyEl.innerText.trim()) break;
        companyEl = null;
    }

    let descEl = null;
    for (const sel of descSelectors) {
        descEl = document.querySelector(sel);
        if (descEl && descEl.innerText.trim().length > 50) break;
        descEl = null;
    }

    console.log(`SafeHire AI: Naukri extraction -> title=${!!titleEl}, desc=${!!descEl}`);

    if (!titleEl || !descEl) return null;

    return {
        url: window.location.href,
        title: titleEl.innerText.trim().slice(0, 200),
        company: companyEl ? companyEl.innerText.trim().slice(0, 100) : "Unknown",
        description: descEl.innerText.trim().slice(0, 8000)
    };
}

// ─── Badge ────────────────────────────────────────────────────────────────────
const BADGE_ID = "safehire-ai-floating-badge";

function ensureStyles() {
    if (document.getElementById("safehire-ai-styles")) return;
    const s = document.createElement("style");
    s.id = "safehire-ai-styles";
    s.textContent = `
        #${BADGE_ID} {
            position: fixed !important;
            bottom: 20px !important;
            right: 20px !important;
            z-index: 2147483647 !important;
            width: 320px !important;
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif !important;
            font-size: 14px !important;
            border-radius: 12px !important;
            overflow: hidden !important;
            box-shadow: 0 10px 40px rgba(0,0,0,0.4) !important;
            animation: sh_slidein 0.35s ease-out !important;
            pointer-events: auto !important;
        }
        @keyframes sh_slidein {
            from { opacity: 0; transform: translateY(16px); }
            to   { opacity: 1; transform: translateY(0); }
        }
        #${BADGE_ID} .sh-head {
            display: flex !important;
            align-items: center !important;
            justify-content: space-between !important;
            padding: 12px 14px !important;
            cursor: pointer !important;
            user-select: none !important;
        }
        #${BADGE_ID} .sh-head-left {
            display: flex !important;
            align-items: center !important;
            gap: 8px !important;
            color: #fff !important;
            font-weight: 700 !important;
        }
        #${BADGE_ID} .sh-score-pill {
            background: rgba(255,255,255,0.25) !important;
            color: #fff !important;
            font-weight: 700 !important;
            font-size: 12px !important;
            padding: 3px 10px !important;
            border-radius: 20px !important;
        }
        #${BADGE_ID} .sh-close {
            background: none !important;
            border: none !important;
            color: rgba(255,255,255,0.8) !important;
            font-size: 18px !important;
            cursor: pointer !important;
            padding: 0 !important;
            line-height: 1 !important;
        }
        #${BADGE_ID} .sh-body {
            padding: 14px !important;
            background: #0f172a !important;
            color: #e2e8f0 !important;
            font-size: 13px !important;
            line-height: 1.55 !important;
        }
        #${BADGE_ID} .sh-risk-bar {
            border-left: 3px solid #fff !important;
            padding: 6px 10px !important;
            border-radius: 0 6px 6px 0 !important;
            margin-bottom: 10px !important;
            font-weight: 600 !important;
        }
        #${BADGE_ID} .sh-flags {
            margin: 8px 0 0 0 !important;
            padding-left: 18px !important;
            color: #fca5a5 !important;
        }
        #${BADGE_ID} .sh-flags li {
            margin-bottom: 4px !important;
        }
        #${BADGE_ID} .sh-ok {
            color: #34d399 !important;
            font-weight: 600 !important;
            margin-top: 6px !important;
        }
        #${BADGE_ID} .sh-pulse {
            width: 9px !important;
            height: 9px !important;
            border-radius: 50% !important;
            background: #fff !important;
            display: inline-block !important;
            animation: sh_pulse 1.4s infinite !important;
        }
        @keyframes sh_pulse {
            0%, 100% { opacity: 1; transform: scale(1); }
            50% { opacity: 0.4; transform: scale(0.75); }
        }
    `;
    document.head.appendChild(s);
}

function showLoadingBadge() {
    removeBadge();
    ensureStyles();
    const badge = document.createElement("div");
    badge.id = BADGE_ID;
    badge.innerHTML = `
        <div class="sh-head" style="background: linear-gradient(135deg,#3b82f6,#1d4ed8);">
            <div class="sh-head-left">
                <span class="sh-pulse"></span>
                <span>SafeHire AI: Scanning...</span>
            </div>
        </div>
    `;
    document.body.appendChild(badge);
    console.log("SafeHire AI: Loading badge shown.");
}

function showResultBadge(result) {
    removeBadge();
    ensureStyles();

    const risk = result.risk_level || "High";
    const score = result.trust_score ?? 0;
    const summary = result.summary || "Analysis complete.";
    const flags = Array.isArray(result.red_flags) ? result.red_flags : [];

    let grad, riskColor, riskBg, emoji;
    if (risk === "Low") {
        grad = "linear-gradient(135deg,#10b981,#059669)";
        riskColor = "#34d399"; riskBg = "rgba(16,185,129,0.12)"; emoji = "🟢";
    } else if (risk === "Medium") {
        grad = "linear-gradient(135deg,#f59e0b,#d97706)";
        riskColor = "#fbbf24"; riskBg = "rgba(245,158,11,0.12)"; emoji = "🟡";
    } else {
        grad = "linear-gradient(135deg,#ef4444,#b91c1c)";
        riskColor = "#f87171"; riskBg = "rgba(239,68,68,0.12)"; emoji = "🔴";
    }

    const flagsHtml = flags.length > 0
        ? `<ul class="sh-flags">${flags.map(f => `<li>${escapeHtml(f)}</li>`).join("")}</ul>`
        : `<p class="sh-ok">✅ No red flags detected.</p>`;

    const badge = document.createElement("div");
    badge.id = BADGE_ID;
    badge.innerHTML = `
        <div class="sh-head" style="background:${grad};">
            <div class="sh-head-left">
                <span>${emoji} SafeHire AI</span>
            </div>
            <div style="display:flex;align-items:center;gap:8px;">
                <span class="sh-score-pill">${score}/100</span>
                <button class="sh-close" id="sh-toggle" title="Toggle details">▾</button>
                <button class="sh-close" id="sh-dismiss" title="Close">✕</button>
            </div>
        </div>
        <div class="sh-body" id="sh-body-content">
            <div class="sh-risk-bar" style="border-color:${riskColor};background:${riskBg};color:${riskColor};">
                ${risk} Risk
            </div>
            <p style="margin:0 0 6px 0;">${escapeHtml(summary)}</p>
            ${flags.length > 0 ? `<strong style="color:#f87171;font-size:12px;">⚠ Flags:</strong>` : ""}
            ${flagsHtml}
        </div>
    `;

    document.body.appendChild(badge);

    document.getElementById("sh-dismiss").addEventListener("click", (e) => {
        e.stopPropagation();
        removeBadge();
    });

    let open = true;
    document.getElementById("sh-toggle").addEventListener("click", (e) => {
        e.stopPropagation();
        open = !open;
        const body = document.getElementById("sh-body-content");
        const btn = document.getElementById("sh-toggle");
        if (body) body.style.display = open ? "block" : "none";
        if (btn) btn.textContent = open ? "▾" : "▸";
    });

    console.log(`SafeHire AI: Badge shown — ${risk} Risk, Score: ${score}`);
}

function removeBadge() {
    const el = document.getElementById(BADGE_ID);
    if (el) el.remove();
}

function escapeHtml(str) {
    return String(str)
        .replace(/&/g, "&amp;")
        .replace(/</g, "&lt;")
        .replace(/>/g, "&gt;")
        .replace(/"/g, "&quot;");
}

// ─── Main scan logic ──────────────────────────────────────────────────────────
async function tryExtractAndScan(retries = 5, delayMs = 1000) {
    for (let i = 0; i < retries; i++) {
        const job = extractJob();
        if (job) {
            console.log("SafeHire AI: Job extracted:", job.title, "| Sending to backend...");
            showLoadingBadge();
            sendToBackground(job);
            return;
        }
        console.log(`SafeHire AI: Extraction attempt ${i + 1}/${retries} failed, retrying in ${delayMs}ms...`);
        await sleep(delayMs);
    }
    console.log("SafeHire AI: Could not extract job after all retries.");
}

function sendToBackground(jobData) {
    try {
        chrome.runtime.sendMessage({ action: "analyzeJob", data: jobData }, (response) => {
            if (chrome.runtime.lastError) {
                console.error("SafeHire AI: Runtime error:", chrome.runtime.lastError.message);
                removeBadge();
                return;
            }
            if (response && !response.error) {
                console.log("SafeHire AI: Got result:", response);
                showResultBadge(response);
            } else {
                console.error("SafeHire AI: API error:", response ? response.error : "no response");
                removeBadge();
            }
        });
    } catch (err) {
        console.error("SafeHire AI: sendMessage exception:", err.message);
        removeBadge();
    }
}

function onUrlChange() {
    const url = window.location.href;
    if (url === lastScannedUrl) return;
    if (!getJobUrl()) return;

    lastScannedUrl = url;
    clearTimeout(scanDebounce);
    scanDebounce = setTimeout(() => {
        tryExtractAndScan();
    }, 1200);
}

// ─── Entry point ─────────────────────────────────────────────────────────────

// Initial check
if (getJobUrl()) {
    setTimeout(() => tryExtractAndScan(), 1500);
    lastScannedUrl = window.location.href;
}

// Watch for SPA navigation
const navObserver = new MutationObserver(() => {
    const url = window.location.href;
    if (url !== lastScannedUrl && getJobUrl()) {
        onUrlChange();
    }
});

navObserver.observe(document.body, { childList: true, subtree: true });
