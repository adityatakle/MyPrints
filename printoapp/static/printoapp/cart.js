document.addEventListener('DOMContentLoaded', function() {
    const payBtn = document.getElementById('pay_btn');
    const queue_number = document.querySelector('#queue_number')
    const priority_queue_number = document.querySelector('#priority_queue_number')
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
                priority_queue_number.innerHTML = result.priority_queue_size;
            })
            .catch(err => console.log("Queue update paused..."));
        };

        updateQueue();

        // Refresh every 7 seconds
        setInterval(updateQueue, 7000);
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
                    "name": "Curio Labs",
                    "description": "Order #" + data.order_id,
                    "order_id": data.order_id,
                    "callback_url": document.querySelector('#status_url').value
                };

                const rzp = new Razorpay(options);

                // Catch any modal-load failures
                rzp.on('payment.failed', function (response) {
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

    // ── PDF preview modal: close when clicking the dark backdrop ──
    // We scope this to pdfPreviewModal only so it doesn't conflict with edit modals
    const pdfModal = document.getElementById('pdfPreviewModal');
    if (pdfModal) {
        pdfModal.addEventListener('click', function(e) {
            if (e.target === pdfModal) {
                closePdfPreview();
            }
        });
    }
});

// ---------------------------------------------------------------------------
// EDIT MODALS
// ---------------------------------------------------------------------------

function openEditModal(itemId) {
    document.getElementById(`modal-${itemId}`).style.display = 'flex';
    document.body.style.overflow = 'hidden';
}

function closeEditModal(itemId) {
    document.getElementById(`modal-${itemId}`).style.display = 'none';
    document.body.style.overflow = 'auto';
}

// Close edit modals when clicking outside the card.
// Explicitly excludes pdfPreviewModal so the two systems don't clash.
window.addEventListener('click', function(event) {
    const target = event.target;
    if (
        target.classList.contains('ct-modal-overlay') &&
        target.id !== 'pdfPreviewModal'
    ) {
        target.style.display = 'none';
        document.body.style.overflow = 'auto';
    }
});

// Copy the namespaced radio values into the shared hidden inputs before submit
function applyEditSettings(itemId) {
    // 1. Update Side Setting (if the element exists for this item)
    const sideSelected = document.querySelector(`input[name="side-${itemId}"]:checked`);
    if (sideSelected && document.getElementById(`side-hidden-${itemId}`)) {
        document.getElementById(`side-hidden-${itemId}`).value = sideSelected.value;
    }

    // 2. Update Orientation Setting
    const portraitSelected = document.querySelector(`input[name="portrait-${itemId}"]:checked`);
    if (portraitSelected && document.getElementById(`portrait-hidden-${itemId}`)) {
        document.getElementById(`portrait-hidden-${itemId}`).value = portraitSelected.value;
    }
}

// ---------------------------------------------------------------------------
// PDF PREVIEW
// ---------------------------------------------------------------------------

// Global in-memory cache: itemId → signed URL
const previewCache = {};

/**
 * Normalise the truthy/falsy values Django templates emit as strings.
 * Handles: true, false, "True", "False", "true", "false", 1, 0
 */
function parseBool(val) {
    if (typeof val === 'boolean') return val;
    return String(val).toLowerCase() === 'true';
}

async function handlePreviewClick(itemId, fileName, isColor, requiresScaling) {
    // Fetch presigned URL from API if not already cached
    if (!previewCache[itemId]) {
        try {
            const csrfToken = document.querySelector('[name=csrfmiddlewaretoken]').value;
            const response = await fetch(`/api/create_preview_link/${itemId}`, {
                method: 'POST',
                headers: { 'X-CSRFToken': csrfToken }
            });
            const data = await response.json();

            if (data.file_url) {
                previewCache[itemId] = data.file_url;
            } else {
                alert("Could not load preview.");
                return;
            }
        } catch (err) {
            alert("Could not load preview.");
            return;
        }
    }

    renderPdfPreview(
        previewCache[itemId],
        fileName,
        parseBool(isColor),
        parseBool(requiresScaling)
    );
}

function renderPdfPreview(url, fileName, isColor, requiresScaling) {
    const modal      = document.getElementById('pdfPreviewModal');
    const iframe     = document.getElementById('pdfPreviewIframe');
    const titleEl    = document.getElementById('previewModalTitle');
    const scaleBadge = document.getElementById('previewScaleBadge');
    const colorBadge = document.getElementById('previewColorBadge');

    // 1. Title
    titleEl.textContent = fileName;

    // 2. Badges
    scaleBadge.style.display = requiresScaling ? 'inline-flex' : 'none';
    colorBadge.textContent   = isColor ? '🎨 Color' : '⬛ B&W';

    // 3. Grayscale simulation for B&W prints
    iframe.style.filter = isColor ? 'none' : 'grayscale(100%) contrast(110%)';

    // 4. Load PDF — assign the presigned URL directly (never via Django template
    //    attribute) so the query-string signature is never HTML-escaped to &amp;
    //    FitH  → fit page width to the iframe width (no horizontal scroll)
    //    toolbar/navpanes/scrollbar=0 → hide browser chrome
    iframe.src = `${url}#toolbar=0&navpanes=0&scrollbar=0&view=FitH`;

    // 5. Show modal
    modal.style.display = 'flex';
    document.body.style.overflow = 'hidden';
}

/**
 * closePdfPreview — was missing from the original file, which caused:
 *   • the ✕ button to do nothing (ReferenceError in console)
 *   • the iframe to keep a stale/broken src on next open, which
 *     caused S3 to reject the already-consumed or malformed signature
 */
function closePdfPreview() {
    const modal  = document.getElementById('pdfPreviewModal');
    const iframe = document.getElementById('pdfPreviewIframe');

    modal.style.display = 'none';
    document.body.style.overflow = 'auto';

    // Reset src so the browser stops streaming and the next open starts clean
    iframe.src = '';
}