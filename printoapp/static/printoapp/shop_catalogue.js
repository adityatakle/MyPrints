/**
 * MyPrints Shop Catalogue & Schedule Logic
 * Handles adding/editing printing services, managing business hours, and form validations.
 */

document.addEventListener('DOMContentLoaded', function() {
    
    // ==========================================
    // 1. CATALOGUE MODAL EVENT LISTENERS
    // ==========================================
    
    // Trigger: Add New Service
    document.querySelectorAll('.new_btn').forEach(btn => {
        btn.addEventListener('click', function (e) {
            e.preventDefault();
            openNewCatalogueModal();
        });
    });

    // Trigger: Edit Existing Service
    document.querySelectorAll('.edit_btn').forEach(btn => {
        btn.addEventListener('click', function (e) {
            e.preventDefault();
            // Pull data from the button's data attributes
            const id = this.value;
            const pageType = this.dataset.pagetype;
            const price = this.dataset.price;
            const isColor = this.dataset.color;
            const isB2b = this.dataset.b2b;
            
            openEditCatalogueModal(id, pageType, price, isColor, isB2b);
        });
    });

    // Trigger: Close Catalogue Modal
    const scModal = document.getElementById('scModal');
    if (document.getElementById('scModalClose')) {
        document.getElementById('scModalClose').addEventListener('click', closeCatalogueModal);
    }
    if (document.getElementById('scModalCancel')) {
        document.getElementById('scModalCancel').addEventListener('click', closeCatalogueModal);
    }
    if (scModal) {
        scModal.addEventListener('click', function (e) {
            if (e.target === scModal) closeCatalogueModal(); // Close if clicking overlay
        });
    }

    // Validation: Prevent 0 or empty price submissions
    const scModalForm = document.getElementById('scModalForm');
    const priceInput = document.getElementById('scPrice');
    const priceError = document.getElementById('scPriceError');
    const saveBtn = document.getElementById('scSaveBtn');

    if (scModalForm) {
        scModalForm.addEventListener('submit', function (e) {
            if (!priceInput.value || parseFloat(priceInput.value) <= 0) {
                e.preventDefault(); // Stop submission
                priceInput.classList.add('scm-price-input--error');
                priceError.style.display = 'block';
                priceInput.focus();
                return;
            }
            // Show loading spinner on save button
            saveBtn.classList.add('scm-save-btn--loading');
            saveBtn.disabled = true;
        });
    }

    // Validation: Hide error when typing a new price
    if (priceInput) {
        priceInput.addEventListener('input', function () {
            if (this.value) {
                this.classList.remove('scm-price-input--error');
                priceError.style.display = 'none';
            }
        });
    }

    // ==========================================
    // 2. TIMING MODAL EVENT LISTENERS
    // ==========================================
    
    // Trigger: Add New Timing
    if (document.getElementById('newTimingBtn')) {
        document.getElementById('newTimingBtn').addEventListener('click', function(e) {
            e.preventDefault();
            openNewTimingModal();
        });
    }

    // Trigger: Edit Existing Timing
    document.querySelectorAll('.timing-edit-btn').forEach(btn => {
        btn.addEventListener('click', function() {
            const id = this.value;
            const day = this.dataset.day;
            const start = this.dataset.start;
            const end = this.dataset.end;
            
            openEditTimingModal(id, day, start, end);
        });
    });

    // Trigger: Close Timing Modal
    const tModal = document.getElementById('timingModal');
    if (document.getElementById('closeTimingModal')) {
        document.getElementById('closeTimingModal').addEventListener('click', closeTimingModal);
    }
    if (document.getElementById('cancelTimingModal')) {
        document.getElementById('cancelTimingModal').addEventListener('click', closeTimingModal);
    }
    if (tModal) {
        tModal.addEventListener('click', function(e) {
            if (e.target === tModal) closeTimingModal();
        });
    }

    // ==========================================
    // 3. GLOBAL LISTENERS
    // ==========================================
    
    // Close any open modal on ESC key
    document.addEventListener('keydown', function (e) {
        if (e.key === 'Escape') {
            closeCatalogueModal();
            closeTimingModal();
        }
    });
    // Inside DOMContentLoaded:

    // 1. Modal Toggle
    const cModal = document.getElementById('couponModal');
    const newCouponBtn = document.getElementById('newCouponBtn');
    const closeCouponModal = document.getElementById('closeCouponModal');
    const cancelCouponModal = document.getElementById('cancelCouponModal');

    if(newCouponBtn) {
        newCouponBtn.addEventListener('click', () => {
            cModal.classList.add('scm-overlay--open');
            document.body.style.overflow = 'hidden';
        });
    }

    const closeC = () => {
        cModal.classList.remove('scm-overlay--open');
        document.body.style.overflow = 'auto';
    };
    if(closeCouponModal) closeCouponModal.addEventListener('click', closeC);
    if(cancelCouponModal) cancelCouponModal.addEventListener('click', closeC);

    // 2. Exclusivity Logic: Max Use vs Days Valid
    const maxUseInput = document.getElementById('c_max_use');
    const daysValidInput = document.getElementById('c_days_valid');

    if(maxUseInput && daysValidInput) {
        maxUseInput.addEventListener('input', function() {
            if (this.value) {
                daysValidInput.value = "";
                daysValidInput.disabled = true;
                daysValidInput.style.opacity = "0.5";
            } else {
                daysValidInput.disabled = false;
                daysValidInput.style.opacity = "1";
            }
        });

        daysValidInput.addEventListener('input', function() {
            if (this.value) {
                maxUseInput.value = "";
                maxUseInput.disabled = true;
                maxUseInput.style.opacity = "0.5";
            } else {
                maxUseInput.disabled = false;
                maxUseInput.style.opacity = "1";
            }
        });
    }
    // Inside your DOMContentLoaded block
    const couponCodeInput = document.querySelector('input[name="code"]');

    if (couponCodeInput) {
        couponCodeInput.addEventListener('input', function() {
            // Force uppercase and remove any spaces while typing
            this.value = this.value.toUpperCase().replace(/\s/g, '');
        });
    }
});


/**
 * ==========================================
 * GLOBAL FUNCTIONS: CATALOGUE MODAL
 * ==========================================
 */

function openNewCatalogueModal() {
    // 1. Set text to 'Add' mode
    document.getElementById('scModalLabel').textContent = 'New Service';
    document.getElementById('scModalAction').value = 'Add_catalogue';
    document.querySelector('#scSaveBtn .scm-save-text').textContent = 'Add to Catalogue';

    // 2. Clear all previous inputs
    document.getElementById('scItemId').value = '';
    document.getElementById('scPageType').value = '';
    document.getElementById('scPrice').value = '';
    document.getElementById('scIsColor').checked = false;
    document.getElementById('scIsB2b').checked = false;

    // 3. Reset any error states
    document.getElementById('scPrice').classList.remove('scm-price-input--error');
    document.getElementById('scPriceError').style.display = 'none';

    // 4. Ensure inputs are unlocked (in case user clicked edit previously)
    unlockCatalogueFields();

    // 5. Open modal and prevent background scrolling
    document.getElementById('scModal').classList.add('scm-overlay--open');
    document.body.style.overflow = 'hidden';
    document.getElementById('scPrice').focus();
}

function openEditCatalogueModal(id, pageType, price, isColor, isB2b) {
    // 1. Set text to 'Edit' mode
    document.getElementById('scModalLabel').textContent = 'Edit Service';
    document.getElementById('scModalAction').value = 'Update_catalogue';
    document.querySelector('#scSaveBtn .scm-save-text').textContent = 'Save Changes';

    // 2. Pre-fill inputs with existing database data
    document.getElementById('scItemId').value = id;
    document.getElementById('scPageType').value = pageType;
    document.getElementById('scPrice').value = price;
    document.getElementById('scIsColor').checked = (isColor === 'True');
    document.getElementById('scIsB2b').checked = (isB2b === 'True');

    // 3. Reset any error states
    document.getElementById('scPrice').classList.remove('scm-price-input--error');
    document.getElementById('scPriceError').style.display = 'none';

    // 4. Lock fields so user can only change the price
    lockCatalogueFields();

    // 5. Open modal and prevent background scrolling
    document.getElementById('scModal').classList.add('scm-overlay--open');
    document.body.style.overflow = 'hidden';
    document.getElementById('scPrice').focus();
}

function closeCatalogueModal() {
    document.getElementById('scModal').classList.remove('scm-overlay--open');
    document.body.style.overflow = 'auto'; // Restore background scrolling
}

// Visual helpers to lock/unlock fields during editing
function lockCatalogueFields() {
    const fields = ['scPageType', 'scIsColor', 'scIsB2b'];
    fields.forEach(id => {
        const wrapper = document.getElementById(id).closest('.scm-field');
        if (wrapper) {
            wrapper.style.pointerEvents = 'none';
            wrapper.style.opacity = '0.5';
        }
    });
}

function unlockCatalogueFields() {
    const fields = ['scPageType', 'scIsColor', 'scIsB2b'];
    fields.forEach(id => {
        const wrapper = document.getElementById(id).closest('.scm-field');
        if (wrapper) {
            wrapper.style.pointerEvents = 'auto';
            wrapper.style.opacity = '1';
        }
    });
}


/**
 * ==========================================
 * GLOBAL FUNCTIONS: TIMING MODAL
 * ==========================================
 */

function openNewTimingModal() {
    document.getElementById('t_request_type').value = "Add_timing";
    document.getElementById('t_id').value = "";
    
    // Set some sensible defaults
    document.getElementById('t_weekday').value = "Monday";
    document.getElementById('t_start').value = "09:00";
    document.getElementById('t_end').value = "21:00";
    
    document.getElementById('timingModal').classList.add('scm-overlay--open');
    document.body.style.overflow = 'hidden';
}

function openEditTimingModal(id, day, start, end) {
    document.getElementById('t_request_type').value = "Update_timing";
    document.getElementById('t_id').value = id;
    
    // Fill with existing data
    document.getElementById('t_weekday').value = day;
    document.getElementById('t_start').value = start;
    document.getElementById('t_end').value = end;
    
    document.getElementById('timingModal').classList.add('scm-overlay--open');
    document.body.style.overflow = 'hidden';
}

function closeTimingModal() {
    document.getElementById('timingModal').classList.remove('scm-overlay--open');
    document.body.style.overflow = 'auto';
}


/**
 * ==========================================
 * GLOBAL FUNCTIONS: DELETION
 * ==========================================
 */

function handleDelete(id, type) {
    const messages = {
        'Delete_timing': "Remove these hours?",
        'Delete_catalogue': "Delete this service?",
        'Delete_coupon': "Delete this coupon code?"
    };

    if (confirm(messages[type])) {
        const form = document.createElement('form');
        form.method = 'POST';
        const csrf = document.querySelector('[name=csrfmiddlewaretoken]').value;
        
        form.innerHTML = `
            <input type="hidden" name="csrfmiddlewaretoken" value="${csrf}">
            <input type="hidden" name="request_type" value="${type}">
            <input type="hidden" name="item_id" value="${id}">
            <input type="hidden" name="timing_id" value="${id}">
            <input type="hidden" name="coupon_id" value="${id}">
        `;
        document.body.appendChild(form);
        form.submit();
    }
}

// Add this to your shop_catalogue.js
document.querySelectorAll('input[name="expiry_type"]').forEach(radio => {
    radio.addEventListener('change', function() {
        const useWrap = document.getElementById('max_use_input_wrap');
        const daysWrap = document.getElementById('days_valid_input_wrap');
        const useInput = document.getElementById('c_max_use');
        const daysInput = document.getElementById('c_days_valid');

        if (this.value === 'max_use') {
            // Show Max Use
            useWrap.style.display = 'block';
            useInput.required = true;
            // Hide Days
            daysWrap.style.display = 'none';
            daysInput.required = false;
            daysInput.value = ""; 
        } else {
            // Show Days
            daysWrap.style.display = 'block';
            daysInput.required = true;
            // Hide Max Use
            useWrap.style.display = 'none';
            useInput.required = false;
            useInput.value = "";
        }
    });
});