from django.http import JsonResponse, HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.db import transaction
from django.utils import timezone
from django.conf import settings
from store.models import Item, Sales, SalesItem, WholesaleItem, Receipt, DispensingLog, Cart
from store.gs1_parser import parse_barcode, is_gs1_barcode, GS1Parser, extract_gtin
from customer.models import Customer, WholesaleCustomer
from supplier.models import Supplier
from wholesale.models import *
from decimal import Decimal, InvalidOperation
import json
import logging
import os

# Handle date parsing for both Django and standard datetime
try:
    from django.utils.dateparse import parse_date
except ImportError:
    from datetime import datetime
    def parse_date(date_string):
        try:
            return datetime.strptime(date_string, '%Y-%m-%d').date()
        except (ValueError, TypeError):
            return None

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
                    elif action_type == 'create_item':
                        # Handle barcode-based item creation from scanner
                        mode = item_data.pop('mode', 'retail')
                        ItemModel = Item if mode == 'retail' else WholesaleItem
                        
                        # Check if barcode already exists to avoid conflicts
                        barcode = item_data.get('barcode', '').strip()
                        if barcode:
                            existing_item = ItemModel.objects.filter(barcode=barcode).first()
                            if existing_item:
                                failed_actions.append({
                                    'action': action,
                                    'error': f'Barcode {barcode} already assigned to {existing_item.name}'
                                })
                                continue
                        
                        ItemModel.objects.create(**item_data)
                        logger.info(f"Created new {mode} item via sync: {item_data.get('name')}")
                        synced_count += 1
                    elif action_type == 'lookup_when_online':
                        # Handle queued barcode lookups when back online
                        barcode = item_data.get('barcode', '').strip()
                        mode = item_data.get('mode', 'retail')
                        
                        if barcode:
                            ItemModel = Item if mode == 'retail' else WholesaleItem
                            try:
                                existing_item = ItemModel.objects.get(barcode=barcode)
                                logger.info(f"Queued barcode found online: {existing_item.name} (ID: {existing_item.id})")
                                synced_count += 1
                            except ItemModel.DoesNotExist:
                                # Still not found, keep in pending or notify user
                                failed_actions.append({
                                    'action': action,
                                    'error': f'Item with barcode {barcode} still not found'
                                })
                        else:
                            failed_actions.append({
                                'action': action,
                                'error': 'Missing barcode for lookup action'
                            })
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

                        # Check if this action was recently synced (within 5 minutes)
                        from django.core.cache import cache
                        action_hash = f"cart-sync-{user_id}-{item_id}-{unit}-{quantity}"

                        if cache.get(action_hash):
                            logger.info(f"Skipping duplicate cart action: {action_hash}")
                            synced_count += 1  # Count as synced (idempotent)
                            continue

                        # Use select_for_update() for atomic operations
                        cart_item, created = Cart.objects.select_for_update().get_or_create(
                            user=user,
                            item=item,
                            unit=unit,
                            status='active',  # Only work with active cart items
                            defaults={'quantity': quantity, 'price': item.price}
                        )

                        if not created:
                            cart_item.quantity += quantity
                            cart_item.price = item.price

                        cart_item.save()

                        # Cache this action hash for 5 minutes to prevent duplicates
                        cache.set(action_hash, True, 300)
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
                        from django.core.cache import cache

                        # Check if this action was recently synced (within 5 minutes)
                        action_hash = f"wholesale-cart-sync-{user_id}-{item_id}-{unit}-{quantity}"

                        if cache.get(action_hash):
                            logger.info(f"Skipping duplicate wholesale cart action: {action_hash}")
                            synced_count += 1  # Count as synced (idempotent)
                            continue

                        # Use select_for_update() for atomic operations
                        cart_item, created = WholesaleCart.objects.select_for_update().get_or_create(
                            user=user,
                            item=item,
                            unit=unit,
                            status='active',  # Only work with active cart items
                            defaults={'quantity': quantity, 'price': item.price}
                        )

                        if not created:
                            cart_item.quantity += quantity
                            cart_item.price = item.price

                        cart_item.save()

                        # Cache this action hash for 5 minutes to prevent duplicates
                        cache.set(action_hash, True, 300)
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

@require_http_methods(["POST"])
def barcode_lookup(request):
    """
    Look up item by barcode or QR code in retail or wholesale mode
    POST body: {"barcode": "123456789012" or "PHARM-RETAIL-123", "mode": "retail"|"wholesale"}

    Supports:
    - Traditional barcodes (UPC, EAN, etc.)
    - PharmApp QR codes (PHARM-RETAIL-ID or PHARM-WHOLESALE-ID format)
    - GS1 barcodes with Application Identifiers (AIs) for pharmaceutical products
    - Complex format: 'NAVIDOXINE(01) 18906047654987(10) 250203 (17) 012028(21) NVDXN0225'
    """
    try:
        data = json.loads(request.body)
        barcode = data.get('barcode', '').strip()
        mode = data.get('mode', 'retail')

        # Log request for debugging
        logger.info(f"Barcode lookup: {barcode} (mode: {mode})")

        if not barcode:
            return JsonResponse({
                'status': 'error',
                'error': 'Barcode is required',
                'user_message': 'Please scan or enter a barcode'
            }, status=400)

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
                        'error': 'Invalid QR code format',
                        'user_message': 'QR code format is invalid. Expected: PHARM-RETAIL-123'
                    }, status=400)

                qr_mode = parts[1].lower()  # 'retail' or 'wholesale'
                item_id = int(parts[2])

                # Verify mode matches
                if qr_mode != mode:
                    return JsonResponse({
                        'status': 'error',
                        'error': f'Mode mismatch: {qr_mode} vs {mode}',
                        'user_message': f'This QR code is for {qr_mode} mode. Please switch modes or scan a different code.'
                    }, status=400)

                # Look up by ID
                item = ItemModel.objects.get(id=item_id)

                logger.info(f"QR code found: {item.name} (ID: {item.id})")

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

            except (ValueError, IndexError) as e:
                logger.warning(f"Invalid QR code format: {barcode}")
                return JsonResponse({
                    'status': 'error',
                    'error': 'Invalid QR code format',
                    'user_message': 'Unable to parse QR code. Please try scanning again.'
                }, status=400)
            except ItemModel.DoesNotExist:
                logger.warning(f"Item not found for QR code: {barcode}")
                return JsonResponse({
                    'status': 'error',
                    'error': 'Item not found',
                    'user_message': 'Item not found for this QR code. It may have been deleted.'
                }, status=404)
        
        # Handle GS1 barcode parsing for pharmaceutical products
        is_gs1 = is_gs1_barcode(barcode)
        
        if is_gs1:
            # Parse the GS1 barcode
            try:
                parsed_data = parse_barcode(barcode)
                logger.info(f"GS1 barcode parsed: {parsed_data}")
                
                # Multi-layered lookup strategy for GS1 barcodes
                search_results = []
                search_confidence = {}
                
                # 1. Try exact barcode match (primary key)
                exact_matches = ItemModel.objects.filter(barcode=barcode)
                for item in exact_matches:
                    search_results.append({
                        'item': item,
                        'match_type': 'exact_barcode',
                        'confidence': 1.0
                    })
                
                # 2. Try GTIN match (if extracted)
                gtin = parsed_data.get('gtin')
                if gtin and len(gtin) >= 8:
                    gtin_matches = ItemModel.objects.filter(gtin=gtin).exclude(
                        id__in=[r['item'].id for r in search_results]
                    )
                    for item in gtin_matches:
                        search_results.append({
                            'item': item,
                            'match_type': 'gtin',
                            'confidence': 0.9
                        })
                
                # 3. Try partial GTIN matches (core digits)
                if gtin and len(gtin) > 8:
                    core_gtin = gtin[-8:]  # Last 8 digits
                    partial_gtin_matches = ItemModel.objects.filter(gtin__endswith=core_gtin).exclude(
                        id__in=[r['item'].id for r in search_results]
                    )
                    for item in partial_gtin_matches:
                        search_results.append({
                            'item': item,
                            'match_type': 'partial_gtin',
                            'confidence': 0.7
                        })
                
                # 4. Try batch + serial combination
                batch_number = parsed_data.get('batch_number')
                serial_number = parsed_data.get('serial_number')
                
                if batch_number and serial_number:
                    batch_serial_matches = ItemModel.objects.filter(
                        batch_number=batch_number,
                        serial_number=serial_number
                    ).exclude(id__in=[r['item'].id for r in search_results])
                    
                    for item in batch_serial_matches:
                        search_results.append({
                            'item': item,
                            'match_type': 'batch_serial',
                            'confidence': 0.8
                        })
                
                # 5. Try batch-only or serial-only matches
                if batch_number:
                    batch_matches = ItemModel.objects.filter(batch_number=batch_number).exclude(
                        id__in=[r['item'].id for r in search_results]
                    )
                    for item in batch_matches:
                        search_results.append({
                            'item': item,
                            'match_type': 'batch_only',
                            'confidence': 0.6
                        })
                
                if serial_number:
                    serial_matches = ItemModel.objects.filter(serial_number=serial_number).exclude(
                        id__in=[r['item'].id for r in search_results]
                    )
                    for item in serial_matches:
                        search_results.append({
                            'item': item,
                            'match_type': 'serial_only',
                            'confidence': 0.6
                        })
                
                # Sort by confidence and return best match
                if search_results:
                    search_results.sort(key=lambda x: x['confidence'], reverse=True)
                    best_match = search_results[0]
                    item = best_match['item']
                    
                    logger.info(f"GS1 match found: {item.name} via {best_match['match_type']} (confidence: {best_match['confidence']})")
                    
                    # Update item with parsed GS1 data if not already set
                    should_update = False
                    update_data = {}
                    
                    if not item.gtin and gtin:
                        update_data['gtin'] = gtin
                        should_update = True
                    
                    if not item.batch_number and batch_number:
                        update_data['batch_number'] = batch_number
                        should_update = True
                    
                    if not item.serial_number and serial_number:
                        update_data['serial_number'] = serial_number
                        should_update = True
                    
                    if should_update:
                        ItemModel.objects.filter(id=item.id).update(**update_data)
                        logger.info(f"Updated item {item.name} with GS1 components")
                    
                    return JsonResponse({
                        'status': 'success',
                        'lookup_type': 'gs1_barcode',
                        'match_type': best_match['match_type'],
                        'confidence': best_match['confidence'],
                        'parsed_data': parsed_data,
                        'total_matches': len(search_results),
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
                            'barcode_type': item.barcode_type or parsed_data.get('barcode_type', 'OTHER'),
                            'exp_date': item.exp_date.isoformat() if item.exp_date else None,
                            'gtin': item.gtin or '',
                            'batch_number': item.batch_number or '',
                            'serial_number': item.serial_number or '',
                        },
                        'other_matches': [
                            {
                                'id': r['item'].id,
                                'name': r['item'].name,
                                'match_type': r['match_type'],
                                'confidence': r['confidence']
                            }
                            for r in search_results[1:4]  # Top 4 additional matches
                        ] if len(search_results) > 1 else None
                    })
                
            except Exception as e:
                logger.error(f"GS1 barcode parsing error: {e}", exc_info=True)
                # Fall back to traditional lookup if GS1 parsing fails
        
        # Traditional barcode lookup (fallback)
        try:
            # Try exact barcode match
            item = ItemModel.objects.get(barcode=barcode)

            logger.info(f"Barcode found: {item.name} (barcode: {barcode})")

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
            logger.warning(f"Barcode not found: {barcode} (mode: {mode})")
            
            # For GS1 barcodes not found, try component-based search
            if is_gs1:
                try:
                    parsed_data = parse_barcode(barcode)
                    gtin = parsed_data.get('gtin')
                    
                    if gtin and len(gtin) >= 8:
                        # Try finding by GTIN component only
                        gtin_matches = ItemModel.objects.filter(gtin=gtin)[:3]
                        if gtin_matches.exists():
                            return JsonResponse({
                                'status': 'partial',
                                'message': f"Exact barcode not found, but found {len(gtin_matches)} item(s) with matching GTIN",
                                'matches': [
                                    {
                                        'id': item.id,
                                        'name': item.name,
                                        'brand': item.brand or '',
                                        'confidence': 'gtin_match'
                                    }
                                    for item in gtin_matches
                                ]
                            }, status=300)  # Multiple choices status
                except Exception as e:
                    logger.error(f"GS1 component search error: {e}")
            
            return JsonResponse({
                'status': 'error',
                'error': 'Item not found',
                'user_message': f'No item found with barcode: {barcode}. Please check if the barcode is assigned.',
                'suggestions': {
                    'gs1_detected': is_gs1,
                    'gs1_parsed': parsed_data if is_gs1 else None,
                    'gtin': gtin if is_gs1 else None
                }
            }, status=404)

    except json.JSONDecodeError as e:
        logger.error(f"Invalid JSON in barcode lookup: {str(e)}")
        return JsonResponse({
            'status': 'error',
            'error': 'Invalid JSON',
            'user_message': 'Request format error. Please try again.'
        }, status=400)
    except Exception as e:
        logger.error(f"Unexpected error in barcode_lookup: {str(e)}", exc_info=True)
        return JsonResponse({
            'status': 'error',
            'error': str(e),
            'user_message': 'An unexpected error occurred. Please try again or contact support.'
        }, status=500)


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


@csrf_exempt
@require_http_methods(["POST"])
def barcode_add_item(request):
    """
    Add new item via barcode scanning
    POST body: {
        "barcode": "123456789012",
        "mode": "retail"|"wholesale",
        "name": "Item Name",
        "cost": 10.50,
        "price": 15.00,
        "stock": 100,
        "brand": "Brand Name",
        "dosage_form": "Tablet",
        "unit": "Pcs",
        "exp_date": "2024-12-31",
        "barcode_type": "UPC"|"EAN13"|"CODE128"|"QR"|"OTHER"
    }
    """
    try:
        data = json.loads(request.body)
        mode = data.get('mode', 'retail')

        # Validate required fields
        required_fields = ['barcode', 'name', 'cost', 'stock']
        missing_fields = [field for field in required_fields if not data.get(field)]
        
        if missing_fields:
            return JsonResponse({
                'status': 'error',
                'error': f'Missing required fields: {", ".join(missing_fields)}',
                'user_message': f'Please provide: {", ".join(missing_fields)}'
            }, status=400)

        # Select appropriate model based on mode
        ItemModel = Item if mode == 'retail' else WholesaleItem

        # Check if barcode already exists
        barcode = data.get('barcode', '').strip()
        existing_item = ItemModel.objects.filter(barcode=barcode).first()
        if existing_item:
            return JsonResponse({
                'status': 'error',
                'error': 'Barcode already exists',
                'user_message': f'Barcode {barcode} is already assigned to {existing_item.name}',
                'existing_item': {
                    'id': existing_item.id,
                    'name': existing_item.name,
                    'brand': existing_item.brand or '',
                    'price': str(existing_item.price),
                    'stock': str(existing_item.stock),
                }
            }, status=409)

        # Create new item
        item_data = {
            'name': data.get('name'),
            'barcode': barcode,
            'barcode_type': data.get('barcode_type', 'OTHER'),
            'cost': Decimal(str(data.get('cost', 0))),
            'price': Decimal(str(data.get('price', 0))),
            'stock': int(data.get('stock', 0)),
            'brand': data.get('brand', ''),
            'dosage_form': data.get('dosage_form', ''),
            'unit': data.get('unit', 'Pcs'),
        }

        # Add optional fields
        if data.get('exp_date'):
            try:
                item_data['exp_date'] = parse_date(data.get('exp_date'))
            except (ValueError, TypeError):
                pass  # Skip invalid date

        if data.get('markup') is not None:
            item_data['markup'] = Decimal(str(data.get('markup', 0)))

        # Calculate price if not provided
        if not item_data.get('price') and item_data.get('cost') and item_data.get('markup'):
            item_data['price'] = item_data['cost'] + (item_data['cost'] * item_data['markup'] / 100)

        # Create the item
        new_item = ItemModel.objects.create(**item_data)

        logger.info(f"Created new {mode} item via barcode: {new_item.name} (ID: {new_item.id})")

        return JsonResponse({
            'status': 'success',
            'message': f'New {mode} item created successfully',
            'item': {
                'id': new_item.id,
                'name': new_item.name,
                'brand': new_item.brand or '',
                'dosage_form': new_item.dosage_form or '',
                'unit': new_item.unit or '',
                'price': str(new_item.price),
                'cost': str(new_item.cost),
                'stock': str(new_item.stock),
                'barcode': new_item.barcode,
                'barcode_type': new_item.barcode_type or 'OTHER',
                'exp_date': new_item.exp_date.isoformat() if new_item.exp_date else None,
                'markup': str(new_item.markup) if hasattr(new_item, 'markup') else None,
            }
        })

    except json.JSONDecodeError as e:
        logger.error(f"Invalid JSON in barcode_add_item: {str(e)}")
        return JsonResponse({
            'status': 'error',
            'error': 'Invalid JSON data',
            'user_message': 'Request format error. Please try again.'
        }, status=400)
    except Exception as e:
        logger.error(f"Error in barcode_add_item: {str(e)}", exc_info=True)
        return JsonResponse({
            'status': 'error',
            'error': str(e),
            'user_message': 'Failed to create item. Please check your data and try again.'
        }, status=500)


@csrf_exempt
@require_http_methods(["POST"])
def barcode_batch_add_items(request):
    """
    Add multiple new items via barcode scanning
    POST body: {
        "mode": "retail"|"wholesale",
        "items": [
            {
                "barcode": "123456789012",
                "name": "Item Name",
                "cost": 10.50,
                "stock": 100,
                ...
            },
            ...
        ]
    }
    """
    try:
        data = json.loads(request.body)
        mode = data.get('mode', 'retail')
        items_data = data.get('items', [])

        if not items_data or not isinstance(items_data, list):
            return JsonResponse({
                'status': 'error',
                'error': 'items array is required',
                'user_message': 'Please provide an array of items to add'
            }, status=400)

        if len(items_data) > 50:  # Limit batch size
            return JsonResponse({
                'status': 'error',
                'error': 'Too many items in batch (max 50)',
                'user_message': 'Please add items in smaller batches (maximum 50 items per request)'
            }, status=400)

        # Select appropriate model based on mode
        ItemModel = Item if mode == 'retail' else WholesaleItem

        created_items = []
        failed_items = []
        duplicate_barcodes = set()

        # Process each item
        for index, item_data in enumerate(items_data):
            try:
                # Validate required fields for this item
                required_fields = ['barcode', 'name', 'cost', 'stock']
                missing_fields = [field for field in required_fields if not item_data.get(field)]
                
                if missing_fields:
                    failed_items.append({
                        'index': index,
                        'barcode': item_data.get('barcode', ''),
                        'error': f'Missing required fields: {", ".join(missing_fields)}'
                    })
                    continue

                barcode = item_data.get('barcode', '').strip()

                # Check for duplicates within this batch
                if barcode in duplicate_barcodes:
                    failed_items.append({
                        'index': index,
                        'barcode': barcode,
                        'error': 'Duplicate barcode in this batch'
                    })
                    continue

                # Check if barcode already exists in database
                existing_item = ItemModel.objects.filter(barcode=barcode).first()
                if existing_item:
                    failed_items.append({
                        'index': index,
                        'barcode': barcode,
                        'error': f'Barcode already assigned to: {existing_item.name}'
                    })
                    continue

                duplicate_barcodes.add(barcode)

                # Prepare item data
                new_item_data = {
                    'name': item_data.get('name'),
                    'barcode': barcode,
                    'barcode_type': item_data.get('barcode_type', 'OTHER'),
                    'cost': Decimal(str(item_data.get('cost', 0))),
                    'price': Decimal(str(item_data.get('price', 0))),
                    'stock': int(item_data.get('stock', 0)),
                    'brand': item_data.get('brand', ''),
                    'dosage_form': item_data.get('dosage_form', ''),
                    'unit': item_data.get('unit', 'Pcs'),
                }

                # Add optional fields
                if item_data.get('exp_date'):
                    try:
                        new_item_data['exp_date'] = parse_date(item_data.get('exp_date'))
                    except (ValueError, TypeError):
                        pass

                if item_data.get('markup') is not None:
                    new_item_data['markup'] = Decimal(str(item_data.get('markup', 0)))

                # Calculate price if not provided
                if not new_item_data.get('price') and new_item_data.get('cost') and item_data.get('markup'):
                    new_item_data['price'] = new_item_data['cost'] + (new_item_data['cost'] * new_item_data['markup'] / 100)

                # Create the item
                new_item = ItemModel.objects.create(**new_item_data)
                
                created_items.append({
                    'index': index,
                    'barcode': barcode,
                    'item': {
                        'id': new_item.id,
                        'name': new_item.name,
                        'brand': new_item.brand or '',
                        'price': str(new_item.price),
                        'stock': str(new_item.stock),
                    }
                })

            except Exception as item_error:
                logger.error(f"Error creating item at index {index}: {str(item_error)}")
                failed_items.append({
                    'index': index,
                    'barcode': item_data.get('barcode', ''),
                    'error': str(item_error)
                })

        # Log batch results
        logger.info(f"Batch add {mode} items: {len(created_items)} created, {len(failed_items)} failed")

        return JsonResponse({
            'status': 'success' if not failed_items else 'partial',
            'message': f'Processed {len(items_data)} items: {len(created_items)} created, {len(failed_items)} failed',
            'total_processed': len(items_data),
            'created_count': len(created_items),
            'failed_count': len(failed_items),
            'created_items': created_items,
            'failed_items': failed_items
        })

    except json.JSONDecodeError as e:
        logger.error(f"Invalid JSON in barcode_batch_add_items: {str(e)}")
        return JsonResponse({
            'status': 'error',
            'error': 'Invalid JSON data',
            'user_message': 'Request format error. Please try again.'
        }, status=400)
    except Exception as e:
        logger.error(f"Error in barcode_batch_add_items: {str(e)}", exc_info=True)
        return JsonResponse({
            'status': 'error',
            'error': str(e),
            'user_message': 'Failed to process batch. Please check your data and try again.'
        }, status=500)