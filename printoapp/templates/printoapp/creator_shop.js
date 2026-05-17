document.addEventListener('DOMContentLoaded', function() {
    const canvas = document.getElementById('shopRevenueChart');
    if (!canvas) return; 

    const ctx = canvas.getContext('2d');
    
    // 1. Retrieve Data
    const shopRawData = JSON.parse(document.getElementById('shop-rev-data').textContent);
    const platformRawData = JSON.parse(document.getElementById('platform-rev-data').textContent);
    
    if (shopRawData.length === 0) {
        ctx.font = "14px 'DM Sans', sans-serif";
        ctx.fillStyle = "#64748b";
        ctx.textAlign = "center";
        ctx.fillText("No revenue data available for this shop.", canvas.width / 2, canvas.height / 2);
        return; 
    }

    // 2. Map Data (Assuming arrays are aligned by month/year)
    // Reversing so oldest is on the left
    const labels = shopRawData.slice().reverse().map(entry => `${entry.month}/${entry.year}`);
    const shopData = shopRawData.slice().reverse().map(entry => parseFloat(entry.total_revenue));
    
    // Platform data might be empty if the shop earned money but fees were 0, so we map safely
    const platformData = platformRawData.slice().reverse().map(entry => parseFloat(entry.total_revenue || 0));

    // 3. Build Chart
    new Chart(ctx, {
        type: 'bar',
        data: {
            labels: labels,
            datasets: [
                {
                    label: 'Platform Share (₹)',
                    data: platformData,
                    backgroundColor: '#007BFF', // MyPrints Blue
                    borderRadius: { topLeft: 4, topRight: 4, bottomLeft: 0, bottomRight: 0 }
                },
                {
                    label: "Shop's Share (₹)",
                    data: shopData,
                    backgroundColor: '#cbd5e1', // Slate Gray
                    borderRadius: { topLeft: 0, topRight: 0, bottomLeft: 4, bottomRight: 4 }
                }
            ]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            scales: {
                x: { stacked: true },
                y: { 
                    stacked: true,
                    beginAtZero: true,
                    ticks: { callback: function(value) { return '₹' + value; } }
                }
            },
            plugins: {
                tooltip: {
                    callbacks: {
                        label: function(context) { return context.dataset.label + ': ₹' + context.parsed.y.toFixed(2); }
                    }
                }
            }
        }
    });
});