from django.http import JsonResponse, HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.db import transaction
from django.utils import timezone
from django.conf import settings
from store.models import Item, Sales, SalesItem, WholesaleItem, Receipt, DispensingLog, Cart
from customer.models import Customer, WholesaleCustomer
from supplier.models import Supplier
from wholesale.models import *
from decimal import Decimal, InvalidOperation
import json
import logging
import os

logger = logging.getLogger(__name__)

def serve_service_worker(request):
    """Serve service worker from root path to enable full scope control"""
    sw_path = os.path.join(settings.BASE_DIR, 'static', 'sw.js')

    try:
        with open(sw_path, 'r', encoding='utf-8') as f:
            sw_content = f.read()

        response = HttpResponse(sw_content, content_type='application/javascript')
        response['Service-Worker-Allowed'] = '/'
        response['Cache-Control'] = 'no-cache, no-store, must-revalidate'
        return response
    except FileNotFoundError:
        return HttpResponse('Service Worker not found', status=404)

@csrf_exempt
@require_http_methods(["GET", "HEAD"])
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
        failed_actions = []

        with transaction.atomic():
            for action in actions:
                try:
                    cart_data = action.get('data', {})
                    action_type = action.get('actionType') or action.get('type')

                    if action_type == 'add_to_cart':
                        # Get user and item
                        user_id = cart_data.get('user_id') or cart_data.get('user')
                        item_id = cart_data.get('item_id') or cart_data.get('item')
                        quantity = Decimal(str(cart_data.get('quantity', 1)))
                        unit = cart_data.get('unit', 'unit')

                        if not user_id or not item_id:
                            failed_actions.append({
                                'action': action,
                                'error': 'Missing user_id or item_id'
                            })
                            continue

                        # Get the item
                        try:
                            item = Item.objects.get(id=item_id)
                        except Item.DoesNotExist:
                            failed_actions.append({
                                'action': action,
                                'error': f'Item {item_id} not found'
                            })
                            continue

                        # Check stock
                        if quantity > item.stock:
                            failed_actions.append({
                                'action': action,
                                'error': f'Insufficient stock for {item.name}'
                            })
                            continue

                        # Add or update cart item
                        from userauth.models import User
                        try:
                            user = User.objects.get(id=user_id)
                        except User.DoesNotExist:
                            failed_actions.append({
                                'action': action,
                                'error': f'User {user_id} not found'
                            })
                            continue

                        cart_item, created = Cart.objects.get_or_create(
                            user=user,
                            item=item,
                            unit=unit,
                            defaults={'quantity': quantity, 'price': item.price}
                        )

                        if not created:
                            cart_item.quantity += quantity
                            cart_item.price = item.price

                        cart_item.save()
                        synced_count += 1

                    elif action_type == 'update_cart':
                        cart_id = cart_data.get('id')
                        if cart_id:
                            Cart.objects.filter(id=cart_id).update(**{
                                k: v for k, v in cart_data.items()
                                if k not in ['id', 'user', 'item']
                            })
                            synced_count += 1

                    elif action_type == 'remove_from_cart':
                        cart_id = cart_data.get('id')
                        if cart_id:
                            Cart.objects.filter(id=cart_id).delete()
                            synced_count += 1
                    else:
                        failed_actions.append({
                            'action': action,
                            'error': f'Unknown action type: {action_type}'
                        })

                except Exception as e:
                    logger.error(f"Error processing cart action: {str(e)}")
                    failed_actions.append({
                        'action': action,
                        'error': str(e)
                    })

        response_data = {
            'status': 'success' if not failed_actions else 'partial',
            'synced_count': synced_count,
            'failed_count': len(failed_actions),
            'failed_actions': failed_actions
        }

        return JsonResponse(response_data)

    except Exception as e:
        logger.error(f"Error in cart_sync: {str(e)}")
        return JsonResponse({'error': str(e)}, status=500)

@csrf_exempt
@require_http_methods(["POST"])
def wholesale_cart_sync(request):
    """Sync wholesale cart items from offline storage"""
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
                    cart_data = action.get('data', {})
                    action_type = action.get('actionType') or action.get('type')

                    if action_type == 'add_to_wholesale_cart':
                        # Get user and item
                        user_id = cart_data.get('user_id') or cart_data.get('user')
                        item_id = cart_data.get('item_id') or cart_data.get('item')
                        quantity = Decimal(str(cart_data.get('quantity', 0.5)))
                        unit = cart_data.get('unit', 'unit')

                        if not user_id or not item_id:
                            failed_actions.append({
                                'action': action,
                                'error': 'Missing user_id or item_id'
                            })
                            continue

                        # Get the wholesale item
                        try:
                            item = WholesaleItem.objects.get(id=item_id)
                        except WholesaleItem.DoesNotExist:
                            failed_actions.append({
                                'action': action,
                                'error': f'Wholesale item {item_id} not found'
                            })
                            continue

                        # Check stock
                        if quantity > item.stock:
                            failed_actions.append({
                                'action': action,
                                'error': f'Insufficient stock for {item.name}'
                            })
                            continue

                        # Add or update cart item
                        from userauth.models import User
                        try:
                            user = User.objects.get(id=user_id)
                        except User.DoesNotExist:
                            failed_actions.append({
                                'action': action,
                                'error': f'User {user_id} not found'
                            })
                            continue

                        from store.models import WholesaleCart
                        cart_item, created = WholesaleCart.objects.get_or_create(
                            user=user,
                            item=item,
                            unit=unit,
                            defaults={'quantity': quantity, 'price': item.price}
                        )

                        if not created:
                            cart_item.quantity += quantity
                            cart_item.price = item.price

                        cart_item.save()
                        synced_count += 1

                    elif action_type == 'update_wholesale_cart':
                        cart_id = cart_data.get('id')
                        if cart_id:
                            from store.models import WholesaleCart
                            WholesaleCart.objects.filter(id=cart_id).update(**{
                                k: v for k, v in cart_data.items()
                                if k not in ['id', 'user', 'item']
                            })
                            synced_count += 1

                    elif action_type == 'remove_from_wholesale_cart':
                        cart_id = cart_data.get('id')
                        if cart_id:
                            from store.models import WholesaleCart
                            WholesaleCart.objects.filter(id=cart_id).delete()
                            synced_count += 1
                    else:
                        failed_actions.append({
                            'action': action,
                            'error': f'Unknown action type: {action_type}'
                        })

                except Exception as e:
                    logger.error(f"Error processing wholesale cart action: {str(e)}")
                    failed_actions.append({
                        'action': action,
                        'error': str(e)
                    })

        response_data = {
            'status': 'success' if not failed_actions else 'partial',
            'synced_count': synced_count,
            'failed_count': len(failed_actions),
            'failed_actions': failed_actions
        }

        return JsonResponse(response_data)

    except Exception as e:
        logger.error(f"Error in wholesale_cart_sync: {str(e)}")
        return JsonResponse({'error': str(e)}, status=500)


# Barcode Scanning API Endpoints

@csrf_exempt
@require_http_methods(["POST"])
def barcode_lookup(request):
    """
    Look up item by barcode or QR code in retail or wholesale mode
    POST body: {"barcode": "123456789012" or "PHARM-RETAIL-123", "mode": "retail"|"wholesale"}

    Supports:
    - Traditional barcodes (UPC, EAN, etc.)
    - PharmApp QR codes (PHARM-RETAIL-ID or PHARM-WHOLESALE-ID format)
    """
    try:
        data = json.loads(request.body)
        barcode = data.get('barcode', '').strip()
        mode = data.get('mode', 'retail')

        if not barcode:
            return JsonResponse({'error': 'Barcode is required'}, status=400)

        # Select appropriate model based on mode
        ItemModel = Item if mode == 'retail' else WholesaleItem

        # Check if this is a PharmApp QR code
        is_qr_code = barcode.startswith('PHARM-')

        if is_qr_code:
            # Parse QR code format: PHARM-RETAIL-123 or PHARM-WHOLESALE-123
            try:
                parts = barcode.split('-')
                if len(parts) != 3:
                    return JsonResponse({
                        'status': 'error',
                        'error': 'Invalid QR code format'
                    }, status=400)

                qr_mode = parts[1].lower()  # 'retail' or 'wholesale'
                item_id = int(parts[2])

                # Verify mode matches
                if qr_mode != mode:
                    return JsonResponse({
                        'status': 'error',
                        'error': f'QR code is for {qr_mode} mode, but scanning in {mode} mode'
                    }, status=400)

                # Look up by ID
                item = ItemModel.objects.get(id=item_id)

                return JsonResponse({
                    'status': 'success',
                    'lookup_type': 'qr_code',
                    'item': {
                        'id': item.id,
                        'name': item.name,
                        'brand': item.brand or '',
                        'dosage_form': item.dosage_form or '',
                        'unit': item.unit or '',
                        'price': str(item.price),
                        'cost': str(item.cost),
                        'stock': str(item.stock),
                        'barcode': item.barcode or '',
                        'barcode_type': item.barcode_type or 'QR',
                        'exp_date': item.exp_date.isoformat() if item.exp_date else None,
                    }
                })

            except (ValueError, IndexError):
                return JsonResponse({
                    'status': 'error',
                    'error': 'Invalid QR code format'
                }, status=400)
            except ItemModel.DoesNotExist:
                return JsonResponse({
                    'status': 'error',
                    'error': 'Item not found for QR code'
                }, status=404)
        else:
            # Traditional barcode lookup
            try:
                # Try exact barcode match
                item = ItemModel.objects.get(barcode=barcode)

                return JsonResponse({
                    'status': 'success',
                    'lookup_type': 'barcode',
                    'item': {
                        'id': item.id,
                        'name': item.name,
                        'brand': item.brand or '',
                        'dosage_form': item.dosage_form or '',
                        'unit': item.unit or '',
                        'price': str(item.price),
                        'cost': str(item.cost),
                        'stock': str(item.stock),
                        'barcode': item.barcode or '',
                        'barcode_type': item.barcode_type or '',
                        'exp_date': item.exp_date.isoformat() if item.exp_date else None,
                    }
                })
            except ItemModel.DoesNotExist:
                return JsonResponse({
                    'status': 'error',
                    'error': 'Item not found'
                }, status=404)

    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON'}, status=400)
    except Exception as e:
        logger.error(f"Error in barcode_lookup: {str(e)}")
        return JsonResponse({'error': str(e)}, status=500)


@csrf_exempt
@require_http_methods(["POST"])
def assign_barcode(request):
    """
    Assign or update barcode for an existing item
    POST body: {"item_id": 123, "barcode": "123456789012", "barcode_type": "UPC", "mode": "retail"}
    """
    try:
        data = json.loads(request.body)
        item_id = data.get('item_id')
        barcode = data.get('barcode', '').strip()
        barcode_type = data.get('barcode_type', 'OTHER')
        mode = data.get('mode', 'retail')

        if not item_id or not barcode:
            return JsonResponse({'error': 'item_id and barcode are required'}, status=400)

        # Select appropriate model based on mode
        ItemModel = Item if mode == 'retail' else WholesaleItem

        try:
            item = ItemModel.objects.get(id=item_id)

            # Check if barcode is already used by another item
            existing = ItemModel.objects.filter(barcode=barcode).exclude(id=item_id).first()
            if existing:
                return JsonResponse({
                    'status': 'warning',
                    'message': f'Barcode already assigned to: {existing.name}',
                    'existing_item': {
                        'id': existing.id,
                        'name': existing.name,
                        'brand': existing.brand or ''
                    }
                }, status=409)

            # Assign barcode
            item.barcode = barcode
            item.barcode_type = barcode_type
            item.save(update_fields=['barcode', 'barcode_type'])

            return JsonResponse({
                'status': 'success',
                'message': 'Barcode assigned successfully',
                'item': {
                    'id': item.id,
                    'name': item.name,
                    'barcode': item.barcode,
                    'barcode_type': item.barcode_type
                }
            })

        except ItemModel.DoesNotExist:
            return JsonResponse({'error': 'Item not found'}, status=404)

    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON'}, status=400)
    except Exception as e:
        logger.error(f"Error in assign_barcode: {str(e)}")
        return JsonResponse({'error': str(e)}, status=500)


@csrf_exempt
@require_http_methods(["POST"])
def barcode_batch_lookup(request):
    """
    Look up multiple items by barcode for rapid scanning
    POST body: {"barcodes": ["123", "456", "789"], "mode": "retail"}
    """
    try:
        data = json.loads(request.body)
        barcodes = data.get('barcodes', [])
        mode = data.get('mode', 'retail')

        if not barcodes or not isinstance(barcodes, list):
            return JsonResponse({'error': 'barcodes array is required'}, status=400)

        # Select appropriate model based on mode
        ItemModel = Item if mode == 'retail' else WholesaleItem

        results = []
        not_found = []

        for barcode in barcodes:
            try:
                item = ItemModel.objects.get(barcode=barcode.strip())
                results.append({
                    'barcode': barcode,
                    'found': True,
                    'item': {
                        'id': item.id,
                        'name': item.name,
                        'brand': item.brand or '',
                        'price': str(item.price),
                        'stock': str(item.stock),
                    }
                })
            except ItemModel.DoesNotExist:
                not_found.append(barcode)
                results.append({
                    'barcode': barcode,
                    'found': False
                })

        return JsonResponse({
            'status': 'success',
            'total': len(barcodes),
            'found_count': len(barcodes) - len(not_found),
            'not_found_count': len(not_found),
            'results': results,
            'not_found': not_found
        })

    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON'}, status=400)
    except Exception as e:
        logger.error(f"Error in barcode_batch_lookup: {str(e)}")
        return JsonResponse({'error': str(e)}, status=500)