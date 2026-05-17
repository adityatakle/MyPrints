document.addEventListener('DOMContentLoaded', function() {
    const tabBtns = document.querySelectorAll('.tab-btn');
    const tabContents = document.querySelectorAll('.tab-content');

    // 1. Check if a tab was previously saved in sessionStorage
    const savedTab = sessionStorage.getItem('activeSettingsTab');
    
    if (savedTab) {
        // Remove default active classes
        tabBtns.forEach(b => b.classList.remove('active'));
        tabContents.forEach(c => c.classList.remove('active'));
        
        // Apply saved active classes
        const targetBtn = document.querySelector(`.tab-btn[data-target="${savedTab}"]`);
        const targetContent = document.getElementById(savedTab);
        
        if (targetBtn && targetContent) {
            targetBtn.classList.add('active');
            targetContent.classList.add('active');
        }
    }

    // 2. Handle Tab Clicks
    tabBtns.forEach(btn => {
        btn.addEventListener('click', () => {
            // Remove active from all
            tabBtns.forEach(b => b.classList.remove('active'));
            tabContents.forEach(c => c.classList.remove('active'));

            // Add active to clicked
            btn.classList.add('active');
            const targetId = btn.getAttribute('data-target');
            document.getElementById(targetId).classList.add('active');

            // Save state so page reloads land on the correct tab
            sessionStorage.setItem('activeSettingsTab', targetId);
        });
    });

    // 3. Update tab state immediately before a form submits
    // This ensures if a user hits "Enter" to submit, the tab is saved.
    const forms = document.querySelectorAll('form');
    forms.forEach(form => {
        form.addEventListener('submit', function() {
            const activeTab = document.querySelector('.tab-content.active');
            if (activeTab) {
                sessionStorage.setItem('activeSettingsTab', activeTab.id);
            }
        });
    });
});