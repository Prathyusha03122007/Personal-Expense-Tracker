// Custom JavaScript
document.addEventListener('DOMContentLoaded', () => {
    // Auto-dismiss success alerts after 5 seconds, keep warnings/errors until manual dismiss
    const alerts = document.querySelectorAll('.alert-success');
    alerts.forEach(alert => {
        setTimeout(() => {
            const bsAlert = new bootstrap.Alert(alert);
            bsAlert.close();
        }, 5000);
    });
});
