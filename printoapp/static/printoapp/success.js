const statusUrl = "{% url 'cart_status' cart_id=cart.id %}";

function checkStatus() {
    fetch(statusUrl, {
        method: 'POST',
        headers: { 'X-CSRFToken': '{{ csrf_token }}' }
    })
    .then(response => response.json())
    .then(data => {
        const statusText = document.getElementById('status-text');
        const spinner = document.getElementById('status-spinner');
        
        if (data.cart_status === 'Printed') {
            statusText.innerText = "Order is Printed! 📄";
            statusText.classList.add('su-text-success');
            spinner.style.display = 'none';
        }
        
        if (data.is_verified) {
            statusText.innerText = "Order Collected! Thank you. ✨";
            const section = document.getElementById('feedback-section');
            const btn = document.getElementById('fb-submit-btn');
            
            section.classList.remove('su-feedback--locked');
            btn.disabled = false;
            document.getElementById('feedback-form').removeAttribute('disabled');
            
            // --- THE FIX: Stop the polling once verified ---
            clearInterval(statusInterval);
            console.log("Polling stopped: Order verified.");
        }
    })
    .catch(err => console.error("Polling error:", err));
}

// Start polling
const statusInterval = setInterval(checkStatus, 10000);

// Run once immediately on load
checkStatus();