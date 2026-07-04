// background.js

chrome.runtime.onMessage.addListener((request, sender, sendResponse) => {
  if (request.action === "analyzeJob") {
    // We must return true to indicate we will respond asynchronously
    analyzeJobData(request.data).then(sendResponse).catch(error => {
      console.error("Analysis error:", error);
      sendResponse({ error: error.message });
    });
    return true;
  }
});

async function analyzeJobData(jobData) {
  try {
    console.log("Sending data to SafeHire AI backend...", jobData);
    const response = await fetch("http://localhost:8000/api/v1/analyze/", {
      method: "POST",
      headers: {
        "Content-Type": "application/json"
      },
      body: JSON.stringify({
        url: jobData.url,
        raw_text: jobData.description
      })
    });

    if (!response.ok) {
      throw new Error(`API returned status ${response.status}`);
    }

    const result = await response.json();
    
    // Save to local storage for the popup history
    const historyItem = {
      title: jobData.title,
      company: jobData.company,
      score: result.trust_score,
      risk: result.risk_level,
      timestamp: new Date().toISOString()
    };
    
    chrome.storage.local.get(["scanHistory"], (res) => {
      let history = res.scanHistory || [];
      history.unshift(historyItem);
      if (history.length > 5) history.pop();
      chrome.storage.local.set({ scanHistory: history });
    });

    return result;
  } catch (error) {
    console.error("Fetch failed:", error);
    throw error;
  }
}
