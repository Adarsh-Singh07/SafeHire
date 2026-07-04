document.addEventListener('DOMContentLoaded', () => {
  const container = document.getElementById('history-container');

  chrome.storage.local.get(["scanHistory"], (result) => {
    const history = result.scanHistory || [];
    
    if (history.length > 0) {
      container.innerHTML = ''; // clear empty state
      
      history.forEach(item => {
        const itemEl = document.createElement('div');
        itemEl.className = 'history-item';
        
        let scoreClass = 'high';
        if (item.risk === 'Low') scoreClass = 'low';
        else if (item.risk === 'Medium') scoreClass = 'medium';
        
        itemEl.innerHTML = `
          <div class="job-info">
            <span class="job-title" title="${item.title}">${item.title}</span>
            <span class="job-company">${item.company}</span>
          </div>
          <div class="score-badge ${scoreClass}">
            ${item.score}
          </div>
        `;
        
        container.appendChild(itemEl);
      });
    }
  });
});
