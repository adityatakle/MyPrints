let allCarts = []; 

document.addEventListener('DOMContentLoaded', function () {
    const searchInput = document.querySelector('.sd-search-input');
    load_data();

    if (searchInput) {
        searchInput.addEventListener('input', function(e) {
            const query = e.target.value.trim();
            const filtered = allCarts.filter(cart => cart.pickup_code.toString().includes(query));
            render_table(filtered);
        });
    }
});

function load_data() {
    fetch('/api/shop_list')
    .then(response => response.json())
    .then(result => {
        allCarts = result['cart_info'] || [];
        render_table(allCarts);
    });
}

function render_table(data) {
    const tableWrap   = document.querySelector('.sd-table-wrap');
    const tableBody   = document.querySelector('.sd-table tbody');
    const emptyState  = document.querySelector('.sd-empty');
    const queueBadge  = document.querySelector('.sd-queue-badge');

    tableBody.innerHTML = ''; 

    if (data.length > 0) {
        tableWrap.style.display = 'block';
        emptyState.style.display = 'none';
        if (queueBadge) {
            queueBadge.textContent = data.length + ' orders total';
            queueBadge.style.display = '';
        }
    } else {
        tableWrap.style.display = 'none';
        emptyState.style.display = 'block';
    }

    data.forEach((cart, index) => {
        const row = document.createElement('tr');
        
        // Highlight logic
        let rowClass = 'sd-row';
        if (cart.is_processing) rowClass += ' sd-row--active';
        else if (cart.priority === 1) rowClass += ' sd-row--priority';
        row.className = rowClass;

        const priorityBadge = cart.priority === 1 ? '<span class="sd-priority-tag">⚡ Priority</span>' : '';

        // Verification Cell Logic
        let actionHTML = '';
        if (cart.is_verified) {
            // No button, just a status badge
            actionHTML = `<span class="sd-status-verified">Verified</span>`;
        } else {
            // Active verify button
            actionHTML = `<button class="sd-verify-btn" onclick="verify_cart(${cart.id})">Verify</button>`;
        }

        row.innerHTML = `
            <td class='sd-row-num'>${index + 1}</td>
            <td><span class="sd-page">${cart.total_pages}</span> ${priorityBadge}</td>
            <td><span class="sd-amount">₹${cart.total_amount}</span></td>
            <td><span class="sd-otp">${cart.pickup_code}</span></td>
            <td class="btn-cell">${actionHTML}</td>`; 
        
        tableBody.appendChild(row);
    });
}

function verify_cart(id) {
    fetch('/api/verify_cart', {
        method: 'POST',
        headers: {
            'cart-id': id,
            'X-CSRFToken': getCookie('csrftoken'),
            'Content-Type': 'application/json'
        }
    }).then(() => load_data());
}

function getCookie(name) {
    let cookieValue = null;
    if (document.cookie && document.cookie !== '') {
        const cookies = document.cookie.split(';');
        for (let i = 0; i < cookies.length; i++) {
            const cookie = cookies[i].trim();
            if (cookie.substring(0, name.length + 1) === (name + '=')) {
                cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                break;
            }
        }
    }
    return cookieValue;
}