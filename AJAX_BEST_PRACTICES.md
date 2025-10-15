# AJAX Best Practices for Pharmacy System

## Quick Reference Guide

This document provides best practices for implementing AJAX functionality in the pharmacy management system to avoid common pitfalls like duplicate messages and inconsistent behavior.

## The Golden Rule

**NEVER mix Django messages framework with AJAX/JSON responses!**

```python
# ❌ WRONG - This causes duplicate messages
messages.success(request, "Operation successful")
return JsonResponse({"success": True, "message": "Operation successful"})

# ✅ CORRECT - Check request type first
if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
    return JsonResponse({"success": True, "message": "Operation successful"})
else:
    messages.success(request, "Operation successful")
    return redirect('some_view')
```

## Backend (Django Views)

### 1. Always Detect AJAX Requests

```python
@login_required
def my_view(request):
    if request.method == "POST":
        try:
            # Your business logic here
            result = do_something()
            
            # Check if AJAX request
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                # Return JSON for AJAX
                return JsonResponse({
                    "success": True,
                    "message": "Operation completed successfully",
                    "data": result
                })
            else:
                # Return redirect with message for regular requests
                messages.success(request, "Operation completed successfully")
                return redirect('success_page')
                
        except Exception as e:
            logger.error(f"Error in my_view: {str(e)}")
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")
            
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({
                    "success": False,
                    "message": str(e)
                }, status=500)
            else:
                messages.error(request, f"Error: {str(e)}")
                return redirect('error_page')
```

### 2. Use Database Transactions for Stock Updates

```python
from django.db import transaction
from django.db.models import F

# ✅ CORRECT - Atomic and safe
with transaction.atomic():
    item.stock = F('stock') - quantity
    item.save()
    item.refresh_from_db()  # Get the updated value
    
    other_item.stock = F('stock') + quantity
    other_item.save()
    other_item.refresh_from_db()

# ❌ WRONG - Race condition possible
item.stock -= quantity
item.save()
other_item.stock += quantity
other_item.save()
```

### 3. Standard JSON Response Format

**Success Response**:
```json
{
    "success": true,
    "message": "Human-readable success message",
    "data": {
        "optional": "additional data"
    }
}
```

**Error Response**:
```json
{
    "success": false,
    "message": "Human-readable error message"
}
```

### 4. Proper Error Handling

```python
try:
    # Your code here
    pass
except ValueError as e:
    # Validation errors
    logger.error(f"Validation error: {str(e)}")
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return JsonResponse({"success": False, "message": f"Validation error: {str(e)}"}, status=400)
    else:
        messages.error(request, f"Validation error: {str(e)}")
        return redirect('error_page')
        
except Exception as e:
    # Unexpected errors
    logger.error(f"Unexpected error: {str(e)}")
    import traceback
    logger.error(f"Traceback: {traceback.format_exc()}")
    
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return JsonResponse({"success": False, "message": "An unexpected error occurred"}, status=500)
    else:
        messages.error(request, "An unexpected error occurred")
        return redirect('error_page')
```

## Frontend (JavaScript)

### 1. Always Add AJAX Header

```javascript
fetch(url, {
    method: 'POST',
    body: formData,
    headers: {
        'X-Requested-With': 'XMLHttpRequest'  // ← CRITICAL!
    }
})
```

### 2. Standard Fetch Pattern

```javascript
document.addEventListener('DOMContentLoaded', function() {
    document.querySelectorAll('.my-form').forEach(form => {
        form.addEventListener('submit', function(e) {
            e.preventDefault();
            
            const submitBtn = this.querySelector('button[type="submit"]');
            const originalText = submitBtn.innerHTML;
            
            // Show loading state
            submitBtn.disabled = true;
            submitBtn.innerHTML = '<span class="spinner-border spinner-border-sm"></span> Processing...';
            
            const formData = new FormData(this);
            
            fetch(this.action, {
                method: 'POST',
                body: formData,
                headers: {
                    'X-Requested-With': 'XMLHttpRequest'
                }
            })
            .then(response => {
                console.log('Response status:', response.status);
                if (!response.ok) {
                    throw new Error(`HTTP error! status: ${response.status}`);
                }
                return response.json();
            })
            .then(data => {
                console.log('Response data:', data);
                if (data.success) {
                    // Handle success
                    showSuccessMessage(data.message);
                } else {
                    // Handle error
                    showErrorMessage(data.message);
                }
            })
            .catch(error => {
                console.error('Error:', error);
                showErrorMessage('An error occurred. Please try again.');
            })
            .finally(() => {
                // Restore button state
                submitBtn.disabled = false;
                submitBtn.innerHTML = originalText;
            });
        });
    });
});

function showSuccessMessage(message) {
    // Display success message to user
    const alertDiv = document.createElement('div');
    alertDiv.className = 'alert alert-success';
    alertDiv.innerHTML = `<i class="fas fa-check-circle"></i> ${message}`;
    document.querySelector('.container').prepend(alertDiv);
}

function showErrorMessage(message) {
    // Display error message to user
    const alertDiv = document.createElement('div');
    alertDiv.className = 'alert alert-danger';
    alertDiv.innerHTML = `<i class="fas fa-exclamation-triangle"></i> ${message}`;
    document.querySelector('.container').prepend(alertDiv);
}
```

### 3. Handle Loading States

```javascript
// Before fetch
submitBtn.disabled = true;
submitBtn.innerHTML = '<span class="spinner-border spinner-border-sm"></span> Loading...';

// In finally block
submitBtn.disabled = false;
submitBtn.innerHTML = originalText;
```

### 4. Update UI Based on Response

```javascript
.then(data => {
    if (data.success) {
        // Update the row to show success
        rowElement.innerHTML = `
            <td>${rowElement.cells[0].textContent}</td>
            <td>
                <div class="alert alert-success mb-0">
                    <i class="fas fa-check-circle"></i> ${data.message}
                </div>
            </td>
        `;
        
        // Remove row after delay
        setTimeout(() => {
            rowElement.style.opacity = '0';
            rowElement.style.transition = 'opacity 0.5s';
            setTimeout(() => rowElement.remove(), 500);
        }, 2000);
    } else {
        // Show error in the row
        showErrorInRow(rowElement, data.message);
    }
})
```

## Common Patterns

### Pattern 1: Form Submission with AJAX

**HTML**:
```html
<form method="post" action="{% url 'my_view' %}" class="ajax-form">
    {% csrf_token %}
    <input type="text" name="field1" required>
    <button type="submit" class="btn btn-primary">
        <span class="btn-text">Submit</span>
        <span class="spinner-border spinner-border-sm d-none" role="status"></span>
    </button>
</form>
<div id="response-message"></div>
```

**JavaScript**:
```javascript
document.querySelector('.ajax-form').addEventListener('submit', function(e) {
    e.preventDefault();
    
    const formData = new FormData(this);
    const responseDiv = document.getElementById('response-message');
    
    fetch(this.action, {
        method: 'POST',
        body: formData,
        headers: {'X-Requested-With': 'XMLHttpRequest'}
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            responseDiv.innerHTML = `<div class="alert alert-success">${data.message}</div>`;
            this.reset();
        } else {
            responseDiv.innerHTML = `<div class="alert alert-danger">${data.message}</div>`;
        }
    })
    .catch(error => {
        responseDiv.innerHTML = '<div class="alert alert-danger">An error occurred.</div>';
    });
});
```

### Pattern 2: Button Click with AJAX

**HTML**:
```html
<button class="btn btn-success ajax-action" data-url="{% url 'my_action' item.id %}">
    Approve
</button>
```

**JavaScript**:
```javascript
document.querySelectorAll('.ajax-action').forEach(btn => {
    btn.addEventListener('click', function() {
        const url = this.dataset.url;
        const csrfToken = document.querySelector('[name=csrfmiddlewaretoken]').value;
        
        const formData = new FormData();
        formData.append('csrfmiddlewaretoken', csrfToken);
        
        fetch(url, {
            method: 'POST',
            body: formData,
            headers: {'X-Requested-With': 'XMLHttpRequest'}
        })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                alert(data.message);
            } else {
                alert('Error: ' + data.message);
            }
        });
    });
});
```

## Debugging Tips

### 1. Check Browser Console
```javascript
console.log('Form submitted');
console.log('Response status:', response.status);
console.log('Response data:', data);
```

### 2. Check Django Logs
```python
logger.info(f"Request received: {request.POST}")
logger.info(f"AJAX request: {request.headers.get('X-Requested-With')}")
logger.error(f"Error occurred: {str(e)}")
logger.error(f"Traceback: {traceback.format_exc()}")
```

### 3. Check Network Tab
- Open browser DevTools → Network tab
- Look for the request
- Check Request Headers (should have `X-Requested-With: XMLHttpRequest`)
- Check Response (should be valid JSON)
- Check Status Code (200 for success, 400/500 for errors)

## Common Mistakes to Avoid

### ❌ Mistake 1: Calling messages.success() for AJAX
```python
# WRONG
messages.success(request, "Success!")
return JsonResponse({"success": True})
```

### ❌ Mistake 2: Forgetting AJAX Header
```javascript
// WRONG
fetch(url, {
    method: 'POST',
    body: formData
    // Missing X-Requested-With header!
})
```

### ❌ Mistake 3: Not Handling Errors
```javascript
// WRONG
fetch(url, {method: 'POST', body: formData})
    .then(response => response.json())
    .then(data => {
        // What if data.success is false?
        // What if fetch fails?
    });
```

### ❌ Mistake 4: Race Conditions in Stock Updates
```python
# WRONG
item.stock -= 10
item.save()
# Another request could modify stock between these lines!
```

### ❌ Mistake 5: Not Using Transactions
```python
# WRONG
item1.stock -= 10
item1.save()
# If this fails, item1 is already updated!
item2.stock += 10
item2.save()
```

## Checklist for New AJAX Features

- [ ] Backend detects AJAX using `request.headers.get('X-Requested-With')`
- [ ] Backend returns JSON for AJAX, messages+redirect for regular requests
- [ ] Backend uses transactions for database updates
- [ ] Backend uses F() expressions for stock updates
- [ ] Backend has proper error handling with logging
- [ ] Frontend adds `X-Requested-With: XMLHttpRequest` header
- [ ] Frontend handles both success and error responses
- [ ] Frontend shows loading states
- [ ] Frontend updates UI based on response
- [ ] Frontend has error handling in catch block
- [ ] Tested both AJAX and non-AJAX scenarios
- [ ] Checked browser console for errors
- [ ] Checked Django logs for errors
- [ ] Checked network tab for correct requests/responses

## Summary

1. **Always detect AJAX requests** before deciding response type
2. **Never mix messages with JSON** responses
3. **Always use transactions** for database updates
4. **Always add AJAX header** in fetch calls
5. **Always handle errors** on both frontend and backend
6. **Always log errors** with tracebacks for debugging
7. **Always test** both AJAX and non-AJAX scenarios

Following these practices will ensure consistent, reliable AJAX functionality throughout the pharmacy system!

