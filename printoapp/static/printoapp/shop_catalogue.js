(function () {
    const modal       = document.getElementById('scModal');
    const modalLabel  = document.getElementById('scModalLabel');
    const modalTitle  = document.getElementById('scModalTitle');
    const itemIdInput = document.getElementById('scItemId');
    const actionInput = document.getElementById('scModalAction');
    const closeBtn    = document.getElementById('scModalClose');
    const cancelBtn   = document.getElementById('scModalCancel');
    const saveBtn     = document.getElementById('scSaveBtn');
    const priceInput  = document.getElementById('scPrice');
    const priceError  = document.getElementById('scPriceError');
    const pageType    = document.getElementById('scPageType');
    const isColor     = document.getElementById('scIsColor');
    const isB2b       = document.getElementById('scIsB2b');

    function openModal(opts) {
        // opts: { label, action, itemId, pageType, price, color, b2b }
        modalLabel.textContent      = opts.label || 'New Service';
        modalTitle.textContent      = 'Configure Printing Service';
        itemIdInput.value           = opts.itemId  || '';
        actionInput.value           = opts.action  || 'Add';
        saveBtn.querySelector('.scm-save-text').textContent =
            opts.action === 'edit' ? 'Save Changes' : 'Add to Catalogue';

        // pre-fill fields
        pageType.value   = opts.pageType || '';
        priceInput.value = opts.price    || '';
        isColor.checked  = opts.color    || false;
        isB2b.checked    = opts.b2b      || false;

        // reset error state
        priceInput.classList.remove('scm-price-input--error');
        priceError.style.display = 'none';

        modal.classList.add('scm-overlay--open');
        document.body.style.overflow = 'hidden';
        priceInput.focus();
    }

    function closeModal() {
        modal.classList.remove('scm-overlay--open');
        document.body.style.overflow = '';
    }

    // ── New Item button ──
    document.querySelectorAll('.new_btn').forEach(btn => {
        btn.addEventListener('click', function (e) {
            e.preventDefault();
            openModal({ label: 'New Service', action: 'Add' });
        });
    });

    // ── Edit buttons — data-* attrs carry values from Django ──
    document.querySelectorAll('.edit_btn').forEach(btn => {
        btn.addEventListener('click', function (e) {
            e.preventDefault();
            openModal({
                label:    'Edit Service',
                action:   'Edit',
                itemId:   this.value,
                pageType: this.dataset.pagetype || '',
                price:    this.dataset.price    || '',
                color:    this.dataset.color    === 'True',
                b2b:      this.dataset.b2b      === 'True',
            });
        });
    });

    // ── Close triggers ──
    closeBtn.addEventListener('click', closeModal);
    cancelBtn.addEventListener('click', closeModal);
    modal.addEventListener('click', function (e) {
        if (e.target === modal) closeModal();
    });
    document.addEventListener('keydown', function (e) {
        if (e.key === 'Escape') closeModal();
    });

    // ── Client-side price validation ──
    document.getElementById('scModalForm').addEventListener('submit', function (e) {
        if (!priceInput.value || parseFloat(priceInput.value) <= 0) {
            e.preventDefault();
            priceInput.classList.add('scm-price-input--error');
            priceError.style.display = 'block';
            priceInput.focus();
            return;
        }
        saveBtn.classList.add('scm-save-btn--loading');
        saveBtn.disabled = true;
    });

    priceInput.addEventListener('input', function () {
        if (this.value) {
            this.classList.remove('scm-price-input--error');
            priceError.style.display = 'none';
        }
    });
})();

// Logic for Weekday Update
(function () {
    const scheduleForm = document.getElementById('scScheduleForm');
    const openDaysInput = document.getElementById('scOpenDaysValue');
    const scheduleBtn = document.getElementById('scScheduleBtn');

    if (scheduleForm) {
        scheduleForm.addEventListener('submit', function (e) {
            // Collect all checked days as a string (e.g., "1,2,3,4,5")
            const selected = Array.from(document.querySelectorAll('.sc-day-cb:checked'))
                                  .map(cb => cb.value)
                                  .join('');
            
            openDaysInput.value = selected;
            
            // Re-use your existing loading state styles
            scheduleBtn.innerHTML = '<span class="scm-save-spinner" style="display:block; margin:0"></span>';
            scheduleBtn.disabled = true;
        });
    }
})();

// --- TIMING MODAL LOGIC ---
const tModal = document.getElementById('timingModal');
const tId = document.getElementById('t_id');
const tReqType = document.getElementById('t_request_type');
const tWeekday = document.getElementById('t_weekday');
const tStart = document.getElementById('t_start');
const tEnd = document.getElementById('t_end');

function openTimingModal(edit = false, data = {}) {
    tReqType.value = edit ? "Update_timing" : "Add_timing";
    tId.value = data.id || "";
    tWeekday.value = data.day || "Monday";
    tStart.value = data.start || "09:00";
    tEnd.value = data.end || "21:00";
    
    tModal.classList.add('scm-overlay--open');
}

document.getElementById('newTimingBtn').addEventListener('click', () => openTimingModal());

document.querySelectorAll('.timing-edit-btn').forEach(btn => {
    btn.addEventListener('click', function() {
        openTimingModal(true, {
            id: this.value,
            day: this.dataset.day,
            start: this.dataset.start,
            end: this.dataset.end
        });
    });
});

document.getElementById('closeTimingModal').onclick = () => tModal.classList.remove('scm-overlay--open');
document.getElementById('cancelTimingModal').onclick = () => tModal.classList.remove('scm-overlay--open');

/**
 * Global helper for handling deletions with confirmation.
 * @param {string} id - The ID of the item/timing to delete.
 * @param {string} type - The request_type (Delete_catalogue or Delete_timing).
 */
function handleDelete(id, type) {
    const message = type === 'Delete_timing' 
        ? "Remove these hours from your schedule?" 
        : "Delete this service from your catalogue?";

    if (confirm(message)) {
        // Create a temporary form to submit the delete request
        const form = document.createElement('form');
        form.method = 'POST';
        form.action = ''; // Current URL

        const csrf = document.querySelector('[name=csrfmiddlewaretoken]').value;
        
        form.innerHTML = `
            <input type="hidden" name="csrfmiddlewaretoken" value="${csrf}">
            <input type="hidden" name="request_type" value="${type}">
            <input type="hidden" name="item_id" value="${id}">
            <input type="hidden" name="timing_id" value="${id}">
        `;

        document.body.appendChild(form);
        form.submit();
    }
}