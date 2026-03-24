// ── STATE ─────────────────────────────────────────────────
let allCarts = []; // Global storage for the fetched data

document.addEventListener('DOMContentLoaded', function () {
    const searchInput = document.querySelector('.sd-search-input');
    
    // Initial load
    load_data();

    // ── SEARCH LOGIC ──────────────────────────────────────
    if (searchInput) {
        searchInput.addEventListener('input', function(e) {
            const query = e.target.value.trim();
            
            // Filter the master list
            const filtered = allCarts.filter(cart => {
                // Matches the full OTP number as a string
                return cart.pickup_code.toString().includes(query);
            });

            // Re-render only the filtered results
            render_table(filtered);
        });
    }
});

function load_data() {
    fetch('/api/shop_list')
    .then(response => response.json())
    .then(result => {
        console.log(result);
        allCarts = result['cart_info'] || [];
        render_table(allCarts);
    });
}

// Extracted the rendering logic so search can use it too
function render_table(data) {
    const tableWrap   = document.querySelector('.sd-table-wrap');
    const tableBody   = document.querySelector('.sd-table tbody');
    const emptyState  = document.querySelector('.sd-empty');
    const queueBadge  = document.querySelector('.sd-queue-badge');

    tableBody.innerHTML = ''; // Clear previous rows

    if (data.length > 0) {
        tableWrap.style.display = 'block';
        emptyState.style.display = 'none';
        if (queueBadge) {
            queueBadge.textContent = data.length + ' pending';
            queueBadge.style.display = '';
        }
    } else {
        tableWrap.style.display = 'none';
        emptyState.style.display = 'block';
    }

    data.forEach((cart, index) => {
        const btn = document.createElement('button');
        const isPaid = cart.cart_status === 'Paid';
        
        btn.className = isPaid ? 'sd-verify-btn' : 'sd-verify-btn--done';
        btn.innerHTML = isPaid 
            ? `<svg width="14" height="14" viewBox="0 0 24 24" fill="none"><polyline points="20 6 9 17 4 12" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"/></svg> Verify`
            : `<svg width="14" height="14" viewBox="0 0 24 24" fill="none"><path d="M18 6L6 18M6 6l12 12" stroke="currentColor" stroke-width="2.5" stroke-linecap="round"/></svg> UnVerify`;

        btn.onclick = function() {
            verify_cart(cart.id);
        };

        const row = document.createElement('tr');
        row.className = 'sd-row';
        row.innerHTML = `
            <td class='sd-row-num'>${index + 1}</td>
            <td><span class="sd-page">${cart.total_pages}</span></td>
            <td><span class="sd-amount">₹${cart.total_amount}</span></td>
            <td><span class="sd-otp">${cart.pickup_code}</span></td>
            <td class="btn-cell"></td>`; 

        row.querySelector('.btn-cell').appendChild(btn);
        tableBody.appendChild(row);
    });
}

function verify_cart(id) {
    fetch('/api/verify_cart', { // Ensure trailing slash matches Django urls
        method: 'POST',
        headers: {
            'cart-id': id,
            'X-CSRFToken': getCookie('csrftoken'),
            'Content-Type': 'application/json'
        }
    })
    .then(response => response.json())
    .then(result => {
        console.log(result);
        load_data(); // Refresh master list and re-render
    });
}

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