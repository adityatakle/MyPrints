document.addEventListener('DOMContentLoaded', function() {
    // Select UI Elements
    const statusText = document.querySelector('#status-text');
    const queueNumber = document.querySelector('#queue-number');
    const statusDot = document.querySelector('#status-dot');
    const feedbackSection = document.querySelector('#feedback-section');
    const fbBtn = document.querySelector('#fb-submit-btn');
    
    // Get URLs and Token
    const statusUrl = document.querySelector('#status_url').value;
    const queueUrl = document.querySelector('#queue_url').value;
    const csrfToken = document.querySelector('#csrf_token').value;

    const updateLiveTracking = () => {
        // --- 1. Update Order Status ---
        fetch(statusUrl, {
            method: 'POST',
            headers: { 'X-CSRFToken': csrfToken, 'Content-Type': 'application/json' }
        })
        .then(res => res.json())
        .then(data => {
            // Handle Printed State
            if (data.cart_status === 'Printed') {
                statusText.innerText = "Order is Printed! 📄";
                statusText.style.color = "#10b981";
                statusDot.style.backgroundColor = "#10b981";
                queueNumber.innerText = "0"; // Position is effectively 0
            }

            // Handle Verified State (Order Finished)
            if (data.is_verified) {
                statusText.innerText = "Order Collected! ✨";
                feedbackSection.classList.remove('su-feedback--locked');
                fbBtn.disabled = false;
                
                // STOP ALL POLLING
                clearInterval(pollingInterval);
                console.log("Polling stopped: Journey Complete.");
            }
        })
        .catch(err => console.error("Status Sync Error:", err));

        // --- 2. Update Queue Position ---
        // Only fetch queue if the order isn't printed yet
        if (statusText.innerText.indexOf("Printed") === -1) {
            fetch(queueUrl, {
                method: 'POST',
                headers: { 'X-CSRFToken': csrfToken, 'Content-Type': 'application/json' }
            })
            .then(res => res.json())
            .then(data => {
                queueNumber.innerText = data.queue_size;
            })
            .catch(err => console.log("Queue Sync Error:", err));
        }
    };

    // Run every 5 seconds
    const pollingInterval = setInterval(updateLiveTracking, 5000);
    
    // Initial Run
    updateLiveTracking();
});