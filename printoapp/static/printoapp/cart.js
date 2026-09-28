document.addEventListener('DOMContentLoaded', function() {
    const payBtn = document.getElementById('pay_btn');
    const queue_number = document.querySelector('#queue_number')
    const priority_queue_number = document.querySelector('#priority_queue_number')
    if (queue_number) {
        const shopId = document.querySelector('#shop_id').value;
        const csrfToken = document.querySelector('[name=csrfmiddlewaretoken]').value;

        const updateQueue = () => {
            fetch(`/api/queue_size`, {
                method: 'POST',
                headers: {
                    'X-CSRFToken': csrfToken,
                    'Content-Type': 'application/json',
                    'type': 'cart'
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

        // Refresh every 10 seconds
        setInterval(updateQueue, 10000);
    }

    if (payBtn) {
        payBtn.addEventListener('click', function(e) {
            e.preventDefault();

            // Grab IDs
            const csrfToken = document.querySelector('[name=csrfmiddlewaretoken]').value;

            // Fetch fresh order details
            fetch(`/initiate-payment`, {
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

    // Page navigation buttons inside the preview modal
    const pdfPrevBtn = document.getElementById('pdfPrevPage');
    const pdfNextBtn = document.getElementById('pdfNextPage');
    if (pdfPrevBtn) pdfPrevBtn.addEventListener('click', goToPrevPage);
    if (pdfNextBtn) pdfNextBtn.addEventListener('click', goToNextPage);

    // Keep the rendered page correctly fitted if the viewport is resized
    // (e.g. rotating a phone) while the preview is open
    let resizeTimer = null;
    window.addEventListener('resize', function() {
        if (!pdfModal || pdfModal.style.display !== 'flex') return;
        clearTimeout(resizeTimer);
        resizeTimer = setTimeout(renderCurrentPage, 150);
    });
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
// PDF PREVIEW — canvas rendering, page-by-page, scaled exactly like the print
// ---------------------------------------------------------------------------
// Why not just embed the PDF in an <iframe>? Browsers render PDFs with their
// own viewer chrome, continuous-scroll gaps between pages, and native zoom —
// none of which reflects what actually comes out of the printer. Rendering
// each page to a <canvas> ourselves lets us reproduce the real print
// behaviour: one physical sheet at a time, scaled-to-fit onto the A4 frame
// (with genuine white margins where the page doesn't fill the sheet), in the
// correct orientation and color mode.

// pdf.js worker — must be set before the first getDocument() call
if (window.pdfjsLib) {
    pdfjsLib.GlobalWorkerOptions.workerSrc =
        'https://cdnjs.cloudflare.com/ajax/libs/pdf.js/3.11.174/pdf.worker.min.js';
}

// Global in-memory caches, keyed by item id
const previewCache = {};   // itemId → signed URL
const pdfDocCache  = {};   // itemId → loaded pdfjs document

// State for whichever preview is currently open
const previewState = {
    itemId: null,
    pdfDoc: null,
    currentPage: 1,
    numPages: 1,
    isColor: true
};

/**
 * Normalise the truthy/falsy values Django templates emit as strings.
 * Handles: true, false, "True", "False", "true", "false", 1, 0
 */
function parseBool(val) {
    if (typeof val === 'boolean') return val;
    return String(val).toLowerCase() === 'true';
}

async function handlePreviewClick(itemId, fileName, isColor, requiresScaling, isPortrait) {
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

    await openPdfPreview(
        itemId,
        previewCache[itemId],
        fileName,
        parseBool(isColor),
        parseBool(requiresScaling),
        parseBool(isPortrait)
    );
}

async function openPdfPreview(itemId, url, fileName, isColor, requiresScaling, isPortrait) {
    const modal      = document.getElementById('pdfPreviewModal');
    const card       = document.getElementById('pdfPreviewCard');
    const paperWrap  = document.getElementById('previewPaperWrap');
    const titleEl    = document.getElementById('previewModalTitle');
    const scaleBadge = document.getElementById('previewScaleBadge');
    const colorBadge = document.getElementById('previewColorBadge');
    const spinner    = document.getElementById('pdfLoadingSpinner');

    titleEl.textContent = fileName;
    scaleBadge.style.display = requiresScaling ? 'inline-flex' : 'none';
    colorBadge.textContent   = isColor ? '🎨 Color' : '⬛ B&W';

    card.classList.toggle('pdf-modal--portrait', isPortrait);
    card.classList.toggle('pdf-modal--landscape', !isPortrait);
    paperWrap.style.paddingBottom = isPortrait ? '141.42%' : '70.71%';

    modal.style.display = 'flex';
    document.body.style.overflow = 'hidden';

    previewState.itemId = itemId;
    previewState.isColor = isColor;
    previewState.isPortrait = isPortrait; 
    previewState.currentPage = 1;

    if (!window.pdfjsLib) {
        alert("Preview engine failed to load — check your connection and try again.");
        return;
    }

    try {
        spinner.style.display = 'flex';
        let pdfDoc = pdfDocCache[itemId];
        
        if (!pdfDoc) {
            let targetUrl = url;
            if (url.startsWith('/')) {
                targetUrl = window.location.origin + url;
            }
            
            // ── MOBILE COMPLIANCE BYPASS ──
            // Instead of passing the URL directly to the worker thread (which mobile blocks),
            // fetch the raw binary buffer directly in the stable main window thread first!
            const response = await fetch(targetUrl);
            if (!response.ok) throw new Error("Network response was not ok: " + response.status);
            
            const arrayBuffer = await response.arrayBuffer();
            
            // Feed the direct, raw binary data array straight to the PDF engine
            pdfDoc = await pdfjsLib.getDocument({ data: arrayBuffer }).promise;
            pdfDocCache[itemId] = pdfDoc;
        }
        
        previewState.pdfDoc = pdfDoc;
        previewState.numPages = pdfDoc.numPages;
        await renderCurrentPage();
        
    } catch (err) {
        console.error("PDF Preview System Error Log:", err);
        alert("Could not load preview file payload. Please check file formatting.");
    } finally {
        spinner.style.display = 'none';
    }
}

async function renderCurrentPage() {
    const { pdfDoc, currentPage, isColor, isPortrait } = previewState;
    if (!pdfDoc) return;

    const stage  = document.querySelector('#previewPaperWrap .pdf-page-stage');
    const canvas = document.getElementById('pdfPreviewCanvas');
    const ctx    = canvas.getContext('2d');

    // MOBILE RUNTIME SAFEGUARD: If the layout is still transitioning, yield briefly
    let stageRect = stage.getBoundingClientRect();
    if (!stageRect.width || stageRect.width === 0) {
        await new Promise(resolve => setTimeout(resolve, 60));
        stageRect = stage.getBoundingClientRect();
    }

    const page = await pdfDoc.getPage(currentPage);
    
    // 1. Read native viewport size, factoring in the PDF's internal rotation tag
    let baseViewport = page.getViewport({ scale: 1 });
    if (page.rotate === 90 || page.rotate === 270) {
        baseViewport = page.getViewport({ scale: 1, rotation: page.rotate });
    }

    // 1b. Only spin the content when a tall/portrait page is being printed onto a
    // landscape sheet — that's the one case where it needs to rotate to fill the
    // sheet. A wide/landscape page assigned to a portrait sheet should just shrink
    // to fit as-is, not be forced to rotate.
    const contentIsPortrait = baseViewport.height >= baseViewport.width;
    const needsExtraSpin = contentIsPortrait && !isPortrait;
    const totalRotation = (page.rotate + (needsExtraSpin ? 90 : 0)) % 360;
    if (needsExtraSpin) {
        baseViewport = page.getViewport({ scale: 1, rotation: totalRotation });
    }

    // 2. MATCHES PYTHON: Derive the target print sheet dimensions directly from state properties[cite: 5]
    const targetW = stageRect.width || 280;
    const targetH = stageRect.height || (isPortrait ? targetW * 1.4142 : targetW / 1.4142);
    const dpr = window.devicePixelRatio || 1;

    // 3. MATCHES PYTHON: Compute scale limits to center it onto the blank canvas[cite: 5]
    const fitScale = Math.min(targetW / baseViewport.width, targetH / baseViewport.height);

    // 4. Generate final viewport frame, including the extra spin from step 1b
    const renderViewport = page.getViewport({ 
        scale: fitScale * dpr, 
        rotation: totalRotation 
    });

    canvas.width  = renderViewport.width;
    canvas.height = renderViewport.height;
    
    const displayW = renderViewport.width / dpr;
    const displayH = renderViewport.height / dpr;
    
    canvas.style.width  = `${displayW}px`;
    canvas.style.height = `${displayH}px`;

    // 5. MATCHES PYTHON: Position absolute center relative offsets exactly like the backend[cite: 5]
    canvas.style.position = 'absolute';
    canvas.style.left = `${(targetW - displayW) / 2}px`;
    canvas.style.top = `${(targetH - displayH) / 2}px`;

    canvas.style.filter = isColor ? 'none' : 'grayscale(100%) contrast(110%)';

    ctx.clearRect(0, 0, canvas.width, canvas.height);

    await page.render({ canvasContext: ctx, viewport: renderViewport }).promise;

    updatePageNav();
}

function updatePageNav() {
    const indicator = document.getElementById('pdfPageIndicator');
    const prevBtn    = document.getElementById('pdfPrevPage');
    const nextBtn    = document.getElementById('pdfNextPage');
    const navBar     = document.getElementById('pdfPageNav');
    if (!indicator || !prevBtn || !nextBtn || !navBar) return;

    indicator.textContent = `Page ${previewState.currentPage} of ${previewState.numPages}`;
    prevBtn.disabled = previewState.currentPage <= 1;
    nextBtn.disabled = previewState.currentPage >= previewState.numPages;
    // Only show page controls when there's more than one sheet to flip through
    navBar.style.display = previewState.numPages > 1 ? 'flex' : 'none';
}

function goToPrevPage() {
    if (previewState.currentPage > 1) {
        previewState.currentPage -= 1;
        renderCurrentPage();
    }
}

function goToNextPage() {
    if (previewState.currentPage < previewState.numPages) {
        previewState.currentPage += 1;
        renderCurrentPage();
    }
}

function closePdfPreview() {
    const modal = document.getElementById('pdfPreviewModal');
    modal.style.display = 'none';
    document.body.style.overflow = 'auto';
    previewState.itemId = null;
    previewState.pdfDoc = null;
}