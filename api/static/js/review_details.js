document.addEventListener('DOMContentLoaded', function() {
    // This script handles enabling the approve button for FACE_ONLY reviews when a match is selected.
    // It runs on all detail pages, but the relevant elements only exist for FACE_ONLY.
    
    const approveButton = document.getElementById('face-only-approve-button');
    const hiddenInput = document.getElementById('selected-employee-id');
    const radioButtons = document.querySelectorAll('.match-radio');

    // Check if the necessary elements for Face-Only review exist on this page
    if (approveButton && hiddenInput && radioButtons.length > 0) {
        radioButtons.forEach(radio => {
            radio.addEventListener('change', function() {
                // Enable button and set value only if a radio is checked
                if (this.checked) {
                    approveButton.disabled = false;
                    hiddenInput.value = this.value;
                }
            });
        });
    } 
    // No 'else' needed - if elements don't exist, script does nothing.
});
