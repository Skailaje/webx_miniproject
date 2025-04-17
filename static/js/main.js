// Socket.IO connection
const socket = io();

// Handle real-time updates
socket.on('booking_update', function(data) {
    showNotification('New booking update received', 'info');
});

// Show notification
function showNotification(message, type = 'info') {
    const alertDiv = document.createElement('div');
    alertDiv.className = `alert alert-${type} alert-dismissible fade show`;
    alertDiv.role = 'alert';
    alertDiv.innerHTML = `
        ${message}
        <button type="button" class="btn-close" data-bs-dismiss="alert" aria-label="Close"></button>
    `;
    
    const container = document.querySelector('.container');
    container.insertBefore(alertDiv, container.firstChild);
    
    // Auto-dismiss after 5 seconds
    setTimeout(() => {
        alertDiv.remove();
    }, 5000);
}

// Form validation
document.addEventListener('DOMContentLoaded', function() {
    const forms = document.querySelectorAll('form');
    
    forms.forEach(form => {
        form.addEventListener('submit', function(event) {
            if (!form.checkValidity()) {
                event.preventDefault();
                event.stopPropagation();
            }
            form.classList.add('was-validated');
        });
    });
    
    // Time validation for booking form
    const bookingForm = document.querySelector('form[action="{{ url_for(\'book\') }}"]');
    if (bookingForm) {
        const startTime = document.getElementById('start_time');
        const endTime = document.getElementById('end_time');
        
        endTime.addEventListener('change', function() {
            if (startTime.value && endTime.value) {
                if (endTime.value <= startTime.value) {
                    endTime.setCustomValidity('End time must be after start time');
                } else {
                    endTime.setCustomValidity('');
                }
            }
        });
    }
}); 