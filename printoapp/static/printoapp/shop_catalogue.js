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