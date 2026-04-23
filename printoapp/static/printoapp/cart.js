document.addEventListener('DOMContentLoaded', function() {
    const payBtn = document.getElementById('pay_btn');
    const queue_number = document.querySelector('#queue_number')
    if (queue_number) {
        const shopId = document.querySelector('#shop_id').value;
        const csrfToken = document.querySelector('[name=csrfmiddlewaretoken]').value;

        const updateQueue = () => {
            fetch(`/api/queue_size/${shopId}`, {
                method: 'POST',
                headers: {
                    'X-CSRFToken': csrfToken,
                    'Content-Type': 'application/json'
                }
            })
            .then(response => response.json())
            .then(result => {
                queue_number.innerHTML = result.queue_size;
            })
            .catch(err => console.log("Queue update paused..."));
        };

        updateQueue();

        // Refresh every 5 seconds
        setInterval(updateQueue, 5000);
    }
    if (payBtn) {
        payBtn.addEventListener('click', function(e) {
            e.preventDefault();

            // Grab IDs
            const shopId = document.querySelector('#shop_id').value;
            const userId = document.querySelector('#user_id').value;
            const csrfToken = document.querySelector('[name=csrfmiddlewaretoken]').value;

            // Fetch fresh order details
            fetch(`/initiate-payment/${shopId}/${userId}/`, {
                method: 'POST',
                headers: {
                    'X-CSRFToken': csrfToken,
                    'Content-Type': 'application/json'
                }
            })
            .then(response => {
                if (!response.ok) throw new Error("Server error: " + response.status);
                return response.json();
            })
            .then(data => {
                if (data.error) {
                    alert(data.error);
                    return;
                }

                // Configure Razorpay
                const options = {
                    "key": data.key_id, 
                    "amount": data.amount,
                    "currency": "INR",
                    "name": "MyPrints",
                    "description": "Order #" + data.order_id,
                    "order_id": data.order_id,
                    "callback_url":document.querySelector('#status_url').value
                
                };

                const rzp = new Razorpay(options);
                
                // Catch any modal-load failures
                rzp.on('payment.failed', function (response){
                    alert("Error: " + response.error.description);
                });

                rzp.open();
            })
            .catch(err => {
                console.error("Payment Init Error:", err);
                alert("Payment gateway connection failed.");
            });
        });
    }
});

function openEditModal(itemId) {
    document.getElementById(`modal-${itemId}`).style.display = 'flex';
    // Prevent body scroll when modal is open
    document.body.style.overflow = 'hidden';
}

function closeEditModal(itemId) {
    document.getElementById(`modal-${itemId}`).style.display = 'none';
    document.body.style.overflow = 'auto';
}

// Close modal if user clicks outside the card
window.onclick = function(event) {
    if (event.target.classList.contains('ct-modal-overlay')) {
        event.target.style.display = 'none';
        document.body.style.overflow = 'auto';
    }
}