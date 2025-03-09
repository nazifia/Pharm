class OfflineFormHandler {
    static async handleSubmit(form, actionType) {
        const formData = new FormData(form);
        const data = Object.fromEntries(formData.entries());
        const successUrl = form.dataset.successUrl;
        
        try {
            if (navigator.onLine) {
                // Online submission
                const response = await fetch(form.action, {
                    method: form.method,
                    body: JSON.stringify(data),
                    headers: {
                        'Content-Type': 'application/json',
                        'X-CSRFToken': document.querySelector('[name=csrfmiddlewaretoken]').value
                    }
                });
                
                if (!response.ok) {
                    throw new Error(`Server returned ${response.status}`);
                }
                
                if (successUrl) {
                    window.location.href = successUrl;
                }
                return true;
            } else {
                // Offline submission
                await window.offlineUtils.saveOfflineAction(actionType, data);
                form.reset();
                
                // Show offline success message
                const offlineMsg = document.createElement('div');
                offlineMsg.className = 'alert alert-info mt-3';
                offlineMsg.textContent = 'Data saved offline. Will sync when online.';
                form.appendChild(offlineMsg);
                
                setTimeout(() => offlineMsg.remove(), 3000);
                return true;
            }
        } catch (error) {
            console.error('Form submission error:', error);
            
            // Show error message
            const errorMsg = document.createElement('div');
            errorMsg.className = 'alert alert-danger mt-3';
            errorMsg.textContent = 'Error submitting form. Please try again.';
            form.appendChild(errorMsg);
            
            setTimeout(() => errorMsg.remove(), 3000);
            return false;
        }
    }
}

// Initialize all offline-enabled forms
document.addEventListener('DOMContentLoaded', () => {
    const offlineForms = document.querySelectorAll('form[data-offline]');
    
    offlineForms.forEach(form => {
        form.addEventListener('submit', async (e) => {
            e.preventDefault();
            const actionType = form.dataset.offlineAction;
            await OfflineFormHandler.handleSubmit(form, actionType);
        });
    });
});
