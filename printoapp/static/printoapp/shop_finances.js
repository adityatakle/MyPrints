document.addEventListener("DOMContentLoaded", function() {
    
    const dayPicker = document.getElementById("dayPicker");
    const dayForm = document.getElementById("dayForm");
    
    const monthPicker = document.getElementById("monthPicker");
    const monthForm = document.getElementById("monthForm");

    // Auto-submit the day form when a new date is selected
    if (dayPicker && dayForm) {
        dayPicker.addEventListener("change", function() {
            dayForm.submit();
        });
    }

    // Auto-submit the month form when a new month is selected from the dropdown
    if (monthPicker && monthForm) {
        monthPicker.addEventListener("change", function() {
            monthForm.submit();
        });
    }
});