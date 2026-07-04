// OfferShield — Glassmorphic Client Application Logic

document.addEventListener("DOMContentLoaded", () => {
    // --- DOM Elements ---
    const companyNameInput = document.getElementById("companyNameInput");
    const recruiterEmailInput = document.getElementById("recruiterEmailInput");
    const jobTextInput = document.getElementById("jobTextInput");
    const consentCheckbox = document.getElementById("consentCheckbox");
    const fileInput = document.getElementById("fileInput");
    const uploadArea = document.getElementById("uploadArea");
    const runAuditBtn = document.getElementById("runAuditBtn");
    const companySearchBtn = document.getElementById("companySearchBtn");

    const emptyResultsView = document.getElementById("emptyResultsView");
    const resultsView = document.getElementById("resultsView");
    const scoreNum = document.getElementById("scoreNum");
    const scoreCircleProgress = document.getElementById("scoreCircleProgress");
    const riskBadge = document.getElementById("riskBadge");
    
    const companyCard = document.getElementById("companyCard");
    const metaName = document.getElementById("metaName");
    const metaCin = document.getElementById("metaCin");
    const metaStatus = document.getElementById("metaStatus");
    const metaInc = document.getElementById("metaInc");
    const metaDirectors = document.getElementById("metaDirectors");
    const metaAddress = document.getElementById("metaAddress");
    const deductionsList = document.getElementById("deductionsList");

    const chatMessages = document.getElementById("chatMessages");
    const chatInput = document.getElementById("chatInput");
    const sendChatBtn = document.getElementById("sendChatBtn");

    // --- State Variables ---
    let currentJobCheckId = null;
    let selectedFile = null;

    // --- 1. File Upload & Drag-and-Drop Operations ---
    uploadArea.addEventListener("click", () => fileInput.click());

    uploadArea.addEventListener("dragover", (e) => {
        e.preventDefault();
        uploadArea.classList.add("dragover");
    });

    uploadArea.addEventListener("dragleave", () => {
        uploadArea.classList.remove("dragover");
    });

    uploadArea.addEventListener("drop", (e) => {
        e.preventDefault();
        uploadArea.classList.remove("dragover");
        if (e.dataTransfer.files.length > 0) {
            handleFileSelection(e.dataTransfer.files[0]);
        }
    });

    fileInput.addEventListener("change", (e) => {
        if (e.target.files.length > 0) {
            handleFileSelection(e.target.files[0]);
        }
    });

    function handleFileSelection(file) {
        selectedFile = file;
        uploadArea.querySelector(".upload-text").textContent = `Selected: ${file.name}`;
        uploadArea.style.borderColor = "var(--accent-indigo)";
    }

    // --- 2. Run Audit Pipeline Trigger ---
    runAuditBtn.addEventListener("click", async () => {
        // Validation: If a file is uploaded, JIT Consent Checkbox MUST be checked
        if (selectedFile && !consentCheckbox.checked) {
            alert("DPDP Act Consent Required: You must consent to document parsing before scanning an uploaded file.");
            return;
        }

        const companyName = companyNameInput.value.trim();
        const recruiterEmail = recruiterEmailInput.value.trim();
        let jobText = jobTextInput.value.trim();

        if (selectedFile && !jobText) {
            // Simulated OCR extractor for Phase 1 MVP
            jobText = `[Parsed from uploaded contract/offer letter: ${selectedFile.name}]
            Urgent joining request. Note: Deposit of Rs. 950 registration fee is required. Contact on Telegram: @ScammyJobs`;
        }

        if (!jobText && !companyName) {
            alert("Please paste a job description text or enter a company name to audit.");
            return;
        }

        // Show loading state
        runAuditBtn.disabled = true;
        runAuditBtn.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> Auditing...';

        try {
            const response = await fetch("/api/v1/scan/job", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({
                    raw_text: jobText || `Query for company: ${companyName}`,
                    company_name: companyName || null,
                    recruiter_email: recruiterEmail || null
                })
            });

            if (!response.ok) throw new Error("Scoring pipeline call failed.");
            const data = await response.json();

            // Store current check ID to feed chatbot context (RAG)
            currentJobCheckId = data.job_check_id;

            renderAuditReport(data);

            // Notify chatbot of the newly scanned audit
            appendBotMessage(`I've loaded **Job Check Audit #${currentJobCheckId}** into my RAG context. Ask me anything about this check or company!`);

        } catch (error) {
            alert(`Error: ${error.message}`);
        } finally {
            runAuditBtn.disabled = false;
            runAuditBtn.innerHTML = '<i class="fa-solid fa-circle-play"></i> Run Security Audit';
        }
    });

    // --- 3. Company Quick Registry Search Trigger ---
    companySearchBtn.addEventListener("click", async () => {
        const companyName = companyNameInput.value.trim();
        if (!companyName) {
            alert("Please enter a company name or CIN to search the registry.");
            return;
        }

        companySearchBtn.disabled = true;
        companySearchBtn.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i>';

        try {
            const response = await fetch(`/api/v1/company/search?query=${encodeURIComponent(companyName)}`);
            if (!response.ok) throw new Error("Company lookup failed.");
            const data = await response.json();

            renderCompanySearchReport(data);

        } catch (error) {
            alert(`Error: ${error.message}`);
        } finally {
            companySearchBtn.disabled = false;
            companySearchBtn.innerHTML = '<i class="fa-solid fa-magnifying-glass"></i>';
        }
    });

    // --- 4. Render Layout Outputs ---
    function renderAuditReport(data) {
        emptyResultsView.style.display = "none";
        resultsView.style.display = "flex";

        // 1. Animate circular score visualizer
        const score = data.trust_score;
        scoreNum.textContent = score;

        // SVG dashoffset calculation: circumference = 2 * PI * r = 2 * 3.14159 * 40 = 251.2
        const dashOffset = 251.2 - (251.2 * score) / 100;
        scoreCircleProgress.style.strokeDashoffset = dashOffset;

        // Color and Risk Badge logic
        if (data.risk_level === "Low") {
            scoreCircleProgress.style.stroke = "var(--color-safe)";
            riskBadge.className = "risk-badge";
            riskBadge.textContent = "LOW RISK (SAFE)";
            riskBadge.style.borderColor = "var(--color-safe)";
            riskBadge.style.color = "var(--color-safe)";
            riskBadge.style.background = "rgba(48, 209, 88, 0.1)";
        } else if (data.risk_level === "Medium") {
            scoreCircleProgress.style.stroke = "var(--color-caution)";
            riskBadge.className = "risk-badge";
            riskBadge.textContent = "MEDIUM RISK (CAUTION)";
            riskBadge.style.borderColor = "var(--color-caution)";
            riskBadge.style.color = "var(--color-caution)";
            riskBadge.style.background = "rgba(255, 159, 10, 0.1)";
        } else {
            scoreCircleProgress.style.stroke = "var(--color-danger)";
            riskBadge.className = "risk-badge";
            riskBadge.textContent = "HIGH RISK (DANGER)";
            riskBadge.style.borderColor = "var(--color-danger)";
            riskBadge.style.color = "var(--color-danger)";
            riskBadge.style.background = "rgba(255, 69, 58, 0.1)";
        }

        // 2. Render Verified Company Details
        const company = data.company_verification;
        if (company && !company.unverified) {
            companyCard.style.display = "block";
            companyCard.className = "company-card";
            companyCard.querySelector("h3").innerHTML = '<i class="fa-solid fa-circle-check verify-icon"></i> Verified Registry Details';
            metaName.textContent = company.name;
            metaCin.textContent = company.cin || "N/A";
            metaStatus.textContent = company.registration_status || "Active";
            metaInc.textContent = company.incorporation_date || "N/A";
            metaDirectors.textContent = company.directors || "N/A";
            metaAddress.textContent = company.registered_address || "N/A";
            renderReputationDetails(company);
        } else if (company && company.unverified) {
            // Show unverified/struck-off flag card
            companyCard.style.display = "block";
            companyCard.className = "company-card unverified-firm";
            companyCard.querySelector("h3").innerHTML = '<i class="fa-solid fa-triangle-exclamation verify-icon"></i> Unverified/Missing Registry';
            metaName.textContent = companyNameInput.value || "Unknown Company";
            metaCin.textContent = "Missing/No Record";
            metaStatus.textContent = "Unregistered";
            metaInc.textContent = "N/A";
            metaDirectors.textContent = "N/A";
            metaAddress.textContent = "No registered physical address found in database.";
            renderReputationDetails(null);
        } else {
            companyCard.style.display = "none";
            renderReputationDetails(null);
        }

        // 3. Render Deductions explanations
        deductionsList.innerHTML = "";
        const explanations = data.explanations;
        if (explanations && explanations.length > 0) {
            explanations.forEach(exp => {
                const li = document.createElement("li");
                li.textContent = exp;
                deductionsList.appendChild(li);
            });
        } else {
            const li = document.createElement("li");
            li.className = "no-deductions";
            li.textContent = "All checks passed. No risk deductions applied to this posting.";
            li.style.color = "var(--color-safe)";
            deductionsList.appendChild(li);
        }
    }

    function renderReputationDetails(company) {
        const reputationCard = document.getElementById("reputationCard");
        const metaDomain = document.getElementById("metaDomain");
        const metaDomainCreated = document.getElementById("metaDomainCreated");
        const metaGlassdoor = document.getElementById("metaGlassdoor");
        const metaTrustpilot = document.getElementById("metaTrustpilot");
        const metaFootprint = document.getElementById("metaFootprint");

        if (company && !company.unverified) {
            reputationCard.style.display = "block";
            metaDomain.textContent = company.domain || "Not found";
            metaDomainCreated.textContent = company.domain_created_at || "Unresolved";
            
            const gdRating = company.glassdoor_rating;
            const gdReviews = company.glassdoor_review_count;
            metaGlassdoor.textContent = gdRating ? `${gdRating} ★ (${gdReviews.toLocaleString()} reviews)` : "No reviews found";
            
            const tpRating = company.trustpilot_rating;
            metaTrustpilot.textContent = tpRating ? `${tpRating} ★` : "No reviews found";
            
            metaFootprint.textContent = company.google_search_footprint || "Low";
        } else {
            reputationCard.style.display = "none";
        }
    }

    function renderCompanySearchReport(company) {
        emptyResultsView.style.display = "none";
        resultsView.style.display = "flex";

        // Score maps to Active/Unverified directly
        const score = company.unverified ? 30 : 100;
        scoreNum.textContent = score;
        const dashOffset = 251.2 - (251.2 * score) / 100;
        scoreCircleProgress.style.strokeDashoffset = dashOffset;

        if (!company.unverified) {
            scoreCircleProgress.style.stroke = "var(--color-safe)";
            riskBadge.textContent = "SAFE REGISTRY";
            riskBadge.style.color = "var(--color-safe)";
            riskBadge.style.borderColor = "var(--color-safe)";
            riskBadge.style.background = "rgba(48, 209, 88, 0.1)";

            companyCard.style.display = "block";
            companyCard.className = "company-card";
            companyCard.querySelector("h3").innerHTML = '<i class="fa-solid fa-circle-check verify-icon"></i> Verified Registry Details';
            metaName.textContent = company.name;
            metaCin.textContent = company.cin || "N/A";
            metaStatus.textContent = company.registration_status || "Active";
            metaInc.textContent = company.incorporation_date || "N/A";
            metaDirectors.textContent = company.directors || "N/A";
            metaAddress.textContent = company.registered_address || "N/A";

            renderReputationDetails(company);
            deductionsList.innerHTML = '<li class="no-deductions" style="color: var(--color-safe);">Firm registry is active and matches records.</li>';
        } else {
            scoreCircleProgress.style.stroke = "var(--color-danger)";
            riskBadge.textContent = "UNVERIFIED";
            riskBadge.style.color = "var(--color-danger)";
            riskBadge.style.borderColor = "var(--color-danger)";
            riskBadge.style.background = "rgba(255, 69, 58, 0.1)";

            companyCard.style.display = "block";
            companyCard.className = "company-card unverified-firm";
            companyCard.querySelector("h3").innerHTML = '<i class="fa-solid fa-triangle-exclamation verify-icon"></i> Unverified/Missing Registry';
            metaName.textContent = companyNameInput.value;
            metaCin.textContent = "Missing";
            metaStatus.textContent = "Unregistered";
            metaInc.textContent = "N/A";
            metaDirectors.textContent = "N/A";
            metaAddress.textContent = "No registered physical address found in database.";

            renderReputationDetails(null);
            deductionsList.innerHTML = '<li>Company is missing from official RoC registers.</li>';
        }
    }

    // --- 5. RAG Chatbot Messaging Interface ---
    sendChatBtn.addEventListener("click", () => handleChatSubmission());
    chatInput.addEventListener("keydown", (e) => {
        if (e.key === "Enter") {
            handleChatSubmission();
        }
    });

    async function handleChatSubmission() {
        const message = chatInput.value.trim();
        if (!message) return;

        appendUserMessage(message);
        chatInput.value = "";

        // Add loading bubble indicator
        const loadingBubble = appendLoadingBubble();
        chatMessages.scrollTop = chatMessages.scrollHeight;

        try {
            const response = await fetch("/api/v1/chat/message", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({
                    message: message,
                    job_check_id: currentJobCheckId
                })
            });

            if (!response.ok) throw new Error("Chat service failed.");
            const data = await response.json();

            loadingBubble.remove();

            appendBotMessage(data.reply, data.sources);

        } catch (error) {
            loadingBubble.remove();
            appendBotMessage(`I'm sorry, I couldn't reach the server: ${error.message}`);
        } finally {
            chatMessages.scrollTop = chatMessages.scrollHeight;
        }
    }

    function appendUserMessage(text) {
        const bubble = document.createElement("div");
        bubble.className = "chat-bubble user-bubble";
        bubble.innerHTML = `
            <div class="bubble-avatar"><i class="fa-solid fa-user"></i></div>
            <div class="bubble-text"><p>${escapeHtml(text)}</p></div>
        `;
        chatMessages.appendChild(bubble);
    }

    function appendBotMessage(markdownText, sources = []) {
        const bubble = document.createElement("div");
        bubble.className = "chat-bubble bot-bubble";
        
        let sourcesHtml = "";
        if (sources && sources.length > 0) {
            sourcesHtml = `
                <div class="chat-sources" style="margin-top: 8px; font-size: 11px; color: var(--text-secondary);">
                    <i class="fa-solid fa-circle-info"></i> Sources: ${sources.join(", ")}
                </div>
            `;
        }

        // Render Markdown safely using Marked.js
        const renderedHtml = marked.parse(markdownText);

        bubble.innerHTML = `
            <div class="bubble-avatar"><i class="fa-solid fa-robot"></i></div>
            <div class="bubble-text">
                ${renderedHtml}
                ${sourcesHtml}
            </div>
        `;
        chatMessages.appendChild(bubble);
    }

    function appendLoadingBubble() {
        const bubble = document.createElement("div");
        bubble.className = "chat-bubble bot-bubble loading-bubble";
        bubble.innerHTML = `
            <div class="bubble-avatar"><i class="fa-solid fa-robot"></i></div>
            <div class="bubble-text"><p><i class="fa-solid fa-circle-notch fa-spin"></i> Shieldy is thinking...</p></div>
        `;
        chatMessages.appendChild(bubble);
        return bubble;
    }

    function escapeHtml(text) {
        const div = document.createElement('div');
        div.innerText = text;
        return div.innerHTML;
    }
});
