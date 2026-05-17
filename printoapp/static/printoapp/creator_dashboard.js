document.addEventListener('DOMContentLoaded', function() {
    const canvas = document.getElementById('revenueChart');
    if (!canvas) return; // Failsafe in case canvas isn't loaded

    const ctx = canvas.getContext('2d');
    
    // 1. Retrieve the REAL data passed by your Django view
    const rawDataElement = document.getElementById('sub-revenue-data');
    if (!rawDataElement) return;

    const rawData = JSON.parse(rawDataElement.textContent);
    
    // 2. Handle the "Zero Data" state for the SITRC Pilot
    if (rawData.length === 0) {
        ctx.font = "14px 'DM Sans', sans-serif";
        ctx.fillStyle = "#64748b"; // Slate color for empty text
        ctx.textAlign = "center";
        ctx.fillText("No subscription revenue recorded yet.", canvas.width / 2, canvas.height / 2);
        return; // Stop building the chart if there's no data
    }

    // 3. Map your real database entries into Chart.js arrays
    // We reverse it so the oldest month is on the left and newest is on the right
    const subLabels = rawData.slice().reverse().map(entry => `${entry.month}/${entry.year}`);
    const subData = rawData.slice().reverse().map(entry => parseFloat(entry.total_revenue));

    // 4. Build the Chart
    new Chart(ctx, {
        type: 'bar', // A bar chart is best for monthly revenue comparisons
        data: {
            labels: subLabels,
            datasets: [{
                label: 'Revenue (₹)',
                data: subData,
                backgroundColor: '#22d3ee', // Cyan color from your theme
                borderRadius: 4,            // Rounded tops on the bars
                borderSkipped: false
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false, // Allows it to fit your container height
            plugins: {
                legend: {
                    display: false // Hides the redundant legend
                },
                tooltip: {
                    callbacks: {
                        label: function(context) {
                            return '₹ ' + context.parsed.y.toFixed(2);
                        }
                    }
                }
            },
            scales: {
                y: { 
                    beginAtZero: true,
                    ticks: {
                        callback: function(value) {
                            return '₹' + value; // Adds the Rupee symbol to the Y-axis
                        }
                    }
                }
            }
        }
    });
});