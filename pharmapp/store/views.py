from django.views.decorators.http import require_http_methods
from django.core.cache import cache
from django.core.paginator import Paginator
from django.db import transaction, IntegrityError
from collections import defaultdict
from decimal import Decimal
import json
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.cache import never_cache
from django.http import HttpResponse, JsonResponse
from django.db.models.functions import TruncMonth, TruncDay
from django.shortcuts import get_object_or_404, render, redirect
from django.utils import timezone
from django.urls import reverse
from customer.models import Wallet, Customer, WholesaleCustomer, WholesaleCustomerWallet, TransactionHistory
from django.forms import formset_factory
from .models import *
from .forms import *
from django.contrib import messages
from django.db import transaction
from datetime import datetime, timedelta
from django.views.decorators.http import require_POST
from django.db.models import Q, F, ExpressionWrapper, Sum, Count, DecimalField, Case, When, Subquery, OuterRef
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib.auth import authenticate, login, logout, update_session_auth_hash
from django.contrib.auth import get_user_model
from django.utils.dateparse import parse_date
from django.utils import timezone
import logging
import hashlib

# Import procurement permission functions
from userauth.permissions import (
    can_manage_retail_procurement,
    can_view_procurement_history
)

logger = logging.getLogger(__name__)

# Import required models for transfer functionality
from .models import TransferRequest, WholesaleItem

# Cache utility functions for search optimization
def get_search_cache_key(model_name, query, user_id=None):
    """Generate a cache key for search results"""
    key_data = f"{model_name}:{query}:{user_id or 'all'}"
    return f"search:{hashlib.md5(key_data.encode()).hexdigest()}"

def cache_search_results(cache_key, results, timeout=300):  # 5 minutes cache
    """Cache search results - simplified to work with QuerySets directly"""
    try:
        # Cache the primary key list to reconstruct the queryset later
        if hasattr(results, 'values_list'):
            # It's a QuerySet, cache the primary keys
            pk_list = list(results.values_list('pk', flat=True))
            cache.set(cache_key, pk_list, timeout)
            return pk_list
        else:
            # It's already a list, cache as-is
            cache.set(cache_key, results, timeout)
            return results
    except Exception as e:
        logger.warning(f"Failed to cache search results: {e}")
        return None

def get_cached_search_results(cache_key):
    """Retrieve cached search results and reconstruct queryset if needed"""
    try:
        cached_data = cache.get(cache_key)
        if cached_data is None:
            return None
            
        # Check if it's a list of primary keys (from queryset caching)
        if isinstance(cached_data, list) and len(cached_data) > 0 and isinstance(cached_data[0], int):
            # Reconstruct the queryset from primary keys
            return Item.objects.filter(pk__in=cached_data).order_by('name')
        
        # Return as-is if it's already a list of items
        return cached_data
    except Exception as e:
        logger.warning(f"Failed to retrieve cached search results: {e}")
        return None


def can_view_all_users_dispensing(user):
    """
    Helper function to determine if a user can view all users' dispensing data.
    Returns True for superusers, staff, admins, and managers.
    """
    return (
        user.is_superuser or
        user.is_staff or
        (hasattr(user, 'profile') and
         user.profile and
         user.profile.user_type in ['Admin', 'Manager'])
    )

def can_view_full_dispensing_stats(user):
    """
    Helper function to determine if a user can view full dispensing statistics.
    Returns True for superusers, staff, admins, and managers.
    Pharmacists, Pharm-Techs, and Salespersons get daily-only stats.
    """
    return (
        user.is_superuser or
        user.is_staff or
        (hasattr(user, 'profile') and
         user.profile and
         user.profile.user_type in ['Admin', 'Manager'])
    )





@login_required
def offline_view(request):
    """
    View for handling offline mode functionality
    """
    context = {
        'title': 'Offline Mode',
        'show_nav': True,
        'is_authenticated': request.user.is_authenticated
    }
    return render(request, 'offline/offline.html', context)


def login_view(request):
    if request.method == 'POST':
        mobile = request.POST.get('mobile')
        password = request.POST.get('password')

        if not mobile or not password:
            messages.error(request, 'Please provide both mobile number and password.')
            return render(request, 'store/index.html')

        user = authenticate(request, username=mobile, password=password)

        if user is not None:
            if user.is_active:
                login(request, user)

                # Ensure user has a profile
                from userauth.models import Profile
                if not hasattr(user, 'profile'):
                    Profile.objects.get_or_create(user=user, defaults={
                        'full_name': user.username or user.mobile,
                        'user_type': 'Salesperson'  # Default role for users without profile
                    })

                # Set user chat status to online
                from chat.models import UserChatStatus
                user_chat_status, created = UserChatStatus.objects.get_or_create(
                    user=user,
                    defaults={'is_online': True, 'last_seen': timezone.now()}
                )
                user_chat_status.is_online = True
                user_chat_status.last_seen = timezone.now()
                user_chat_status.save()

                next_url = request.GET.get('next', 'store:dashboard')
                messages.success(request, f'Welcome back, {user.username or user.mobile}!')
                return redirect(next_url)
            else:
                messages.error(request, 'Your account has been deactivated. Please contact an administrator.')
        else:
            messages.error(request, 'Invalid mobile number or password. Please try again.')

    return render(request, 'store/index.html')


@csrf_exempt
def sync_offline_actions(request):
    """Handle syncing of offline actions"""
    if request.method != 'POST':
        return JsonResponse({'error': 'Invalid method'}, status=405)

    try:
        data = json.loads(request.body)
        actions = data.get('pendingActions', [])
        results = []

        for action in actions:
            # Process each offline action
            action_type = action.get('type')
            action_data = action.get('data')

            if action_type == 'CREATE':
                # Handle create operations
                model_name = action_data.get('model')
                model_data = action_data.get('data')
                if model_name == 'Item':
                    item = Item.objects.create(**model_data)
                    result = {'id': item.id, 'status': 'success'}
                elif model_name == 'Sales':
                    sale = Sales.objects.create(**model_data)
                    result = {'id': sale.id, 'status': 'success'}
                else:
                    result = {'status': 'error', 'message': f'Unknown model: {model_name}'}
                results.append(result)
            # Add other action types as needed

        return JsonResponse({
            'success': True,
            'results': results
        })
    except Exception as e:
        return JsonResponse({
            'error': str(e)
        }, status=500)

# Create your views here.
def is_admin(user):
    return user.is_authenticated and user.is_superuser or user.is_staff



def index(request):
    if request.method == 'POST':
        mobile = request.POST.get('mobile')
        password = request.POST.get('password')

        if not mobile or not password:
            messages.error(request, 'Please provide both mobile number and password.')
            return render(request, 'store/index.html')

        # Perform any necessary authentication logic here
        user = authenticate(request, username=mobile, password=password)
        if user is not None:
            if user.is_active:
                login(request, user)

                # Ensure user has a profile
                from userauth.models import Profile
                if not hasattr(user, 'profile'):
                    Profile.objects.get_or_create(user=user, defaults={
                        'full_name': user.username or user.mobile,
                        'user_type': 'Salesperson'  # Default role for users without profile
                    })

                messages.success(request, f'Welcome back, {user.username or user.mobile}!')
                return redirect('store:dashboard')
            else:
                messages.error(request, 'Your account has been deactivated. Please contact an administrator.')
        else:
            messages.error(request, 'Invalid mobile number or password. Please try again.')

    return render(request, 'store/index.html')


def dashboard(request):
    return render(request, 'store/dashboard.html')


def logout_user(request):
    # Set user chat status to offline before logout
    if request.user.is_authenticated:
        from chat.models import UserChatStatus
        try:
            user_chat_status = UserChatStatus.objects.filter(user=request.user).first()
            if user_chat_status:
                user_chat_status.is_online = False
                user_chat_status.last_seen = timezone.now()
                user_chat_status.save()
        except Exception:
            # Silently handle any errors to avoid breaking logout process
            pass
    
    logout(request)
    return redirect('store:dashboard')





@never_cache
@login_required
def store(request):
    if request.user.is_authenticated:
        from userauth.permissions import can_operate_retail
        if not can_operate_retail(request.user):
            messages.error(request, 'You do not have permission to access retail operations.')
            return redirect('store:index')
        items = Item.objects.all().order_by('name')
        settings = StoreSettings.get_settings()

        if request.method == 'POST' and request.user.is_superuser:
            settings_form = StoreSettingsForm(request.POST, instance=settings)
            if settings_form.is_valid():
                settings = settings_form.save()
                messages.success(request, 'Settings updated successfully')
            else:
                messages.error(request, 'Error updating settings')
        else:
            settings_form = StoreSettingsForm(instance=settings)

        # Use the threshold from settings
        low_stock_threshold = settings.low_stock_threshold

        # Identify low-stock items using the threshold from settings
        low_stock_items = [item for item in items if item.stock <= low_stock_threshold]

        context = {
            'items': items,
            'low_stock_items': low_stock_items,
            'settings_form': settings_form,
            'low_stock_threshold': low_stock_threshold,
        }

        # Only include financial data if user has permission
        if request.user.has_permission('view_financial_reports'):
            from decimal import Decimal
            # Calculate values using the threshold from settings
            total_purchase_value = sum(item.cost * Decimal(item.stock) for item in items)
            total_stock_value = sum(item.price * Decimal(item.stock) for item in items)
            total_profit = total_stock_value - total_purchase_value

            context.update({
                'total_purchase_value': total_purchase_value,
                'total_stock_value': total_stock_value,
                'total_profit': total_profit,
            })
        return render(request, 'store/store.html', context)
    else:
        return redirect('store:index')



@login_required
def add_item(request):
    if request.user.is_authenticated:
        from userauth.permissions import can_manage_items
        if not can_manage_items(request.user):
            messages.error(request, 'You do not have permission to add items.')
            return redirect('store:store')
        if request.method == 'POST':
            # The form now uses hidden fields for dosage_form and unit
            # which are set by JavaScript, so we can use the form directly
            form = addItemForm(request.POST)

            if form.is_valid():
                item = form.save(commit=False)

                # Check if manual price override is enabled
                manual_price_override = request.POST.get('manual_price_override') == 'on'

                # Convert markup_percentage to Decimal to ensure compatible types
                markup = Decimal(form.cleaned_data.get("markup", 0))
                item.markup = markup

                # Get the price from the form
                submitted_price = Decimal(form.cleaned_data.get("price", 0))

                if not manual_price_override:
                    # Calculate price based on the cost and markup percentage
                    item.price = item.cost + (item.cost * markup / Decimal(100))
                else:
                    # Use the manually entered price
                    item.price = submitted_price

                item.save()
                messages.success(request, 'Item added successfully')
                return redirect('store:store')
            else:
                print("Form errors:", form.errors)  # Debugging output
                messages.error(request, 'Error creating item')
        else:
            form = addItemForm()
        if request.headers.get('HX-Request'):
            return render(request, 'partials/add_item_modal.html', {'form': form})
        else:
            return render(request, 'store/store.html', {'form': form})
    else:
        return redirect('store:index')


@never_cache
@login_required
def search_item(request):
    if request.user.is_authenticated:
        query = request.GET.get('search', '').strip()
        if query:
            # Check if query looks like a barcode (numeric, 8-14 digits)
            is_barcode = query.isdigit() and 8 <= len(query) <= 14

            # Optimized search with better performance
            # Use istartswith for better index utilization, fallback to icontains
            if len(query) >= 2:  # Only search if query is meaningful
                if is_barcode:
                    # Try barcode lookup first
                    items = Item.objects.filter(barcode=query).order_by('name')[:50]
                    if not items.exists():
                        # Fallback to name/brand search if barcode not found
                        items = Item.objects.filter(
                            Q(name__istartswith=query) |
                            Q(brand__istartswith=query) |
                            Q(name__icontains=query) |
                            Q(brand__icontains=query)
                        ).distinct().order_by('name')[:50]
                else:
                    # Regular name/brand search
                    items = Item.objects.filter(
                        Q(name__istartswith=query) |  # Faster prefix search
                        Q(brand__istartswith=query) |
                        Q(name__icontains=query) |  # Fallback for partial matches
                        Q(brand__icontains=query)
                    ).distinct().order_by('name')[:50]  # Limit results for performance
            else:
                items = Item.objects.none()  # Don't search for very short queries
        else:
            items = Item.objects.all().order_by('name')[:50]  # Limit initial load

        # Check if this is an HTMX request (for embedded search in store page)
        if request.headers.get('HX-Request'):
            return render(request, 'partials/search_item.html', {'items': items})
        else:
            # Regular page request - redirect to store page with search
            return redirect(f"{reverse('store:store')}?search={query}" if query else reverse('store:store'))
    else:
        return redirect('store:index')

@login_required
def edit_item(request, pk):
    if request.user.is_authenticated:
        from userauth.permissions import can_manage_items
        if not can_manage_items(request.user):
            messages.error(request, 'You do not have permission to edit items.')
            return redirect('store:store')
        item = get_object_or_404(Item, id=pk)

        if request.method == 'POST':
            form = addItemForm(request.POST, instance=item)
            if form.is_valid():
                # Check if manual price override is enabled
                manual_price_override = request.POST.get('manual_price_override') == 'on'

                # Convert markup_percentage to Decimal to ensure compatible types
                markup = Decimal(form.cleaned_data.get("markup", 0))
                item.markup = markup

                # Get the price from the form
                submitted_price = Decimal(form.cleaned_data.get("price", 0))

                if not manual_price_override:
                    # Calculate price based on the cost and markup percentage
                    item.price = item.cost + (item.cost * markup / Decimal(100))
                else:
                    # Use the manually entered price
                    item.price = submitted_price

                # Save the form with updated fields
                form.save()

                messages.success(request, f'{item.name} updated successfully')
                return redirect('store:store')
            else:
                messages.error(request, 'Failed to update item')
        else:
            form = addItemForm(instance=item)

        # Render the modal or full page based on request type
        if request.headers.get('HX-Request'):
            return render(request, 'partials/edit_item_modal.html', {'form': form, 'item': item})
        else:
            return render(request, 'store/store.html', {'form': form})
    else:
        return redirect('store:index')


@never_cache
@login_required
def dispense(request):
    print(f"DEBUG: STORE dispense view called by user: {request.user}")
    print(f"DEBUG: Request path: {request.path}")
    if request.user.is_authenticated:
        if request.method == 'POST':
            form = dispenseForm(request.POST)
            if form.is_valid():
                q = form.cleaned_data['q']
                
                try:
                    # Use cached search results for better performance
                    cache_key = get_search_cache_key('item', q, request.user.id)
                    cached_results = get_cached_search_results(cache_key)
                    
                    if cached_results:
                        # Use cached results directly
                        results = cached_results
                    else:
                        # Optimized database query
                        results = Item.objects.filter(
                            Q(name__icontains=q) | Q(brand__icontains=q)
                        ).filter(stock__gt=0).order_by('name')[:50]  # Only show items with stock > 0, limit for performance
                        
                        # Cache the results for 5 minutes
                        cache_search_results(cache_key, results)
                except Exception as e:
                    logger.error(f"Error in dispense POST search: {e}")
                    # Fallback to basic query without caching
                    results = Item.objects.filter(
                        Q(name__icontains=q) | Q(brand__icontains=q)
                    ).filter(stock__gt=0).order_by('name')[:50]
        else:
            # GET request - preserve cart items for continued dispensing
            # Note: Cart is no longer auto-cleared to allow items to persist
            # Users can manually clear cart using the "Clear Cart" button

            form = dispenseForm()
            results = None

        # Check if this is an HTMX request (for modal)
        if request.headers.get('HX-Request'):
            response = render(request, 'partials/dispense_modal.html', {'form': form, 'results': results})
            # Add explicit cache-control headers for HTMX requests
            response['Cache-Control'] = 'no-cache, no-store, must-revalidate, max-age=0'
            response['Pragma'] = 'no-cache'
            response['Expires'] = '0'
            return response
        else:
            # Regular page request - get cart summary with optimized query
            cart_items = Cart.objects.select_related('item').filter(user=request.user)
            cart_count = cart_items.count()
            cart_total = sum(cart_item.subtotal for cart_item in cart_items)

            context = {
                'form': form,
                'results': results,
                'cart_count': cart_count,
                'cart_total': cart_total
            }
            response = render(request, 'store/dispense.html', context)
            # Add explicit cache-control headers for regular requests
            response['Cache-Control'] = 'no-cache, no-store, must-revalidate, max-age=0'
            response['Pragma'] = 'no-cache'
            response['Expires'] = '0'
            return response
    else:
        return redirect('store:index')


@never_cache
@login_required
def dispense_search_items(request):
    """HTMX endpoint for dynamic item search in dispensing"""
    if request.user.is_authenticated:
        query = request.GET.get('q', '').strip()
        results = []

        if query and len(query) >= 2:
            try:
                # Check if query looks like a barcode (numeric, 8-14 digits)
                is_barcode = query.isdigit() and 8 <= len(query) <= 14

                # Use cached search results for better performance
                cache_key = get_search_cache_key('item', query, request.user.id)
                cached_results = get_cached_search_results(cache_key)

                if cached_results:
                    # Use cached results directly as they're already in the right format
                    results = cached_results
                else:
                    if is_barcode:
                        # Try barcode lookup first
                        barcode_results = Item.objects.filter(barcode=query).filter(stock__gt=0).order_by('name')[:50]
                        if barcode_results.exists():
                            results = barcode_results
                        else:
                            # Fallback to name/brand search if barcode not found
                            results = Item.objects.filter(
                                Q(name__icontains=query) | Q(brand__icontains=query)
                            ).filter(stock__gt=0).order_by('name')[:50]
                    else:
                        # Regular name/brand search
                        results = Item.objects.filter(
                            Q(name__icontains=query) | Q(brand__icontains=query)
                        ).filter(stock__gt=0).order_by('name')[:50]

                    # Cache the results for 5 minutes
                    cache_search_results(cache_key, results)
            except Exception as e:
                logger.error(f"Error in dispense search: {e}")
                # Fallback to basic query without caching if something goes wrong
                results = Item.objects.filter(
                    Q(name__icontains=query) | Q(brand__icontains=query) | Q(barcode=query)
                ).filter(stock__gt=0).order_by('name')[:50]

        return render(request, 'partials/dispense_search_results.html', {'results': results, 'query': query})
    else:
        return redirect('store:index')


@login_required
def cart(request):
    if request.user.is_authenticated:
        # Optimized query with select_related and only necessary fields
        # Only show active cart items (exclude those sent to cashier or processed)
        cart_items = Cart.objects.select_related('item').filter(
            user=request.user, 
            status='active'
        ).only(
            'id', 'user', 'item', 'quantity', 'price', 'discount_amount', 'subtotal', 'status',
            'item__id', 'item__name', 'item__brand', 'item__dosage_form', 'item__unit', 
            'item__price', 'item__stock', 'item__exp_date'
        )

        # Check if cart is empty and cleanup session if needed
        from store.cart_utils import auto_cleanup_empty_cart_session
        cleanup_summary = auto_cleanup_empty_cart_session(request, 'retail')
        if cleanup_summary:
            logger.info(f"Empty cart session cleaned up on cart view: {cleanup_summary}")

        total_price, total_discount = 0, 0

        if request.method == 'POST':
            # Process each discount form submission
            for cart_item in cart_items:
                # Fetch the discount amount using cart_item.id in the input name
                discount = Decimal(request.POST.get(f'discount_amount-{cart_item.id}', 0))
                cart_item.discount_amount = max(discount, 0)
                cart_item.save()

        # Calculate totals
        base_total = 0
        for cart_item in cart_items:
            # Update the price field to match the item's current price
            if cart_item.price != cart_item.item.price:
                cart_item.price = cart_item.item.price
                # This will trigger the save method which recalculates subtotal
                cart_item.save()
            else:
                # Ensure subtotal is correctly calculated even if price hasn't changed
                cart_item.save()  # This will recalculate subtotal with discount

            # Calculate base total (before discount) and total discount
            base_total += cart_item.price * cart_item.quantity
            total_discount += cart_item.discount_amount

        # Calculate final totals
        total_price = base_total  # Total before discount
        total_discounted_price = base_total - total_discount  # Total after discount
        final_total = total_discounted_price

        # Get customer from user-specific session if it exists
        from userauth.session_utils import get_user_customer_id
        customer = None
        customer_id = get_user_customer_id(request)
        if customer_id:
            try:
                customer = Customer.objects.get(id=customer_id)
            except Customer.DoesNotExist:
                pass

        # Define available payment methods and statuses
        payment_methods = ["Cash", "Wallet", "Transfer"]
        statuses = ["Paid", "Unpaid"]

        return render(request, 'store/cart.html', {
            'cart_items': cart_items,
            'total_discount': total_discount,
            'total_price': total_price,
            'total_discounted_price': total_discounted_price,
            'final_total': final_total,
            'customer': customer,
            'payment_methods': payment_methods,
            'statuses': statuses,
        })
    else:
        return redirect('store:index')


@login_required
@require_POST
def add_to_cart(request, pk):
    if request.user.is_authenticated:
        item = get_object_or_404(Item, id=pk)
        quantity = int(request.POST.get('quantity', 1))
        unit = request.POST.get('unit')

        if quantity <= 0:
            messages.warning(request, "Quantity must be greater than zero.")
            return redirect('store:cart')

        if quantity > item.stock:
            messages.error(request, f"Not enough stock for {item.name}. Available stock: {item.stock}")
            return redirect('store:cart')

        # Add the item to the cart or update its quantity if it already exists
        # Only work with active cart items
        cart_item, created = Cart.objects.get_or_create(
            user=request.user,
            item=item,
            unit=unit,
            status='active',  # Only create/modify active cart items
            defaults={'quantity': quantity, 'price': item.price}
        )
        if not created:
            cart_item.quantity += quantity

        # Always update the price to match the current item price
        cart_item.price = item.price

        # Save the cart item (subtotal is recalculated in the model's save method)
        cart_item.save()

        # Update stock quantity in the wholesale inventory
        item.stock -= quantity
        item.save()

        messages.success(request, f"{quantity} {item.unit} of {item.name} added to cart.")

        # Return the cart summary as JSON if this was an HTMX request
        if request.headers.get('HX-Request'):
            cart_items = Cart.objects.filter(user=request.user, status='active')  # Only count active items
            total_price = sum(cart_item.subtotal for cart_item in cart_items)

            # Check if this is from the dispensing page (has specific header or parameter)
            if request.GET.get('from_dispense') or request.POST.get('from_dispense'):
                # Return HTML fragment for cart summary widget update
                context = {
                    'cart_count': cart_items.count(),
                    'cart_total': total_price,
                    'success_message': f"{quantity} {item.unit} of {item.name} added to cart."
                }
                return render(request, 'partials/cart_summary_widget.html', context)
            else:
                # Return JSON for other HTMX requests
                return JsonResponse({
                    'cart_items_count': cart_items.count(),
                    'total_price': float(total_price),
                })

        # Redirect to the cart page if not an HTMX request
        return redirect('store:cart')
    else:
        return redirect('store:index')



@never_cache
@login_required
def view_cart(request):
    if request.user.is_authenticated:
        cart_items = Cart.objects.select_related('item').filter(user=request.user)

        # Check if cart is empty and cleanup session if needed
        from store.cart_utils import auto_cleanup_empty_cart_session
        cleanup_summary = auto_cleanup_empty_cart_session(request, 'retail')
        if cleanup_summary:
            logger.info(f"Empty cart session cleaned up on view_cart: {cleanup_summary}")

        total_price, total_discount = 0, 0

        if request.method == 'POST':
            # Process each discount form submission
            for cart_item in cart_items:
                # Fetch the discount amount using cart_item.id in the input name
                discount = Decimal(request.POST.get(f'discount_amount-{cart_item.id}', 0))
                cart_item.discount_amount = max(discount, 0)
                cart_item.save()

        # Calculate totals
        base_total = 0
        for cart_item in cart_items:
            # Update the price field to match the item's current price
            if cart_item.price != cart_item.item.price:
                cart_item.price = cart_item.item.price
                # This will trigger the save method which recalculates subtotal
                cart_item.save()
            else:
                # Ensure subtotal is correctly calculated even if price hasn't changed
                cart_item.save()  # This will recalculate subtotal with discount

            # Calculate base total (before discount) and total discount
            base_total += cart_item.price * cart_item.quantity
            total_discount += cart_item.discount_amount

        # Calculate final totals
        total_price = base_total  # Total before discount
        total_discounted_price = base_total - total_discount  # Total after discount
        final_total = total_discounted_price

        # Get customer from user-specific session if it exists
        from userauth.session_utils import get_user_customer_id
        customer = None
        customer_id = get_user_customer_id(request)
        if customer_id:
            try:
                customer = Customer.objects.get(id=customer_id)
            except Customer.DoesNotExist:
                pass

        # Define available payment methods and statuses
        payment_methods = ["Cash", "Wallet", "Transfer"]
        statuses = ["Paid", "Unpaid"]

        return render(request, 'store/cart.html', {
            'cart_items': cart_items,
            'total_discount': total_discount,
            'total_price': total_price,
            'total_discounted_price': total_discounted_price,
            'final_total': final_total,
            'customer': customer,
            'payment_methods': payment_methods,
            'statuses': statuses,
        })
    else:
        return redirect('store:index')



@login_required
def update_cart_quantity(request, pk):
    if request.user.is_authenticated:
        # Ensure user can only update their own cart items
        cart_item = get_object_or_404(Cart, id=pk, user=request.user)
        if request.method == 'POST':
            quantity_str = request.POST.get('quantity', '').strip()
            if not quantity_str:
                return JsonResponse({'error': 'Quantity is required'}, status=400)
            try:
                quantity_to_return = int(quantity_str)
            except ValueError:
                return JsonResponse({'error': 'Invalid quantity value'}, status=400)
            if 0 < quantity_to_return <= cart_item.quantity:
                cart_item.item.stock += quantity_to_return
                cart_item.item.save()

                # Adjust DispensingLog entries - consider discounted amount
                discounted_amount = (cart_item.item.price * quantity_to_return) - (cart_item.discount_amount or Decimal('0.00'))
                DispensingLog.objects.filter(
                    user=request.user,
                    name=cart_item.item.name,
                    quantity=quantity_to_return,
                    amount=discounted_amount
                ).delete()

                # Update cart item quantity or remove it
                cart_item.quantity -= quantity_to_return
                if cart_item.quantity > 0:
                    cart_item.save()
                else:
                    cart_item.delete()
                    # Check if cart is now empty and cleanup session if needed
                    from store.cart_utils import auto_cleanup_empty_cart_session
                    cleanup_summary = auto_cleanup_empty_cart_session(request, 'retail')
                    if cleanup_summary:
                        logger.info(f"Cart became empty after item removal, session cleaned up: {cleanup_summary}")

                messages.success(request, f"{quantity_to_return} {cart_item.item.unit} of {cart_item.item.name} removed from cart.")

        return redirect('store:cart')

    else:
        return redirect('store:index')

@login_required
def clear_cart(request):
    if request.user.is_authenticated:
        if request.method == 'POST':
            try:
                with transaction.atomic():
                    # Get cart items specifically for retail
                    cart_items = Cart.objects.filter(user=request.user)

                    if not cart_items.exists():
                        messages.info(request, 'Cart is already empty.')
                        return redirect('store:cart')

                    # Get customer from user-specific session if it exists
                    from userauth.session_utils import get_user_customer_id
                    customer_id = get_user_customer_id(request)
                    current_customer = None
                    if customer_id:
                        try:
                            current_customer = Customer.objects.get(id=customer_id)
                        except Customer.DoesNotExist:
                            pass

                    # Check for completed sales (those WITH receipts) for the current customer
                    completed_sales = Sales.objects.filter(
                        user=request.user,
                        customer=current_customer,
                        receipts__isnull=False  # Sales that have receipts (completed transactions)
                    ).distinct()

                    # Check for pending sales (those WITHOUT receipts) for the current customer
                    pending_sales = Sales.objects.filter(
                        user=request.user,
                        customer=current_customer,
                        receipts__isnull=True  # Sales without receipts (incomplete transactions)
                    ).distinct()

                    # Always clear cart (preserve existing functionality) but only process refunds when receipts exist

                    # Calculate total amount to refund based on actual receipts (not cart items)
                    total_refund = Decimal('0.00')
                    if completed_sales.exists():
                        # Only calculate refunds when there are completed sales with receipts
                        for sale in completed_sales:
                            # Only refund wallet payments (as per business logic)
                            receipts = sale.receipts.filter(payment_method='Wallet')
                            for receipt in receipts:
                                total_refund += receipt.total_amount

                    # Always return items to stock and clear cart (preserve existing functionality)
                    for cart_item in cart_items:
                        # Return items to stock
                        cart_item.item.stock += cart_item.quantity
                        cart_item.item.save()

                        # Remove DispensingLog entries (only if they exist)
                        DispensingLog.objects.filter(
                            user=request.user,
                            name=cart_item.item.name,
                            quantity=cart_item.quantity,
                            status='Dispensed'  # Only remove dispensed logs
                        ).delete()

                    # Process refunds ONLY when receipts exist and refund amount > 0
                    if current_customer and total_refund > 0:
                        try:
                            wallet = current_customer.wallet
                            if wallet:
                                # For registered customers, provide automatic wallet refund when cart is cleared
                                wallet.balance += total_refund
                                wallet.save()

                                # Create transaction history noting the cart clear with wallet refund
                                TransactionHistory.objects.create(
                                    customer=current_customer,
                                    user=request.user,
                                    transaction_type='refund',
                                    amount=total_refund,
                                    description=f'Cart cleared - Refund for returned items (â‚¦{total_refund})'
                                )
                                messages.success(
                                    request,
                                    f'Cart cleared for customer {current_customer.name}. Return value â‚¦{total_refund} refunded to wallet.'
                                )
                        except Wallet.DoesNotExist:
                            messages.warning(
                                request,
                                f'Wallet not found for customer {current_customer.name}'
                            )

                    # Always clear cart items (preserve existing functionality)
                    cart_items.delete()

                    # Comprehensive cart session cleanup after clearing
                    from store.cart_utils import cleanup_cart_session_after_receipt
                    cleanup_summary = cleanup_cart_session_after_receipt(request, 'retail')
                    logger.info(f"Cart session cleanup after cart clear: {cleanup_summary}")

                    # Clean up orphaned sales records without receipts
                    if pending_sales.exists():
                        for sale in pending_sales:
                            # Delete associated sales items first
                            sale.sales_items.all().delete()
                            # Delete the orphaned sale
                            sale.delete()

                    # Provide appropriate success message
                    if total_refund > 0:
                        messages.success(
                            request,
                            'Cart cleared successfully. All items returned to stock and transactions reversed.'
                        )
                    else:
                        messages.success(
                            request,
                            'Cart cleared successfully. All items returned to stock.'
                        )



            except Exception as e:
                messages.error(request, f'Error clearing cart: {str(e)}')
                return redirect('store:cart')

        return redirect('store:cart')
    return redirect('store:index')



@transaction.atomic
@login_required
def send_to_cashier(request):
    """Send payment request to cashier/billing-point/pay-point"""
    if request.user.is_authenticated:
        from userauth.permissions import can_dispense_items
        
        # Check if user can dispense items (is a dispenser)
        if not can_dispense_items(request.user):
            messages.error(request, 'You do not have dispenser permissions to send payment requests.')
            return redirect('store:cart')
        try:
            # Get cart items
            cart_items = Cart.objects.filter(user=request.user)
            if not cart_items.exists():
                messages.error(request, "Your cart is empty. Cannot send payment request.")
                return redirect('store:cart')

            # Get customer info
            from userauth.session_utils import get_user_customer_id
            customer = None
            customer_id = get_user_customer_id(request)
            if customer_id:
                try:
                    customer = Customer.objects.get(id=customer_id)
                except Customer.DoesNotExist:
                    pass

            # Calculate total amount
            total_amount = sum(item.subtotal for item in cart_items)
            
            # Create payment request
            payment_request = PaymentRequest.objects.create(
                dispenser=request.user,
                customer=customer,
                payment_type='retail',
                total_amount=total_amount,
                notes=request.POST.get('notes', ''),
                status='pending'
            )

            # Create payment request items
            for cart_item in cart_items:
                PaymentRequestItem.objects.create(
                    payment_request=payment_request,
                    item_name=cart_item.item.name,
                    brand=cart_item.brand,
                    dosage_form=str(cart_item.dosage_form.dosage_form) if cart_item.dosage_form else '',
                    unit=cart_item.unit,
                    quantity=cart_item.quantity,
                    unit_price=cart_item.price,
                    discount_amount=cart_item.discount_amount,
                    subtotal=cart_item.subtotal,
                    retail_item=cart_item.item
                )

            # Create notification for available cashiers
            from store.models import Notification
            available_cashiers = Cashier.objects.filter(is_active=True)
            for cashier in available_cashiers:
                notification = Notification.objects.create(
                    user=cashier.user,
                    notification_type='payment_request',
                    priority='high',
                    title=f'New Payment Request {payment_request.request_id}',
                    message=f'Payment request of â‚¦{total_amount} from {request.user.username} pending your review.',
                    related_payment_request=payment_request
                )

            # Mark cart items as sent to cashier (optional status change)
            cart_items.update(status='sent_to_cashier')  # You'll need to add this field to Cart model
            
            messages.success(request, f'Payment request {payment_request.request_id} sent to cashier successfully.')
            return redirect('store:payment_requests')
            
        except Exception as e:
            messages.error(request, f'Error sending payment request: {str(e)}')
            return redirect('store:cart')
    
    return redirect('store:index')


@never_cache
@login_required
def payment_requests(request):
    """Show dispenser's payment requests history with date and cashier search"""
    if request.user.is_authenticated:
        from userauth.permissions import can_dispense_items, is_admin_or_manager
        from django.utils.dateparse import parse_date
        
        # Check if user can dispense items (is a dispenser) or is admin/manager
        is_admin_user = is_admin_or_manager(request.user)
        
        # Superusers have access to everything
        if request.user.is_superuser:
            # Continue to the rest of the function
            pass
        elif not can_dispense_items(request.user) and not is_admin_user:
            messages.error(request, 'You do not have permissions to view payment requests.')
            return redirect('store:index')
        
        # Get filter parameters
        start_date = request.GET.get('start_date')
        end_date = request.GET.get('end_date')
        cashier_id = request.GET.get('cashier_id')
        
        # Parse dates
        start_date_parsed = None
        end_date_parsed = None
        if start_date:
            try:
                start_date_parsed = parse_date(start_date)
            except (ValueError, TypeError):
                messages.warning(request, 'Invalid start date format.')
                start_date = None
        
        if end_date:
            try:
                end_date_parsed = parse_date(end_date)
            except (ValueError, TypeError):
                messages.warning(request, 'Invalid end date format.')
                end_date = None
        
        # Base query - show user's requests if dispenser, all if admin/superuser
        if request.user.is_superuser or is_admin_user:
            payment_requests = PaymentRequest.objects.all().order_by('-created_at')
        else:
            payment_requests = PaymentRequest.objects.filter(dispenser=request.user).order_by('-created_at')
        
        # Apply date filters with improved logic
        if start_date_parsed:
            # Create datetime at the start of the day (00:00:00)
            start_datetime = timezone.make_aware(timezone.datetime.combine(start_date_parsed, timezone.datetime.min.time()))
            payment_requests = payment_requests.filter(created_at__gte=start_datetime)
        if end_date_parsed:
            # Create datetime at the end of the day (23:59:59.999999) for inclusive filtering
            end_datetime = timezone.make_aware(timezone.datetime.combine(end_date_parsed, timezone.datetime.max.time()))
            payment_requests = payment_requests.filter(created_at__lte=end_datetime)
        
        # Debug logging for date filtering
        if start_date_parsed or end_date_parsed:
            logger.info(f"Date filter applied - Start: {start_date_parsed}, End: {end_date_parsed}")
            logger.info(f"Filtered payment requests count: {payment_requests.count()}")
        
        # Apply cashier filter
        if cashier_id:
            try:
                from store.models import Cashier
                selected_cashier = Cashier.objects.get(cashier_id=cashier_id)
                payment_requests = payment_requests.filter(cashier=selected_cashier)
            except Cashier.DoesNotExist:
                messages.warning(request, 'Selected cashier not found.')
                cashier_id = None
                selected_cashier = None
        else:
            selected_cashier = None
        
        # Get all cashiers for filter dropdown (only if admin/superuser)
        all_cashiers = None
        if request.user.is_superuser or is_admin_user:
            from store.models import Cashier
            all_cashiers = Cashier.objects.filter(is_active=True).order_by('name')
        
        return render(request, 'store/payment_requests.html', {
            'payment_requests': payment_requests,
            'all_cashiers': all_cashiers,
            'selected_cashier': selected_cashier,
            'start_date': start_date,
            'end_date': end_date,
            'is_admin': request.user.is_superuser or is_admin_user,
        })
    
    return redirect('store:index')


@login_required
def payment_request_detail(request, request_id):
    """Show payment request details"""
    if request.user.is_authenticated:
        from userauth.permissions import is_admin_or_manager
        try:
            payment_request = PaymentRequest.objects.get(request_id=request_id)

            # Check if user is authorized (dispenser, cashier, admin, or superuser)
            is_authorized = (
                payment_request.dispenser == request.user or
                hasattr(request.user, 'cashier') or
                request.user.is_superuser or
                is_admin_or_manager(request.user)
            )

            if not is_authorized:
                messages.error(request, 'You are not authorized to view this payment request.')
                return redirect('store:payment_requests')
            
            return render(request, 'store/payment_request_detail.html', {
                'payment_request': payment_request,
            })
            
        except PaymentRequest.DoesNotExist:
            messages.error(request, 'Payment request not found.')
            return redirect('store:payment_requests')
    
    return redirect('store:index')


@never_cache
@login_required
def cashier_dashboard(request):
    """Cashier dashboard showing pending payment requests"""
    if request.user.is_authenticated:
        from userauth.permissions import is_cashier, is_admin_or_manager

        # Check if user is admin/manager first
        is_admin = is_admin_or_manager(request.user)

        # Use the centralized cashier check function
        if not is_cashier(request.user) and not is_admin:
            messages.error(request, 'You do not have cashier permissions to access this page.')
            return redirect('store:index')

        try:
            # Check if user has a dedicated cashier record
            cashier = request.user.cashier
            is_active = cashier.is_active if cashier else True
        except Cashier.DoesNotExist:
            # User is a cashier through profile or admin/manager
            cashier = None
            is_active = True

        try:
            if not is_active and not is_admin:
                messages.error(request, 'Your cashier account is deactivated.')
                return redirect('store:index')

            # For admin/manager, get all cashiers and check for selected cashier
            all_cashiers = None
            selected_cashier = None
            if is_admin:
                all_cashiers = Cashier.objects.filter(is_active=True).order_by('name')
                selected_cashier_id = request.GET.get('cashier_id')
                if selected_cashier_id:
                    try:
                        selected_cashier = Cashier.objects.get(cashier_id=selected_cashier_id)
                    except Cashier.DoesNotExist:
                        messages.warning(request, 'Selected cashier not found.')

            # Get date filters from request
            start_date = request.GET.get('start_date')
            end_date = request.GET.get('end_date')
            filter_start_date_parsed = None
            filter_end_date_parsed = None
            
            if start_date:
                try:
                    from django.utils.dateparse import parse_date
                    filter_start_date_parsed = parse_date(start_date)
                except (ValueError, TypeError):
                    messages.warning(request, 'Invalid start date format.')
                    start_date = None
                    
            if end_date:
                try:
                    from django.utils.dateparse import parse_date
                    filter_end_date_parsed = parse_date(end_date)
                except (ValueError, TypeError):
                    messages.warning(request, 'Invalid end date format.')
                    end_date = None

            # Get pending payment requests
            pending_requests = PaymentRequest.objects.filter(status='pending').order_by('-created_at')
            
            # Apply date filters to pending requests
            if filter_start_date_parsed:
                start_datetime = timezone.make_aware(timezone.datetime.combine(filter_start_date_parsed, timezone.datetime.min.time()))
                pending_requests = pending_requests.filter(created_at__gte=start_datetime)
            if filter_end_date_parsed:
                end_datetime = timezone.make_aware(timezone.datetime.combine(filter_end_date_parsed, timezone.datetime.max.time()))
                pending_requests = pending_requests.filter(created_at__lte=end_datetime)
            
            # Debug logging for pending requests
            if filter_start_date_parsed or filter_end_date_parsed:
                logger.info(f"Cashier dashboard - Pending requests date filter: {filter_start_date_parsed} to {filter_end_date_parsed}")
                logger.info(f"Filtered pending requests count: {pending_requests.count()}")

            # Get accepted payment requests (separate from completed)
            accepted_requests = PaymentRequest.objects.filter(status='accepted').order_by('-accepted_at')
            
            # Apply date filters to accepted requests
            if filter_start_date_parsed:
                start_datetime = timezone.make_aware(timezone.datetime.combine(filter_start_date_parsed, timezone.datetime.min.time()))
                accepted_requests = accepted_requests.filter(accepted_at__gte=start_datetime)
            if filter_end_date_parsed:
                end_datetime = timezone.make_aware(timezone.datetime.combine(filter_end_date_parsed, timezone.datetime.max.time()))
                accepted_requests = accepted_requests.filter(accepted_at__lte=end_datetime)
            
            # Debug logging for accepted requests
            if filter_start_date_parsed or filter_end_date_parsed:
                logger.info(f"Cashier dashboard - Accepted requests date filter: {filter_start_date_parsed} to {filter_end_date_parsed}")
                logger.info(f"Filtered accepted requests count: {accepted_requests.count()}")

            # Filter for specific cashier if not admin, or if admin selected a cashier
            if is_admin and selected_cashier:
                # Admin selected a specific cashier
                accepted_requests = accepted_requests.filter(cashier=selected_cashier)
                my_requests = PaymentRequest.objects.filter(
                    cashier=selected_cashier,
                    status='completed'
                ).order_by('-completed_at')
            elif is_admin and not selected_cashier:
                # Admin viewing all cashiers
                my_requests = PaymentRequest.objects.filter(
                    status='completed'
                ).order_by('-completed_at')
            elif cashier:
                # Regular cashier with dedicated record
                accepted_requests = accepted_requests.filter(cashier=cashier)
                my_requests = PaymentRequest.objects.filter(
                    Q(cashier=cashier) | Q(cashier__isnull=True),
                    status='completed'
                ).order_by('-completed_at')
            else:
                # For profile-based cashiers, use user as identifier
                accepted_requests = accepted_requests.filter(cashier__user=request.user)
                my_requests = PaymentRequest.objects.filter(
                    Q(cashier__user=request.user) | Q(cashier__isnull=True),
                    status='completed'
                ).order_by('-completed_at')
            
            # Apply date filters to my_requests
            if filter_start_date_parsed:
                start_datetime = timezone.make_aware(timezone.datetime.combine(filter_start_date_parsed, timezone.datetime.min.time()))
                my_requests = my_requests.filter(completed_at__gte=start_datetime)
            if filter_end_date_parsed:
                end_datetime = timezone.make_aware(timezone.datetime.combine(filter_end_date_parsed, timezone.datetime.max.time()))
                my_requests = my_requests.filter(completed_at__lte=end_datetime)
            
            # Debug logging for completed requests
            if filter_start_date_parsed or filter_end_date_parsed:
                logger.info(f"Cashier dashboard - Completed requests date filter: {filter_start_date_parsed} to {filter_end_date_parsed}")
                logger.info(f"Filtered completed requests count: {my_requests.count()}")
            
            # Calculate comprehensive statistics
            # Filter all_processed by cashier if selected
            all_processed = PaymentRequest.objects.filter(status='completed')
            if is_admin and selected_cashier:
                all_processed = all_processed.filter(cashier=selected_cashier)
            elif cashier and not is_admin:
                all_processed = all_processed.filter(Q(cashier=cashier) | Q(cashier__isnull=True))
            elif not is_admin:
                all_processed = all_processed.filter(Q(cashier__user=request.user) | Q(cashier__isnull=True))

            # Apply date filters to completed count
            completed_in_range = all_processed
            if filter_start_date_parsed:
                start_datetime = timezone.make_aware(timezone.datetime.combine(filter_start_date_parsed, timezone.datetime.min.time()))
                completed_in_range = completed_in_range.filter(completed_at__gte=start_datetime)
            if filter_end_date_parsed:
                end_datetime = timezone.make_aware(timezone.datetime.combine(filter_end_date_parsed, timezone.datetime.max.time()))
                completed_in_range = completed_in_range.filter(completed_at__lte=end_datetime)

            stats = {
                'pending_count': pending_requests.count(),
                'completed_today_count': completed_in_range.count(),  # Now respects date filter
                'total_processed_count': my_requests.count(),
                'total_value': my_requests.aggregate(total=models.Sum('total_amount'))['total'] or 0,
                'pending_value': pending_requests.aggregate(total=models.Sum('total_amount'))['total'] or 0,
            }
            
            # Create cashier info for template (handle both record-based and profile-based cashiers)
            cashier_info = cashier
            if cashier_info is None and not is_admin:
                # Create a mock cashier object for profile-based cashiers
                class MockCashier:
                    def __init__(self, user):
                        self.name = user.profile.full_name if user.profile else user.username
                        self.cashier_id = f"PROFILE-{user.id}"
                    def __str__(self):
                        return self.name

                cashier_info = MockCashier(request.user)

            # Get daily payment totals
            from datetime import timedelta

            # Use user's selected date filter or default to last 7 days
            if filter_start_date_parsed and filter_end_date_parsed:
                daily_start_date = filter_start_date_parsed
                daily_end_date = filter_end_date_parsed
            else:
                daily_end_date = timezone.now().date()
                daily_start_date = daily_end_date - timedelta(days=7)  # Last 7 days

            if is_admin and selected_cashier:
                # Get daily totals for the selected cashier only
                daily_payment_totals = get_cashier_daily_payment_totals(selected_cashier.user, daily_start_date, daily_end_date)
            else:
                # Get daily totals for current user or all cashiers
                daily_payment_totals = get_cashier_daily_payment_totals(request.user, daily_start_date, daily_end_date)

            # Calculate period total and today's total
            period_total = Decimal('0.00')
            today_total = Decimal('0.00')
            today_payment_methods = {}

            for day_data in daily_payment_totals:
                for cashier_data in day_data['cashiers']:
                    period_total += cashier_data['total_amount']
                    if day_data['date'] == timezone.now().date():
                        today_total += cashier_data['total_amount']
                        # Aggregate payment methods for today
                        for method, amount in cashier_data['payment_methods'].items():
                            if method in today_payment_methods:
                                today_payment_methods[method] += amount
                            else:
                                today_payment_methods[method] = amount

            # Filter my_requests to show only today's processed payments
            today_processed_requests = my_requests.filter(completed_at__date=timezone.now().date())

            return render(request, 'store/cashier_dashboard.html', {
                'pending_requests': pending_requests,
                'accepted_requests': accepted_requests,
                'my_requests': my_requests,
                'today_processed_requests': today_processed_requests,
                'cashier': cashier_info,
                'is_admin': is_admin,
                'all_cashiers': all_cashiers,
                'selected_cashier': selected_cashier,
                'stats': stats,
                'daily_payment_totals': daily_payment_totals,
                'period_total': period_total,  # Changed from seven_day_total to period_total
                'today_total': today_total,
                'today_payment_methods': today_payment_methods,
                'start_date': start_date,
                'end_date': end_date,
                'daily_start_date': daily_start_date,  # Pass the actual date range used
                'daily_end_date': daily_end_date,
            })
                
        except Exception as e:
            # Handle any errors
            messages.error(request, f'Error loading cashier dashboard: {str(e)}')
            return redirect('store:index')
    
    return redirect('store:index')


@transaction.atomic
@login_required
def accept_payment_request(request, request_id):
    """Accept a payment request"""
    if request.user.is_authenticated:
        try:
            payment_request = PaymentRequest.objects.get(request_id=request_id)
            
            # Check if user is a cashier or admin
            is_cashier = (hasattr(request.user, 'cashier') or 
                        (hasattr(request.user, 'profile') and request.user.profile and 
                         request.user.profile.user_type == 'Cashier'))
            
            if not (is_cashier or request.user.is_superuser or 
                (hasattr(request.user, 'profile') and request.user.profile and 
                 request.user.profile.user_type in ['Admin', 'Manager'])):
                messages.error(request, 'You are not authorized to accept payment requests.')
                return redirect('store:cashier_dashboard')
            
            if payment_request.status != 'pending':
                messages.error(request, 'This payment request has already been processed.')
                return redirect('store:cashier_dashboard')
            
            # Assign to cashier if not admin
            if hasattr(request.user, 'cashier'):
                payment_request.cashier = request.user.cashier
            elif is_cashier and not request.user.is_superuser:
                # For profile-based cashiers, find or create cashier record
                try:
                    cashier = request.user.cashier
                    payment_request.cashier = cashier
                except Cashier.DoesNotExist:
                    # Create cashier record if it doesn't exist
                    from store.models import Cashier
                    cashier = Cashier.objects.create(
                        user=request.user,
                        name=request.user.profile.full_name if request.user.profile else request.user.username,
                        is_active=True
                    )
                    payment_request.cashier = cashier
            
            payment_request.status = 'accepted'
            payment_request.accepted_at = timezone.now()
            payment_request.save()
            
            messages.success(request, f'Payment request {request_id} accepted successfully. You can now complete the payment.')
            return redirect('store:payment_request_detail', request_id=request_id)
            
        except PaymentRequest.DoesNotExist:
            messages.error(request, 'Payment request not found.')
            return redirect('store:cashier_dashboard')
    
    return redirect('store:index')


@login_required
def reject_payment_request(request, request_id):
    """Reject a payment request"""
    if request.user.is_authenticated:
        try:
            payment_request = PaymentRequest.objects.get(request_id=request_id)
            
            # Check if user is a cashier or admin
            is_cashier = (hasattr(request.user, 'cashier') or 
                        (hasattr(request.user, 'profile') and request.user.profile and 
                         request.user.profile.user_type == 'Cashier'))
            
            if not (is_cashier or request.user.is_superuser or 
                (hasattr(request.user, 'profile') and request.user.profile and 
                 request.user.profile.user_type in ['Admin', 'Manager'])):
                messages.error(request, 'You are not authorized to reject payment requests.')
                return redirect('store:cashier_dashboard')
            
            if payment_request.status != 'pending':
                messages.error(request, 'This payment request has already been processed.')
                return redirect('store:cashier_dashboard')
            
            payment_request.status = 'rejected'
            payment_request.save()
            
            # Return items to stock and clear cart
            for payment_item in payment_request.items.all():
                if payment_item.retail_item:
                    payment_item.retail_item.stock += payment_item.quantity
                    payment_item.retail_item.save()
            
            # Clear the cart for the dispenser whose payment request was rejected
            try:
                # Clear all cart items for the original dispenser
                from store.models import Cart
                Cart.objects.filter(user=payment_request.dispenser).delete()
                
                # Comprehensive cart session cleanup for the dispenser
                from store.cart_utils import cleanup_cart_session_after_receipt
                # We need to create a mock request object for the cart cleanup
                # Since we can't access the original dispenser's request,
                # we'll clear the cart items directly
                logger.info(f"Cleared cart for user {payment_request.dispenser.username} after payment request rejection")
                
            except Exception as e:
                logger.warning(f"Error clearing cart after payment request rejection: {e}")
            
            messages.success(request, f'Payment request {request_id} rejected. Items returned to stock and cart cleared.')
            return redirect('store:cashier_dashboard')
            
        except PaymentRequest.DoesNotExist:
            messages.error(request, 'Payment request not found.')
            return redirect('store:cashier_dashboard')
    
    return redirect('store:index')


@transaction.atomic
@login_required
def complete_payment_request(request, request_id):
    """Complete a payment request and generate receipt"""
    if request.user.is_authenticated:
        try:
            payment_request = PaymentRequest.objects.get(request_id=request_id)
            
            # Check if user is the assigned cashier or admin
            is_cashier = (hasattr(request.user, 'cashier') or 
                        (hasattr(request.user, 'profile') and request.user.profile and 
                         request.user.profile.user_type == 'Cashier'))
            
            if not (is_cashier or request.user.is_superuser or 
                (hasattr(request.user, 'profile') and request.user.profile and 
                 request.user.profile.user_type in ['Admin', 'Manager'])):
                messages.error(request, 'You are not authorized to complete this payment request.')
                return redirect('store:cashier_dashboard')
            
            if payment_request.status != 'accepted':
                messages.error(request, 'This payment request must be accepted first.')
                return redirect('store:cashier_dashboard')
            
            if request.method == 'POST':
                payment_method = request.POST.get('payment_method')
                payment_status = request.POST.get('payment_status', 'Paid')

                if not payment_method:
                    messages.error(request, 'Payment method is required.')
                    return redirect('store:cashier_dashboard')

                # Get cashier object if user is a cashier
                cashier = None
                if hasattr(request.user, 'cashier'):
                    cashier = request.user.cashier
                elif is_cashier and not request.user.is_superuser:
                    # For profile-based cashiers, find or create cashier record
                    try:
                        cashier = request.user.cashier
                    except Cashier.DoesNotExist:
                        # Create cashier record if it doesn't exist
                        from store.models import Cashier
                        cashier = Cashier.objects.create(
                            user=request.user,
                            name=request.user.profile.full_name if request.user.profile else request.user.username,
                            is_active=True
                        )

                # Create sales and receipt
                sales = Sales.objects.create(
                    user=payment_request.dispenser,
                    customer=payment_request.customer,
                    total_amount=payment_request.total_amount
                )

                receipt = Receipt.objects.create(
                    customer=payment_request.customer,
                    sales=sales,
                    cashier=cashier,
                    buyer_name=payment_request.customer.name if payment_request.customer else 'WALK-IN CUSTOMER',
                    buyer_address=payment_request.customer.address if payment_request.customer else '',
                    total_amount=payment_request.total_amount,
                    payment_method=payment_method,
                    status=payment_status
                )
                
                # Create sales items from payment request items
                for payment_item in payment_request.items.all():
                    if payment_item.retail_item:
                        SalesItem.objects.create(
                            sales=sales,
                            item=payment_item.retail_item,
                            price=payment_item.unit_price,
                            quantity=payment_item.quantity,
                            discount_amount=payment_item.discount_amount,
                            brand=payment_item.brand
                        )
                        
                        # Update stock
                        payment_item.retail_item.stock -= payment_item.quantity
                        payment_item.retail_item.save()
                        
                        # Create dispensing log
                        DispensingLog.objects.create(
                            user=payment_request.dispenser,
                            name=payment_item.item_name,
                            brand=payment_item.brand,
                            unit=payment_item.unit,
                            quantity=payment_item.quantity,
                            amount=payment_item.subtotal,
                            discount_amount=payment_item.discount_amount,
                            status='Dispensed'
                        )
                
                # Update payment request
                payment_request.status = 'completed'
                payment_request.completed_at = timezone.now()
                payment_request.receipt = receipt
                payment_request.save()
                
                # Clear the original cart items that were used to create this payment request
                try:
                    cart_items = Cart.objects.filter(user=payment_request.dispenser)
                    # Remove cart items that correspond to the payment request items
                    for payment_item in payment_request.items.all():
                        if payment_item.retail_item:
                            cart_items.filter(item=payment_item.retail_item).delete()
                    
                    # Comprehensive cart session cleanup after receipt generation
                    from store.cart_utils import cleanup_cart_session_after_receipt
                    cleanup_summary = cleanup_cart_session_after_receipt(request, 'retail')
                    logger.info(f"Cart session cleanup after payment request completion: {cleanup_summary}")
                except Exception as e:
                    logger.warning(f"Error clearing cart after payment request completion: {e}")
                
                messages.success(request, f'Payment request {request_id} completed successfully. Receipt generated.')
                return redirect('store:receipt_detail', receipt_id=receipt.receipt_id)
            
            # Show payment completion form
            return render(request, 'store/complete_payment_request.html', {
                'payment_request': payment_request,
            })
            
        except PaymentRequest.DoesNotExist:
            messages.error(request, 'Payment request not found.')
            return redirect('store:cashier_dashboard')
    
    return redirect('store:index')


@transaction.atomic
@login_required
def receipt(request):
    if request.user.is_authenticated:
        print("\n==== RECEIPT GENERATION DEBUG =====")
        print(f"Request method: {request.method}")
        print(f"POST data: {request.POST}")

        buyer_name = request.POST.get('buyer_name', '')
        buyer_address = request.POST.get('buyer_address', '')

        print(f"Buyer name: {buyer_name}")
        print(f"Buyer address: {buyer_address}")

        # Check if this is a split payment
        payment_type = request.POST.get('payment_type', 'single')

        if payment_type == 'split':
            # This is a split payment
            payment_method = 'Split'
            payment_method_1 = request.POST.get('payment_method_1')
            payment_method_2 = request.POST.get('payment_method_2')

            print(f"Split payment detected")
            print(f"Payment method 1: {payment_method_1}")
            print(f"Payment method 2: {payment_method_2}")

            try:
                payment_amount_1 = Decimal(request.POST.get('payment_amount_1', '0'))
                payment_amount_2 = Decimal(request.POST.get('payment_amount_2', '0'))
                print(f"Payment amount 1: {payment_amount_1}")
                print(f"Payment amount 2: {payment_amount_2}")
            except Exception as e:
                print(f"Error converting payment amounts: {e}")
                payment_amount_1 = Decimal('0')
                payment_amount_2 = Decimal('0')

            status = request.POST.get('split_status', 'Paid')
            print(f"Split payment status: {status}")

            # Validate the payment methods and amounts
            if not payment_method_1 or not payment_method_2:
                messages.error(request, "Please select both payment methods for split payment.")
                return redirect('store:cart')

            if payment_amount_1 <= 0:
                messages.error(request, "First payment amount must be greater than zero.")
                return redirect('store:cart')
        else:
            # This is a single payment
            payment_method = request.POST.get('payment_method')
            status = request.POST.get('status')

            # If not provided in POST, try to get from user session (from select_items)
            if not payment_method or not status:
                from userauth.session_utils import get_user_payment_data
                session_payment_data = get_user_payment_data(request)
                if not payment_method:
                    payment_method = session_payment_data.get('payment_method')
                if not status:
                    status = session_payment_data.get('payment_status')

            # Final defaults if still not set
            if not status:
                status = 'Paid'  # Default to 'Paid' if not provided

            payment_method_1 = None
            payment_method_2 = None
            payment_amount_1 = Decimal('0')
            payment_amount_2 = Decimal('0')

        # Dump all POST data for debugging
        print("\n\n==== ALL POST DATA: =====")
        for key, value in request.POST.items():
            print(f"  {key}: {value}")
        print(f"\nDirect access - Payment Type: {payment_type}, Payment Method: {payment_method}, Status: {status}\n")
        if payment_type == 'split':
            print(f"Split Payment - Method 1: {payment_method_1}, Amount 1: {payment_amount_1}")
            print(f"Split Payment - Method 2: {payment_method_2}, Amount 2: {payment_amount_2}")

        # Get customer ID from user-specific session if it exists
        from userauth.session_utils import get_user_customer_id
        customer_id = get_user_customer_id(request)
        customer = None
        has_customer = False
        if customer_id:
            try:
                customer = Customer.objects.get(id=customer_id)
                has_customer = True
            except Customer.DoesNotExist:
                pass

        # Set default values based on customer presence if not provided
        if not payment_method and payment_type != 'split':
            if has_customer:  # If this is a registered customer
                payment_method = "Wallet"  # Default for registered customers
            else:  # For walk-in customers
                payment_method = "Cash"  # Default for walk-in customers

        if not status:
            # Default status is "Paid" for all customers (both registered and walk-in)
            status = "Paid"

        print(f"After initial defaults - Payment Type: {payment_type}, Payment Method: {payment_method}, Status: {status}")

        cart_items = Cart.objects.filter(user=request.user)
        if not cart_items.exists():
            messages.warning(request, "No items in the cart.")
            return redirect('store:cart')

        total_price, total_discount = 0, 0

        for cart_item in cart_items:
            subtotal = cart_item.item.price * cart_item.quantity
            total_price += subtotal
            total_discount += getattr(cart_item, 'discount_amount', 0)

        total_discounted_price = total_price - total_discount
        final_total = total_discounted_price if total_discount > 0 else total_price

        # Customer is already retrieved above, no need to fetch again

        # Always create a new Sales instance to avoid conflicts
        sales = Sales.objects.create(
            user=request.user,
            customer=customer,
            total_amount=final_total
        )

        try:
            receipt = Receipt.objects.filter(sales=sales).first()
            if not receipt:
                # Ensure we're using the payment_method and status from the beginning of the function
                # This ensures we use the values selected by the user

                # Ensure payment_method and status have valid values
                if payment_method not in ["Cash", "Wallet", "Transfer", "Split"]:
                    if sales.customer:
                        payment_method = "Wallet"  # Default for registered customers
                    else:
                        payment_method = "Cash"  # Default for walk-in customers

                if status not in ["Paid", "Partially Paid", "Unpaid"]:
                    # Default status based on customer type
                    if sales.customer:
                        status = "Paid"  # Registered customers default to Paid
                    else:
                        status = "Paid"  # Walk-in customers also default to Paid

                # Force the values for debugging purposes
                print(f"\n==== FORCING VALUES FOR RECEIPT =====")
                print(f"Customer: {sales.customer}")
                print(f"Payment Method: {payment_method}")
                print(f"Status: {status}\n")

                print(f"\n==== FINAL VALUES =====")
                print(f"Payment Method: {payment_method}")
                print(f"Status: {status}\n")

                # Generate a unique receipt ID using uuid
                import uuid
                receipt_id = str(uuid.uuid4())[:5]  # Use first 5 characters of a UUID

                # Create the receipt WITHOUT payment method and status first
                receipt = Receipt.objects.create(
                    sales=sales,
                    receipt_id=receipt_id,
                    total_amount=final_total,
                    customer=sales.customer,
                    buyer_name=buyer_name if not sales.customer else sales.customer.name,
                    buyer_address=buyer_address if not sales.customer else sales.customer.address,
                    date=datetime.now()
                )

                # Now explicitly set the payment method and status
                receipt.payment_method = payment_method
                receipt.status = status

                # Check if wallet went negative (from session for single payments)
                if request.session.get('wallet_went_negative', False):
                    receipt.wallet_went_negative = True
                    # Clear the session flag
                    del request.session['wallet_went_negative']

                receipt.save()

                # If this is a split payment, create the payment records
                if payment_type == 'split':
                    # Handle wallet payments for registered customers
                    if has_customer:
                        # Only deduct the amount specified for wallet payment method
                        wallet_amount = Decimal('0.00')
                        if payment_method_1 == 'Wallet':
                            wallet_amount = Decimal(str(payment_amount_1))
                            # Deduct from customer's wallet
                            try:
                                wallet = Wallet.objects.get(customer=sales.customer)
                                # Check if wallet will go negative
                                wallet_balance_before = wallet.balance
                                # Allow negative balance
                                wallet.balance -= wallet_amount
                                wallet.save()

                                # Check if wallet went negative and set flag
                                if wallet_balance_before >= 0 and wallet.balance < 0:
                                    receipt.wallet_went_negative = True
                                    receipt.save()

                                # Transaction history will be created later to avoid duplicates

                                print(f"Deducted {wallet_amount} from customer {sales.customer.name}'s wallet for first payment")
                                # Inform if balance is negative
                                if wallet.balance < 0:
                                    print(f"Info: Customer {sales.customer.name} now has a negative wallet balance of {wallet.balance}")
                                    messages.info(request, f"Customer {sales.customer.name} now has a negative wallet balance of {wallet.balance}")
                            except Wallet.DoesNotExist:
                                print(f"Error: Wallet not found for customer {sales.customer.name}")
                                messages.error(request, f"Error: Wallet not found for customer {sales.customer.name}")

                        if payment_method_2 == 'Wallet':
                            wallet_amount = Decimal(str(payment_amount_2))
                            # Deduct from customer's wallet
                            try:
                                wallet = Wallet.objects.get(customer=sales.customer)
                                # Check if wallet will go negative
                                wallet_balance_before = wallet.balance
                                # Allow negative balance
                                wallet.balance -= wallet_amount
                                wallet.save()

                                # Check if wallet went negative and set flag
                                if wallet_balance_before >= 0 and wallet.balance < 0:
                                    receipt.wallet_went_negative = True
                                    receipt.save()

                                # Transaction history will be created later to avoid duplicates

                                print(f"Deducted {wallet_amount} from customer {sales.customer.name}'s wallet for second payment")
                                # Inform if balance is negative
                                if wallet.balance < 0:
                                    print(f"Info: Customer {sales.customer.name} now has a negative wallet balance of {wallet.balance}")
                                    messages.info(request, f"Customer {sales.customer.name} now has a negative wallet balance of {wallet.balance}")
                            except Wallet.DoesNotExist:
                                print(f"Error: Wallet not found for customer {sales.customer.name}")
                                messages.error(request, f"Error: Wallet not found for customer {sales.customer.name}")

                    # Create the first payment
                    try:
                        print(f"\n==== CREATING RECEIPT PAYMENT RECORDS =====")
                        print(f"Receipt ID: {receipt.receipt_id}")
                        print(f"Payment method 1: {payment_method_1}, Amount 1: {payment_amount_1}")
                        print(f"Payment method 2: {payment_method_2}, Amount 2: {payment_amount_2}")

                        payment1 = ReceiptPayment.objects.create(
                            receipt=receipt,
                            amount=payment_amount_1,
                            payment_method=payment_method_1,
                            status=status,
                            date=datetime.now()
                        )
                        print(f"Created first payment record: {payment1.id}")

                        # Create the second payment
                        payment2 = ReceiptPayment.objects.create(
                            receipt=receipt,
                            amount=payment_amount_2,
                            payment_method=payment_method_2,
                            status=status,
                            date=datetime.now()
                        )
                        print(f"Created second payment record: {payment2.id}")
                    except Exception as e:
                        print(f"Error creating payment records: {e}")

                    print(f"\n==== CREATED SPLIT PAYMENTS =====")
                    print(f"Payment 1: {payment_method_1} - {payment_amount_1}")
                    print(f"Payment 2: {payment_method_2} - {payment_amount_2}")

                # Double-check that the payment method and status were set correctly
                # Refresh from database to ensure we see the actual saved values
                receipt.refresh_from_db()
                print(f"\n==== CREATED RECEIPT =====")
                print(f"Receipt ID: {receipt.receipt_id}")
                print(f"Payment Method: {receipt.payment_method}")
                print(f"Status: {receipt.status}\n")

                # Create transaction history for non-wallet payments (to avoid duplicates)
                if sales.customer and payment_type != 'split':
                    # Only create transaction history for non-wallet payments
                    # Wallet payments already create their own transaction history above
                    if receipt.payment_method != 'Wallet':
                        from customer.models import TransactionHistory
                        TransactionHistory.objects.create(
                            customer=sales.customer,
                            user=request.user,
                            transaction_type='purchase',
                            amount=sales.total_amount,
                            description=f'Purchase payment via {receipt.payment_method} (Receipt ID: {receipt.receipt_id})'
                        )
                    # For wallet payments, deduct from wallet and create transaction history
                    elif receipt.payment_method == 'Wallet' and sales.customer:
                        from customer.models import TransactionHistory
                        try:
                            wallet = Wallet.objects.get(customer=sales.customer)
                            # Check if wallet will go negative
                            wallet_balance_before = wallet.balance
                            wallet.balance -= sales.total_amount
                            wallet.save()

                            # Check if wallet went negative and set flag
                            if wallet_balance_before >= 0 and wallet.balance < 0:
                                receipt.wallet_went_negative = True
                                receipt.save()

                            # Create transaction history entry
                            TransactionHistory.objects.create(
                                customer=sales.customer,
                                user=request.user,
                                transaction_type='purchase',
                                amount=sales.total_amount,
                                description=f'Purchase payment from wallet (Receipt ID: {receipt.receipt_id})'
                            )
                        except Wallet.DoesNotExist:
                            messages.warning(request, f'Wallet not found for customer {sales.customer.name}')

                # Clear payment session data after successful receipt creation
                from userauth.session_utils import delete_user_session_data
                delete_user_session_data(request, 'payment_method')
                delete_user_session_data(request, 'payment_status')
        except Exception as e:
            print(f"Error processing receipt: {e}")
            messages.error(request, "An error occurred while processing the receipt.")
            return redirect('store:cart')

        for cart_item in cart_items:
            SalesItem.objects.get_or_create(
                sales=sales,
                item=cart_item.item,
                defaults={
                    'quantity': cart_item.quantity,
                    'price': cart_item.item.price,
                    'discount_amount': cart_item.discount_amount
                }
            )

            subtotal = cart_item.item.price * cart_item.quantity
            # Get or create Formulation object for dosage_form
            dosage_form_obj = None
            if cart_item.item.dosage_form:
                dosage_form_obj, created = Formulation.objects.get_or_create(
                    dosage_form=cart_item.item.dosage_form
                )

            # Calculate discounted amount for dispensing log
            discounted_amount = subtotal - cart_item.discount_amount

            DispensingLog.objects.create(
                user=request.user,
                name=cart_item.item.name,
                brand=cart_item.item.brand,
                dosage_form=dosage_form_obj,
                unit=cart_item.item.unit,
                quantity=cart_item.quantity,
                amount=discounted_amount,
                discount_amount=cart_item.discount_amount,
                status="Dispensed"
            )

            # Create ItemSelectionHistory entry for purchase (only when receipt is generated)
            if sales.customer:
                ItemSelectionHistory.objects.create(
                    customer=sales.customer,
                    user=request.user,
                    item=cart_item.item,
                    quantity=cart_item.quantity,
                    action='purchase',
                    unit_price=cart_item.item.price,
                )

        request.session['receipt_data'] = {
            'total_price': float(total_price),
            'total_discount': float(total_discount),
            'buyer_address': buyer_address,
        }
        request.session['receipt_id'] = str(receipt.receipt_id)

        # Mark cart items as processed before deleting
        cart_items.update(status='processed')
        cart_items.delete()

        # Comprehensive cart session cleanup after receipt generation
        from store.cart_utils import cleanup_cart_session_after_receipt
        cleanup_summary = cleanup_cart_session_after_receipt(request, 'retail')
        logger.info(f"Cart session cleanup after receipt: {cleanup_summary}")

        daily_sales_data = get_daily_sales()
        monthly_sales_data = get_monthly_sales_with_expenses()

        sales_items = sales.sales_items.all()

        payment_methods = ["Cash", "Wallet", "Transfer"]
        statuses = ["Paid", "Unpaid"]

        # Double-check the receipt values one more time before rendering
        receipt.refresh_from_db()
        print(f"\n==== FINAL RECEIPT VALUES BEFORE RENDERING =====")
        print(f"Receipt ID: {receipt.receipt_id}")
        print(f"Payment Method: {receipt.payment_method}")
        print(f"Status: {receipt.status}\n")

        # Set appropriate payment method and status based on customer type and payment type
        if has_customer and payment_type != 'split' and receipt.customer:
            # For registered customers with single payment, default to Wallet if not specified
            if not receipt.payment_method or receipt.payment_method == 'Cash':
                print(f"Setting payment method to Wallet for customer {receipt.customer.name}")
                receipt.payment_method = 'Wallet'
                receipt.save()

            # Only set status to 'Paid' if no status was set at all (respect user's choice)
            if not receipt.status:
                print(f"Setting default status to Paid for customer {receipt.customer.name} (no status was set)")
                receipt.status = 'Paid'
                receipt.save()

            receipt.refresh_from_db()
        elif has_customer and payment_type == 'split' and receipt.customer:
            # For split payments with registered customers, ensure the payment method is 'Split'
            if receipt.payment_method != 'Split':
                print(f"Setting payment method to Split for customer {receipt.customer.name}")
                receipt.payment_method = 'Split'
                receipt.save()
                receipt.refresh_from_db()
        else:
            # For walk-in customers, respect the selected payment method and status
            # Only default to 'Paid' if status is not explicitly set
            if not receipt.status:
                print(f"Setting default status to Paid for walk-in customer")
                receipt.status = 'Paid'
                receipt.save()
                receipt.refresh_from_db()

        # Get split payment details if this is a split payment
        split_payment_details = None
        if payment_type == 'split':
            split_payment_details = {
                'payment_method_1': payment_method_1,
                'payment_method_2': payment_method_2,
                'payment_amount_1': float(payment_amount_1),
                'payment_amount_2': float(payment_amount_2),
            }

            # Store the split payment details in the session for later use
            request.session['split_payment_details'] = split_payment_details
            request.session['split_payment_receipt_id'] = receipt.receipt_id

        # Fetch receipt payments directly
        receipt_payments = receipt.receipt_payments.all() if receipt.payment_method == 'Split' else None

        # Render to the receipt template
        try:
            return render(request, 'store/receipt.html', {
                'receipt': receipt,
                'sales': sales,
                'sales_items': sales_items,
                'total_price': total_price,
                'total_discount': total_discount,
                'total_discounted_price': total_discounted_price,
                'daily_sales': daily_sales_data,
                'monthly_sales': monthly_sales_data,
                'logs': DispensingLog.objects.filter(user=request.user),
                'payment_methods': payment_methods,
                'statuses': statuses,
                'split_payment_details': split_payment_details,
                'receipt_payments': receipt_payments,
                'payment_type': payment_type,
            })
        except Exception as e:
            logger.error(f"Error rendering receipt detail for {receipt_id}: {e}")
            messages.error(request, f"Error displaying receipt: {receipt_id}")
            return redirect('store:receipt_list')
    else:
        return redirect('store:index')



@login_required
def receipt_detail(request, receipt_id):
    if request.user.is_authenticated:
        # First check if this receipt ID belongs to a wholesale receipt
        try:
            wholesale_receipt = WholesaleReceipt.objects.filter(receipt_id=receipt_id).first()
            if wholesale_receipt:
                # This is a wholesale receipt, redirect to wholesale receipt detail
                messages.info(request, 'This is a wholesale receipt. Redirecting to wholesale receipt view.')
                return redirect('wholesale:wholesale_receipt_detail', receipt_id=receipt_id)
        except Exception as e:
            logger.error(f"Error checking for wholesale receipt {receipt_id}: {e}")

        try:
            # Retrieve the existing retail receipt
            receipt = get_object_or_404(Receipt, receipt_id=receipt_id)
        except Exception as e:
            logger.error(f"Error retrieving receipt {receipt_id}: {e}")
            messages.error(request, f"Receipt not found: {receipt_id}")
            return redirect('store:receipt_list')

        # Respect the user's selected payment status - don't force to "Paid"
        print(f"Receipt {receipt.receipt_id} status: {receipt.status}")

        # Retrieve sales and sales items linked to the receipt
        sales = receipt.sales
        sales_items = sales.sales_items.all() if sales else []

        # Calculate totals for the receipt
        total_price = sum(item.subtotal for item in sales_items)
        total_discount = Decimal('0.0')  # Modify if a discount amount is present in `Receipt`
        total_discounted_price = total_price - total_discount

        # Update and save the receipt with calculated totals
        receipt.total_amount = total_discounted_price
        receipt.save()

        # If this is a split payment receipt but has no payment records, create them
        if receipt.payment_method == 'Split' and not receipt.receipt_payments.exists():
            print(f"Creating payment records for split payment receipt {receipt.receipt_id}")

            # Check if we have stored split payment details for this receipt
            stored_details = None
            try:
                if request.session.get('split_payment_receipt_id') == receipt.receipt_id:
                    stored_details = request.session.get('split_payment_details')
                    print(f"Found stored split payment details: {stored_details}")
            except Exception as e:
                logger.error(f"Error accessing session data for receipt {receipt_id}: {e}")
                stored_details = None

            if stored_details:
                # Use the stored payment details
                payment_method_1 = stored_details.get('payment_method_1')
                payment_method_2 = stored_details.get('payment_method_2')
                payment_amount_1 = Decimal(str(stored_details.get('payment_amount_1', 0)))
                payment_amount_2 = Decimal(str(stored_details.get('payment_amount_2', 0)))

                # Create the payment records using the stored details
                ReceiptPayment.objects.create(
                    receipt=receipt,
                    amount=payment_amount_1,
                    payment_method=payment_method_1,
                    status='Paid',
                    date=receipt.date
                )
                ReceiptPayment.objects.create(
                    receipt=receipt,
                    amount=payment_amount_2,
                    payment_method=payment_method_2,
                    status='Paid',
                    date=receipt.date
                )
                print(f"Created payment records using stored details: {payment_method_1}: {payment_amount_1}, {payment_method_2}: {payment_amount_2}")
            else:
                # No stored details, use reasonable defaults based on customer type
                if receipt.customer:
                    # For registered customers, it's more likely they used their wallet
                    # Assume 70% wallet, 30% cash or transfer as a reasonable default
                    wallet_amount = receipt.total_amount * Decimal('0.7')
                    cash_amount = receipt.total_amount - wallet_amount

                    # Create the payment records
                    ReceiptPayment.objects.create(
                        receipt=receipt,
                        amount=wallet_amount,
                        payment_method='Wallet',
                        status='Paid',
                        date=receipt.date
                    )
                    ReceiptPayment.objects.create(
                        receipt=receipt,
                        amount=cash_amount,
                        payment_method='Cash',
                        status='Paid',
                        date=receipt.date
                    )
                    print(f"Created payment records for registered customer: Wallet: {wallet_amount}, Cash: {cash_amount}")
                else:
                    # For walk-in customers, it's more likely they used cash and transfer
                    # Assume 70% cash, 30% transfer as a reasonable default
                    cash_amount = receipt.total_amount * Decimal('0.7')
                    transfer_amount = receipt.total_amount - cash_amount

                    # Create the payment records
                    ReceiptPayment.objects.create(
                        receipt=receipt,
                        amount=cash_amount,
                        payment_method='Cash',
                        status='Paid',
                        date=receipt.date
                    )
                    ReceiptPayment.objects.create(
                        receipt=receipt,
                        amount=transfer_amount,
                        payment_method='Transfer',
                        status='Paid',
                        date=receipt.date
                    )
                    print(f"Created payment records for walk-in customer: Cash: {cash_amount}, Transfer: {transfer_amount}")

        # Define available payment methods and statuses
        payment_methods = ["Cash", "Wallet", "Transfer"]
        statuses = ["Paid", "Unpaid"]

        # Fetch receipt payments directly
        receipt_payments = receipt.receipt_payments.all() if receipt.payment_method == 'Split' else None

        # Debug information
        print(f"\n==== RECEIPT DETAIL DEBUG =====")
        print(f"Receipt ID: {receipt.receipt_id}")
        print(f"Payment Method: {receipt.payment_method}")
        print(f"Has receipt_payments: {receipt_payments is not None}")
        if receipt_payments:
            print(f"Number of receipt_payments: {receipt_payments.count()}")
            for i, payment in enumerate(receipt_payments):
                print(f"Payment {i+1}: {payment.payment_method} - {payment.amount}")

        # Create split payment details if receipt payments exist
        split_payment_details = None
        if receipt_payments and receipt_payments.count() > 0:
            payments = list(receipt_payments)
            if receipt_payments.count() == 2:
                split_payment_details = {
                    'payment_method_1': payments[0].payment_method,
                    'payment_amount_1': payments[0].amount,
                    'payment_method_2': payments[1].payment_method,
                    'payment_amount_2': payments[1].amount,
                }
            elif receipt_payments.count() == 1:
                # Handle case with only one payment record
                split_payment_details = {
                    'payment_method_1': payments[0].payment_method,
                    'payment_amount_1': payments[0].amount,
                    'payment_method_2': 'Unknown',
                    'payment_amount_2': receipt.total_amount - payments[0].amount,
                }

            print(f"Created split_payment_details: {split_payment_details}")

        # Render the receipt details template
        return render(request, 'partials/receipt_detail.html', {
            'receipt': receipt,
            'sales': sales,
            'sales_items': sales_items,
            'total_price': total_price,
            'total_discount': total_discount,
            'total_discounted_price': total_discounted_price,
            'user': request.user,
            'payment_methods': payment_methods,
            'statuses': statuses,
            'receipt_payments': receipt_payments,
            'split_payment_details': split_payment_details,
            'payment_type': 'split' if receipt.payment_method == 'Split' else 'single',
        })
    else:
        return redirect('store:index')


@login_required
def return_item(request, pk):
    if request.user.is_authenticated:
        item = get_object_or_404(Item, id=pk)

        if request.method == 'POST':
            form = ReturnItemForm(request.POST)
            if form.is_valid():
                return_quantity = form.cleaned_data.get('return_item_quantity')

                try:
                    with transaction.atomic():
                        # Update item stock
                        item.stock += return_quantity
                        item.save()

                        # Find the sales item associated with the returned item
                        sales_item = SalesItem.objects.filter(item=item).order_by('-quantity').first()
                        if not sales_item or sales_item.quantity < return_quantity:
                            messages.error(request, f'No valid sales record found for {item.name}.')
                            return redirect('store:store')

                        # Calculate refund and update sales item
                        refund_amount = return_quantity * sales_item.price
                        if sales_item.quantity > return_quantity:
                            sales_item.quantity -= return_quantity
                            sales_item.save()
                        else:
                            sales_item.delete()

                        # Update sales total
                        sales = sales_item.sales
                        sales.total_amount -= refund_amount
                        sales.save()

                        # Get or create Formulation object for dosage_form
                        dosage_form_obj = None
                        if item.dosage_form:
                            dosage_form_obj, created = Formulation.objects.get_or_create(
                                dosage_form=item.dosage_form
                            )

                        # Calculate proportional discount for the return
                        proportional_discount = Decimal('0')
                        if sales_item.discount_amount > 0 and sales_item.quantity > 0:
                            discount_per_unit = sales_item.discount_amount / sales_item.quantity
                            proportional_discount = discount_per_unit * return_quantity

                        # Create dispensing log entry for the return
                        DispensingLog.objects.create(
                            user=request.user,
                            name=item.name,
                            brand=item.brand,
                            dosage_form=dosage_form_obj,
                            unit=item.unit,
                            quantity=return_quantity,
                            amount=refund_amount,
                            discount_amount=proportional_discount,
                            status='Returned'
                        )

                        # Get payment method and status for the receipt
                        payment_method = request.POST.get('payment_method', 'Cash')
                        status = request.POST.get('status', 'Paid')

                        # Store in session for later use in receipt generation
                        request.session['payment_method'] = payment_method
                        request.session['payment_status'] = status

                        # Note: Wallet refund for registered customers is now handled in select_items function
                        messages.success(
                            request,
                            f'{return_quantity} of {item.name} successfully returned (â‚¦{refund_amount}).'
                        )

                        # Handle HTMX response for return processing
                        if request.headers.get('HX-Request'):
                            # Update daily and monthly sales data
                            daily_sales = get_daily_sales()
                            monthly_sales = get_monthly_sales_with_expenses()

                            # Return updated dispensing log for HTMX requests
                            context = {
                                'logs': DispensingLog.objects.filter(user=request.user).order_by('-created_at'),
                                'daily_sales': daily_sales,
                                'monthly_sales': monthly_sales
                            }
                            return render(request, 'store/dispensing_log.html', context)

                        return redirect('store:store')

                except Exception as e:
                    print(f'Error during item return: {e}')
                    messages.error(request, f'Error processing return: {e}')
                    return redirect('store:store')
            else:
                messages.error(request, 'Invalid input. Please correct the form and try again.')

        else:
            form = ReturnItemForm()

        if request.headers.get('HX-Request'):
            return render(request, 'partials/return_item_modal.html', {'form': form, 'item': item})
        else:
            return render(request, 'store/store.html', {'form': form})
    else:
        return redirect('store:index')


@login_required
@user_passes_test(lambda user: user.is_authenticated and (user.is_superuser or (hasattr(user, 'profile') and user.profile and user.profile.user_type in ['Admin', 'Manager'])))
def delete_item(request, pk):
    if request.user.is_authenticated:
        item = get_object_or_404(Item, id=pk)
        item.delete()
        messages.success(request, 'Item deleted successfully')
        return redirect('store:store')
    else:
        return redirect('store:index')

def get_daily_sales():
    # Simplified version to avoid annotation conflicts
    # Use DispensingLog data to match the dispensing log page calculation
    # This ensures both pages show the same daily sales values

    # Get dispensed sales (positive amounts) with cashier information
    dispensed_sales = (
        DispensingLog.objects
        .filter(status='Dispensed')
        .annotate(day=TruncDay('created_at'))
        .values('day', 'user__username')
        .annotate(
            total_sales=Sum('amount'),
            total_cost=Sum('amount') * Decimal('0.7'),  # Simplified cost calculation (70% of sales)
            transaction_count=Count('id', distinct=True)
        )
    )

    # Get returned sales (negative amounts to subtract) with cashier information
    returned_sales = (
        DispensingLog.objects
        .filter(status__in=['Returned', 'Partially Returned'])
        .annotate(day=TruncDay('created_at'))
        .values('day', 'user__username')
        .annotate(
            total_returns=Sum('amount'),
            total_return_cost=Sum('amount') * Decimal('0.7'),  # Simplified cost calculation (70% of returns)
            transaction_count=Count('id', distinct=True)
        )
    )

    # Get retail sales by payment method - using TruncDay to match the day format from sales queries
    # First, get regular payment methods from receipts that aren't split payments and aren't returned
    payment_method_sales = (
        Receipt.objects
        .filter(Q(status='Paid') | Q(status='Unpaid'))  # Include both paid and unpaid receipts
        .filter(is_returned=False)  # Exclude returned receipts
        .exclude(payment_method='Split')  # Exclude split payments, we'll handle them separately
        .annotate(day=TruncDay('date'))
        .values('day', 'payment_method')
        .annotate(
            total_amount=Sum('total_amount')
        )
        .order_by('day', 'payment_method')
    )

    # Now get the split payments from ReceiptPayment records
    # This includes split payments for both walk-in and registered customers
    split_payment_sales = (
        ReceiptPayment.objects
        .filter(Q(receipt__status='Paid') | Q(receipt__status='Unpaid'))
        .annotate(day=TruncDay('date'))
        .values('day', 'payment_method')
        .annotate(
            total_amount=Sum('amount')
        )
        .order_by('day', 'payment_method')
    )

    # Get wholesale sales by payment method - using TruncDay to match the day format
    # First, get regular payment methods from receipts that aren't split payments
    wholesale_payment_method_sales = (
        WholesaleReceipt.objects
        .filter(Q(status='Paid') | Q(status='Unpaid'))  # Include both paid and unpaid receipts
        .filter(is_returned=False)  # Exclude returned wholesale receipts
        .exclude(payment_method='Split')  # Exclude split payments, we'll handle them separately
        .annotate(day=TruncDay('date'))
        .values('day', 'payment_method')
        .annotate(
            total_amount=Sum('total_amount')
        )
        .order_by('day', 'payment_method')
    )

    # Now get the split payments from WholesaleReceiptPayment records
    # This includes split payments for both walk-in and registered customers
    wholesale_split_payment_sales = (
        WholesaleReceiptPayment.objects
        .filter(Q(receipt__status='Paid') | Q(receipt__status='Unpaid'))
        .filter(receipt__is_returned=False)  # Exclude payments for returned receipts
        .annotate(day=TruncDay('date'))
        .values('day', 'payment_method')
        .annotate(
            total_amount=Sum('amount')
        )
        .order_by('day', 'payment_method')
    )

    # Combine results with cashier information
    combined_sales = defaultdict(lambda: {
        'total_sales': Decimal('0.00'),
        'total_cost': Decimal('0.00'),
        'total_profit': Decimal('0.00'),
        'payment_methods': {
            'Cash': Decimal('0.00'),
            'Wallet': Decimal('0.00'),
            'Transfer': Decimal('0.00')
        },
        'cashiers': {}  # Store cashier performance data
    })

    # Helper function to normalize dates to date objects (not datetime)
    def normalize_date(date_obj):
        if hasattr(date_obj, 'date'):
            # If it's a datetime object, convert to date
            return date_obj.date()
        return date_obj

    # Add dispensed sales data (positive amounts) with cashier information
    for sale in dispensed_sales:
        day = normalize_date(sale['day'])
        cashier_username = sale['user__username'] or 'Unknown'
        
        # Update daily totals
        combined_sales[day]['total_sales'] += sale['total_sales'] or Decimal('0.00')
        combined_sales[day]['total_cost'] += sale['total_cost'] or Decimal('0.00')
        # Calculate profit as sales - cost
        profit = (sale['total_sales'] or Decimal('0.00')) - (sale['total_cost'] or Decimal('0.00'))
        combined_sales[day]['total_profit'] += profit
        
        # Update cashier-specific data
        if cashier_username not in combined_sales[day]['cashiers']:
            combined_sales[day]['cashiers'][cashier_username] = {
                'total_sales': Decimal('0.00'),
                'total_cost': Decimal('0.00'),
                'total_profit': Decimal('0.00'),
                'transaction_count': 0
            }
        
        cashier_profit = (sale['total_sales'] or Decimal('0.00')) - (sale['total_cost'] or Decimal('0.00'))
        combined_sales[day]['cashiers'][cashier_username]['total_sales'] += sale['total_sales'] or Decimal('0.00')
        combined_sales[day]['cashiers'][cashier_username]['total_cost'] += sale['total_cost'] or Decimal('0.00')
        combined_sales[day]['cashiers'][cashier_username]['total_profit'] += cashier_profit
        combined_sales[day]['cashiers'][cashier_username]['transaction_count'] += sale['transaction_count'] or 0

    # Subtract returned sales data (negative amounts) with cashier tracking
    for return_sale in returned_sales:
        day = normalize_date(return_sale['day'])
        cashier_username = return_sale['user__username'] or 'Unknown'
        
        # Update daily totals (subtract)
        combined_sales[day]['total_sales'] -= return_sale['total_returns'] or Decimal('0.00')
        combined_sales[day]['total_cost'] -= return_sale['total_return_cost'] or Decimal('0.00')
        # Subtract return profit as well
        return_profit = (return_sale['total_returns'] or Decimal('0.00')) - (return_sale['total_return_cost'] or Decimal('0.00'))
        combined_sales[day]['total_profit'] -= return_profit
        
        # Update cashier-specific data (subtract for returns)
        if cashier_username not in combined_sales[day]['cashiers']:
            combined_sales[day]['cashiers'][cashier_username] = {
                'total_sales': Decimal('0.00'),
                'total_cost': Decimal('0.00'),
                'total_profit': Decimal('0.00'),
                'transaction_count': 0
            }
        
        combined_sales[day]['cashiers'][cashier_username]['total_sales'] -= return_sale['total_returns'] or Decimal('0.00')
        combined_sales[day]['cashiers'][cashier_username]['total_cost'] -= return_sale['total_return_cost'] or Decimal('0.00')
        combined_sales[day]['cashiers'][cashier_username]['total_profit'] -= return_profit
        combined_sales[day]['cashiers'][cashier_username]['transaction_count'] += return_sale['transaction_count'] or 0

    # Add retail payment method data (non-split payments)
    for sale in payment_method_sales:
        day = normalize_date(sale['day'])
        payment_method = sale['payment_method']
        if payment_method in combined_sales[day]['payment_methods']:
            combined_sales[day]['payment_methods'][payment_method] += sale['total_amount'] or Decimal('0.00')

    # Add retail split payment data
    for sale in split_payment_sales:
        day = normalize_date(sale['day'])
        payment_method = sale['payment_method']
        if payment_method in combined_sales[day]['payment_methods']:
            combined_sales[day]['payment_methods'][payment_method] += sale['total_amount'] or Decimal('0.00')

    # Add wholesale payment method data (non-split payments)
    for sale in wholesale_payment_method_sales:
        day = normalize_date(sale['day'])
        payment_method = sale['payment_method']
        if payment_method in combined_sales[day]['payment_methods']:
            combined_sales[day]['payment_methods'][payment_method] += sale['total_amount'] or Decimal('0.00')

    # Add wholesale split payment data
    for sale in wholesale_split_payment_sales:
        day = normalize_date(sale['day'])
        payment_method = sale['payment_method']
        if payment_method in combined_sales[day]['payment_methods']:
            combined_sales[day]['payment_methods'][payment_method] += sale['total_amount'] or Decimal('0.00')

    # Verify payment method totals match overall sales totals and adjust if needed
    for day, data in combined_sales.items():
        payment_total = sum(data['payment_methods'].values())
        sales_total = data['total_sales']

        # If there's a significant discrepancy, adjust the payment methods
        if abs(payment_total - sales_total) > Decimal('0.01'):
            logger.info(f"Adjusting payment methods for {day}: Payment total ({payment_total}) vs Sales total ({sales_total})")

            if payment_total == 0 and sales_total > 0:
                # If no payment methods are recorded but we have sales, assign to Cash by default
                data['payment_methods']['Cash'] = sales_total
            elif payment_total > 0 and sales_total == 0:
                # If we have payment methods but no sales, adjust sales to match payments
                data['total_sales'] = payment_total
            elif payment_total > 0 and sales_total > 0:
                # If both are non-zero but different, proportionally adjust payment methods
                adjustment_factor = sales_total / payment_total
                for method in data['payment_methods']:
                    data['payment_methods'][method] = data['payment_methods'][method] * adjustment_factor

    # Convert combined sales to a sorted list by date in descending order
    sorted_combined_sales = sorted(combined_sales.items(), key=lambda x: x[0], reverse=True)

    return sorted_combined_sales


def get_cashier_daily_payment_totals(user, start_date=None, end_date=None):
    """
    Get daily payment totals for a specific cashier.
    For cashiers: returns only their own payment totals
    For admin/managers: returns all cashiers' payment totals
    """
    from django.db.models import Q, Sum, F
    from datetime import datetime
    
    # Set default date range to last 30 days if not provided
    if not start_date:
        start_date = timezone.now().date() - timedelta(days=30)
    if not end_date:
        end_date = timezone.now().date()
    
    # Check if user is admin/manager or cashier
    is_admin = (
        user.is_superuser or 
        user.is_staff or 
        (hasattr(user, 'profile') and user.profile and user.profile.user_type in ['Admin', 'Manager'])
    )
    
    results = []
    
    # Retail receipts payment data
    retail_receipts = Receipt.objects.filter(
        date__date__gte=start_date,
        date__date__lte=end_date,
        is_returned=False
    ).annotate(
        day=TruncDay('date'),
        cashier_name=F('cashier__name'),
        username=F('cashier__user__username'),
        cashier_pk=F('cashier__id')
    ).values('day', 'cashier_name', 'username', 'payment_method', 'cashier_pk').annotate(
        total_amount=Sum('total_amount')
    ).order_by('-day', 'cashier_name')

    # Retail split payments
    retail_split_payments = ReceiptPayment.objects.filter(
        date__date__gte=start_date,
        date__date__lte=end_date,
        receipt__is_returned=False
    ).annotate(
        day=TruncDay('date'),
        cashier_name=F('receipt__cashier__name'),
        username=F('receipt__cashier__user__username'),
        cashier_pk=F('receipt__cashier__id')
    ).values('day', 'cashier_name', 'username', 'payment_method', 'cashier_pk').annotate(
        total_amount=Sum('amount')
    ).order_by('-day', 'cashier_name')

    # Wholesale receipts payment data
    wholesale_receipts = WholesaleReceipt.objects.filter(
        date__date__gte=start_date,
        date__date__lte=end_date,
        is_returned=False
    ).annotate(
        day=TruncDay('date'),
        cashier_name=F('cashier__name'),
        username=F('cashier__user__username'),
        cashier_pk=F('cashier__id')
    ).values('day', 'cashier_name', 'username', 'payment_method', 'cashier_pk').annotate(
        total_amount=Sum('total_amount')
    ).order_by('-day', 'cashier_name')

    # Wholesale split payments
    wholesale_split_payments = WholesaleReceiptPayment.objects.filter(
        date__date__gte=start_date,
        date__date__lte=end_date,
        receipt__is_returned=False
    ).annotate(
        day=TruncDay('date'),
        cashier_name=F('receipt__cashier__name'),
        username=F('receipt__cashier__user__username'),
        cashier_pk=F('receipt__cashier__id')
    ).values('day', 'cashier_name', 'username', 'payment_method', 'cashier_pk').annotate(
        total_amount=Sum('amount')
    ).order_by('-day', 'cashier_name')
    
    # Combine all payment data
    all_payments = []
    all_payments.extend(retail_receipts)
    all_payments.extend(retail_split_payments)
    all_payments.extend(wholesale_receipts)
    all_payments.extend(wholesale_split_payments)
    
    # Group by date and cashier
    from collections import defaultdict
    daily_cashier_totals = defaultdict(lambda: defaultdict(lambda: {
        'name': '',
        'username': '',
        'total': Decimal('0.00'),
        'payment_methods': defaultdict(lambda: Decimal('0.00'))
    }))
    
    for payment in all_payments:
        day = payment['day'].date()
        cashier_name = payment['cashier_name'] or 'Unknown'
        cashier_id = payment.get('cashier_pk') or 'unknown'
        username = payment['username'] or 'Unknown'
        payment_method = payment['payment_method']
        amount = payment['total_amount']

        if cashier_id is None:
            cashier_id = 'unknown'
        daily_cashier_totals[day][cashier_id]['name'] = cashier_name
        daily_cashier_totals[day][cashier_id]['username'] = username
        daily_cashier_totals[day][cashier_id]['total'] += amount
        daily_cashier_totals[day][cashier_id]['payment_methods'][payment_method] += amount
    
    # Filter based on user role
    if not is_admin and hasattr(user, 'cashier'):
        # Cashier can only see their own data
        user_cashier_id = user.cashier.id
        cashier_daily_totals = {}
        for day, cashiers in daily_cashier_totals.items():
            if user_cashier_id in cashiers:
                cashier_daily_totals[day] = {user_cashier_id: cashiers[user_cashier_id]}
        daily_cashier_totals = cashier_daily_totals
    
    # Convert to sorted list
    for day, cashiers in sorted(daily_cashier_totals.items(), key=lambda x: x[0], reverse=True):
        day_data = {
            'date': day,
            'cashiers': []
        }
        
        for cashier_id, data in cashiers.items():
            cashier_data = {
                'cashier_id': cashier_id,
                'name': data['name'],
                'username': data['username'],
                'total_amount': data['total'],
                'payment_methods': dict(data['payment_methods'])
            }
            day_data['cashiers'].append(cashier_data)
        
        # Sort cashiers by total amount (highest first)
        day_data['cashiers'].sort(key=lambda x: x['total_amount'], reverse=True)
        results.append(day_data)
    
    return results


def get_monthly_expenses():
    """
    Returns a dictionary mapping the first day of each month to its total expenses.
    """
    expenses = (
        Expense.objects
        .annotate(month=TruncMonth('date'))
        .values('month')
        .annotate(total_expense=Sum('amount'))
    )
    return {entry['month']: entry['total_expense'] for entry in expenses}


def get_monthly_customer_performance(start_date=None, end_date=None):
    """
    Get customer performance data aggregated by month.
    Returns both retail and wholesale customer performance.
    """
    from django.db.models import Q, F, Sum, Count, Avg, Max, Min
    from django.db.models.functions import TruncMonth
    from collections import defaultdict

    # Set default date range if not provided
    if not start_date:
        start_date = timezone.now().date().replace(day=1, month=1)  # Start of current year
    if not end_date:
        end_date = timezone.now().date()

    # Retail customer performance
    retail_performance = (
        SalesItem.objects
        .filter(
            sales__date__gte=start_date,
            sales__date__lte=end_date,
            sales__is_returned=False  # Exclude returned items
        )
        .annotate(month=TruncMonth('sales__date'))
        .values('sales__customer__id', 'sales__customer__name', 'month')
        .annotate(
            total_amount=Sum(F('price') * F('quantity') - F('discount_amount')),
            total_cost=Sum(F('item__cost') * F('quantity')),
            profit=Sum(F('price') * F('quantity') - F('discount_amount') - F('item__cost') * F('quantity')),
            transaction_count=Count('sales', distinct=True),
            total_items=Sum('quantity'),
            avg_transaction=Avg(F('price') * F('quantity') - F('discount_amount'))
        )
        .order_by('month', '-total_amount')
    )

    # Wholesale customer performance
    wholesale_performance = (
        WholesaleSalesItem.objects
        .filter(
            sales__date__gte=start_date,
            sales__date__lte=end_date,
            sales__is_returned=False  # Exclude returned items
        )
        .annotate(month=TruncMonth('sales__date'))
        .values('sales__wholesale_customer__id', 'sales__wholesale_customer__name', 'month')
        .annotate(
            total_amount=Sum(F('price') * F('quantity') - F('discount_amount')),
            total_cost=Sum(F('item__cost') * F('quantity')),
            profit=Sum(F('price') * F('quantity') - F('discount_amount') - F('item__cost') * F('quantity')),
            transaction_count=Count('sales', distinct=True),
            total_items=Sum('quantity'),
            avg_transaction=Avg(F('price') * F('quantity') - F('discount_amount'))
        )
        .order_by('month', '-total_amount')
    )

    # Combine and structure the data
    combined_performance = defaultdict(lambda: {
        'retail_customers': [],
        'wholesale_customers': [],
        'month_total': Decimal('0.00'),
        'month_profit': Decimal('0.00'),
        'total_customers': 0
    })

    # Process retail customers
    for item in retail_performance:
        month = item['month']
        customer_data = {
            'customer_id': item['sales__customer__id'],
            'customer_name': item['sales__customer__name'],
            'customer_type': 'retail',
            'total_amount': item['total_amount'] or Decimal('0.00'),
            'total_cost': item.get('total_cost') or Decimal('0.00'),
            'profit': item.get('profit') or Decimal('0.00'),
            'transaction_count': item['transaction_count'],
            'total_items': item['total_items'] or 0,
            'avg_transaction': item['avg_transaction'] or Decimal('0.00')
        }
        combined_performance[month]['retail_customers'].append(customer_data)
        combined_performance[month]['month_total'] += customer_data['total_amount']
        combined_performance[month]['month_profit'] += customer_data['profit']
        combined_performance[month]['total_customers'] += 1

    # Process wholesale customers
    for item in wholesale_performance:
        month = item['month']
        customer_data = {
            'customer_id': item['sales__wholesale_customer__id'],
            'customer_name': item['sales__wholesale_customer__name'],
            'customer_type': 'wholesale',
            'total_amount': item['total_amount'] or Decimal('0.00'),
            'total_cost': item.get('total_cost') or Decimal('0.00'),
            'profit': item.get('profit') or Decimal('0.00'),
            'transaction_count': item['transaction_count'],
            'total_items': item['total_items'] or 0,
            'avg_transaction': item['avg_transaction'] or Decimal('0.00')
        }
        combined_performance[month]['wholesale_customers'].append(customer_data)
        combined_performance[month]['month_total'] += customer_data['total_amount']
        combined_performance[month]['month_profit'] += customer_data['profit']
        combined_performance[month]['total_customers'] += 1

    # Convert to sorted list
    return sorted(combined_performance.items(), key=lambda x: x[0], reverse=True)


def get_yearly_customer_performance(start_year=None, end_year=None):
    """
    Get customer performance data aggregated by year.
    Returns both retail and wholesale customer performance.
    """
    from django.db.models import Q, F, Sum, Count, Avg, Max, Min
    from django.db.models.functions import TruncYear
    from collections import defaultdict

    # Set default year range if not provided
    current_year = timezone.now().year
    if not start_year:
        start_year = current_year - 2  # Last 3 years by default
    if not end_year:
        end_year = current_year

    start_date = timezone.datetime(start_year, 1, 1).date()
    end_date = timezone.datetime(end_year, 12, 31).date()

    # Retail customer performance
    retail_performance = (
        SalesItem.objects
        .filter(
            sales__date__gte=start_date,
            sales__date__lte=end_date,
            sales__is_returned=False  # Exclude returned items
        )
        .annotate(year=TruncYear('sales__date'))
        .values('sales__customer__id', 'sales__customer__name', 'year')
        .annotate(
            total_amount=Sum(F('price') * F('quantity') - F('discount_amount')),
            total_cost=Sum(F('item__cost') * F('quantity')),
            profit=Sum(F('price') * F('quantity') - F('discount_amount') - F('item__cost') * F('quantity')),
            transaction_count=Count('sales', distinct=True),
            total_items=Sum('quantity'),
            avg_transaction=Avg(F('price') * F('quantity') - F('discount_amount')),
            first_purchase=Min('sales__date'),
            last_purchase=Max('sales__date')
        )
        .order_by('year', '-total_amount')
    )

    # Wholesale customer performance
    wholesale_performance = (
        WholesaleSalesItem.objects
        .filter(
            sales__date__gte=start_date,
            sales__date__lte=end_date,
            sales__is_returned=False  # Exclude returned items
        )
        .annotate(year=TruncYear('sales__date'))
        .values('sales__wholesale_customer__id', 'sales__wholesale_customer__name', 'year')
        .annotate(
            total_amount=Sum(F('price') * F('quantity') - F('discount_amount')),
            total_cost=Sum(F('item__cost') * F('quantity')),
            profit=Sum(F('price') * F('quantity') - F('discount_amount') - F('item__cost') * F('quantity')),
            transaction_count=Count('sales', distinct=True),
            total_items=Sum('quantity'),
            avg_transaction=Avg(F('price') * F('quantity') - F('discount_amount')),
            first_purchase=Min('sales__date'),
            last_purchase=Max('sales__date')
        )
        .order_by('year', '-total_amount')
    )

    # Combine and structure the data
    combined_performance = defaultdict(lambda: {
        'retail_customers': [],
        'wholesale_customers': [],
        'year_total': Decimal('0.00'),
        'year_profit': Decimal('0.00'),
        'total_customers': 0
    })

    # Process retail customers
    for item in retail_performance:
        year = item['year']
        customer_data = {
            'customer_id': item['sales__customer__id'],
            'customer_name': item['sales__customer__name'],
            'customer_type': 'retail',
            'total_amount': item['total_amount'] or Decimal('0.00'),
            'total_cost': item.get('total_cost') or Decimal('0.00'),
            'profit': item.get('profit') or Decimal('0.00'),
            'transaction_count': item['transaction_count'],
            'total_items': item['total_items'] or 0,
            'avg_transaction': item['avg_transaction'] or Decimal('0.00'),
            'first_purchase': item['first_purchase'],
            'last_purchase': item['last_purchase']
        }
        combined_performance[year]['retail_customers'].append(customer_data)
        combined_performance[year]['year_total'] += customer_data['total_amount']
        combined_performance[year]['year_profit'] += customer_data['profit']
        combined_performance[year]['total_customers'] += 1

    # Process wholesale customers
    for item in wholesale_performance:
        year = item['year']
        customer_data = {
            'customer_id': item['sales__wholesale_customer__id'],
            'customer_name': item['sales__wholesale_customer__name'],
            'customer_type': 'wholesale',
            'total_amount': item['total_amount'] or Decimal('0.00'),
            'total_cost': item.get('total_cost') or Decimal('0.00'),
            'profit': item.get('profit') or Decimal('0.00'),
            'transaction_count': item['transaction_count'],
            'total_items': item['total_items'] or 0,
            'avg_transaction': item['avg_transaction'] or Decimal('0.00'),
            'first_purchase': item['first_purchase'],
            'last_purchase': item['last_purchase']
        }
        combined_performance[year]['wholesale_customers'].append(customer_data)
        combined_performance[year]['year_total'] += customer_data['total_amount']
        combined_performance[year]['year_profit'] += customer_data['profit']
        combined_performance[year]['total_customers'] += 1

    # Convert to sorted list
    return sorted(combined_performance.items(), key=lambda x: x[0], reverse=True)

def get_monthly_sales_with_expenses():
    # Fetch regular sales data per month with cashier information
    regular_sales = (
        SalesItem.objects
        .annotate(month=TruncMonth('sales__date'))
        .values('month', 'sales__user__username', 'sales__user')
        .annotate(
            total_sales=Sum(F('price') * F('quantity') - F('discount_amount')),
            total_cost=Sum(F('item__cost') * F('quantity')),
            total_profit=ExpressionWrapper(
                Sum(F('price') * F('quantity') - F('discount_amount')) - Sum(F('item__cost') * F('quantity')),
                output_field=DecimalField()
            ),
            transaction_count=Count('sales', distinct=True)
        )
    )

    # Fetch wholesale sales data per month with cashier information
    wholesale_sales = (
        WholesaleSalesItem.objects
        .annotate(month=TruncMonth('sales__date'))
        .values('month', 'sales__user__username', 'sales__user')
        .annotate(
            total_sales=Sum(F('price') * F('quantity') - F('discount_amount')),
            total_cost=Sum(F('item__cost') * F('quantity')),
            total_profit=ExpressionWrapper(
                Sum(F('price') * F('quantity') - F('discount_amount')) - Sum(F('item__cost') * F('quantity')),
                output_field=DecimalField()
            ),
            transaction_count=Count('sales', distinct=True)
        )
    )

    # Get monthly payment method data for retail (non-split payments)
    monthly_payment_method_sales = (
        Receipt.objects
        .filter(Q(status='Paid') | Q(status='Unpaid'))
        .exclude(payment_method='Split')
        .annotate(month=TruncMonth('date'))
        .values('month', 'payment_method')
        .annotate(
            total_amount=Sum('total_amount')
        )
        .order_by('month', 'payment_method')
    )

    # Get monthly split payment data for retail
    monthly_split_payment_sales = (
        ReceiptPayment.objects
        .filter(Q(receipt__status='Paid') | Q(receipt__status='Unpaid'))
        .annotate(month=TruncMonth('date'))
        .values('month', 'payment_method')
        .annotate(
            total_amount=Sum('amount')
        )
        .order_by('month', 'payment_method')
    )

    # Get monthly payment method data for wholesale (non-split payments)
    monthly_wholesale_payment_method_sales = (
        WholesaleReceipt.objects
        .filter(Q(status='Paid') | Q(status='Unpaid'))
        .exclude(payment_method='Split')
        .annotate(month=TruncMonth('date'))
        .values('month', 'payment_method')
        .annotate(
            total_amount=Sum('total_amount')
        )
        .order_by('month', 'payment_method')
    )

    # Get monthly split payment data for wholesale
    monthly_wholesale_split_payment_sales = (
        WholesaleReceiptPayment.objects
        .filter(Q(receipt__status='Paid') | Q(receipt__status='Unpaid'))
        .annotate(month=TruncMonth('date'))
        .values('month', 'payment_method')
        .annotate(
            total_amount=Sum('amount')
        )
        .order_by('month', 'payment_method')
    )

    # Get monthly expenses as a dictionary: {month_date: total_expense}
    monthly_expenses = get_monthly_expenses()

    # Combine the two types of sales into one dict with cashier information
    combined_sales = defaultdict(lambda: {
        'total_sales': Decimal('0.00'),
        'total_cost': Decimal('0.00'),
        'total_profit': Decimal('0.00'),
        'payment_methods': {
            'Cash': Decimal('0.00'),
            'Wallet': Decimal('0.00'),
            'Transfer': Decimal('0.00')
        },
        'cashiers': {}  # Store cashier performance data
    })

    for sale in regular_sales:
        month = sale['month']
        cashier_username = sale['sales__user__username'] or 'Unknown'
        
        # Update monthly totals
        combined_sales[month]['total_sales'] += sale['total_sales'] or Decimal('0.00')
        combined_sales[month]['total_cost'] += sale['total_cost'] or Decimal('0.00')
        combined_sales[month]['total_profit'] += sale['total_profit'] or Decimal('0.00')
        
        # Update cashier-specific data
        if cashier_username not in combined_sales[month]['cashiers']:
            combined_sales[month]['cashiers'][cashier_username] = {
                'total_sales': Decimal('0.00'),
                'total_cost': Decimal('0.00'),
                'total_profit': Decimal('0.00'),
                'transaction_count': 0
            }
        
        combined_sales[month]['cashiers'][cashier_username]['total_sales'] += sale['total_sales'] or Decimal('0.00')
        combined_sales[month]['cashiers'][cashier_username]['total_cost'] += sale['total_cost'] or Decimal('0.00')
        combined_sales[month]['cashiers'][cashier_username]['total_profit'] += sale['total_profit'] or Decimal('0.00')
        combined_sales[month]['cashiers'][cashier_username]['transaction_count'] += sale['transaction_count'] or 0

    for sale in wholesale_sales:
        month = sale['month']
        cashier_username = sale['sales__user__username'] or 'Unknown'
        
        # Update monthly totals
        combined_sales[month]['total_sales'] += sale['total_sales'] or Decimal('0.00')
        combined_sales[month]['total_cost'] += sale['total_cost'] or Decimal('0.00')
        combined_sales[month]['total_profit'] += sale['total_profit'] or Decimal('0.00')
        
        # Update cashier-specific data
        if cashier_username not in combined_sales[month]['cashiers']:
            combined_sales[month]['cashiers'][cashier_username] = {
                'total_sales': Decimal('0.00'),
                'total_cost': Decimal('0.00'),
                'total_profit': Decimal('0.00'),
                'transaction_count': 0
            }
        
        combined_sales[month]['cashiers'][cashier_username]['total_sales'] += sale['total_sales'] or Decimal('0.00')
        combined_sales[month]['cashiers'][cashier_username]['total_cost'] += sale['total_cost'] or Decimal('0.00')
        combined_sales[month]['cashiers'][cashier_username]['total_profit'] += sale['total_profit'] or Decimal('0.00')
        combined_sales[month]['cashiers'][cashier_username]['transaction_count'] += sale['transaction_count'] or 0

    # Add retail payment method data (non-split payments)
    for sale in monthly_payment_method_sales:
        month = sale['month']
        payment_method = sale['payment_method']
        if payment_method in combined_sales[month]['payment_methods']:
            combined_sales[month]['payment_methods'][payment_method] += sale['total_amount'] or Decimal('0.00')

    # Add retail split payment data
    for sale in monthly_split_payment_sales:
        month = sale['month']
        payment_method = sale['payment_method']
        if payment_method in combined_sales[month]['payment_methods']:
            combined_sales[month]['payment_methods'][payment_method] += sale['total_amount'] or Decimal('0.00')

    # Add wholesale payment method data (non-split payments)
    for sale in monthly_wholesale_payment_method_sales:
        month = sale['month']
        payment_method = sale['payment_method']
        if payment_method in combined_sales[month]['payment_methods']:
            combined_sales[month]['payment_methods'][payment_method] += sale['total_amount'] or Decimal('0.00')

    # Add wholesale split payment data
    for sale in monthly_wholesale_split_payment_sales:
        month = sale['month']
        payment_method = sale['payment_method']
        if payment_method in combined_sales[month]['payment_methods']:
            combined_sales[month]['payment_methods'][payment_method] += sale['total_amount'] or Decimal('0.00')

    # Add expense data and calculate net profit for each month
    for month, data in combined_sales.items():
        data['total_expense'] = monthly_expenses.get(month, 0)
        data['net_profit'] = data['total_profit'] - data['total_expense']

    # Sort results by month (descending)
    # Convert datetime objects to date objects to ensure consistent comparison
    def get_sort_key(item):
        key = item[0]
        # Check if it's a datetime object
        if hasattr(key, 'date') and callable(getattr(key, 'date')):
            return key.date()
        return key

    sorted_sales = sorted(combined_sales.items(), key=get_sort_key, reverse=True)
    return sorted_sales



@user_passes_test(is_admin)
def monthly_sales_with_deduction(request):
    if request.user.is_authenticated:
        # Read the selected month from GET parameters (format: YYYY-MM)
        selected_month_str = request.GET.get('deduction_month')
        result = None

        if selected_month_str:
            try:
                # Parse selected month to a date representing the first day of that month
                selected_month = datetime.strptime(selected_month_str, '%Y-%m').date()
            except ValueError:
                selected_month = None

            if selected_month:
                # Wrap the profit expression so Django knows the output type
                profit_expr_regular = ExpressionWrapper(
                    F('price') * F('quantity') - F('discount_amount') - F('item__cost') * F('quantity'),
                    output_field=DecimalField()
                )

                profit_expr_wholesale = ExpressionWrapper(
                    F('price') * F('quantity') - F('discount_amount') - F('item__cost') * F('quantity'),
                    output_field=DecimalField()
                )

                total_profit_regular = SalesItem.objects.filter(
                    sales__date__year=selected_month.year,
                    sales__date__month=selected_month.month
                ).aggregate(
                    profit=Sum(profit_expr_regular)
                )['profit'] or 0

                total_profit_wholesale = WholesaleSalesItem.objects.filter(
                    sales__date__year=selected_month.year,
                    sales__date__month=selected_month.month
                ).aggregate(
                    profit=Sum(profit_expr_wholesale)
                )['profit'] or 0

                total_profit = total_profit_regular + total_profit_wholesale

                # Get total expenses for the selected month
                total_expense = Expense.objects.filter(
                    date__year=selected_month.year,
                    date__month=selected_month.month
                ).aggregate(total=Sum('amount'))['total'] or 0

                # Calculate net profit (sales profit minus selected month's expenses)
                net_profit = total_profit - total_expense

                result = {
                    'month': selected_month,
                    'total_profit': total_profit,
                    'total_expense': total_expense,
                    'net_profit': net_profit
                }

        return render(request, 'store/monthly_sales_deduction.html', {
            'result': result,
            'selected_month': selected_month_str
        })
    else:
        return redirect('store:index')


# Assume is_admin is your custom user test function
@user_passes_test(is_admin)
def monthly_sales(request):
    if request.user.is_authenticated:
        # Get the full monthly sales data with expenses deducted
        sales_data = get_monthly_sales_with_expenses()

        # Read selected month from GET parameters (in YYYY-MM format)
        selected_month_str = request.GET.get('month')
        filtered_sales = sales_data  # default: show all months

        if selected_month_str:
            try:
                # Convert string to a date representing the first day of that month
                selected_month = datetime.strptime(selected_month_str, '%Y-%m').date()
                # Filter for the selected month only
                filtered_sales = [entry for entry in sales_data if entry[0] == selected_month]
            except ValueError:
                # If parsing fails, leave filtered_sales unchanged (or handle the error as needed)
                pass

        # Add pagination
        paginator = Paginator(filtered_sales, 12)  # Show 12 months per page
        page_number = request.GET.get('page')
        page_obj = paginator.get_page(page_number)
        
        context = {
            'monthly_sales': page_obj,
            'selected_month': selected_month_str,  # pass back to pre-fill the form field
            'is_paginated': paginator.num_pages > 1,
            'page_obj': page_obj
        }
        return render(request, 'store/monthly_sales.html', context)
    else:
        return redirect('store:index')




@login_required
def cashier_payment_totals(request):
    """
    View for displaying cashier daily payment totals with date filtering
    Cashiers see only their own totals, admins/managers see all cashiers
    """
    if request.user.is_authenticated:
        from datetime import timedelta
        
        # Get date range from request parameters
        start_date = request.GET.get('start_date')
        end_date = request.GET.get('end_date')
        
        if start_date:
            start_date = parse_date(start_date)
        else:
            start_date = timezone.now().date() - timedelta(days=30)  # Default to last 30 days
            
        if end_date:
            end_date = parse_date(end_date)
        else:
            end_date = timezone.now().date()
        
        # Get daily payment totals
        daily_payment_totals = get_cashier_daily_payment_totals(request.user, start_date, end_date)
        
        # Check if user is admin/manager
        is_admin = (
            request.user.is_superuser or 
            request.user.is_staff or 
            (hasattr(request.user, 'profile') and request.user.profile and 
             request.user.profile.user_type in ['Admin', 'Manager'])
        )
        
        context = {
            'daily_payment_totals': daily_payment_totals,
            'is_admin': is_admin,
            'start_date': start_date,
            'end_date': end_date,
        }
        
        return render(request, 'store/cashier_payment_totals.html', context)
    else:
        return redirect('store:index')


@user_passes_test(is_admin)
def daily_sales(request):
    if request.user.is_authenticated:
        daily_sales = get_daily_sales()  # Already sorted by date in descending order
        
        # Add pagination
        paginator = Paginator(daily_sales, 10)  # Show 10 days per page
        page_number = request.GET.get('page')
        page_obj = paginator.get_page(page_number)
        
        context = {
            'daily_sales': page_obj,
            'is_paginated': paginator.num_pages > 1,
            'page_obj': page_obj
        }
        return render(request, 'store/daily_sales.html', context)
    else:
        return redirect('store:index')


@user_passes_test(is_admin)
def monthly_sales(request):
    if request.user.is_authenticated:
        monthly_sales = get_monthly_sales_with_expenses()  # Now includes expenses
        context = {'monthly_sales': monthly_sales}
        return render(request, 'store/monthly_sales.html', context)
    else:
        return redirect('store:index')


@user_passes_test(is_admin)
def monthly_customer_performance(request):
    """View for displaying monthly customer performance data"""
    if request.user.is_authenticated:
        # Get date range from request parameters
        start_date_str = request.GET.get('start_date')
        end_date_str = request.GET.get('end_date')

        start_date = None
        end_date = None

        if start_date_str:
            try:
                start_date = datetime.strptime(start_date_str, '%Y-%m-%d').date()
            except ValueError:
                pass

        if end_date_str:
            try:
                end_date = datetime.strptime(end_date_str, '%Y-%m-%d').date()
            except ValueError:
                pass

        # Get customer performance data
        monthly_performance = get_monthly_customer_performance(start_date, end_date)

        # Calculate summary statistics
        total_customers = 0
        total_revenue = Decimal('0.00')
        total_profit = Decimal('0.00')
        total_transactions = 0

        for month, data in monthly_performance:
            total_customers += data['total_customers']
            total_revenue += data['month_total']
            # accumulate profit if present
            total_profit += data.get('month_profit', Decimal('0.00'))
            for customer in data['retail_customers'] + data['wholesale_customers']:
                total_transactions += customer['transaction_count']

        context = {
            'monthly_performance': monthly_performance,
            'start_date': start_date,
            'end_date': end_date,
            'summary': {
                'total_customers': total_customers,
                'total_revenue': total_revenue,
                    'total_transactions': total_transactions,
                    'total_profit': total_profit,
                    'avg_revenue_per_customer': total_revenue / total_customers if total_customers > 0 else Decimal('0.00')
            }
        }
        return render(request, 'store/monthly_customer_performance.html', context)
    else:
        return redirect('store:index')


@user_passes_test(is_admin)
def yearly_customer_performance(request):
    """View for displaying yearly customer performance data"""
    if request.user.is_authenticated:
        # Get year range from request parameters
        start_year_str = request.GET.get('start_year')
        end_year_str = request.GET.get('end_year')

        start_year = None
        end_year = None

        if start_year_str:
            try:
                start_year = int(start_year_str)
            except ValueError:
                pass

        if end_year_str:
            try:
                end_year = int(end_year_str)
            except ValueError:
                pass

        # Get customer performance data
        yearly_performance = get_yearly_customer_performance(start_year, end_year)

        # Calculate summary statistics
        total_customers = 0
        total_revenue = Decimal('0.00')
        total_profit = Decimal('0.00')
        total_transactions = 0

        for year, data in yearly_performance:
            total_customers += data['total_customers']
            total_revenue += data['year_total']
            total_profit += data.get('year_profit', Decimal('0.00'))
            for customer in data['retail_customers'] + data['wholesale_customers']:
                total_transactions += customer['transaction_count']

        context = {
            'yearly_performance': yearly_performance,
            'start_year': start_year,
            'end_year': end_year,
            'summary': {
                'total_customers': total_customers,
                'total_revenue': total_revenue,
                    'total_transactions': total_transactions,
                    'total_profit': total_profit,
                    'avg_revenue_per_customer': total_revenue / total_customers if total_customers > 0 else Decimal('0.00')
            }
        }
        return render(request, 'store/yearly_customer_performance.html', context)
    else:
        return redirect('store:index')


def get_sales_by_user(date_from=None, date_to=None):
    # Filter sales by date range if provided
    filters = Q()
    if date_from:
        filters &= Q(date__gte=date_from)
    if date_to:
        filters &= Q(date__lte=date_to)

    # Aggregating sales for each user
    sales_by_user = (
        Sales.objects.filter(filters)
        .values('user__username')  # Group by user
        .annotate(
            total_sales=Sum('total_amount'),  # Sum of total amounts
            total_items=Sum(F('sales_items__quantity') )  # Sum of all quantities sold
        )
        .order_by('-total_sales')  # Sort by total sales in descending order
    )
    return sales_by_user



@user_passes_test(is_admin)
def sales_by_user(request):
    if request.user.is_authenticated:
        # Get the date filters from the request
        date_from = request.GET.get('date_from')
        date_to = request.GET.get('date_to')

        # Parse dates if provided
        date_from = datetime.strptime(date_from, '%Y-%m-%d').date() if date_from else None
        date_to = datetime.strptime(date_to, '%Y-%m-%d').date() if date_to else None

        # Fetch sales data
        user_sales = get_sales_by_user(date_from=date_from, date_to=date_to)


        context = {
            'user_sales': user_sales,
            'date_from': date_from,
            'date_to': date_to,
        }
        return render(request, 'partials/sales_by_user.html', context)
    else:
        return redirect('store:index')


@login_required
def register_customers(request):
    if request.user.is_authenticated:
        if request.method == 'POST':
            form = CustomerForm(request.POST)
            if form.is_valid():
                form.save()
                messages.success(request, 'Customer successfully registered')
                if request.headers.get('HX-Request'):
                    return JsonResponse({'success': True, 'message': 'Registration successful'})
                return redirect('store:customer_list')
        else:
            form = CustomerForm()
        if request.headers.get('HX-Request'):
            return render(request, 'partials/register_customers.html', {'form': form})
        return render(request, 'store/register_customers.html', {'form': form})
    else:
        return redirect('store:index')

@login_required
def customer_list(request):
    if request.user.is_authenticated:
        from userauth.permissions import can_manage_retail_customers
        if not can_manage_retail_customers(request.user):
            messages.error(request, 'You do not have permission to manage retail customers.')
            return redirect('store:index')
            
        # Optimized query with pagination for better performance
        customers = Customer.objects.select_related('wallet').order_by('name')
        
        # Add pagination - 50 customers per page
        paginator = Paginator(customers, 50)
        page_number = request.GET.get('page')
        page_obj = paginator.get_page(page_number)
        
        # Check if this is an HTMX request for partial updates
        if request.headers.get('HX-Request'):
            return render(request, 'partials/customer_list_partial.html', {'page_obj': page_obj})
        else:
            return render(request, 'partials/customer_list.html', {'page_obj': page_obj})
    else:
        return redirect('store:index')

@login_required
def wallet_details(request, pk):
    if request.user.is_authenticated:
        customer = get_object_or_404(Customer, pk=pk)
        wallet = customer.wallet
        return render(request, 'partials/wallet_details.html', {'customer': customer, 'wallet': wallet})
    else:
        return redirect('store:index')

@login_required
@user_passes_test(is_admin)
def delete_customer(request, pk):
    if request.user.is_authenticated:
        customer = get_object_or_404(Customer, pk=pk)
        customer.delete()
        messages.success(request, 'Customer deleted successfully.')
        return redirect('store:customer_list')
    else:
        return redirect('store:index')

@login_required
def add_funds(request, pk):
    if request.user.is_authenticated:
        customer = get_object_or_404(Customer, pk=pk)
        wallet = customer.wallet

        if request.method == 'POST':
            form = AddFundsForm(request.POST)
            if form.is_valid():
                amount = form.cleaned_data['amount']
                wallet.add_funds(amount, user=request.user)
                messages.success(request, f'Funds successfully added to {wallet.customer.name}\'s wallet.')
                return redirect('store:customer_list')
            else:
                messages.error(request, 'Error adding funds')
        else:
            form = AddFundsForm()
        return render(request, 'partials/add_funds.html', {'form': form, 'customer': customer})
    else:
        return redirect('store:index')

@login_required
@user_passes_test(is_admin)
def reset_wallet(request, pk):
    if request.user.is_authenticated:
        wallet = get_object_or_404(Wallet, pk=pk)
        wallet.balance = 0
        wallet.save()
        messages.success(request, f'{wallet.customer.name}\'s wallet reset successfully.')
        return redirect('store:customer_list')
    else:
        return redirect('store:index')

@login_required
def customers_on_negative(request):
    if request.user.is_authenticated:
        customers_on_negative = Customer.objects.filter(wallet__balance__lt=0)
        return render(request, 'partials/customers_on_negative.html', {'customers': customers_on_negative})
    else:
        return redirect('store:index')

@login_required
def edit_customer(request, pk):
    if request.user.is_authenticated:
        customer = get_object_or_404(Customer, id=pk)
        if request.method == 'POST':
            form = CustomerForm(request.POST, instance=customer)
            if form.is_valid():
                form.save()
                messages.success(request, f'{customer.name} edited successfully.')
                return redirect('store:customer_list')
            else:
                messages.warning(request, f'{customer.name} failed to edit, please try again')
        else:
            form = CustomerForm(instance=customer)
        if request.headers.get('HX-Request'):
            return render(request, 'partials/edit_customer_modal.html', {'form': form, 'customer': customer})
        else:
            return render(request, 'store/customer_list.html')
    else:
        return redirect('store:index')



@transaction.atomic
@login_required
def select_items(request, pk):
    if request.user.is_authenticated:
        customer = get_object_or_404(Customer, id=pk)
        # Store customer ID in user-specific session for later use
        from userauth.session_utils import set_user_customer_id
        set_user_customer_id(request, customer.id)

        # Check if this is a return action request
        action = request.GET.get('action', 'purchase')
        if request.method == 'POST':
            action = request.POST.get('action', 'purchase')

        # Filter items based on action
        if action == 'return':
            # For returns, show only items that were previously purchased by this customer
            purchased_item_ids = SalesItem.objects.filter(
                sales__customer=customer
            ).values_list('item_id', flat=True).distinct()
            items = Item.objects.filter(id__in=purchased_item_ids).order_by('name')
        else:
            # For purchases, show all available items
            items = Item.objects.all().order_by('name')

        # Fetch wallet balance
        wallet_balance = Decimal('0.0')
        try:
            wallet_balance = customer.wallet.balance
        except Wallet.DoesNotExist:
            messages.warning(request, 'This customer does not have an associated wallet.')

        if request.method == 'POST':
            action = request.POST.get('action', 'purchase')  # Default to purchase
            item_ids = request.POST.getlist('item_ids', [])
            quantities = request.POST.getlist('quantities', [])
            # discount_amounts = request.POST.getlist('discount_amounts', [])
            units = request.POST.getlist('units', [])

            if len(item_ids) != len(quantities):
                messages.warning(request, 'Mismatch between selected items and quantities.')
                return redirect('store:select_items', pk=pk)

            total_cost = Decimal('0.0')

            # Create a new Sales record only for purchases, not for returns
            sales = None
            if action == 'purchase':
                # Create a new Sales record for this transaction
                sales = Sales.objects.create(
                    user=request.user,
                    customer=customer,
                    total_amount=Decimal('0.0')
                )

            # Store payment method and status in session for later use in receipt generation
            payment_method = request.POST.get('payment_method', 'Cash')
            status = request.POST.get('status', 'Paid')
            request.session['payment_method'] = payment_method
            request.session['payment_status'] = status

            # Don't create a receipt here - it will be created in the receipt view


            for i, item_id in enumerate(item_ids):
                try:
                    item = Item.objects.get(id=item_id)
                    quantity = Decimal(quantities[i])
                    # discount = Decimal(discount_amounts[i]) if i < len(discount_amounts) else Decimal('0.0')
                    unit = units[i] if i < len(units) else item.unit

                    if action == 'purchase':
                        # Check stock and update inventory
                        if quantity > item.stock:
                            messages.warning(request, f'Not enough stock for {item.name}.')
                            return redirect('wholesale:select_wholesale_items', pk=pk)

                        item.stock -= quantity
                        item.save()

                        # Update or create a WholesaleCartItem
                        cart_item, created = Cart.objects.get_or_create(
                            user=request.user,
                            item=item,
                            defaults={'quantity': quantity, 'unit': unit, 'price': item.price}
                        )
                        if not created:
                            cart_item.quantity += quantity
                            # cart_item.discount_amount += discount
                            cart_item.unit = unit

                        # Always update the price to match the current item price
                        cart_item.price = item.price
                        cart_item.save()

                        # Calculate subtotal and log dispensing
                        base_subtotal = (item.price * quantity)
                        # Get discount amount from cart item if it exists
                        discount_amount = Decimal('0.00')
                        try:
                            cart_item = Cart.objects.get(user=request.user, item=item)
                            discount_amount = cart_item.discount_amount or Decimal('0.00')
                        except Cart.DoesNotExist:
                            pass

                        discounted_subtotal = base_subtotal - discount_amount
                        total_cost += discounted_subtotal

                        # Update or create SalesItem
                        sales_item, created = SalesItem.objects.get_or_create(
                            sales=sales,
                            item=item,
                            defaults={'quantity': quantity, 'price': item.price, 'discount_amount': discount_amount}
                        )
                        if not created:
                            sales_item.quantity += quantity
                            sales_item.discount_amount += discount_amount
                            sales_item.save()

                        # Update the sales total amount with discounted amount
                        sales.total_amount += discounted_subtotal
                        sales.save()

                        # Note: ItemSelectionHistory for purchases is now created in receipt function
                        # to ensure it only happens when receipts are actually generated

                    elif action == 'return':
                        # Handle return logic - find existing sales items for this customer and item
                        item.stock += quantity
                        item.save()

                        # Find existing sales items for this customer and item (exclude already returned sales)
                        existing_sales_items = SalesItem.objects.filter(
                            sales__customer=customer,
                            sales__is_returned=False,  # Only include non-returned sales
                            item=item
                        ).order_by('-sales__date')

                        if not existing_sales_items.exists():
                            messages.warning(request, f"No purchase record found for {item.name} for this customer, or all purchases have already been returned.")
                            continue

                        # Calculate total available quantity to return
                        total_available = sum(si.quantity for si in existing_sales_items)
                        if total_available < quantity:
                            messages.warning(request, f"Cannot return {quantity} {item.name}. Only {total_available} available for return.")
                            continue

                        # Process returns from most recent purchases first
                        remaining_to_return = quantity
                        total_refund_amount = Decimal('0.0')

                        for sales_item in existing_sales_items:
                            if remaining_to_return <= 0:
                                break

                            return_from_this_sale = min(sales_item.quantity, remaining_to_return)
                            refund_amount = (sales_item.price * return_from_this_sale)
                            total_refund_amount += refund_amount

                            # Update sales item
                            sales_item.quantity -= return_from_this_sale
                            if sales_item.quantity == 0:
                                sales_item.delete()
                            else:
                                sales_item.save()

                            # Update sales total
                            sales_item.sales.total_amount -= refund_amount
                            sales_item.sales.save()

                            remaining_to_return -= return_from_this_sale

                        # Get or create Formulation object for dosage_form
                        dosage_form_obj = None
                        if item.dosage_form:
                            dosage_form_obj, created = Formulation.objects.get_or_create(
                                dosage_form=item.dosage_form
                            )

                        # Calculate proportional discount for the return
                        proportional_discount = Decimal('0')
                        if sales_item.discount_amount > 0 and sales_item.quantity > 0:
                            discount_per_unit = sales_item.discount_amount / sales_item.quantity
                            proportional_discount = discount_per_unit * quantity

                        # Create dispensing log for the return
                        DispensingLog.objects.create(
                            user=request.user,
                            name=item.name,
                            brand=item.brand,
                            dosage_form=dosage_form_obj,
                            unit=unit,
                            quantity=quantity,
                            amount=total_refund_amount,
                            discount_amount=proportional_discount,
                            status='Returned'
                        )

                        # **Log Item Selection History (Return)**
                        ItemSelectionHistory.objects.create(
                            customer=customer,
                            user=request.user,
                            item=item,
                            quantity=quantity,
                            action=action,
                            unit_price=item.price,
                        )

                        total_cost -= total_refund_amount

                        # Mark affected sales as returned and track return information
                        from django.utils import timezone
                        affected_sales = set()
                        for sales_item in existing_sales_items:
                            if sales_item.sales not in affected_sales:
                                affected_sales.add(sales_item.sales)

                        # Update return tracking for affected sales
                        for sales in affected_sales:
                            if not sales.is_returned:  # Only update if not already marked as returned
                                sales.is_returned = True
                                sales.return_date = timezone.now()
                                sales.return_amount += total_refund_amount
                                sales.return_processed_by = request.user
                                sales.save()

                except Item.DoesNotExist:
                    messages.warning(request, 'One of the selected items does not exist.')
                    return redirect('store:select_items', pk=pk)

            # Add success message for return processing
            if action == 'return':
                messages.success(request, f'Items successfully returned and sales statistics updated.')

            # Handle HTMX response for return processing
            if action == 'return' and request.headers.get('HX-Request'):
                # Update daily and monthly sales data
                daily_sales = get_daily_sales()
                monthly_sales = get_monthly_sales_with_expenses()

                # Return updated dispensing log for HTMX requests
                context = {
                    'logs': DispensingLog.objects.filter(user=request.user).order_by('-created_at'),
                    'daily_sales': daily_sales,
                    'monthly_sales': monthly_sales
                }
                return render(request, 'store/dispensing_log.html', context)

            # Handle return processing for registered customers
            if action == 'return':
                try:
                    wallet = customer.wallet
                    # For registered customers, provide automatic wallet refund on returns
                    if abs(total_cost) > 0:
                        wallet.balance += abs(total_cost)
                        wallet.save()

                        # Create transaction history for the return refund
                        TransactionHistory.objects.create(
                            customer=customer,
                            user=request.user,
                            transaction_type='refund',
                            amount=abs(total_cost),
                            description=f'Refund for returned items (â‚¦{abs(total_cost)})'
                        )
                        messages.success(request, f'Return processed for â‚¦{abs(total_cost)}. Amount refunded to wallet.')
                except Wallet.DoesNotExist:
                    messages.warning(request, 'Customer does not have a wallet.')
                    return redirect('store:select_items', pk=pk)

            # Note: Wallet deduction for purchases now happens during receipt generation, not here

            # Store payment method and status in user-specific session for receipt generation
            from userauth.session_utils import set_user_payment_data
            payment_method = request.POST.get('payment_method', 'Cash')
            status = request.POST.get('status', 'Paid')
            set_user_payment_data(request, payment_method=payment_method, payment_status=status)

            action_message = 'added to cart' if action == 'purchase' else 'returned successfully'
            messages.success(request, f'Action completed: Items {action_message}.')
            return redirect('store:cart')

        return render(request, 'partials/select_items.html', {
            'customer': customer,
            'items': items,
            'wallet_balance': wallet_balance,
            'action': action
        })
    else:
        return redirect('store:index')



@never_cache
@login_required
def dispensing_log(request):
    if request.user.is_authenticated:
        # Permission check: Superusers, Admins, and Managers can see all users, others can see all users' logs but with limited statistics
        can_view_all_users = can_view_all_users_dispensing(request.user)

        # Get user queryset and logs - now all users can see all dispensing logs
        # Optimize user queryset with select_related for better performance
        user_queryset = User.objects.filter(dispensinglog__isnull=False).distinct().order_by('username')

        # Optimize logs query with select_related for foreign keys
        logs = DispensingLog.objects.select_related('user', 'dosage_form').order_by('-created_at')

        # Initialize search form with user queryset
        search_form = DispensingLogSearchForm(request.GET, user_queryset=user_queryset)

        # Apply filters based on search parameters
        if search_form.is_valid():
            # Filter by item name (search by first few letters)
            if item_name := search_form.cleaned_data.get('item_name'):
                logs = logs.filter(name__istartswith=item_name)

            # Filter by brand (search by first few letters)
            if brand := search_form.cleaned_data.get('brand'):
                logs = logs.filter(brand__istartswith=brand)

            # Filter by date range
            date_from = search_form.cleaned_data.get('date_from')
            date_to = search_form.cleaned_data.get('date_to')
            if date_from or date_to:
                from utils.date_utils import filter_queryset_by_date_range
                logs = filter_queryset_by_date_range(logs, 'created_at',
                                                   str(date_from) if date_from else None,
                                                   str(date_to) if date_to else None)

            # Filter by status
            if status_filter := search_form.cleaned_data.get('status'):
                logs = logs.filter(status=status_filter)

            # Filter by user (only for admins/managers)
            if user_filter := search_form.cleaned_data.get('user'):
                if can_view_all_users:
                    logs = logs.filter(user=user_filter)
                # For regular users, this filter is ignored as they can see all data but can't filter by specific users

        # Check if this is an HTMX request
        if request.headers.get('HX-Request'):
            # Return only the partial template with filtered logs
            return render(request, 'partials/partials_dispensing_log.html', {'logs': logs})
        else:
            # Render the full template for non-HTMX requests
            return render(request, 'store/dispensing_log.html', {
                'logs': logs,
                'search_form': search_form,
                'can_view_all_users': can_view_all_users
            })
    else:
        return redirect('store:index')


@login_required
def dispensing_log_search_suggestions(request):
    """
    Provides search suggestions for item names in dispensing log
    """
    if request.user.is_authenticated:
        query = request.GET.get('q', '').strip()
        suggestions = []

        if query and len(query) >= 1:  # Reduce minimum query length for faster suggestions
            # Optimized query with better performance
            dispensed_items = DispensingLog.objects.filter(
                name__istartswith=query
            ).values_list('name', flat=True).distinct().order_by('name')[:8]  # Reduce to 8 for faster response

            suggestions = list(dispensed_items)

        return JsonResponse({'suggestions': suggestions})
    else:
        return JsonResponse({'suggestions': []})


@login_required
def dispensing_log_stats(request):
    """
    Provides statistics for dispensed items based on searched/filtered data
    """
    if request.user.is_authenticated:
        try:
            from django.db.models import Count, Sum
            from datetime import date, timedelta
            from decimal import Decimal

            # Get current month's start and end dates for default stats
            today = date.today()
            current_month_start = today.replace(day=1)

            # Calculate next month's first day to get current month's end
            if today.month == 12:
                next_month_start = today.replace(year=today.year + 1, month=1, day=1)
            else:
                next_month_start = today.replace(month=today.month + 1, day=1)
            current_month_end = next_month_start - timedelta(days=1)

            # Default to current month instead of last 30 days
            start_date = current_month_start
            end_date = current_month_end

            # Override with specific date range if provided
            date_from_filter = request.GET.get('date_from')
            date_to_filter = request.GET.get('date_to')

            if date_from_filter or date_to_filter:
                try:
                    if date_from_filter:
                        start_date = parse_date(date_from_filter)
                        if not start_date:
                            start_date = current_month_start
                    if date_to_filter:
                        end_date = parse_date(date_to_filter)
                        if not end_date:
                            end_date = current_month_end
                except Exception as e:
                    # If date parsing fails, use current month default
                    pass

            # Permission check: Superusers, Admins, and Managers can see all users, others can see all logs but with limited statistics
            can_view_all_users = can_view_all_users_dispensing(request.user)
            can_view_full_stats = can_view_full_dispensing_stats(request.user)

            # Get base queryset - all users can see all dispensing logs
            logs = DispensingLog.objects.all()

            # For statistics calculation, regular users still get totals for the filtered date/search criteria
            # but they see all users' dispensing logs in the list

            # Apply the same filters as the main dispensing log view to ensure stats match filtered data
            # Filter by item name (search by first few letters)
            if item_name := request.GET.get('item_name'):
                logs = logs.filter(name__istartswith=item_name)

            # Filter by brand (search by first few letters)
            if brand := request.GET.get('brand'):
                logs = logs.filter(brand__istartswith=brand)

            # Filter by date range - this is the key change to make stats match search results
            date_from_filter = request.GET.get('date_from')
            date_to_filter = request.GET.get('date_to')
            if date_from_filter or date_to_filter:
                from utils.date_utils import filter_queryset_by_date_range
                logs = filter_queryset_by_date_range(logs, 'created_at',
                                                   date_from_filter, date_to_filter)
            else:
                # For users with full stats access (Admin, Manager, Superuser): show current month
                # For users with limited access (Pharmacist, Pharm-Tech, Salesperson): show today only
                if can_view_full_stats:
                    # Default to current month for privileged users
                    logs = logs.filter(created_at__date__range=[start_date, end_date])
                else:
                    # Default to today only for Pharmacists, Pharm-Techs, and Salespersons
                    today = date.today()
                    logs = logs.filter(created_at__date=today)
                    # Update date range for context
                    start_date = today
                    end_date = today

            # Filter by status
            if status_filter := request.GET.get('status'):
                logs = logs.filter(status=status_filter)

            # Filter by user (if user has permission to view all users)
            if can_view_all_users and (user_filter := request.GET.get('user')):
                try:
                    user_id = int(user_filter)
                    logs = logs.filter(user_id=user_id)
                except (ValueError, TypeError):
                    pass

            # Convert QuerySets to lists for JSON serialization
            try:
                top_dispensed_items = list(logs.values('name').annotate(
                    count=Count('name'),
                    total_amount=Sum('amount')
                ).order_by('-count')[:5])

                dispensed_by_status = list(logs.values('status').annotate(
                    count=Count('status')
                ).order_by('-count'))
            except Exception as e:
                top_dispensed_items = []
                dispensed_by_status = []

            # Convert Decimal to float for JSON serialization
            try:
                total_amount = logs.aggregate(total=Sum('amount'))['total'] or Decimal('0')
                total_amount = float(total_amount)
            except Exception as e:
                total_amount = 0.0

            # Convert Decimal amounts in top_dispensed_items
            for item in top_dispensed_items:
                try:
                    if item.get('total_amount'):
                        item['total_amount'] = float(item['total_amount'])
                    else:
                        item['total_amount'] = 0.0
                except Exception as e:
                    item['total_amount'] = 0.0

            # Calculate additional stats for better insights
            total_quantity_dispensed = logs.aggregate(total_qty=Sum('quantity'))['total_qty'] or Decimal('0')

            # Get monthly total sales for comparison (if not already filtered by month)
            monthly_total_sales = Decimal('0')
            if not request.GET.get('date'):  # Only show monthly comparison when showing default monthly stats
                try:
                    monthly_sales_data = get_monthly_sales_with_expenses()
                    current_month_data = None
                    for month, data in monthly_sales_data:
                        if month.year == today.year and month.month == today.month:
                            current_month_data = data
                            break

                    if current_month_data:
                        monthly_total_sales = float(current_month_data['total_sales'])
                except Exception as e:
                    monthly_total_sales = 0.0

            # Determine the context of the stats (filtered vs default)
            is_filtered = bool(request.GET.get('item_name') or request.GET.get('date_from') or
                             request.GET.get('date_to') or request.GET.get('status') or request.GET.get('user'))

            # For users without full stats access (Pharmacists, Pharm-Techs, Salespersons), show statistics but hide sensitive financial data
            if not can_view_full_stats:
                # Determine the appropriate context message
                if request.GET.get('date_from') or request.GET.get('date_to'):
                    period_description = 'Filtered Period Statistics'
                    context_description = 'Filtered Period'
                else:
                    # For users with limited access, default is always daily (today's sales)
                    period_description = 'Daily Statistics'
                    context_description = 'Daily'

                # Get daily total sales for regular users (from dispensing logs in the filtered date range)
                daily_total_sales = Decimal('0')
                try:
                    # Calculate total sales from dispensing logs (matching the displayed data and date range)
                    # Use the same filtered logs that are being displayed
                    # Use discounted amounts (amount field now contains discounted amount)
                    filtered_dispensing_sales = logs.filter(
                        status='Dispensed'  # Only count dispensed items
                    ).aggregate(
                        total=Sum('amount')
                    )['total'] or Decimal('0')

                    # Calculate total returns from dispensing logs in the same date range
                    filtered_returns = logs.filter(
                        status__in=['Returned', 'Partially Returned']  # Count all types of returns
                    ).aggregate(
                        total=Sum('amount')
                    )['total'] or Decimal('0')

                    # Net sales = Dispensed - Returned
                    daily_total_sales = float(filtered_dispensing_sales - filtered_returns)
                except Exception as e:
                    daily_total_sales = 0.0

                stats = {
                    'total_items_dispensed': logs.count(),
                    'total_amount': total_amount,  # This will be hidden in frontend
                    'total_quantity_dispensed': float(total_quantity_dispensed),  # This will be hidden in frontend
                    'unique_items': logs.values('name').distinct().count(),
                    'daily_total_sales': daily_total_sales,  # Daily sales for regular users
                    'is_filtered': is_filtered,
                    'date_range': {
                        'start': start_date.isoformat(),
                        'end': end_date.isoformat(),
                        'description': context_description
                    },
                    'context': {
                        'period': period_description,
                        'user_restricted': True
                    }
                }
            else:
                # For privileged users, show all detailed statistics

                # Calculate daily total sales for privileged users (from filtered dispensing logs)
                daily_total_sales_privileged = Decimal('0')
                try:
                    # Calculate total sales from dispensing logs (matching the displayed data and date range)
                    # Use the same filtered logs that are being displayed
                    filtered_dispensing_sales_privileged = logs.filter(
                        status='Dispensed'  # Only count dispensed items
                    ).aggregate(
                        total=Sum('amount')
                    )['total'] or Decimal('0')

                    # Calculate total returns from dispensing logs in the same date range
                    filtered_returns_privileged = logs.filter(
                        status__in=['Returned', 'Partially Returned']  # Count all types of returns
                    ).aggregate(
                        total=Sum('amount')
                    )['total'] or Decimal('0')

                    # Net sales = Dispensed - Returned
                    daily_total_sales_privileged = float(filtered_dispensing_sales_privileged - filtered_returns_privileged)
                except Exception as e:
                    daily_total_sales_privileged = 0.0

                stats = {
                    'total_items_dispensed': logs.count(),
                    'total_amount': total_amount,
                    'total_quantity_dispensed': float(total_quantity_dispensed),
                    'unique_items': logs.values('name').distinct().count(),
                    'top_dispensed_items': top_dispensed_items,
                    'dispensed_by_status': dispensed_by_status,
                    'monthly_total_sales': monthly_total_sales,
                    'daily_total_sales': daily_total_sales_privileged,  # Add daily sales for privileged users
                    'is_filtered': is_filtered,
                    'date_range': {
                        'start': start_date.isoformat(),
                        'end': end_date.isoformat(),
                        'description': 'Current Month' if not (request.GET.get('date_from') or request.GET.get('date_to')) else 'Filtered Date Range'
                    },
                    'context': {
                        'period': 'Current Month Total Sales' if not is_filtered else 'Filtered Results',
                        'filters_applied': {
                            'item_name': request.GET.get('item_name', ''),
                            'date_from': request.GET.get('date_from', ''),
                            'date_to': request.GET.get('date_to', ''),
                            'status': request.GET.get('status', ''),
                            'user': request.GET.get('user', '') if can_view_all_users else ''
                        },
                        'user_restricted': False
                    }
                }

            return JsonResponse(stats, safe=False)

        except Exception as e:
            # Return error response with basic stats
            return JsonResponse({
                'error': f'Error generating stats: {str(e)}',
                'total_items_dispensed': 0,
                'total_amount': 0.0,
                'unique_items': 0,
                'top_dispensed_items': [],
                'dispensed_by_status': [],
                'date_range': {
                    'start': date.today().isoformat(),
                    'end': date.today().isoformat()
                }
            }, status=500)
    else:
        return JsonResponse({'error': 'Unauthorized'}, status=401)


@never_cache
def receipt_list(request):
    if request.user.is_authenticated:
        receipts = Receipt.objects.all().order_by('-date')  # Order by date, latest first
        return render(request, 'partials/receipt_list.html', {'receipts': receipts})
    else:
        return redirect('store:index')

def search_receipts(request):
    if request.user.is_authenticated:
        from utils.date_utils import filter_queryset_by_date, get_date_filter_context

        # Get the date query from the GET request
        date_context = get_date_filter_context(request, 'date')
        date_query = date_context['date_string']

        # Debugging log
        print(f"Date Query: {date_query}")

        receipts = Receipt.objects.all()
        if date_query and date_context['is_valid_date']:
            receipts = filter_queryset_by_date(receipts, 'date', date_query)
        elif date_query and not date_context['is_valid_date']:
            print(f"Invalid date format: {date_query}")

        # Order receipts by date
        receipts = receipts.order_by('-date')

        # Debugging log for queryset
        print(f"Filtered Receipts: {receipts.query}")

        # Check if this is an HTMX request (for embedded search)
        if request.headers.get('HX-Request'):
            return render(request, 'partials/search_receipts.html', {'receipts': receipts})
        else:
            # Regular page request - redirect to receipt list page
            return redirect(f"{reverse('store:receipt_list')}?date={date_query}" if date_query else reverse('store:receipt_list'))
    else:
        return redirect('store:index')




@login_required
def exp_date_alert(request):
    if request.user.is_authenticated:
        from userauth.permissions import can_manage_retail_expiry
        if not can_manage_retail_expiry(request.user):
            messages.error(request, 'You do not have permission to manage retail expiry dates.')
            return redirect('store:index')

        alert_threshold = datetime.now() + timedelta(days=90)

        expiring_items = Item.objects.filter(exp_date__lte=alert_threshold, exp_date__gt=datetime.now())

        expired_items = Item.objects.filter(exp_date__lt=datetime.now())

        for expired_item in expired_items:

            if expired_item.stock > 0:

                expired_item.stock = 0
                expired_item.save()

        return render(request, 'partials/exp_date_alert.html', {
            'expired_items': expired_items,
            'expiring_items': expiring_items,
        })
    else:
        return redirect('store:index')


@login_required
def customer_history(request, customer_id):
    if request.user.is_authenticated:
        customer = get_object_or_404(Customer, id=customer_id)

        histories = SalesItem.objects.filter(
            sales__customer=customer
        ).select_related(
            'item', 'sales'
        ).order_by('-sales__date')

        # Process histories and calculate totals
        history_data = {}
        for history in histories:
            year = history.sales.date.year
            month = history.sales.date.strftime('%B')  # Full month name

            if year not in history_data:
                history_data[year] = {'total': Decimal('0'), 'months': {}}

            if month not in history_data[year]['months']:
                history_data[year]['months'][month] = {'total': Decimal('0'), 'items': []}

            # Calculate subtotal
            calculated_subtotal = history.quantity * history.price

            # Update totals
            history_data[year]['total'] += calculated_subtotal
            history_data[year]['months'][month]['total'] += calculated_subtotal

            # Add the history item to the month's items list
            history_data[year]['months'][month]['items'].append({
                'date': history.sales.date,
                'item': history.item,
                'quantity': history.quantity,
                'subtotal': calculated_subtotal
            })

        context = {
            'customer': customer,
            'history_data': history_data,
        }

        if request.headers.get('HX-Request'):
            return render(request, 'partials/customer_history.html', context)
        else:
            return render(request, 'store/customer_history.html', context)
    return redirect('store:index')


@login_required
def register_supplier_view(request):
    if request.user.is_authenticated:
        if request.method == 'POST':
            form = SupplierRegistrationForm(request.POST)
            if form.is_valid():
                form.save()
                messages.success(request, 'Supplier successfully registered')
                return redirect('store:supplier_list')
        else:
            form = SupplierRegistrationForm()
        return render(request, 'partials/supplier_reg_form.html', {'form': form})
    else:
        return redirect('store:index')

def supplier_list_partial(request):
    if request.user.is_authenticated:
        suppliers = Supplier.objects.all()  # Get all suppliers
        return render(request, 'partials/supplier_list.html', {'suppliers': suppliers})
    else:
        return redirect('store:index')

@login_required
def list_suppliers_view(request):
    if request.user.is_authenticated:
        suppliers = Supplier.objects.all().order_by('name')  # Get all suppliers ordered by name
        return render(request, 'partials/supplier_list.html', {'suppliers': suppliers})
    else:
        return redirect('store:index')

@login_required
def edit_supplier(request, pk):
    if request.user.is_authenticated:
        supplier = get_object_or_404(Supplier, id=pk)
        if request.method == 'POST':
            form = SupplierRegistrationForm(request.POST, instance=supplier)
            if form.is_valid():
                form.save()
                messages.success(request, f'{supplier.name} edited successfully.')
                return redirect('store:supplier_list')
            else:
                messages.warning(request, f'{supplier.name} failed to edit, please try again')
        else:
            form = SupplierRegistrationForm(instance=supplier)
        if request.headers.get('HX-Request'):
            return render(request, 'partials/edit_supplier_modal.html', {'form': form, 'supplier': supplier})
        else:
            return render(request, 'partials/supplier_list.html')
    else:
        return redirect('store:index')

@login_required
@user_passes_test(is_admin)
def delete_supplier(request, pk):
    if request.user.is_authenticated:
        supplier = get_object_or_404(Supplier, id=pk)
        supplier_name = supplier.name
        supplier.delete()
        messages.success(request, f'{supplier_name} deleted successfully.')
        return redirect('store:supplier_list')
    else:
        return redirect('store:index')



@user_passes_test(can_manage_retail_procurement)
@login_required
def add_procurement(request):
    if request.user.is_authenticated:
        # Use the predefined formset from forms.py
        from .forms import ProcurementItemFormSet

        if request.method == 'POST':
            # Check if we're continuing a draft procurement
            draft_id = request.GET.get('draft_id') or request.POST.get('draft_id')

            if draft_id:
                try:
                    draft_procurement = Procurement.objects.get(id=draft_id, status='draft')
                    procurement_form = ProcurementForm(request.POST, instance=draft_procurement)

                    # When continuing a draft, we need to handle the formset differently
                    # First, get the existing items
                    existing_items = draft_procurement.items.all()

                    # Create the formset with the POST data
                    formset = ProcurementItemFormSet(request.POST, prefix='form')

                    # We'll handle the items manually in the save section
                except Procurement.DoesNotExist:
                    messages.error(request, "Draft procurement not found.")
                    procurement_form = ProcurementForm(request.POST)
                    formset = ProcurementItemFormSet(request.POST, queryset=ProcurementItem.objects.none(), prefix='form')
            else:
                procurement_form = ProcurementForm(request.POST)
                formset = ProcurementItemFormSet(request.POST, queryset=ProcurementItem.objects.none(), prefix='form')

            action = request.POST.get('action', 'save')

            # Check if the formset is valid
            # We'll handle empty forms specially
            formset_valid = formset.is_valid()

            # If there are validation errors for empty forms, ignore them
            if not formset_valid:
                # Check if the only errors are for empty forms
                empty_form_errors_only = True
                for form in formset:
                    if hasattr(form, 'errors') and form.errors:
                        # If the form has item_name and it's empty, this is an empty form
                        if 'item_name' in form.errors and not form.data.get(f'{form.prefix}-item_name', ''):
                            # This is an empty form with errors, which is expected
                            continue
                        # If we get here, there's a real error
                        empty_form_errors_only = False
                        break

                # If the only errors are for empty forms, consider the formset valid
                if empty_form_errors_only:
                    formset_valid = True

            if procurement_form.is_valid() and formset_valid:
                # Check if we're continuing a draft procurement
                draft_id = request.GET.get('draft_id') or request.POST.get('draft_id')

                if draft_id:
                    try:
                        procurement = Procurement.objects.get(id=draft_id, status='draft')
                        # Update the procurement with the form data
                        procurement.supplier = procurement_form.cleaned_data['supplier']
                        procurement.date = procurement_form.cleaned_data['date']

                        # Delete existing items to avoid duplicates
                        procurement.items.all().delete()
                    except Procurement.DoesNotExist:
                        # Create a new procurement if draft not found
                        procurement = procurement_form.save(commit=False)
                        procurement.created_by = request.user
                else:
                    # Create a new procurement
                    procurement = procurement_form.save(commit=False)
                    procurement.created_by = request.user

                # Set status based on action
                if action == 'pause':
                    procurement.status = 'draft'
                    # For pause, we just save the items without moving them to store
                    procurement.save()

                    for form in formset:
                        # Skip forms that are marked for deletion or don't have cleaned_data
                        if not hasattr(form, 'cleaned_data') or form.cleaned_data.get('DELETE'):
                            continue

                        # Save only forms with an item_name
                        if form.cleaned_data.get('item_name'):
                            procurement_item = form.save(commit=False)
                            procurement_item.procurement = procurement
                            # Ensure markup has a default value
                            if not hasattr(procurement_item, 'markup') or procurement_item.markup is None:
                                procurement_item.markup = 0
                            # Don't move to store yet, just save the procurement item
                            procurement_item.save(commit=True, move_to_store=False)
                else:
                    # For save, we complete the procurement and move items to store
                    procurement.status = 'completed'
                    procurement.save()

                    for form in formset:
                        # Skip forms that are marked for deletion or don't have cleaned_data
                        if not hasattr(form, 'cleaned_data') or form.cleaned_data.get('DELETE'):
                            continue

                        # Save only forms with an item_name
                        if form.cleaned_data.get('item_name'):  # Save only valid items
                            procurement_item = form.save(commit=False)
                            procurement_item.procurement = procurement
                            # Ensure markup has a default value
                            if not hasattr(procurement_item, 'markup') or procurement_item.markup is None:
                                procurement_item.markup = 0
                            # Move to store when saving as completed
                            procurement_item.save(commit=True, move_to_store=True)

                # Calculate and update the total
                procurement.calculate_total()

                if action == 'pause':
                    messages.success(request, "Procurement saved as draft. You can continue later.")
                    return redirect('store:procurement_list')  # Replace with your actual URL name
                else:
                    messages.success(request, "Procurement and items added successfully!")
                    return redirect('store:procurement_list')  # Replace with your actual URL name
            else:
                # Print form errors for debugging
                if not procurement_form.is_valid():
                    for field, errors in procurement_form.errors.items():
                        for error in errors:
                            messages.error(request, f"{field}: {error}")

                if not formset.is_valid():
                    for i, form in enumerate(formset):
                        # Skip errors for empty forms
                        if 'item_name' in form.errors and not form.data.get(f'{form.prefix}-item_name', ''):
                            continue

                        for field, errors in form.errors.items():
                            for error in errors:
                                messages.error(request, f"Item {i+1} - {field}: {error}")

                messages.error(request, "Please correct the errors below.")
        else:
            # Check if we're continuing a draft procurement
            draft_id = request.GET.get('draft_id')
            if draft_id:
                try:
                    draft_procurement = Procurement.objects.get(id=draft_id, status='draft')
                    procurement_form = ProcurementForm(instance=draft_procurement)
                    # Use prefix to match the formset in the template
                    formset = ProcurementItemFormSet(queryset=draft_procurement.items.all(), prefix='form')
                except Procurement.DoesNotExist:
                    messages.error(request, "Draft procurement not found.")
                    procurement_form = ProcurementForm()
                    formset = ProcurementItemFormSet(queryset=ProcurementItem.objects.none(), prefix='form')
            else:
                procurement_form = ProcurementForm()
                formset = ProcurementItemFormSet(queryset=ProcurementItem.objects.none(), prefix='form')

        return render(
            request,
            'partials/add_procurement.html',
            {
                'procurement_form': procurement_form,
                'formset': formset,
            }
        )
    else:
        return redirect('store:index')

@user_passes_test(can_manage_retail_procurement)
@login_required
def procurement_form(request):
    if request.user.is_authenticated:
        # Create an empty formset for the items
        item_formset = ProcurementItemFormSet(queryset=ProcurementItem.objects.none())  # Replace with your model if needed

        # Get the empty form (form for the new item)
        new_form = item_formset.empty_form

        # Render the HTML for the new form
        return render(request, 'partials/procurement_form.html', {'form': new_form})
    else:
        return redirect('store:index')

@login_required
def search_store_items(request):
    """API endpoint for searching store items for procurement"""
    query = request.GET.get('q', '')
    if query and len(query) >= 2:
        # Search for items in both Item and StoreItem models
        store_items = StoreItem.objects.filter(
            Q(name__icontains=query) |
            Q(brand__icontains=query) |
            Q(dosage_form__icontains=query)
        ).order_by('name')[:10]

        items = Item.objects.filter(
            Q(name__icontains=query) |
            Q(brand__icontains=query) |
            Q(dosage_form__icontains=query)
        ).order_by('name')[:10]

        # Combine results
        results = []

        # Add StoreItem results
        for item in store_items:
            results.append({
                'id': f'store_{item.id}',
                'name': item.name,
                'brand': item.brand or '',
                'dosage_form': item.dosage_form or '',
                'unit': item.unit,
                'cost_price': float(item.cost_price),
                'expiry_date': item.expiry_date.isoformat() if item.expiry_date else '',
                'source': 'store'
            })

        # Add Item results
        for item in items:
            results.append({
                'id': f'item_{item.id}',
                'name': item.name,
                'brand': item.brand or '',
                'dosage_form': item.dosage_form or '',
                'unit': item.unit,
                'cost_price': float(item.cost),
                'expiry_date': item.exp_date.isoformat() if item.exp_date else '',
                'source': 'item'
            })

        return JsonResponse({'results': results})
    else:
        return JsonResponse({'results': []})

@user_passes_test(can_view_procurement_history)
@login_required
def procurement_list(request):
    if request.user.is_authenticated:
        procurements = (
            Procurement.objects.annotate(calculated_total=Sum('items__subtotal'))
            .order_by('-date')
        )
        return render(request, 'partials/procurement_list.html', {
            'procurements': procurements,
        })
    else:
        return redirect('store:index')

@user_passes_test(can_view_procurement_history)
@login_required
def search_procurement(request):
    if request.user.is_authenticated:
        # Base query with calculated total and ordering
        procurements = (
            Procurement.objects.annotate(calculated_total=Sum('items__subtotal'))
            .order_by('-date')
        )

        # Get search parameters from the request
        name_query = request.GET.get('name', '').strip()

        # Apply filters if search parameters are provided
        if name_query:
            procurements = procurements.filter(supplier__name__icontains=name_query)

        # Check if this is an HTMX request (for embedded search)
        if request.headers.get('HX-Request'):
            # Render the filtered results
            return render(request, 'partials/search_procurement.html', {
                'procurements': procurements,
            })
        else:
            # Regular page request - redirect to procurement list page
            return redirect(f"{reverse('store:procurement_list')}?name={name_query}" if name_query else reverse('store:procurement_list'))
    else:
        return redirect('store:index')

@user_passes_test(can_view_procurement_history)
@login_required
def procurement_detail(request, procurement_id):
    if request.user.is_authenticated:
        procurement = get_object_or_404(Procurement, id=procurement_id)

        # Calculate total from ProcurementItem objects
        total = procurement.items.aggregate(total=models.Sum('subtotal'))['total'] or 0

        return render(request, 'partials/procurement_detail.html', {
            'procurement': procurement,
            'total': total,
        })
    else:
        return redirect('store:index')




@login_required
def transfer_multiple_store_items(request):
    if request.user.is_authenticated:
        if request.method == "GET":
            search_query = request.GET.get("search", "").strip()
            if search_query:
                store_items = StoreItem.objects.filter(
                    Q(name__icontains=search_query) | 
                    Q(brand__icontains=search_query)
                ).distinct().order_by('name')
            else:
                store_items = StoreItem.objects.all().order_by('name')

            # Check if there are any items to display
            if not store_items.exists():
                messages.info(request, "No items found in the store. Please add items to the store through procurement or direct entry first.")

            # Get unit choices from the UNIT constant
            unit_choices = UNIT

            # If this is an HTMX request triggered by search, return only the table body
            if request.headers.get("HX-Request") and "search" in request.GET:
                return render(request, "partials/_store_items_table.html", {
                    "store_items": store_items,
                    "unit_choices": unit_choices
                })

            return render(request, "store/transfer_multiple_store_items.html", {
                "store_items": store_items,
                "unit_choices": unit_choices
            })

        elif request.method == "POST":
            processed_items = []
            errors = []
            store_items = list(StoreItem.objects.all())  # materialize the queryset

            for item in store_items:
                # Process only items that have been selected.
                if request.POST.get(f'select_{item.id}') == 'on':
                    try:
                        qty = float(request.POST.get(f'quantity_{item.id}', 0))
                        markup = float(request.POST.get(f'markup_{item.id}', 0))
                        transfer_unit = request.POST.get(f'transfer_unit_{item.id}', item.unit)
                        unit_conversion = float(request.POST.get(f'unit_conversion_{item.id}', 1))
                        price_override = request.POST.get(f'price_override_{item.id}') == 'on'
                        manual_price = float(request.POST.get(f'manual_price_{item.id}', 0)) if price_override else 0
                    except (ValueError, TypeError):
                        errors.append(f"Invalid input for {item.name}.")
                        continue

                    destination = request.POST.get(f'destination_{item.id}', '')

                    if qty <= 0:
                        errors.append(f"Quantity must be positive for {item.name}.")
                        continue
                    if item.stock < qty:
                        errors.append(f"Not enough stock for {item.name}.")
                        continue
                    if destination not in ['retail', 'wholesale']:
                        errors.append(f"Invalid destination for {item.name}.")
                        continue
                    if transfer_unit not in [unit[0] for unit in UNIT]:
                        errors.append(f"Invalid unit for {item.name}.")
                        continue
                    if unit_conversion <= 0:
                        errors.append(f"Unit conversion must be positive for {item.name}.")
                        continue

                    # Get the original cost
                    original_cost = item.cost_price

                    # Calculate the destination quantity using the unit conversion
                    # Convert both values to Decimal to avoid type errors
                    dest_qty_per_source = Decimal(str(unit_conversion))

                    # Adjust the cost based on the unit conversion
                    # If converting from higher to lower unit (e.g., box to tablet), divide cost by conversion factor
                    # If converting from lower to higher unit (e.g., tablet to box), multiply cost by conversion factor
                    # The cost per unit should remain consistent
                    if dest_qty_per_source > 1:  # Converting from higher to lower unit
                        # For example: 1 box = 100 tablets, so cost per tablet = box_cost / 100
                        adjusted_cost = original_cost / dest_qty_per_source
                    else:  # Converting from lower to higher unit or same unit
                        # For example: 100 tablets = 1 box, so cost per box = tablet_cost * 100
                        adjusted_cost = original_cost * (Decimal('1') / dest_qty_per_source) if dest_qty_per_source > 0 else original_cost

                    # Use the adjusted cost for price calculations
                    cost = adjusted_cost
                    if price_override:
                        # Use the manually entered price
                        new_price = Decimal(str(manual_price))
                    else:
                        # Calculate price based on cost and markup
                        new_price = cost + (cost * Decimal(markup) / Decimal(100))

                    # Process transfer for this item.
                    if destination == "retail":
                        # First, try to find an exact match (same name, brand, and unit)
                        exact_matches = Item.objects.filter(
                            name=item.name,
                            brand=item.brand,
                            unit=transfer_unit
                        )

                        if exact_matches.exists():
                            # Use the existing item with exact match
                            dest_item = exact_matches.first()
                            created = False
                        else:
                            # If no exact match, look for items with same name but different unit
                            similar_items = Item.objects.filter(
                                name=item.name,
                                brand=item.brand
                            )

                            if similar_items.exists():
                                # Use the first similar item but update its unit
                                dest_item = similar_items.first()
                                dest_item.unit = transfer_unit
                                created = False
                            else:
                                # Create a new item if no match found
                                dest_item = Item.objects.create(
                                    name=item.name,
                                    brand=item.brand,
                                    unit=transfer_unit,
                                    dosage_form=item.dosage_form,
                                    cost=cost,
                                    price=new_price,
                                    markup=markup,
                                    stock=0,
                                    exp_date=item.expiry_date
                                )
                                created = True
                    else:  # destination == "wholesale"
                        # First, try to find an exact match (same name, brand, and unit)
                        exact_matches = WholesaleItem.objects.filter(
                            name=item.name,
                            brand=item.brand,
                            unit=transfer_unit
                        )

                        if exact_matches.exists():
                            # Use the existing item with exact match
                            dest_item = exact_matches.first()
                            created = False
                        else:
                            # If no exact match, look for items with same name but different unit
                            similar_items = WholesaleItem.objects.filter(
                                name=item.name,
                                brand=item.brand
                            )

                            if similar_items.exists():
                                # Use the first similar item but update its unit
                                dest_item = similar_items.first()
                                dest_item.unit = transfer_unit
                                created = False
                            else:
                                # Create a new item if no match found
                                dest_item = WholesaleItem.objects.create(
                                    name=item.name,
                                    brand=item.brand,
                                    unit=transfer_unit,
                                    dosage_form=item.dosage_form,
                                    cost=cost,
                                    price=new_price,
                                    markup=markup,
                                    stock=0,
                                    exp_date=item.expiry_date
                                )
                                created = True

                    # Calculate the final destination quantity (source quantity * conversion factor)
                    dest_qty = Decimal(str(qty)) * dest_qty_per_source

                    # Update the destination item's stock and key fields.
                    dest_item.stock += dest_qty

                    # Always update the cost price
                    dest_item.cost = cost

                    # Update price based on override or markup
                    if price_override:
                        # Use the manually entered price
                        dest_item.price = new_price
                    elif markup > 0:
                        # Only update markup and price if explicitly requested or if it's a new item
                        dest_item.markup = markup
                        dest_item.price = new_price

                    # Update expiry date if the source item has a later expiry date
                    if item.expiry_date and (not hasattr(dest_item, 'exp_date') or not dest_item.exp_date or item.expiry_date > dest_item.exp_date):
                        dest_item.exp_date = item.expiry_date

                    dest_item.save()

                    # Deduct the transferred quantity from the store item.
                    # Convert qty to Decimal to avoid type mismatch with item.stock
                    item.stock -= Decimal(str(qty))
                    item.save()

                    # Remove the store item if its stock is zero or less.
                    if item.stock <= Decimal('0'):
                        item.delete()
                        price_info = f"Price manually set to {new_price:.2f}" if price_override else f"Price calculated as {new_price:.2f} ({markup}% markup)"
                        processed_items.append(
                            f"Transferred {qty} {item.unit} of {item.name} to {destination} as {dest_qty} {transfer_unit} and removed {item.name} from the store (stock reached zero). "
                            f"Item was {'created' if created else 'updated'} in {destination}. "
                            f"Cost adjusted from {original_cost:.2f} to {cost:.2f} per {transfer_unit}. {price_info}"
                        )
                    else:
                        price_info = f"Price manually set to {new_price:.2f}" if price_override else f"Price calculated as {new_price:.2f} ({markup}% markup)"
                        processed_items.append(
                            f"Transferred {qty} {item.unit} of {item.name} to {destination} as {dest_qty} {transfer_unit}. "
                            f"Item was {'created' if created else 'updated'} in {destination}. "
                            f"Cost adjusted from {original_cost:.2f} to {cost:.2f} per {transfer_unit}. {price_info}"
                        )

            # Use Django's messages framework to show errors/success messages.
            for error in errors:
                messages.error(request, error)
            for msg in processed_items:
                messages.success(request, msg)

            # Refresh the store items after processing.
            store_items = StoreItem.objects.all()

            # Get unit choices from the UNIT constant
            unit_choices = UNIT

            if request.headers.get('HX-request'):
                return render(request, "partials/_transfer_multiple_store_items.html", {
                    "store_items": store_items,
                    "unit_choices": unit_choices
                })
            else:
                return render(request, "store/transfer_multiple_store_items.html", {
                    "store_items": store_items,
                    "unit_choices": unit_choices
                })

        return JsonResponse({"success": False, "message": "Invalid request method."}, status=400)
    else:
        return redirect('store:index')



import logging
logger = logging.getLogger(__name__)

@user_passes_test(lambda u: u.is_superuser or (hasattr(u, 'profile') and u.profile and u.profile.user_type in ['Admin', 'Manager']))
@login_required
def create_stock_check(request):
    if request.user.is_authenticated:
        if request.method == "POST":
            # Get the zero_empty_items flag from the form
            zero_empty_items = request.POST.get('zero_empty_items', 'true').lower() == 'true'

            # Get selected items if any
            selected_items_str = request.POST.get('selected_items', '')

            if selected_items_str:
                # Filter items based on selection
                selected_item_ids = [int(id) for id in selected_items_str.split(',') if id]
                items = Item.objects.filter(id__in=selected_item_ids)
            else:
                # Get all items
                items = Item.objects.all()

            if not items.exists():
                messages.error(request, "No items found to check stock.")
                return redirect('store:store')

            stock_check = StockCheck.objects.create(created_by=request.user, status='in_progress')

            stock_check_items = []
            for item in items:
                # Skip items with zero stock if zero_empty_items is True
                if not zero_empty_items or item.stock > 0:
                    stock_check_items.append(
                        StockCheckItem(
                            stock_check=stock_check,
                            item=item,
                            expected_quantity=Decimal(str(item.stock)) if item.stock else Decimal('0'),
                            actual_quantity=Decimal('0'),
                            status='pending'
                        )
                    )

            StockCheckItem.objects.bulk_create(stock_check_items)

            messages.success(request, "Stock check created successfully.")
            return redirect('store:update_stock_check', stock_check.id)

        return render(request, 'store/create_stock_check.html')
    else:
        return redirect('store:index')


@login_required
def update_stock_check(request, stock_check_id):
    if request.user.is_authenticated:
        stock_check = get_object_or_404(StockCheck, id=stock_check_id)
        if stock_check.status not in ['in_progress', 'completed']:
            messages.error(request, "Stock check status is invalid for updates.")
            return redirect('store:store')

        if request.method == "POST":
            # Get the zero_empty_items flag from the form
            zero_empty_items = request.POST.get('zero_empty_items', 'false').lower() == 'true'

            stock_items = []
            for item_id, actual_qty in request.POST.items():
                if item_id.startswith("item_"):
                    item_id = int(item_id.replace("item_", ""))
                    stock_item = StockCheckItem.objects.get(stock_check=stock_check, item_id=item_id)

                    # Convert to Decimal for proper handling
                    try:
                        actual_qty_decimal = Decimal(str(actual_qty)) if actual_qty else Decimal('0')
                    except (ValueError, TypeError):
                        actual_qty_decimal = Decimal('0')

                    # If zero_empty_items is True and both expected and actual are 0, set to 0
                    if zero_empty_items and stock_item.expected_quantity == 0 and actual_qty_decimal == 0:
                        stock_item.actual_quantity = Decimal('0')
                    else:
                        stock_item.actual_quantity = actual_qty_decimal

                    stock_items.append(stock_item)

            StockCheckItem.objects.bulk_update(stock_items, ['actual_quantity'])
            messages.success(request, "Stock check updated successfully.")
            return redirect('store:stock_check_report', stock_check.id)

        return render(request, 'store/update_stock_check.html', {'stock_check': stock_check})
    else:
        return redirect('store:index')



@login_required
def update_stock_check(request, stock_check_id):
    if request.user.is_authenticated:
        stock_check = get_object_or_404(StockCheck, id=stock_check_id)

        # Check if user can edit completed stock checks
        can_edit_completed = request.user.is_superuser or (hasattr(request.user, 'profile') and request.user.profile and request.user.profile.user_type in ['Admin', 'Manager'])

        # If stock check is completed and user doesn't have permission, redirect to report
        if stock_check.status == 'completed' and not can_edit_completed:
            messages.info(request, "This stock check has been completed and cannot be modified.")
            return redirect('store:stock_check_report', stock_check.id)

        if request.method == "POST":
            stock_items = []
            for item_id, actual_qty in request.POST.items():
                if item_id.startswith("item_"):
                    item_id = int(item_id.replace("item_", ""))
                    stock_item = StockCheckItem.objects.get(stock_check=stock_check, item_id=item_id)

                    # Convert to Decimal for proper handling
                    try:
                        actual_qty_decimal = Decimal(str(actual_qty)) if actual_qty else Decimal('0')
                    except (ValueError, TypeError):
                        actual_qty_decimal = Decimal('0')

                    stock_item.actual_quantity = actual_qty_decimal
                    stock_items.append(stock_item)
            StockCheckItem.objects.bulk_update(stock_items, ['actual_quantity'])
            messages.success(request, "Stock check updated successfully.")
            return redirect('store:update_stock_check', stock_check.id)

        # Pass permission info to template
        context = {
            'stock_check': stock_check,
            'can_approve_adjust': can_edit_completed
        }
        return render(request, 'store/update_stock_check.html', context)
    else:
        return redirect('store:index')



@user_passes_test(lambda u: u.is_superuser or (hasattr(u, 'profile') and u.profile and u.profile.user_type in ['Admin', 'Manager']))
@login_required
def approve_stock_check(request, stock_check_id):
    if request.user.is_authenticated:
        stock_check = get_object_or_404(StockCheck, id=stock_check_id)
        if stock_check.status != 'in_progress':
            messages.error(request, "Stock check is not in progress.")
            return redirect('store:store')

        if request.method == "POST":
            selected_items = request.POST.getlist('item')
            if not selected_items:
                messages.error(request, "Please select at least one item to approve.")
                return redirect('store:update_stock_check', stock_check.id)

            stock_items = StockCheckItem.objects.filter(id__in=selected_items, stock_check=stock_check)
            stock_items.update(status='approved', approved_by=request.user, approved_at=datetime.now())

            if stock_items.count() == stock_check.stockcheckitem_set.count():
                stock_check.status = 'completed'
                stock_check.save()

            messages.success(request, f"{stock_items.count()} items approved successfully.")
            return redirect('store:update_stock_check', stock_check.id)

        return redirect('store:update_stock_check', stock_check.id)
    else:
        return redirect('store:index')

@user_passes_test(lambda u: u.is_superuser or (hasattr(u, 'profile') and u.profile and u.profile.user_type in ['Admin', 'Manager']))
@login_required
def bulk_adjust_stock(request, stock_check_id):
    if request.user.is_authenticated:
        stock_check = get_object_or_404(StockCheck, id=stock_check_id)
        if stock_check.status not in ['in_progress', 'completed']:
            messages.error(request, "Stock check status is invalid for adjustments.")
            return redirect('store:store')

        if request.method == "POST":
            selected_items = request.POST.getlist('item')
            if not selected_items:
                messages.error(request, "Please select at least one item to adjust.")
                return redirect('store:update_stock_check', stock_check.id)

            stock_items = StockCheckItem.objects.filter(id__in=selected_items, stock_check=stock_check)
            for item in stock_items:
                discrepancy = item.discrepancy()
                if discrepancy != 0:
                    item.item.stock += discrepancy
                    item.status = 'adjusted'
                    item.save()
                    Item.objects.filter(id=item.item.id).update(stock=item.item.stock)

            messages.success(request, f"Stock adjusted for {stock_items.count()} items.")
            return redirect('store:store')

        return redirect('store:update_stock_check', stock_check.id)
    else:
        return redirect('store:index')


@user_passes_test(lambda u: u.is_superuser or (hasattr(u, 'profile') and u.profile and u.profile.user_type in ['Admin', 'Manager']))
@login_required
def adjust_stock(request, stock_item_id):
    """Handle individual stock check item adjustments"""
    stock_item = get_object_or_404(StockCheckItem, id=stock_item_id)

    if request.method == 'POST':
        try:
            # Check if zero_item is checked
            zero_item = request.POST.get('zero_item', 'off') == 'on'

            if zero_item:
                # If zero_item is checked, set adjusted_quantity to 0
                adjusted_quantity = 0
            else:
                # Otherwise, get the adjusted_quantity from the form
                adjusted_quantity = int(request.POST.get('adjusted_quantity', 0))

            # Update the item's stock
            item = stock_item.item
            old_stock = item.stock

            # Calculate the adjustment needed
            adjustment = adjusted_quantity - stock_item.actual_quantity

            # Update the stock check item
            stock_item.actual_quantity = adjusted_quantity
            stock_item.status = 'adjusted'
            stock_item.save()

            # Update the item's stock
            item.stock += adjustment
            item.save()

            messages.success(
                request,
                f'Stock for {item.name} adjusted from {old_stock} to {item.stock}'
            )

            return redirect('store:stock_check_report', stock_item.stock_check.id)

        except ValueError:
            messages.error(request, 'Invalid quantity value provided')

    return render(request, 'store/adjust_stock.html', {'stock_item': stock_item})


@login_required
def stock_check_report(request, stock_check_id):
    stock_check = get_object_or_404(StockCheck, id=stock_check_id)
    total_cost_difference = 0

    # Loop through each stock check item and aggregate the cost difference.
    for item in stock_check.stockcheckitem_set.all():
        discrepancy = item.discrepancy()  # Actual - Expected
        # Assuming each item has a 'price' attribute.
        unit_price = getattr(item.item, 'price', 0)
        cost_difference = discrepancy * unit_price
        total_cost_difference += cost_difference

    context = {
        'stock_check': stock_check,
        'total_cost_difference': total_cost_difference,
    }
    return render(request, 'store/stock_check_report.html', context)


@login_required
def list_stock_checks(request):
    # Get all StockCheck objects ordered by date (newest first)
    stock_checks = StockCheck.objects.all().order_by('-date')

    # Check if user can delete stock check reports
    from userauth.permissions import can_delete_stock_check_reports
    can_delete_reports = can_delete_stock_check_reports(request.user)

    context = {
        'stock_checks': stock_checks,
        'can_delete_reports': can_delete_reports,
    }
    return render(request, 'store/stock_check_list.html', context)

@login_required
@require_POST
def delete_stock_check(request, stock_check_id):
    """Delete a stock check report"""
    if request.user.is_authenticated:
        from userauth.permissions import can_delete_stock_check_reports
        if not can_delete_stock_check_reports(request.user):
            messages.error(request, 'You do not have permission to delete stock check reports.')
            return redirect('store:list_stock_checks')

        stock_check = get_object_or_404(StockCheck, id=stock_check_id)

        # Check if stock check can be deleted (only pending or in_progress)
        if stock_check.status == 'completed':
            messages.error(request, 'Cannot delete completed stock check reports.')
            return redirect('store:list_stock_checks')

        stock_check_id_display = stock_check.id
        stock_check.delete()
        messages.success(request, f'Stock check report #{stock_check_id_display} deleted successfully.')
        return redirect('store:list_stock_checks')
    else:
        return redirect('store:index')




import logging
logger = logging.getLogger(__name__)

@login_required
def create_transfer_request_wholesale(request):
    if request.user.is_authenticated:
        if request.method == "GET":
            try:
                # Get search query
                search_query = request.GET.get('search', '').strip()
                logger.info(f"Search query received: '{search_query}'")
                
                # Filter retail items based on search
                if search_query:
                    retail_items = Item.objects.filter(
                        Q(name__icontains=search_query) | 
                        Q(brand__icontains=search_query) |
                        Q(dosage_form__icontains=search_query)
                    ).order_by('name')
                    logger.info(f"Found {retail_items.count()} retail items matching search: '{search_query}'")
                else:
                    retail_items = Item.objects.all().order_by('name')
                    logger.info(f"Rendering wholesale transfer form with {retail_items.count()} retail items")
                
                context = {
                    "retail_items": retail_items,
                    "search_query": search_query
                }
                
                logger.info(f"Rendering template with context: {context}")
                return render(request, "wholesale/wholesale_transfer_request.html", context)
                
            except Exception as e:
                logger.error(f"Error in create_transfer_request_wholesale (GET): {str(e)}")
                logger.error(f"Exception type: {type(e).__name__}")
                import traceback
                logger.error(f"Traceback: {traceback.format_exc()}")
                
                # Fallback to showing all items without search
                retail_items = Item.objects.all().order_by('name')
                return render(request, "wholesale/wholesale_transfer_request.html", {
                    "retail_items": retail_items,
                    "search_query": "",
                    "error_message": f"Search functionality temporarily unavailable: {str(e)}"
                })

        elif request.method == "POST":
            logger.info(f"POST request received for transfer creation: {request.POST}")
            try:
                from decimal import Decimal
                requested_quantity = Decimal(request.POST.get("requested_quantity", 0))
                item_id = request.POST.get("item_id")
                from_wholesale = request.POST.get("from_wholesale", "false").lower() == "true"

                if not item_id or requested_quantity <= 0:
                    return JsonResponse({"success": False, "message": "Invalid input provided."}, status=400)

                # Get the source item based on transfer direction
                if from_wholesale:
                    # Wholesale requesting from Retail (Retail â†’ Wholesale transfer)
                    source_item = get_object_or_404(Item, id=item_id)
                    if source_item.stock < requested_quantity:
                        return JsonResponse({"success": False, "message": f"Insufficient stock. Available: {source_item.stock}"}, status=400)

                    transfer = TransferRequest.objects.create(
                        retail_item=source_item,
                        requested_quantity=requested_quantity,
                        from_wholesale=True,
                        status="pending",
                        created_at=timezone.now()
                    )
                    logger.info(f"Created transfer request: Retailâ†’Wholesale ({source_item.name} x{requested_quantity})")
                else:
                    # Retail requesting from Wholesale (Wholesale â†’ Retail transfer)
                    source_item = get_object_or_404(WholesaleItem, id=item_id)
                    if source_item.stock < requested_quantity:
                        return JsonResponse({"success": False, "message": f"Insufficient stock. Available: {source_item.stock}"}, status=400)

                    transfer = TransferRequest.objects.create(
                        wholesale_item=source_item,
                        requested_quantity=requested_quantity,
                        from_wholesale=False,
                        status="pending",
                        created_at=timezone.now()
                    )
                    logger.info(f"Created transfer request: Wholesaleâ†’Retail ({source_item.name} x{requested_quantity})")

                return JsonResponse({"success": True, "message": "Transfer request created successfully."})

            except (TypeError, ValueError) as e:
                logger.error(f"Validation error in create_transfer_request_wholesale: {str(e)}")
                if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                    return JsonResponse({"success": False, "message": str(e)}, status=400)
                else:
                    messages.error(request, str(e))
                    return redirect('store:create_transfer_request_wholesale')
            except Exception as e:
                logger.error(f"Error in create_transfer_request_wholesale: {str(e)}")
                if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                    return JsonResponse({"success": False, "message": "An error occurred."}, status=500)
                else:
                    messages.error(request, "An error occurred while creating the transfer request.")
                    return redirect('store:create_transfer_request_wholesale')

    return redirect('store:index')




@login_required
def pending_transfer_requests(request):
    if request.user.is_authenticated:
        # For a wholesale-initiated request, the retail_item field is set.
        pending_transfers = TransferRequest.objects.filter(status="pending", from_wholesale=True)
        return render(request, "store/pending_transfer_requests.html", {"pending_transfers": pending_transfers})
    else:
        return redirect('store:index')


@login_required
def approve_transfer(request, transfer_id):
    if request.user.is_authenticated:
        if request.method == "POST":
            try:
                transfer = get_object_or_404(TransferRequest, id=transfer_id)

                # Determine approved quantity
                approved_qty_param = request.POST.get("approved_quantity")
                try:
                    from decimal import Decimal
                    approved_qty = Decimal(approved_qty_param) if approved_qty_param else transfer.requested_quantity
                    if approved_qty <= 0:
                        return JsonResponse({
                            "success": False,
                            "message": "Quantity must be greater than zero."
                        }, status=400)
                except (ValueError, TypeError):
                    return JsonResponse({
                        "success": False,
                        "message": "Invalid quantity value."
                    }, status=400)

                if transfer.from_wholesale:
                    source_item = transfer.retail_item
                    # Check if source has enough stock
                    if source_item.stock < approved_qty:
                        return JsonResponse({
                            "success": False,
                            "message": f"Insufficient stock. Available: {source_item.stock}, Requested: {approved_qty}"
                        }, status=400)

                    # Create or get destination wholesale item
                    destination_item, created = WholesaleItem.objects.get_or_create(
                        name=source_item.name,
                        brand=source_item.brand,
                        unit=source_item.unit,
                        defaults={
                            "dosage_form": source_item.dosage_form,
                            "cost": source_item.cost,
                            "price": source_item.price,
                            "markup": source_item.markup,
                            "stock": 0,
                            "exp_date": source_item.exp_date,
                        }
                    )

                    # Use transaction to ensure atomicity
                    with transaction.atomic():
                        # Deduct from source
                        source_item.stock = F('stock') - approved_qty
                        source_item.save()
                        source_item.refresh_from_db()

                        # Add to destination
                        destination_item.stock = F('stock') + approved_qty
                        destination_item.cost = source_item.cost
                        destination_item.exp_date = source_item.exp_date
                        destination_item.markup = source_item.markup
                        destination_item.price = source_item.price
                        destination_item.save()
                        destination_item.refresh_from_db()

                        # Update transfer request
                        transfer.status = "approved"
                        transfer.approved_quantity = approved_qty
                        transfer.save()

                    # Return JSON response for AJAX requests
                    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                        return JsonResponse({
                            "success": True,
                            "message": f"Transfer approved with quantity {approved_qty}.",
                            "source_stock": str(source_item.stock),
                            "destination_stock": str(destination_item.stock),
                        })
                    else:
                        messages.success(
                            request,
                            f"Transfer approved: {approved_qty} {source_item.name} moved from retail to wholesale."
                        )
                        return redirect('store:pending_transfer_requests')

            except Exception as e:
                logger.error(f"Error in approve_transfer: {str(e)}")
                import traceback
                logger.error(f"Traceback: {traceback.format_exc()}")

                if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                    return JsonResponse({
                        "success": False,
                        "message": f"An error occurred while processing the transfer: {str(e)}"
                    }, status=500)
                else:
                    messages.error(request, f"An error occurred while processing the transfer: {str(e)}")
                    return redirect('store:pending_transfer_requests')

        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({
                "success": False,
                "message": "Invalid request method."
            }, status=400)
        else:
            messages.error(request, "Invalid request method.")
            return redirect('store:pending_transfer_requests')

    return redirect('store:index')



@login_required
def reject_transfer(request, transfer_id):
    if request.user.is_authenticated:
        """
        Rejects a transfer request.
        """
        if request.method == "POST":
            try:
                transfer = get_object_or_404(TransferRequest, id=transfer_id)
                transfer.status = "rejected"
                transfer.save()

                if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                    return JsonResponse({"success": True, "message": "Transfer request rejected successfully."})
                else:
                    messages.error(request, "Transfer request rejected.")
                    return redirect('store:pending_transfer_requests')
            except Exception as e:
                logger.error(f"Error rejecting transfer {transfer_id}: {str(e)}")
                if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                    return JsonResponse({"success": False, "message": str(e)}, status=400)
                else:
                    messages.error(request, f"Error rejecting transfer: {str(e)}")
                    return redirect('store:pending_transfer_requests')

        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({"success": False, "message": "Invalid request method!"}, status=400)
        else:
            messages.error(request, "Invalid request method!")
            return redirect('store:pending_transfer_requests')
    else:
        return redirect('store:index')


@login_required
def transfer_request_list(request):
    if request.user.is_authenticated:
        """
        Display all transfer requests and transfers.
        Optionally filter by a specific date (YYYY-MM-DD).
        """
        from utils.date_utils import filter_queryset_by_date, get_date_filter_context

        # Get the date filter from GET parameters.
        date_context = get_date_filter_context(request, 'date')
        date_str = date_context['date_string']
        transfers = TransferRequest.objects.all().order_by("-created_at")

        if date_str and date_context['is_valid_date']:
            transfers = filter_queryset_by_date(transfers, 'created_at', date_str)
        elif date_str and not date_context['is_valid_date']:
            logger.warning("Invalid date format provided: %s", date_str)

        context = {
            "transfers": transfers,
            "search_date": date_str or ""
        }
        return render(request, "store/transfer_request_list.html", context)
    else:
        return redirect('store:index')

# EXPENSES TRACKING LOGIC
@user_passes_test(is_admin)
@login_required
def generate_monthly_report(request):
    # Get selected month from request, default to current month
    selected_month_str = request.GET.get('month')

    if selected_month_str:
        try:
            selected_date = datetime.strptime(selected_month_str, '%Y-%m')
        except ValueError:
            selected_date = datetime.now()
    else:
        selected_date = datetime.now()

    # Filter expenses for the selected month
    expenses = Expense.objects.filter(
        date__month=selected_date.month,
        date__year=selected_date.year
    ).order_by('-date')

    total_expenses = expenses.aggregate(Sum('amount'))['amount__sum'] or 0

    # Group expenses by category
    expenses_by_category = defaultdict(Decimal)
    for expense in expenses:
        expenses_by_category[expense.category.name] += expense.amount

    context = {
        'expenses': expenses,
        'total_expenses': total_expenses,
        'expenses_by_category': dict(expenses_by_category),
        'month': selected_date.strftime('%B %Y'),
        'selected_month': selected_month_str or selected_date.strftime('%Y-%m')
    }

    return render(request, 'store/expense_report.html', context)


@login_required
def expense_list(request):
    if request.user.is_authenticated:
        from userauth.permissions import can_manage_expenses, can_add_expenses, can_add_expense_categories, can_manage_expense_categories

        # Allow all authenticated users to view expenses
        expenses = Expense.objects.all().order_by('-date')
        expense_categories = ExpenseCategory.objects.all().order_by('name')

        # Pass permission info to template
        context = {
            'expenses': expenses,
            'expense_categories': expense_categories,
            'can_manage_expenses': can_manage_expenses(request.user),
            'can_add_expenses': can_add_expenses(request.user),
            'can_add_expense_categories': can_add_expense_categories(request.user),
            'can_manage_expense_categories': can_manage_expense_categories(request.user)
        }
        return render(request, 'store/expense_list.html', context)
    else:
        return redirect('store:index')


@login_required
def add_expense_form(request):
    if request.user.is_authenticated:
        from userauth.permissions import can_add_expenses
        if not can_add_expenses(request.user):
            messages.error(request, 'You do not have permission to add expenses.')
            return redirect('store:index')
        """Return the modal form for adding expenses."""
        form = ExpenseForm()
        return render(request, 'partials/_expense_form.html', {'form': form})
    else:
        return redirect('store:index')


@login_required
def add_expense(request):
    if request.user.is_authenticated:
        from userauth.permissions import can_add_expenses, can_manage_expenses
        if not can_add_expenses(request.user):
            messages.error(request, 'You do not have permission to add expenses.')
            return redirect('store:index')
        """Handle expense form submission."""
        if request.method == 'POST':
            form = ExpenseForm(request.POST)
            if form.is_valid():
                form.save()
                expenses = Expense.objects.all().order_by('-date')
                context = {
                    'expenses': expenses,
                    'can_manage_expenses': can_manage_expenses(request.user)
                }
                return render(request, 'partials/_expense_list.html', context)
        else:
            form = ExpenseForm()

        return render(request, 'partials/_expense_form.html', {'form': form})
    else:
        return redirect('store:index')

@login_required
def edit_expense_form(request, expense_id):
    if request.user.is_authenticated:
        from userauth.permissions import can_manage_expenses
        if not can_manage_expenses(request.user):
            messages.error(request, 'You do not have permission to edit expenses.')
            return redirect('store:index')
        """Return the modal form for editing an expense."""
        expense = get_object_or_404(Expense, id=expense_id)
        form = ExpenseForm(instance=expense)
        return render(request, 'partials/_expense_form.html', {'form': form, 'expense_id': expense.id})
    else:
        return redirect('store:index')

@login_required
@require_POST
def update_expense(request, expense_id):
    if request.user.is_authenticated:
        from userauth.permissions import can_manage_expenses
        if not can_manage_expenses(request.user):
            messages.error(request, 'You do not have permission to update expenses.')
            return redirect('store:index')
        """Handle updating an expense."""
        expense = get_object_or_404(Expense, id=expense_id)
        form = ExpenseForm(request.POST, instance=expense)
        if form.is_valid():
            form.save()
            expenses = Expense.objects.all().order_by('-date')  # Refresh list
            context = {
                'expenses': expenses,
                'can_manage_expenses': can_manage_expenses(request.user)
            }
            return render(request, 'partials/_expense_list.html', context)
        return JsonResponse({'error': form.errors}, status=400)
    else:
        return redirect('store:index')

@user_passes_test(lambda u: u.is_superuser)
@login_required
def adjust_stock_levels(request):
    """View for the main stock adjustment page"""
    items = Item.objects.all().order_by('name')
    return render(request, 'store/adjust_stock_level.html', {'items': items})

@user_passes_test(lambda u: u.is_superuser)
@login_required
def search_for_adjustment(request):
    """Handle search requests for stock adjustment"""
    query = request.GET.get('q', '')
    if query:
        items = Item.objects.filter(
            Q(name__icontains=query) |
            Q(brand__icontains=query) |
            Q(dosage_form__icontains=query)
        ).order_by('name')
    else:
        items = Item.objects.all().order_by('name')

    # Check if this is an HTMX request (for embedded search)
    if request.headers.get('HX-Request'):
        return render(request, 'store/search_for_adjustment.html', {'items': items})
    else:
        # Regular page request - redirect to adjust stock levels page
        return redirect(f"{reverse('store:adjust_stock_levels')}?q={query}" if query else reverse('store:adjust_stock_levels'))


@login_required
def search_items(request):
    """API endpoint for searching items for stock check"""
    query = request.GET.get('q', '').strip()
    if query and len(query) >= 2:  # Only search for meaningful queries
        # Optimized search with prefix matching first, then partial matching
        items = Item.objects.filter(
            Q(name__istartswith=query) |
            Q(brand__istartswith=query) |
            Q(dosage_form__istartswith=query) |
            Q(name__icontains=query) |
            Q(brand__icontains=query) |
            Q(dosage_form__icontains=query)
        ).distinct().order_by('name')[:30]  # Increased limit but still reasonable
    else:
        items = Item.objects.all().order_by('name')[:30]  # Increased limit for better UX

    # Check if this is an HTMX request
    if request.headers.get('HX-Request'):
        # Log for debugging
        print(f"HTMX request received for search_items with query: {query}")
        print(f"Found {len(items)} items matching the query")
        # Return the search results template
        return render(request, 'partials/search_items_results.html', {'items': items})
    else:
        # Return JSON response for other cases (like stock check)
        items_data = [{
            'id': item.id,
            'name': item.name,
            'brand': item.brand,
            'dosage_form': item.dosage_form,
            'unit': item.unit,
            'stock': item.stock
        } for item in items]
        return JsonResponse({'items': items_data})

@user_passes_test(lambda u: u.is_superuser)
@login_required
def adjust_stock_level(request, item_id):
    """Handle individual item stock adjustments"""
    if request.method == 'POST':
        item = get_object_or_404(Item, id=item_id)
        try:
            new_stock = int(request.POST.get(f'new-stock-{item_id}', 0))
            old_stock = item.stock

            # Log the stock adjustment (without using the new model fields yet)
            logger.info(f"Manual stock adjustment for {item.name} (ID: {item.id}) by {request.user.username}: {old_stock} -> {new_stock}")

            # Update the item stock
            item.stock = new_stock
            item.save()

            messages.success(
                request,
                f'Stock for {item.name} updated from {old_stock} to {new_stock}'
            )

            return render(request, 'store/search_for_adjustment.html', {'items': [item]})

        except ValueError:
            messages.error(request, 'Invalid stock value provided')
            return HttpResponse(status=400)

    return HttpResponse(status=405)  # Method not allowed

@login_required
@require_POST
def delete_expense(request, expense_id):
    if request.user.is_authenticated:
        from userauth.permissions import can_manage_expenses
        if not can_manage_expenses(request.user):
            messages.error(request, 'You do not have permission to delete expenses.')
            return redirect('store:index')
        """Handle deleting an expense."""
        expense = get_object_or_404(Expense, id=expense_id)
        expense.delete()
        expenses = Expense.objects.all().order_by('-date')  # Refresh list
        context = {
            'expenses': expenses,
            'can_manage_expenses': can_manage_expenses(request.user)
        }
        return render(request, 'partials/_expense_list.html', context)
    else:
        return redirect('store:index')




@login_required
def add_expense_category_form(request):
    from userauth.permissions import can_add_expense_categories
    if not can_add_expense_categories(request.user):
        messages.error(request, 'You do not have permission to add expense categories.')
        return redirect('store:index')
    """Return the modal form for adding an expense category."""
    form = ExpenseCategoryForm()
    return render(request, 'partials/_expense_category_form.html', {'form': form})

@login_required
def add_expense_category(request):
    from userauth.permissions import can_add_expense_categories, can_manage_expense_categories
    if not can_add_expense_categories(request.user):
        messages.error(request, 'You do not have permission to add expense categories.')
        return redirect('store:index')
    """Handle expense category form submission."""
    if request.method == 'POST':
        form = ExpenseCategoryForm(request.POST)
        if form.is_valid():
            form.save()
            # Get all categories to update the list on the page
            categories = ExpenseCategory.objects.all().order_by('name')
            context = {
                'categories': categories,
                'can_manage_expense_categories': can_manage_expense_categories(request.user)
            }
            return render(request, 'partials/_expense_category_list.html', context)
        else:
            return render(request, 'partials/_expense_category_form.html', {'form': form})
    else:
        form = ExpenseCategoryForm()
    return render(request, 'partials/_expense_category_form.html', {'form': form})

@login_required
def edit_expense_category_form(request, category_id):
    from userauth.permissions import can_manage_expense_categories
    if not can_manage_expense_categories(request.user):
        messages.error(request, 'You do not have permission to edit expense categories.')
        return redirect('store:index')
    """Return the modal form for editing an expense category."""
    category = get_object_or_404(ExpenseCategory, id=category_id)
    form = ExpenseCategoryForm(instance=category)
    return render(request, 'partials/_expense_category_form.html', {'form': form, 'category_id': category.id})

@login_required
@require_POST
def update_expense_category(request, category_id):
    from userauth.permissions import can_manage_expense_categories
    if not can_manage_expense_categories(request.user):
        messages.error(request, 'You do not have permission to update expense categories.')
        return redirect('store:index')
    """Handle updating an expense category."""
    category = get_object_or_404(ExpenseCategory, id=category_id)
    form = ExpenseCategoryForm(request.POST, instance=category)
    if form.is_valid():
        form.save()
        categories = ExpenseCategory.objects.all().order_by('name')  # Refresh list
        context = {
            'categories': categories,
            'can_manage_expense_categories': can_manage_expense_categories(request.user)
        }
        return render(request, 'partials/_expense_category_list.html', context)
    return JsonResponse({'error': form.errors}, status=400)

@login_required
@require_POST
def delete_expense_category(request, category_id):
    from userauth.permissions import can_manage_expense_categories
    if not can_manage_expense_categories(request.user):
        messages.error(request, 'You do not have permission to delete expense categories.')
        return redirect('store:index')
    """Handle deleting an expense category."""
    category = get_object_or_404(ExpenseCategory, id=category_id)

    # Check if category is being used by any expenses
    if category.expense_set.exists():
        return JsonResponse({'error': 'Cannot delete category that is being used by expenses.'}, status=400)

    category.delete()
    categories = ExpenseCategory.objects.all().order_by('name')  # Refresh list
    context = {
        'categories': categories,
        'can_manage_expense_categories': can_manage_expense_categories(request.user)
    }
    return render(request, 'partials/_expense_category_list.html', context)

@require_http_methods(["POST"])
@user_passes_test(lambda u: u.is_superuser)
def update_marquee(request):
    marquee_text = request.POST.get('marquee_text')
    if marquee_text:
        # Store the marquee text in cache
        cache.set('marquee_text', marquee_text, timeout=None)
        return HttpResponse(status=200)
    return HttpResponse(status=400)


@login_required
def complete_customer_history(request, customer_id):
    if request.user.is_authenticated:
        customer = get_object_or_404(Customer, id=customer_id)

        # Get all selection history (includes both purchases and returns)
        selection_history = ItemSelectionHistory.objects.filter(
            customer=customer
        ).select_related(
            'item', 'user'
        ).order_by('-date')  # Changed from -created_at to -date

        # Combine and process all history
        history_data = {}

        # Process selection history
        for entry in selection_history:
            year = entry.date.year  # Changed from created_at to date
            month = entry.date.strftime('%B')

            if year not in history_data:
                history_data[year] = {'total': Decimal('0'), 'months': {}}

            if month not in history_data[year]['months']:
                history_data[year]['months'][month] = {'total': Decimal('0'), 'items': []}

            subtotal = entry.quantity * entry.unit_price

            # Update totals (subtract for returns, add for purchases)
            if entry.action == 'return':
                history_data[year]['total'] -= subtotal
                history_data[year]['months'][month]['total'] -= subtotal
            else:
                history_data[year]['total'] += subtotal
                history_data[year]['months'][month]['total'] += subtotal

            history_data[year]['months'][month]['items'].append({
                'date': entry.date,  # Changed from created_at to date
                'item': entry.item,
                'quantity': entry.quantity,
                'price': entry.unit_price,
                'subtotal': subtotal,
                'action': entry.action,
                'user': entry.user
            })

        context = {
            'customer': customer,
            'history_data': history_data,
        }

        return render(request, 'store/complete_customer_history.html', context)
    return redirect('store:index')


@login_required
def wallet_transaction_history(request, customer_id):
    """View for displaying wallet transaction history for retail customers"""
    if request.user.is_authenticated:
        customer = get_object_or_404(Customer, id=customer_id)

        # Get all transactions for this customer
        transactions = TransactionHistory.objects.filter(
            customer=customer
        ).order_by('-date')

        # Apply filters if provided
        transaction_type = request.GET.get('transaction_type')
        date_from = request.GET.get('date_from')
        date_to = request.GET.get('date_to')

        if transaction_type:
            transactions = transactions.filter(transaction_type=transaction_type)

        if date_from:
            try:
                date_from_parsed = parse_date(date_from)
                if date_from_parsed:
                    transactions = transactions.filter(date__gte=date_from_parsed)
            except ValueError:
                pass

        if date_to:
            try:
                date_to_parsed = parse_date(date_to)
                if date_to_parsed:
                    transactions = transactions.filter(date__lte=date_to_parsed)
            except ValueError:
                pass

        # Get wallet balance
        wallet_balance = Decimal('0.0')
        try:
            wallet_balance = customer.wallet.balance
        except Wallet.DoesNotExist:
            pass

        # Calculate totals by transaction type
        totals = {
            'deposit': transactions.filter(transaction_type='deposit').aggregate(
                total=Sum('amount'))['total'] or Decimal('0.0'),
            'purchase': transactions.filter(transaction_type='purchase').aggregate(
                total=Sum('amount'))['total'] or Decimal('0.0'),
            'debit': transactions.filter(transaction_type='debit').aggregate(
                total=Sum('amount'))['total'] or Decimal('0.0'),
            'refund': transactions.filter(transaction_type='refund').aggregate(
                total=Sum('amount'))['total'] or Decimal('0.0'),
        }

        context = {
            'customer': customer,
            'transactions': transactions,
            'wallet_balance': wallet_balance,
            'totals': totals,
            'transaction_types': TransactionHistory.TRANSACTION_TYPES,
            'filters': {
                'transaction_type': transaction_type,
                'date_from': date_from,
                'date_to': date_to,
            }
        }

        return render(request, 'store/wallet_transaction_history.html', context)
    else:
        return redirect('store:index')


@login_required
def wholesale_wallet_transaction_history(request, customer_id):
    """View for displaying wallet transaction history for wholesale customers"""
    if request.user.is_authenticated:
        customer = get_object_or_404(WholesaleCustomer, id=customer_id)

        # Get all transactions for this wholesale customer
        transactions = TransactionHistory.objects.filter(
            wholesale_customer=customer
        ).order_by('-date')

        # Apply filters if provided
        transaction_type = request.GET.get('transaction_type')
        date_from = request.GET.get('date_from')
        date_to = request.GET.get('date_to')

        if transaction_type:
            transactions = transactions.filter(transaction_type=transaction_type)

        if date_from:
            try:
                date_from_parsed = parse_date(date_from)
                if date_from_parsed:
                    transactions = transactions.filter(date__gte=date_from_parsed)
            except ValueError:
                pass

        if date_to:
            try:
                date_to_parsed = parse_date(date_to)
                if date_to_parsed:
                    transactions = transactions.filter(date__lte=date_to_parsed)
            except ValueError:
                pass

        # Get wallet balance
        wallet_balance = Decimal('0.0')
        try:
            wallet_balance = customer.wholesale_customer_wallet.balance
        except WholesaleCustomerWallet.DoesNotExist:
            pass

        # Calculate totals by transaction type
        totals = {
            'deposit': transactions.filter(transaction_type='deposit').aggregate(
                total=Sum('amount'))['total'] or Decimal('0.0'),
            'purchase': transactions.filter(transaction_type='purchase').aggregate(
                total=Sum('amount'))['total'] or Decimal('0.0'),
            'debit': transactions.filter(transaction_type='debit').aggregate(
                total=Sum('amount'))['total'] or Decimal('0.0'),
            'refund': transactions.filter(transaction_type='refund').aggregate(
                total=Sum('amount'))['total'] or Decimal('0.0'),
        }

        context = {
            'customer': customer,
            'transactions': transactions,
            'wallet_balance': wallet_balance,
            'totals': totals,
            'transaction_types': TransactionHistory.TRANSACTION_TYPES,
            'filters': {
                'transaction_type': transaction_type,
                'date_from': date_from,
                'date_to': date_to,
            }
        }

        return render(request, 'wholesale/wallet_transaction_history.html', context)
    else:
        return redirect('store:index')


@login_required
def user_dispensing_summary(request):
    """View for displaying dispensing summary by user"""
    if request.user.is_authenticated:
        # Get date filters
        date_from = request.GET.get('date_from')
        date_to = request.GET.get('date_to')
        user_filter = request.GET.get('user_id')

        # Permission check: Superusers, Admins, and Managers can see all users, others can see all logs but with limited filtering
        can_view_all_users = can_view_all_users_dispensing(request.user)

        # Start with all dispensing logs - all users can see all data
        logs = DispensingLog.objects.all()

        # For regular users, they can't filter by specific users (user_filter is ignored for them)

        # Apply filters using date utilities
        from utils.date_utils import filter_queryset_by_date_range
        logs = filter_queryset_by_date_range(logs, 'created_at', date_from, date_to)

        if user_filter:
            logs = logs.filter(user_id=user_filter)

        # Group by user and calculate summaries
        from django.contrib.auth import get_user_model
        User = get_user_model()

        user_summaries = []
        users = User.objects.filter(dispensinglog__in=logs).distinct()

        for user in users:
            user_logs = logs.filter(user=user)

            dispensed_logs = user_logs.filter(status='Dispensed')
            returned_logs = user_logs.filter(status__in=['Returned', 'Partially Returned'])

            dispensed_count = dispensed_logs.count()
            dispensed_amount = dispensed_logs.aggregate(total=Sum('amount'))['total'] or Decimal('0.0')
            dispensed_quantity = dispensed_logs.aggregate(total=Sum('quantity'))['total'] or Decimal('0.0')

            returned_count = returned_logs.count()
            returned_amount = returned_logs.aggregate(total=Sum('amount'))['total'] or Decimal('0.0')
            returned_quantity = returned_logs.aggregate(total=Sum('quantity'))['total'] or Decimal('0.0')

            net_amount = dispensed_amount - returned_amount
            net_quantity = dispensed_quantity - returned_quantity

            user_summaries.append({
                'user': user,
                'dispensed_count': dispensed_count,
                'dispensed_amount': dispensed_amount,
                'dispensed_quantity': dispensed_quantity,
                'returned_count': returned_count,
                'returned_amount': returned_amount,
                'returned_quantity': returned_quantity,
                'net_amount': net_amount,
                'net_quantity': net_quantity,
            })

        # Sort by net amount descending
        user_summaries.sort(key=lambda x: x['net_amount'], reverse=True)

        # Get users for filter dropdown based on permissions
        if can_view_all_users:
            all_users = User.objects.filter(dispensinglog__isnull=False).distinct()
        else:
            # Regular users only see themselves in the dropdown
            all_users = User.objects.filter(id=request.user.id)

        context = {
            'user_summaries': user_summaries,
            'all_users': all_users,
            'can_view_all_users': can_view_all_users,
            'filters': {
                'date_from': date_from,
                'date_to': date_to,
                'user_id': user_filter,
            }
        }

        return render(request, 'store/user_dispensing_summary.html', context)
    else:
        return redirect('store:index')


@login_required
def user_dispensing_details(request, user_id=None):
    """View for displaying detailed dispensing breakdown by user"""
    if request.user.is_authenticated:
        # Get filters
        date_from = request.GET.get('date_from')
        date_to = request.GET.get('date_to')
        status_filter = request.GET.get('status')

        # Permission check: Superusers, Admins, and Managers can see all users, others can see all logs but with limited filtering
        can_view_all_users = can_view_all_users_dispensing(request.user)

        # Get the specific user if user_id is provided
        target_user = None
        if user_id:
            try:
                target_user = User.objects.get(id=user_id)
                # Check if user has permission to view this user's data
                if not can_view_all_users and target_user != request.user:
                    messages.error(request, 'You can only view your own dispensing details.')
                    return redirect('store:user_dispensing_details')
            except User.DoesNotExist:
                messages.error(request, 'User not found.')
                return redirect('store:user_dispensing_summary')
        elif not can_view_all_users:
            # If regular user doesn't specify user_id, show their own data
            target_user = request.user

        # Start with all dispensing logs - all users can see all data
        logs = DispensingLog.objects.select_related('user').all()

        # Filter by user if specified
        if target_user:
            logs = logs.filter(user=target_user)

        # Apply date filters using date utilities
        from utils.date_utils import filter_queryset_by_date_range
        logs = filter_queryset_by_date_range(logs, 'created_at', date_from, date_to)

        # Apply status filter
        if status_filter:
            logs = logs.filter(status=status_filter)

        # Order by most recent first
        logs = logs.order_by('-created_at')

        # Pagination
        from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
        paginator = Paginator(logs, 50)  # 50 records per page
        page = request.GET.get('page', 1)

        try:
            logs_page = paginator.page(page)
        except PageNotAnInteger:
            logs_page = paginator.page(1)
        except EmptyPage:
            logs_page = paginator.page(paginator.num_pages)

        # Get users for filter dropdown based on permissions
        if can_view_all_users:
            all_users = User.objects.filter(dispensinglog__isnull=False).distinct()
        else:
            # Regular users can see all users but can't filter by them (dropdown is disabled)
            all_users = User.objects.filter(dispensinglog__isnull=False).distinct()

        # Get status choices for filter
        status_choices = [
            ('Dispensed', 'Dispensed'),
            ('Returned', 'Returned'),
            ('Partially Returned', 'Partially Returned'),
        ]

        context = {
            'logs': logs_page,
            'target_user': target_user,
            'all_users': all_users,
            'can_view_all_users': can_view_all_users,
            'status_choices': status_choices,
            'filters': {
                'date_from': date_from,
                'date_to': date_to,
                'status': status_filter,
                'user_id': user_id,
            }
        }

        return render(request, 'store/user_dispensing_details.html', context)
    else:
        return redirect('store:index')


@login_required
def my_dispensing_details(request):
    """View for users to see their own dispensing details"""
    # Redirect to user_dispensing_details with current user's ID
    return user_dispensing_details(request, user_id=request.user.id)


@login_required
def add_items_to_stock_check(request, stock_check_id):
    """Add more items to an existing stock check"""
    if request.user.is_authenticated:
        stock_check = get_object_or_404(StockCheck, id=stock_check_id)

        # Only allow adding items to in-progress stock checks
        if stock_check.status != 'in_progress':
            messages.error(request, 'Cannot add items to a completed stock check.')
            return redirect('store:update_stock_check', stock_check.id)

        # Get items that are not already in this stock check
        existing_item_ids = stock_check.stockcheckitem_set.values_list('item_id', flat=True)
        available_items = Item.objects.exclude(id__in=existing_item_ids).order_by('name')

        if request.method == 'POST':
            selected_item_ids = request.POST.getlist('selected_items')
            zero_empty_items = request.POST.get('zero_empty_items', 'true').lower() == 'true'

            if not selected_item_ids:
                messages.error(request, 'Please select at least one item to add.')
                return redirect('store:add_items_to_stock_check', stock_check.id)

            # Create stock check items for selected items
            stock_check_items = []
            added_count = 0

            for item_id in selected_item_ids:
                try:
                    item = Item.objects.get(id=item_id)

                    # Skip items with zero stock if zero_empty_items is True
                    if not zero_empty_items or item.stock > 0:
                        stock_check_items.append(
                            StockCheckItem(
                                stock_check=stock_check,
                                item=item,
                                expected_quantity=item.stock,
                                actual_quantity=0,
                                status='pending'
                            )
                        )
                        added_count += 1
                except Item.DoesNotExist:
                    continue

            if stock_check_items:
                StockCheckItem.objects.bulk_create(stock_check_items)
                messages.success(request, f'{added_count} items added to stock check successfully.')
            else:
                messages.warning(request, 'No items were added. Items may have zero stock or already exist in the stock check.')

            return redirect('store:update_stock_check', stock_check.id)

        context = {
            'stock_check': stock_check,
            'available_items': available_items,
        }

        return render(request, 'store/add_items_to_stock_check.html', context)
    else:
        return redirect('store:index')


# Notification Views
@login_required
def notification_list(request):
    """Display all notifications for the current user"""
    if request.user.is_authenticated:
        from .notifications import NotificationService
        from .models import Notification
        from django.db import models

        # Get notifications for this user and system-wide notifications
        notifications = Notification.objects.filter(
            is_dismissed=False
        ).filter(
            models.Q(user=request.user) | models.Q(user=None)
        ).order_by('-created_at')

        # Mark notifications as read when viewed
        unread_notifications = notifications.filter(is_read=False)
        for notification in unread_notifications:
            notification.mark_as_read()

        return render(request, 'store/notifications.html', {
            'notifications': notifications
        })
    else:
        return redirect('store:index')


@login_required
def notification_count_api(request):
    """API endpoint to get unread notification count"""
    if request.user.is_authenticated:
        from .notifications import NotificationService
        count = NotificationService.get_unread_count(request.user)
        return JsonResponse({'count': count})
    return JsonResponse({'count': 0})


@login_required
def dismiss_notification(request, notification_id):
    """Dismiss a specific notification"""
    if request.user.is_authenticated:
        from .models import Notification
        from django.db import models

        try:
            notification = Notification.objects.filter(
                id=notification_id
            ).filter(
                models.Q(user=request.user) | models.Q(user=None)
            ).first()

            if not notification:
                raise Notification.DoesNotExist()
            notification.dismiss()
            messages.success(request, 'Notification dismissed.')
        except Notification.DoesNotExist:
            messages.error(request, 'Notification not found.')

        return redirect('store:notification_list')
    else:
        return redirect('store:index')


@login_required
def check_stock_notifications(request):
    """Manually trigger stock check and create notifications"""
    if request.user.is_authenticated:
        from .notifications import check_stock_and_notify

        notifications_created = check_stock_and_notify()

        if notifications_created > 0:
            messages.success(request, f'Created {notifications_created} new stock notifications.')
        else:
            messages.info(request, 'No new stock notifications needed.')

        return redirect('store:notification_list')
    else:
        return redirect('store:index')


# ============================================================================
# SUPPLIER ANALYTICS AND ENHANCED SEARCH VIEWS
# ============================================================================

@login_required
@user_passes_test(can_view_procurement_history)
def supplier_monthly_analytics(request):
    """
    View to display monthly purchase totals from each supplier
    """
    if request.user.is_authenticated:
        from datetime import datetime
        from django.db.models import Sum, Count
        from django.db.models.functions import TruncMonth

        # Get filter parameters
        year = request.GET.get('year')
        month = request.GET.get('month')
        supplier_id = request.GET.get('supplier')

        # Base querysets for both retail and wholesale procurement
        retail_procurements = Procurement.objects.filter(status='completed')
        wholesale_procurements = WholesaleProcurement.objects.filter(status='completed')

        # Apply filters
        if year:
            retail_procurements = retail_procurements.filter(date__year=year)
            wholesale_procurements = wholesale_procurements.filter(date__year=year)

        if month:
            retail_procurements = retail_procurements.filter(date__month=month)
            wholesale_procurements = wholesale_procurements.filter(date__month=month)

        if supplier_id:
            retail_procurements = retail_procurements.filter(supplier_id=supplier_id)
            wholesale_procurements = wholesale_procurements.filter(supplier_id=supplier_id)

        # Calculate monthly totals for retail procurement
        retail_monthly_data = (
            retail_procurements
            .annotate(month=TruncMonth('date'))
            .values('month', 'supplier__name', 'supplier__id')
            .annotate(
                total_amount=Sum('total'),
                procurement_count=Count('id')
            )
            .order_by('-month', 'supplier__name')
        )

        # Calculate monthly totals for wholesale procurement
        wholesale_monthly_data = (
            wholesale_procurements
            .annotate(month=TruncMonth('date'))
            .values('month', 'supplier__name', 'supplier__id')
            .annotate(
                total_amount=Sum('total'),
                procurement_count=Count('id')
            )
            .order_by('-month', 'supplier__name')
        )

        # Combine and organize data by month and supplier
        combined_data = {}

        # Process retail data
        for item in retail_monthly_data:
            month_key = item['month'].strftime('%Y-%m')
            supplier_key = f"{item['supplier__id']}_{item['supplier__name']}"

            if month_key not in combined_data:
                combined_data[month_key] = {}

            if supplier_key not in combined_data[month_key]:
                combined_data[month_key][supplier_key] = {
                    'supplier_id': item['supplier__id'],
                    'supplier_name': item['supplier__name'],
                    'retail_total': Decimal('0.00'),
                    'wholesale_total': Decimal('0.00'),
                    'retail_count': 0,
                    'wholesale_count': 0,
                    'grand_total': Decimal('0.00')
                }

            combined_data[month_key][supplier_key]['retail_total'] = item['total_amount'] or Decimal('0.00')
            combined_data[month_key][supplier_key]['retail_count'] = item['procurement_count']

        # Process wholesale data
        for item in wholesale_monthly_data:
            month_key = item['month'].strftime('%Y-%m')
            supplier_key = f"{item['supplier__id']}_{item['supplier__name']}"

            if month_key not in combined_data:
                combined_data[month_key] = {}

            if supplier_key not in combined_data[month_key]:
                combined_data[month_key][supplier_key] = {
                    'supplier_id': item['supplier__id'],
                    'supplier_name': item['supplier__name'],
                    'retail_total': Decimal('0.00'),
                    'wholesale_total': Decimal('0.00'),
                    'retail_count': 0,
                    'wholesale_count': 0,
                    'grand_total': Decimal('0.00')
                }

            combined_data[month_key][supplier_key]['wholesale_total'] = item['total_amount'] or Decimal('0.00')
            combined_data[month_key][supplier_key]['wholesale_count'] = item['procurement_count']

        # Calculate grand totals
        for month_key in combined_data:
            for supplier_key in combined_data[month_key]:
                supplier_data = combined_data[month_key][supplier_key]
                supplier_data['grand_total'] = supplier_data['retail_total'] + supplier_data['wholesale_total']

        # Get all suppliers for filter dropdown
        suppliers = Supplier.objects.all().order_by('name')

        # Get available years for filter
        current_year = datetime.now().year
        years = list(range(current_year - 5, current_year + 1))

        # Months for filter
        months = [
            (1, 'January'), (2, 'February'), (3, 'March'), (4, 'April'),
            (5, 'May'), (6, 'June'), (7, 'July'), (8, 'August'),
            (9, 'September'), (10, 'October'), (11, 'November'), (12, 'December')
        ]

        context = {
            'combined_data': combined_data,
            'suppliers': suppliers,
            'years': years,
            'months': months,
            'selected_year': year,
            'selected_month': month,
            'selected_supplier': supplier_id,
        }

        return render(request, 'store/supplier_monthly_analytics.html', context)
    else:
        return redirect('store:index')


@login_required
@user_passes_test(can_view_procurement_history)
def supplier_performance_dashboard(request):
    """
    Dashboard view showing supplier performance metrics and top suppliers
    """
    if request.user.is_authenticated:
        from datetime import datetime, timedelta
        from django.db.models import Sum, Count, Avg

        # Get date range (default to last 12 months)
        end_date = datetime.now().date()
        start_date = end_date - timedelta(days=365)

        # Override with user-provided dates if available
        if request.GET.get('start_date'):
            start_date = datetime.strptime(request.GET.get('start_date'), '%Y-%m-%d').date()
        if request.GET.get('end_date'):
            end_date = datetime.strptime(request.GET.get('end_date'), '%Y-%m-%d').date()

        # Calculate supplier performance for retail procurement
        retail_supplier_stats = (
            Procurement.objects
            .filter(status='completed', date__range=[start_date, end_date])
            .values('supplier__id', 'supplier__name')
            .annotate(
                total_amount=Sum('total'),
                procurement_count=Count('id'),
                avg_amount=Avg('total')
            )
            .order_by('-total_amount')
        )

        # Calculate supplier performance for wholesale procurement
        wholesale_supplier_stats = (
            WholesaleProcurement.objects
            .filter(status='completed', date__range=[start_date, end_date])
            .values('supplier__id', 'supplier__name')
            .annotate(
                total_amount=Sum('total'),
                procurement_count=Count('id'),
                avg_amount=Avg('total')
            )
            .order_by('-total_amount')
        )

        # Combine retail and wholesale data
        combined_supplier_stats = {}

        # Process retail data
        for stat in retail_supplier_stats:
            supplier_id = stat['supplier__id']
            if supplier_id not in combined_supplier_stats:
                combined_supplier_stats[supplier_id] = {
                    'supplier_name': stat['supplier__name'],
                    'retail_total': Decimal('0.00'),
                    'wholesale_total': Decimal('0.00'),
                    'retail_count': 0,
                    'wholesale_count': 0,
                    'retail_avg': Decimal('0.00'),
                    'wholesale_avg': Decimal('0.00'),
                    'grand_total': Decimal('0.00'),
                    'total_count': 0
                }

            combined_supplier_stats[supplier_id]['retail_total'] = stat['total_amount'] or Decimal('0.00')
            combined_supplier_stats[supplier_id]['retail_count'] = stat['procurement_count']
            combined_supplier_stats[supplier_id]['retail_avg'] = stat['avg_amount'] or Decimal('0.00')

        # Process wholesale data
        for stat in wholesale_supplier_stats:
            supplier_id = stat['supplier__id']
            if supplier_id not in combined_supplier_stats:
                combined_supplier_stats[supplier_id] = {
                    'supplier_name': stat['supplier__name'],
                    'retail_total': Decimal('0.00'),
                    'wholesale_total': Decimal('0.00'),
                    'retail_count': 0,
                    'wholesale_count': 0,
                    'retail_avg': Decimal('0.00'),
                    'wholesale_avg': Decimal('0.00'),
                    'grand_total': Decimal('0.00'),
                    'total_count': 0
                }

            combined_supplier_stats[supplier_id]['wholesale_total'] = stat['total_amount'] or Decimal('0.00')
            combined_supplier_stats[supplier_id]['wholesale_count'] = stat['procurement_count']
            combined_supplier_stats[supplier_id]['wholesale_avg'] = stat['avg_amount'] or Decimal('0.00')

        # Calculate grand totals and sort
        for supplier_id in combined_supplier_stats:
            stats = combined_supplier_stats[supplier_id]
            stats['grand_total'] = stats['retail_total'] + stats['wholesale_total']
            stats['total_count'] = stats['retail_count'] + stats['wholesale_count']

        # Sort by grand total (descending)
        sorted_suppliers = sorted(
            combined_supplier_stats.items(),
            key=lambda x: x[1]['grand_total'],
            reverse=True
        )

        # Get top 10 suppliers
        top_suppliers = sorted_suppliers[:10]

        # Calculate overall statistics
        total_procurement_value = sum(stats['grand_total'] for _, stats in sorted_suppliers)
        total_procurements = sum(stats['total_count'] for _, stats in sorted_suppliers)
        active_suppliers_count = len(sorted_suppliers)

        context = {
            'top_suppliers': top_suppliers,
            'all_suppliers': sorted_suppliers,
            'total_procurement_value': total_procurement_value,
            'total_procurements': total_procurements,
            'active_suppliers_count': active_suppliers_count,
            'start_date': start_date,
            'end_date': end_date,
        }

        return render(request, 'store/supplier_performance_dashboard.html', context)
    else:
        return redirect('store:index')


@login_required
@user_passes_test(can_view_procurement_history)
def enhanced_procurement_search(request):
    """
    Enhanced search view with advanced filtering capabilities
    """
    if request.user.is_authenticated:
        from datetime import datetime
        from django.db.models import Q, Sum

        # Get search parameters
        search_query = request.GET.get('search', '').strip()
        supplier_id = request.GET.get('supplier')
        start_date = request.GET.get('start_date')
        end_date = request.GET.get('end_date')
        min_amount = request.GET.get('min_amount')
        max_amount = request.GET.get('max_amount')
        status = request.GET.get('status')
        procurement_type = request.GET.get('type', 'all')  # 'retail', 'wholesale', or 'all'

        # Initialize querysets
        retail_procurements = Procurement.objects.all()
        wholesale_procurements = WholesaleProcurement.objects.all()

        # Apply search filters
        if search_query:
            retail_procurements = retail_procurements.filter(
                Q(supplier__name__icontains=search_query) |
                Q(items__item_name__icontains=search_query)
            ).distinct()

            wholesale_procurements = wholesale_procurements.filter(
                Q(supplier__name__icontains=search_query) |
                Q(items__item_name__icontains=search_query)
            ).distinct()

        if supplier_id:
            retail_procurements = retail_procurements.filter(supplier_id=supplier_id)
            wholesale_procurements = wholesale_procurements.filter(supplier_id=supplier_id)

        if start_date:
            start_date_obj = datetime.strptime(start_date, '%Y-%m-%d').date()
            retail_procurements = retail_procurements.filter(date__gte=start_date_obj)
            wholesale_procurements = wholesale_procurements.filter(date__gte=start_date_obj)

        if end_date:
            end_date_obj = datetime.strptime(end_date, '%Y-%m-%d').date()
            retail_procurements = retail_procurements.filter(date__lte=end_date_obj)
            wholesale_procurements = wholesale_procurements.filter(date__lte=end_date_obj)

        if status:
            retail_procurements = retail_procurements.filter(status=status)
            wholesale_procurements = wholesale_procurements.filter(status=status)

        # Apply amount filters
        if min_amount:
            try:
                min_amount_decimal = Decimal(min_amount)
                retail_procurements = retail_procurements.filter(total__gte=min_amount_decimal)
                wholesale_procurements = wholesale_procurements.filter(total__gte=min_amount_decimal)
            except (ValueError, TypeError):
                pass

        if max_amount:
            try:
                max_amount_decimal = Decimal(max_amount)
                retail_procurements = retail_procurements.filter(total__lte=max_amount_decimal)
                wholesale_procurements = wholesale_procurements.filter(total__lte=max_amount_decimal)
            except (ValueError, TypeError):
                pass

        # Annotate with calculated totals and order by date
        retail_procurements = (
            retail_procurements
            .annotate(calculated_total=Sum('items__subtotal'))
            .order_by('-date')
        )

        wholesale_procurements = (
            wholesale_procurements
            .annotate(calculated_total=Sum('items__subtotal'))
            .order_by('-date')
        )

        # Filter by procurement type
        results = []
        if procurement_type in ['all', 'retail']:
            for procurement in retail_procurements:
                results.append({
                    'id': procurement.id,
                    'type': 'retail',
                    'supplier_name': procurement.supplier.name,
                    'date': procurement.date,
                    'total': procurement.calculated_total or procurement.total,
                    'status': procurement.status,
                    'created_by': procurement.created_by.username if procurement.created_by else 'Unknown',
                    'items_count': procurement.items.count()
                })

        if procurement_type in ['all', 'wholesale']:
            for procurement in wholesale_procurements:
                results.append({
                    'id': procurement.id,
                    'type': 'wholesale',
                    'supplier_name': procurement.supplier.name,
                    'date': procurement.date,
                    'total': procurement.calculated_total or procurement.total,
                    'status': procurement.status,
                    'created_by': procurement.created_by.username if procurement.created_by else 'Unknown',
                    'items_count': procurement.items.count()
                })

        # Sort combined results by date (newest first)
        results.sort(key=lambda x: x['date'], reverse=True)

        # Pagination
        from django.core.paginator import Paginator
        paginator = Paginator(results, 20)  # Show 20 results per page
        page_number = request.GET.get('page')
        page_obj = paginator.get_page(page_number)

        # Get all suppliers for filter dropdown
        suppliers = Supplier.objects.all().order_by('name')

        # Calculate summary statistics
        total_results = len(results)
        total_value = sum(result['total'] or Decimal('0.00') for result in results)

        context = {
            'page_obj': page_obj,
            'suppliers': suppliers,
            'search_query': search_query,
            'selected_supplier': supplier_id,
            'start_date': start_date,
            'end_date': end_date,
            'min_amount': min_amount,
            'max_amount': max_amount,
            'selected_status': status,
            'selected_type': procurement_type,
            'total_results': total_results,
            'total_value': total_value,
            'status_choices': [('draft', 'Draft'), ('completed', 'Completed')],
            'type_choices': [('all', 'All'), ('retail', 'Retail'), ('wholesale', 'Wholesale')],
        }

        return render(request, 'store/enhanced_procurement_search.html', context)
    else:
        return redirect('store:index')


@login_required
@user_passes_test(can_view_procurement_history)
def supplier_comparison_view(request):
    """
    View to compare multiple suppliers side by side
    """
    if request.user.is_authenticated:
        from datetime import datetime, timedelta
        from django.db.models import Sum, Count, Avg, Min, Max

        # Get selected suppliers for comparison
        supplier_ids = request.GET.getlist('suppliers')
        if not supplier_ids:
            # If no suppliers selected, show form to select suppliers
            suppliers = Supplier.objects.all().order_by('name')
            return render(request, 'store/supplier_comparison_select.html', {'suppliers': suppliers})

        # Get date range (default to last 12 months)
        end_date = datetime.now().date()
        start_date = end_date - timedelta(days=365)

        if request.GET.get('start_date'):
            start_date = datetime.strptime(request.GET.get('start_date'), '%Y-%m-%d').date()
        if request.GET.get('end_date'):
            end_date = datetime.strptime(request.GET.get('end_date'), '%Y-%m-%d').date()

        comparison_data = []

        for supplier_id in supplier_ids:
            try:
                supplier = Supplier.objects.get(id=supplier_id)

                # Get retail procurement stats
                retail_stats = (
                    Procurement.objects
                    .filter(
                        supplier_id=supplier_id,
                        status='completed',
                        date__range=[start_date, end_date]
                    )
                    .aggregate(
                        total_amount=Sum('total'),
                        procurement_count=Count('id'),
                        avg_amount=Avg('total'),
                        min_amount=Min('total'),
                        max_amount=Max('total'),
                        first_procurement=Min('date'),
                        last_procurement=Max('date')
                    )
                )

                # Get wholesale procurement stats
                wholesale_stats = (
                    WholesaleProcurement.objects
                    .filter(
                        supplier_id=supplier_id,
                        status='completed',
                        date__range=[start_date, end_date]
                    )
                    .aggregate(
                        total_amount=Sum('total'),
                        procurement_count=Count('id'),
                        avg_amount=Avg('total'),
                        min_amount=Min('total'),
                        max_amount=Max('total'),
                        first_procurement=Min('date'),
                        last_procurement=Max('date')
                    )
                )

                # Combine stats
                retail_total = retail_stats['total_amount'] or Decimal('0.00')
                wholesale_total = wholesale_stats['total_amount'] or Decimal('0.00')
                grand_total = retail_total + wholesale_total

                retail_count = retail_stats['procurement_count'] or 0
                wholesale_count = wholesale_stats['procurement_count'] or 0
                total_count = retail_count + wholesale_count

                # Calculate overall average
                overall_avg = grand_total / total_count if total_count > 0 else Decimal('0.00')

                # Get first and last procurement dates
                first_dates = [d for d in [retail_stats['first_procurement'], wholesale_stats['first_procurement']] if d]
                last_dates = [d for d in [retail_stats['last_procurement'], wholesale_stats['last_procurement']] if d]

                first_procurement = min(first_dates) if first_dates else None
                last_procurement = max(last_dates) if last_dates else None

                comparison_data.append({
                    'supplier': supplier,
                    'retail_total': retail_total,
                    'wholesale_total': wholesale_total,
                    'grand_total': grand_total,
                    'retail_count': retail_count,
                    'wholesale_count': wholesale_count,
                    'total_count': total_count,
                    'retail_avg': retail_stats['avg_amount'] or Decimal('0.00'),
                    'wholesale_avg': wholesale_stats['avg_amount'] or Decimal('0.00'),
                    'overall_avg': overall_avg,
                    'retail_min': retail_stats['min_amount'] or Decimal('0.00'),
                    'retail_max': retail_stats['max_amount'] or Decimal('0.00'),
                    'wholesale_min': wholesale_stats['min_amount'] or Decimal('0.00'),
                    'wholesale_max': wholesale_stats['max_amount'] or Decimal('0.00'),
                    'first_procurement': first_procurement,
                    'last_procurement': last_procurement,
                })

            except Supplier.DoesNotExist:
                continue

        # Sort by grand total (descending)
        comparison_data.sort(key=lambda x: x['grand_total'], reverse=True)

        context = {
            'comparison_data': comparison_data,
            'start_date': start_date,
            'end_date': end_date,
            'selected_suppliers': supplier_ids,
        }

        return render(request, 'store/supplier_comparison.html', context)
    else:
        return redirect('store:index')


@login_required
def quick_supplier_search(request):
    """
    AJAX endpoint for quick supplier search with autocomplete
    """
    if request.user.is_authenticated:
        query = request.GET.get('q', '').strip()
        results = []

        if query and len(query) >= 2:
            suppliers = Supplier.objects.filter(
                Q(name__icontains=query) |
                Q(phone__icontains=query) |
                Q(contact_info__icontains=query)
            ).order_by('name')[:10]

            for supplier in suppliers:
                results.append({
                    'id': supplier.id,
                    'name': supplier.name,
                    'phone': supplier.phone or '',
                    'contact_info': supplier.contact_info or '',
                })

        return JsonResponse({'results': results})
    else:
        return JsonResponse({'error': 'Unauthorized'}, status=401)


@login_required
def quick_procurement_search(request):
    """
    AJAX endpoint for quick procurement search
    """
    if request.user.is_authenticated:
        query = request.GET.get('q', '').strip()
        procurement_type = request.GET.get('type', 'all')
        results = []

        if query and len(query) >= 2:
            # Search retail procurements
            if procurement_type in ['all', 'retail']:
                retail_procurements = Procurement.objects.filter(
                    Q(supplier__name__icontains=query) |
                    Q(items__item_name__icontains=query)
                ).distinct().order_by('-date')[:5]

                for procurement in retail_procurements:
                    results.append({
                        'id': procurement.id,
                        'type': 'retail',
                        'supplier_name': procurement.supplier.name,
                        'date': procurement.date.strftime('%Y-%m-%d'),
                        'total': float(procurement.total or 0),
                        'status': procurement.status,
                        'url': f"/procurement_detail/{procurement.id}/"
                    })

            # Search wholesale procurements
            if procurement_type in ['all', 'wholesale']:
                wholesale_procurements = WholesaleProcurement.objects.filter(
                    Q(supplier__name__icontains=query) |
                    Q(items__item_name__icontains=query)
                ).distinct().order_by('-date')[:5]

                for procurement in wholesale_procurements:
                    results.append({
                        'id': procurement.id,
                        'type': 'wholesale',
                        'supplier_name': procurement.supplier.name,
                        'date': procurement.date.strftime('%Y-%m-%d'),
                        'total': float(procurement.total or 0),
                        'status': procurement.status,
                        'url': f"/wholesale/wholesale_procurement_detail/{procurement.id}/"
                    })

        # Sort by date (newest first)
        results.sort(key=lambda x: x['date'], reverse=True)

        return JsonResponse({'results': results[:10]})  # Limit to 10 results
    else:
        return JsonResponse({'error': 'Unauthorized'}, status=401)


@login_required
def supplier_stats_api(request, supplier_id):
    """
    API endpoint to get quick statistics for a specific supplier
    """
    if request.user.is_authenticated:
        try:
            supplier = Supplier.objects.get(id=supplier_id)

            # Get retail procurement stats
            retail_stats = Procurement.objects.filter(
                supplier=supplier,
                status='completed'
            ).aggregate(
                total_amount=Sum('total'),
                count=Count('id')
            )

            # Get wholesale procurement stats
            wholesale_stats = WholesaleProcurement.objects.filter(
                supplier=supplier,
                status='completed'
            ).aggregate(
                total_amount=Sum('total'),
                count=Count('id')
            )

            # Calculate totals
            retail_total = retail_stats['total_amount'] or Decimal('0.00')
            wholesale_total = wholesale_stats['total_amount'] or Decimal('0.00')
            grand_total = retail_total + wholesale_total

            retail_count = retail_stats['count'] or 0
            wholesale_count = wholesale_stats['count'] or 0
            total_count = retail_count + wholesale_count

            return JsonResponse({
                'supplier_id': supplier.id,
                'supplier_name': supplier.name,
                'retail_total': float(retail_total),
                'wholesale_total': float(wholesale_total),
                'grand_total': float(grand_total),
                'retail_count': retail_count,
                'wholesale_count': wholesale_count,
                'total_count': total_count,
                'average_order_value': float(grand_total / total_count) if total_count > 0 else 0.0
            })

        except Supplier.DoesNotExist:
            return JsonResponse({'error': 'Supplier not found'}, status=404)
    else:
        return JsonResponse({'error': 'Unauthorized'}, status=401)




# QR Code Generation Views
from .qr_utils import (
    generate_qr_code_base64,
    generate_item_qr_data,
    generate_receipt_qr_data,
    generate_item_label_base64
)

@login_required
@require_http_methods(['GET'])
def generate_item_qr(request, item_id):
    """Generate QR code for a specific item"""
    try:
        item = get_object_or_404(Item, id=item_id)
        qr_data = generate_item_qr_data(item, mode='retail')
        qr_image = generate_qr_code_base64(qr_data, size=10, border=2)
        
        return JsonResponse({
            'success': True,
            'qr_image': qr_image,
            'qr_data': qr_data,
            'item': {
                'id': item.id,
                'name': item.name,
                'barcode': item.barcode if hasattr(item, 'barcode') else None,
            }
        })
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=400)


@login_required
@require_http_methods(['GET'])
def generate_item_label(request, item_id):
    """Generate printable QR code label for an item"""
    try:
        item = get_object_or_404(Item, id=item_id)
        include_price = request.GET.get('include_price', 'true').lower() == 'true'
        
        label_image = generate_item_label_base64(item, mode='retail', include_price=include_price)
        
        return JsonResponse({
            'success': True,
            'label_image': label_image,
            'item': {
                'id': item.id,
                'name': item.name,
            }
        })
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=400)


@login_required
@require_http_methods(['GET'])
def generate_receipt_qr(request, receipt_id):
    """Generate QR code for a specific receipt"""
    try:
        receipt = get_object_or_404(Receipt, id=receipt_id)
        qr_data = generate_receipt_qr_data(receipt, mode='retail')
        qr_image = generate_qr_code_base64(qr_data, size=10, border=2)
        
        return JsonResponse({
            'success': True,
            'qr_image': qr_image,
            'qr_data': qr_data,
            'receipt': {
                'id': receipt.id,
                'receipt_no': receipt.receipt_no,
                'total': str(receipt.total_amount),
            }
        })
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=400)


@login_required
def print_item_labels(request):
    """Render page for bulk printing item labels with QR codes"""
    items = Item.objects.filter(stock__gt=0).order_by('name')
    
    context = {
        'items': items,
    }
    return render(request, 'store/print_item_labels.html', context)


@login_required
@require_http_methods(['POST'])
def bulk_generate_labels(request):
    """Generate multiple item labels at once"""
    try:
        item_ids = request.POST.getlist('item_ids[]')
        include_price = request.POST.get('include_price', 'true').lower() == 'true'
        
        labels = []
        for item_id in item_ids:
            try:
                item = Item.objects.get(id=item_id)
                label_image = generate_item_label_base64(item, mode='retail', include_price=include_price)
                labels.append({
                    'item_id': item.id,
                    'item_name': item.name,
                    'label_image': label_image
                })
            except Item.DoesNotExist:
                continue
        
        return JsonResponse({
            'success': True,
            'labels': labels,
            'count': len(labels)
        })
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=400)

