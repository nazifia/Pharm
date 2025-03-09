from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.db import transaction
from store.models import Item, Sales, SalesItem, WholesaleItem
from customer.models import Customer
from supplier.models import Supplier
from wholesale.models import *
import json

@csrf_exempt
def get_initial_data(request):
    """Return initial data for offline caching"""
    data = {
        'inventory': list(Item.objects.values()),
        'customers': list(Customer.objects.values()),
        'suppliers': list(Supplier.objects.values()),
        'wholesale': list(WholesaleItem.objects.values()),
    }
    return JsonResponse(data)

@csrf_exempt
def inventory_sync(request):
    if request.method != 'POST':
        return JsonResponse({'error': 'Invalid method'}, status=405)
    
    try:
        data = json.loads(request.body)
        actions = data.get('pendingActions', [])
        
        with transaction.atomic():
            for action in actions:
                item_data = action['data']
                action_type = action['actionType']
                
                if action_type == 'add_item':
                    Item.objects.create(**item_data)
                elif action_type == 'update_item':
                    Item.objects.filter(id=item_data['id']).update(**item_data)
                elif action_type == 'delete_item':
                    Item.objects.filter(id=item_data['id']).delete()
                    
        return JsonResponse({'status': 'success'})
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)

@csrf_exempt
def sales_sync(request):
    if request.method != 'POST':
        return JsonResponse({'error': 'Invalid method'}, status=405)
    
    try:
        data = json.loads(request.body)
        actions = data.get('pendingActions', [])
        
        with transaction.atomic():
            for action in actions:
                sale_data = action['data']
                items = sale_data.pop('items', [])
                
                # Create sale
                sale = Sales.objects.create(**sale_data)
                
                # Create sale items
                for item in items:
                    SalesItem.objects.create(sale=sale, **item)
                    
                    # Update inventory
                    inventory_item = Item.objects.get(id=item['item_id'])
                    inventory_item.stock -= item['quantity']
                    inventory_item.save()
                    
        return JsonResponse({'status': 'success'})
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)

@csrf_exempt
def customers_sync(request):
    if request.method != 'POST':
        return JsonResponse({'error': 'Invalid method'}, status=405)
    
    try:
        data = json.loads(request.body)
        actions = data.get('pendingActions', [])
        
        with transaction.atomic():
            for action in actions:
                customer_data = action['data']
                action_type = action['actionType']
                
                if action_type == 'add_customer':
                    Customer.objects.create(**customer_data)
                elif action_type == 'update_customer':
                    Customer.objects.filter(id=customer_data['id']).update(**customer_data)
                    
        return JsonResponse({'status': 'success'})
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)

@csrf_exempt
def suppliers_sync(request):
    if request.method != 'POST':
        return JsonResponse({'error': 'Invalid method'}, status=405)
    
    try:
        data = json.loads(request.body)
        actions = data.get('pendingActions', [])
        
        with transaction.atomic():
            for action in actions:
                supplier_data = action['data']
                action_type = action['actionType']
                
                if action_type == 'add_supplier':
                    Supplier.objects.create(**supplier_data)
                elif action_type == 'update_supplier':
                    Supplier.objects.filter(id=supplier_data['id']).update(**supplier_data)
                    
        return JsonResponse({'status': 'success'})
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)

@csrf_exempt
def wholesale_sync(request):
    if request.method != 'POST':
        return JsonResponse({'error': 'Invalid method'}, status=405)
    
    try:
        data = json.loads(request.body)
        actions = data.get('pendingActions', [])
        
        with transaction.atomic():
            for action in actions:
                wholesale_data = action['data']
                action_type = action['actionType']
                
                if action_type == 'add_wholesale_sale':
                    items = wholesale_data.pop('items', [])
                    sale = Sales.objects.create(**wholesale_data)
                    
                    for item in items:
                        # Create sale item and update inventory
                        wholesale_item = WholesaleItem.objects.get(id=item['item_id'])
                        wholesale_item.stock -= item['quantity']
                        wholesale_item.save()
                    
        return JsonResponse({'status': 'success'})
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)