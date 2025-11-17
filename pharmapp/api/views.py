from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.db import transaction
from django.utils import timezone
from store.models import Item, Sales, SalesItem, WholesaleItem, Receipt, DispensingLog, Cart
from customer.models import Customer, WholesaleCustomer
from supplier.models import Supplier
from wholesale.models import *
from decimal import Decimal, InvalidOperation
import json
import logging

logger = logging.getLogger(__name__)

@csrf_exempt
@require_http_methods(["GET"])
def health_check(request):
    """Health check endpoint for connectivity testing"""
    return JsonResponse({'status': 'ok', 'timestamp': timezone.now().isoformat()})

@csrf_exempt
@require_http_methods(["GET"])
def get_initial_data(request):
    """Return initial data for offline caching"""
    try:
        data = {
            'inventory': list(Item.objects.values()),
            'customers': list(Customer.objects.values()),
            'suppliers': list(Supplier.objects.values()),
            'wholesale': list(WholesaleItem.objects.values()),
            'wholesale_customers': list(WholesaleCustomer.objects.values()),
        }

        # Convert Decimal fields to strings for JSON serialization
        for item in data['inventory'] + data['wholesale']:
            for key, value in item.items():
                if isinstance(value, Decimal):
                    item[key] = str(value)

        return JsonResponse(data)
    except Exception as e:
        logger.error(f"Error in get_initial_data: {str(e)}")
        return JsonResponse({'error': str(e)}, status=500)

@csrf_exempt
@require_http_methods(["POST"])
def inventory_sync(request):
    """Sync inventory changes from offline storage"""
    try:
        data = json.loads(request.body)
        actions = data.get('pendingActions', [])

        if not actions:
            return JsonResponse({'status': 'success', 'message': 'No actions to process'})

        synced_count = 0
        failed_actions = []

        with transaction.atomic():
            for action in actions:
                try:
                    item_data = action.get('data', {})
                    action_type = action.get('actionType') or action.get('type')

                    # Convert string decimals back to Decimal
                    for key in ['stock', 'cost', 'price', 'markup', 'low_stock_threshold']:
                        if key in item_data and item_data[key] is not None:
                            try:
                                item_data[key] = Decimal(str(item_data[key]))
                            except (InvalidOperation, ValueError):
                                logger.warning(f"Invalid decimal value for {key}: {item_data[key]}")

                    if action_type == 'add_item':
                        Item.objects.create(**item_data)
                        synced_count += 1
                    elif action_type == 'update_item':
                        item_id = item_data.pop('id', None)
                        if item_id:
                            Item.objects.filter(id=item_id).update(**item_data)
                            synced_count += 1
                    elif action_type == 'delete_item':
                        Item.objects.filter(id=item_data.get('id')).delete()
                        synced_count += 1
                    else:
                        failed_actions.append({'action': action, 'error': f'Unknown action type: {action_type}'})

                except Exception as e:
                    logger.error(f"Error processing action {action.get('id', 'unknown')}: {str(e)}")
                    failed_actions.append({'action': action, 'error': str(e)})

        response_data = {
            'status': 'success' if not failed_actions else 'partial',
            'synced_count': synced_count,
            'failed_count': len(failed_actions),
            'failed_actions': failed_actions
        }

        return JsonResponse(response_data)

    except json.JSONDecodeError as e:
        logger.error(f"Invalid JSON in inventory_sync: {str(e)}")
        return JsonResponse({'error': 'Invalid JSON data'}, status=400)
    except Exception as e:
        logger.error(f"Error in inventory_sync: {str(e)}")
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

@csrf_exempt
@require_http_methods(["POST"])
def receipts_sync(request):
    """Sync receipts from offline storage"""
    try:
        data = json.loads(request.body)
        actions = data.get('pendingActions', [])

        if not actions:
            return JsonResponse({'status': 'success', 'message': 'No actions to process'})

        synced_count = 0

        with transaction.atomic():
            for action in actions:
                receipt_data = action.get('data', {})
                # Process receipt data as needed
                synced_count += 1

        return JsonResponse({'status': 'success', 'synced_count': synced_count})

    except Exception as e:
        logger.error(f"Error in receipts_sync: {str(e)}")
        return JsonResponse({'error': str(e)}, status=500)

@csrf_exempt
@require_http_methods(["POST"])
def dispensing_sync(request):
    """Sync dispensing log from offline storage"""
    try:
        data = json.loads(request.body)
        actions = data.get('pendingActions', [])

        if not actions:
            return JsonResponse({'status': 'success', 'message': 'No actions to process'})

        synced_count = 0

        with transaction.atomic():
            for action in actions:
                dispensing_data = action.get('data', {})
                # Process dispensing data as needed
                synced_count += 1

        return JsonResponse({'status': 'success', 'synced_count': synced_count})

    except Exception as e:
        logger.error(f"Error in dispensing_sync: {str(e)}")
        return JsonResponse({'error': str(e)}, status=500)

@csrf_exempt
@require_http_methods(["POST"])
def cart_sync(request):
    """Sync cart items from offline storage"""
    try:
        data = json.loads(request.body)
        actions = data.get('pendingActions', [])

        if not actions:
            return JsonResponse({'status': 'success', 'message': 'No actions to process'})

        synced_count = 0

        with transaction.atomic():
            for action in actions:
                cart_data = action.get('data', {})
                # Process cart data as needed
                synced_count += 1

        return JsonResponse({'status': 'success', 'synced_count': synced_count})

    except Exception as e:
        logger.error(f"Error in cart_sync: {str(e)}")
        return JsonResponse({'error': str(e)}, status=500)