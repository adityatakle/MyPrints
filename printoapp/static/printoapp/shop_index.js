/**
 * MyPrints Shop Dashboard Logic
 * Handles real-time search, queue rendering, and OTP verification.
 */

let allCarts = []; 

document.addEventListener('DOMContentLoaded', function () {
    const searchInput = document.querySelector('.sd-search-input');
    
    // Initial data fetch
    load_data();

    // Setup local search (filtering by OTP/Pickup Code)
    if (searchInput) {
        searchInput.addEventListener('input', function(e) {
            const query = e.target.value.trim();
            const filtered = allCarts.filter(cart => 
                cart.pickup_code.toString().includes(query)
            );
            render_table(filtered);
        });
    }
});

/**
 * Fetches the latest queue from the Django API
 */
function load_data() {
    fetch('/api/shop_list')
    .then(response => response.json())
    .then(result => {
        allCarts = result['cart_info'] || [];
        render_table(allCarts);
    })
    .catch(err => {
        console.error("Failed to load shop data:", err);
    });
}

/**
 * Dynamically builds the HTML table or shows the empty state
 */
function render_table(data) {
    const tableWrap   = document.querySelector('.sd-table-wrap');
    const tableBody   = document.querySelector('.sd-table tbody');
    const emptyState  = document.querySelector('.sd-empty');
    const queueBadge  = document.querySelector('.sd-queue-badge');

    // 1. Clear current table rows
    tableBody.innerHTML = ''; 

    // 2. Visibility Logic (Preventing the Blank Screen)
    if (data && data.length > 0) {
        if (tableWrap) tableWrap.style.display = 'block';
        if (emptyState) emptyState.style.display = 'none';
        
        if (queueBadge) {
            queueBadge.textContent = data.length + (data.length === 1 ? ' order' : ' orders') + ' total';
            queueBadge.style.display = 'inline-block';
        }
    } else {
        // Show empty state if no carts match
        if (tableWrap) tableWrap.style.display = 'none';
        if (emptyState) emptyState.style.display = 'block';
        if (queueBadge) queueBadge.style.display = 'none';
        return; 
    }

    // 3. Loop through data and create rows
    data.forEach((cart, index) => {
        const row = document.createElement('tr');
        
        // CSS Highlight Logic based on Cart state
        let rowClass = 'sd-row';
        if (cart.is_processing) rowClass += ' sd-row--active'; 
        else if (cart.priority === 1) rowClass += ' sd-row--priority';
        row.className = rowClass;

        // Action Cell Logic: Verification Guard
        let actionHTML = '';
        if (cart.is_verified) {
            // Already handed over to student
            actionHTML = `<span class="sd-status-verified">Verified ✓</span>`;
        } else if (cart.is_printed) {
            // Script finished printing; Ready for OTP
            actionHTML = `<button class="sd-verify-btn" onclick="verify_cart(this, ${cart.id})">Verify OTP</button>`;
        } else {
            // Script is still downloading/printing
            actionHTML = `<span class="sd-status-waiting">Printing...</span>`;
        }

        const priorityTag = cart.priority === 1 ? '<span class="sd-priority-tag">⚡ Priority</span>' : '';

        row.innerHTML = `
            <td class='sd-row-num'>${index + 1}</td>
            <td>
                <div class="sd-page-cell">
                    <span class="sd-page">${cart.total_pages} pages</span>
                    ${priorityTag}
                </div>
            </td>
            <td><span class="sd-amount">₹${cart.total_amount || 0}</span></td>
            <td><span class="sd-otp">${cart.pickup_code}</span></td>
            <td class="btn-cell">${actionHTML}</td>`; 
        
        tableBody.appendChild(row);
    });
}

/**
 * Handles the OTP verification process
 */
function verify_cart(btn, id) {
    // Immediate visual feedback to prevent double-clicks
    const originalContent = btn.innerHTML;
    btn.disabled = true;
    btn.innerHTML = '...';

    fetch('/api/verify_cart', {
        method: 'POST',
        headers: {
            'cart-id': id,
            'X-CSRFToken': getCookie('csrftoken'),
            'Content-Type': 'application/json'
        }
    })
    .then(response => {
        if (response.ok) {
            // Success: Refresh the table to show "Verified" status
            load_data();
        } else {
            // Failure: Likely the cart isn't printed yet or OTP mismatch
            alert("Verification failed. Please ensure the order is fully printed.");
            btn.disabled = false;
            btn.innerHTML = originalContent;
        }
    })
    .catch(err => {
        console.error("Verification error:", err);
        btn.disabled = false;
        btn.innerHTML = originalContent;
    });
}

/**
 * Utility to retrieve CSRF token from Django's cookie
 */
function getCookie(name) {
    let cookieValue = null;
    if (document.cookie && document.cookie !== '') {
        const cookies = document.cookie.split(';');
        for (let i = 0; i < cookies.length; i++) {
            const cookie = cookies[i].trim();
            // Does this cookie string begin with the name we want?
            if (cookie.substring(0, name.length + 1) === (name + '=')) {
                cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                break;
            }
        }
    }
    return cookieValue;
}