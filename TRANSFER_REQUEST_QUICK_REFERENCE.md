# Transfer Request System - Quick Reference

## 🔄 Transfer Directions

### Wholesale → Retail
**Who**: Retail user requesting items from wholesale inventory  
**URL**: `/transfer/create/`  
**Template**: `retail_transfer_request.html`  
**Parameter**: `from_wholesale="false"`  
**Source**: WholesaleItem  
**Database**:
```python
TransferRequest(
    wholesale_item=<WholesaleItem>,
    retail_item=None,
    from_wholesale=False,
    status="pending"
)
```

### Retail → Wholesale
**Who**: Wholesale user requesting items from retail inventory  
**URL**: `/transfer_wholesale/`  
**Template**: `wholesale_transfer_request.html`  
**Parameter**: `from_wholesale="true"`  
**Source**: Item (retail)  
**Database**:
```python
TransferRequest(
    retail_item=<Item>,
    wholesale_item=None,
    from_wholesale=True,
    status="pending"
)
```

## 📝 Model Fields Explained

```python
class TransferRequest(models.Model):
    # Source item fields (only ONE is set)
    wholesale_item = ForeignKey('WholesaleItem')  # Set when retail requests
    retail_item = ForeignKey('Item')              # Set when wholesale requests
    
    # Direction indicator
    from_wholesale = BooleanField()
    # True  = Wholesale is requesting (from retail)
    # False = Retail is requesting (from wholesale)
    
    # Quantities
    requested_quantity = PositiveIntegerField()
    approved_quantity = PositiveIntegerField(null=True)
    
    # Status tracking
    status = CharField(choices=[
        ("pending", "Pending"),
        ("approved", "Approved"),
        ("rejected", "Rejected"),
        ("received", "Received")
    ])
    
    created_at = DateTimeField()
```

## 🎯 Key Logic Pattern

```python
def create_transfer_request(request):
    if request.method == "POST":
        from_wholesale = request.POST.get("from_wholesale", "false").lower() == "true"
        item_id = request.POST.get("item_id")
        requested_quantity = int(request.POST.get("requested_quantity", 0))
        
        if from_wholesale:
            # Wholesale requesting from Retail
            source_item = get_object_or_404(Item, id=item_id)
            transfer = TransferRequest.objects.create(
                retail_item=source_item,
                from_wholesale=True,
                requested_quantity=requested_quantity,
                status="pending"
            )
        else:
            # Retail requesting from Wholesale
            source_item = get_object_or_404(WholesaleItem, id=item_id)
            transfer = TransferRequest.objects.create(
                wholesale_item=source_item,
                from_wholesale=False,
                requested_quantity=requested_quantity,
                status="pending"
            )
```

## 🔍 Debugging Checklist

### When transfer request fails:
1. ✅ Check `from_wholesale` parameter value
2. ✅ Verify correct item type is being fetched (Item vs WholesaleItem)
3. ✅ Confirm stock availability
4. ✅ Check correct model field is being set (retail_item vs wholesale_item)
5. ✅ Verify `from_wholesale` boolean matches the direction

### Common Mistakes:
- ❌ Hardcoding `from_wholesale=True` for all transfers
- ❌ Always fetching `Item` regardless of direction
- ❌ Not validating stock before creating transfer
- ❌ Setting both `retail_item` and `wholesale_item` (should be only one)
- ❌ Confusing the direction (from_wholesale=True means wholesale is requesting)

## 📊 Status Flow

```
pending → approved → received
   ↓
rejected (terminal state)
```

## 🛠️ Testing Commands

### Create Wholesale → Retail Transfer
```bash
curl -X POST http://127.0.0.1:8000/transfer/create/ \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "item_id=123&requested_quantity=10&from_wholesale=false"
```

### Create Retail → Wholesale Transfer
```bash
curl -X POST http://127.0.0.1:8000/transfer_wholesale/ \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "item_id=456&requested_quantity=5&from_wholesale=true"
```

### Check Transfer in Database
```python
# Django shell
from store.models import TransferRequest

# Wholesale → Retail transfers
TransferRequest.objects.filter(from_wholesale=False)

# Retail → Wholesale transfers
TransferRequest.objects.filter(from_wholesale=True)

# Pending transfers
TransferRequest.objects.filter(status="pending")
```

## 🎨 UI Elements

### Retail Transfer Request Form
```html
<form method="post" action="{% url 'wholesale:create_transfer_request' %}">
    {% csrf_token %}
    <input type="hidden" name="from_wholesale" value="false">
    
    <select name="item_id">
        {% for item in wholesale_items %}
        <option value="{{ item.id }}">{{ item.name }} ({{ item.stock }})</option>
        {% endfor %}
    </select>
    
    <input type="number" name="requested_quantity" min="1">
    <button type="submit">Request Transfer</button>
</form>
```

### Wholesale Transfer Request Form
```html
<form hx-post="{% url 'wholesale:create_transfer_request' %}">
    {% csrf_token %}
    <input type="hidden" name="from_wholesale" value="true">
    
    <select name="item_id">
        {% for item in retail_items %}
        <option value="{{ item.id }}">{{ item.name }} ({{ item.stock }})</option>
        {% endfor %}
    </select>
    
    <input type="number" name="requested_quantity" min="1">
    <button type="submit">Request Transfer</button>
</form>
```

## 📍 URL Patterns

### Store App (Retail)
```python
# pharmapp/store/urls.py
path("transfer/create/", views.create_transfer_request_wholesale, name="create_transfer_request_wholesale"),
path("pending_transfer_requests/", views.pending_transfer_requests, name="pending_transfer_requests"),
path("transfer/approve/<int:transfer_id>/", views.approve_transfer, name="approve_transfer"),
path("transfer/reject/<int:transfer_id>/", views.reject_transfer, name="reject_transfer"),
```

### Wholesale App
```python
# pharmapp/wholesale/urls.py
path("transfer_wholesale/", views.create_transfer_request, name="create_transfer_request"),
path("wholesale_pending_transfer_requests/", views.pending_wholesale_transfer_requests, name="pending_wholesale_transfer_requests"),
path("wholesale/approve/<int:transfer_id>/", views.wholesale_approve_transfer, name="wholesale_approve_transfer"),
path("transfer/reject/<int:transfer_id>/", views.reject_wholesale_transfer, name="reject_wholesale_transfer"),
```

## 🚨 Error Messages

### Insufficient Stock
```json
{
    "success": false,
    "message": "Insufficient stock. Available: 50"
}
```

### Invalid Input
```json
{
    "success": false,
    "message": "Invalid input provided."
}
```

### Success
```json
{
    "success": true,
    "message": "Transfer request created successfully."
}
```

## 💡 Remember

1. **from_wholesale** parameter indicates WHO is requesting, not WHERE items are going
2. **from_wholesale=True** → Wholesale requesting FROM retail
3. **from_wholesale=False** → Retail requesting FROM wholesale
4. Only ONE of `retail_item` or `wholesale_item` should be set
5. Always validate stock before creating transfer
6. Use appropriate item model based on direction (Item vs WholesaleItem)

