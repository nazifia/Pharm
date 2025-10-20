from django.db import transaction
from django.shortcuts import render, redirect, get_object_or_404
from django.http import HttpResponse, JsonResponse
from django.contrib import messages
from django.utils.timezone import now, timezone
from datetime import timedelta, datetime
from decimal import Decimal
from django.db.models import Sum, Q, F
from django.contrib.auth.decorators import login_required, user_passes_test
from django.views.decorators.http import require_POST
import uuid
from store.models import *
from store.forms import *
from supplier.models import *
from customer.models import *
from .forms import *
# Import functions from store.views carefully to avoid circular imports
# These functions are defined at module level, so they can be imported directly
from store.views import get_daily_sales, get_monthly_sales_with_expenses
import logging

# Import procurement permission functions
from userauth.permissions import (
    can_manage_wholesale_procurement,
    can_view_procurement_history
)

logger = logging.getLogger(__name__)

# Add this at the top of your views.py if not already present
def is_superuser(user):
    return user.is_superuser

@login_required
@user_passes_test(is_superuser)
def adjust_wholesale_stock_levels(request):
    items = WholesaleItem.objects.all().order_by('name')
    context = {
        'items': items,
        'title': 'Adjust Wholesale Stock Levels'
    }
    return render(request, 'wholesale/adjust_wholesale_stock_level.html', context)

@login_required
@user_passes_test(is_superuser)
def search_wholesale_for_adjustment(request):
    query = request.GET.get('q', '')
    if query:
        items = WholesaleItem.objects.filter(
            Q(name__icontains=query) |
            Q(brand__icontains=query) |
            Q(dosage_form__icontains=query)
        ).order_by('name')
    else:
        items = WholesaleItem.objects.all().order_by('name')
    return render(request, 'wholesale/search_wholesale_for_adjustment.html', {'items': items})


@login_required
def search_wholesale_items(request):
    """API endpoint for searching wholesale items for stock check"""
    query = request.GET.get('q', '').strip()
    if query and len(query) >= 2:  # Only search for meaningful queries
        # Optimized search with prefix matching first, then partial matching
        items = WholesaleItem.objects.filter(
            Q(name__istartswith=query) |
            Q(brand__istartswith=query) |
            Q(dosage_form__istartswith=query) |
            Q(name__icontains=query) |
            Q(brand__icontains=query) |
            Q(dosage_form__icontains=query)
        ).distinct().order_by('name')[:30]  # Increased limit but still reasonable
    else:
        items = WholesaleItem.objects.all().order_by('name')[:30]  # Increased limit for better UX

    # Check if this is an HTMX request
    if request.headers.get('HX-Request'):
        # Log for debugging
        print(f"HTMX request received for search_wholesale_items with query: {query}")
        print(f"Found {len(items)} items matching the query")
        # Return the search results template
        return render(request, 'partials/search_wholesale_items_results.html', {'items': items})
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

@login_required
@user_passes_test(is_superuser)
def adjust_wholesale_stock_level(request, item_id):
    if request.method == 'POST':
        item = get_object_or_404(WholesaleItem, id=item_id)
        try:
            new_stock = int(request.POST.get(f'new-stock-{item_id}', 0))
            old_stock = item.stock

            # Log the stock adjustment (without using the new model fields yet)
            logger.info(f"Manual wholesale stock adjustment for {item.name} (ID: {item.id}) by {request.user.username}: {old_stock} -> {new_stock}")

            # Update the item stock
            item.stock = new_stock
            item.save()

            messages.success(request, f'Stock for {item.name} updated from {old_stock} to {new_stock}')
            return render(request, 'wholesale/search_wholesale_for_adjustment.html', {'items': [item]})
        except ValueError:
            messages.error(request, 'Invalid stock value provided')
            return HttpResponse(status=400)
    return HttpResponse(status=405)

# Admin check - allows Admin and Manager users
def is_admin_or_manager(user):
    return (user.is_authenticated and
            hasattr(user, 'profile') and
            user.profile and
            user.profile.user_type in ['Admin', 'Manager'])

def wholesale_page(request):
    return render(request, 'wholesale_page.html')

@login_required
def wholesale_dashboard(request):
    """
    Wholesale-only dashboard for users with wholesale permissions
    """
    if request.user.is_authenticated:
        from userauth.permissions import can_operate_wholesale
        if not can_operate_wholesale(request.user):
            messages.error(request, 'You do not have permission to access wholesale operations.')
            return redirect('store:index')

        from customer.models import WholesaleCustomer

        # Get wholesale items and statistics
        items = WholesaleItem.objects.all()
        settings = WholesaleSettings.get_settings()
        low_stock_threshold = settings.low_stock_threshold

        # Calculate statistics
        total_items = items.count()
        low_stock_items = [item for item in items if item.stock <= low_stock_threshold]
        low_stock_count = len(low_stock_items)
        in_stock_items = items.filter(stock__gt=0).count()
        out_of_stock = items.filter(stock=0).count()

        # Get wholesale customers count
        total_customers = WholesaleCustomer.objects.count()

        context = {
            'total_items': total_items,
            'low_stock_items': low_stock_items,
            'low_stock_count': low_stock_count,
            'in_stock_items': in_stock_items,
            'out_of_stock': out_of_stock,
            'total_customers': total_customers,
            'low_stock_threshold': low_stock_threshold,
        }

        # Only include financial data if user has permission
        if request.user.has_permission('view_financial_reports'):
            total_purchase_value = sum(item.cost * item.stock for item in items)
            total_stock_value = sum(item.price * item.stock for item in items)
            total_profit = total_stock_value - total_purchase_value

            context.update({
                'total_purchase_value': total_purchase_value,
                'total_stock_value': total_stock_value,
                'total_profit': total_profit,
            })

        return render(request, 'wholesale/wholesale_dashboard.html', context)
    else:
        return redirect('store:index')

@login_required
def wholesales(request):
    if request.user.is_authenticated:
        from userauth.permissions import can_operate_wholesale
        if not can_operate_wholesale(request.user):
            messages.error(request, 'You do not have permission to access wholesale operations.')
            return redirect('store:index')
        items = WholesaleItem.objects.all().order_by('name')
        settings = WholesaleSettings.get_settings()

        if request.method == 'POST' and request.user.is_superuser:
            settings_form = WholesaleSettingsForm(request.POST, instance=settings)
            if settings_form.is_valid():
                settings = settings_form.save()
                messages.success(request, 'Wholesale settings updated successfully')
            else:
                messages.error(request, 'Error updating wholesale settings')
        else:
            settings_form = WholesaleSettingsForm(instance=settings)

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
            # Calculate values using the threshold from settings
            total_purchase_value = sum(item.cost * item.stock for item in items)
            total_stock_value = sum(item.price * item.stock for item in items)
            total_profit = total_stock_value - total_purchase_value

            context.update({
                'total_purchase_value': total_purchase_value,
                'total_stock_value': total_stock_value,
                'total_profit': total_profit,
            })
        return render(request, 'wholesale/wholesales.html', context)
    else:
        return redirect('store:index')

@login_required
def search_wholesale_item(request):
    if request.user.is_authenticated:
        from userauth.permissions import can_operate_wholesale
        if not can_operate_wholesale(request.user):
            messages.error(request, 'You do not have permission to access wholesale operations.')
            return redirect('store:index')

        query = request.GET.get('search', '').strip()
        if query and len(query) >= 2:  # Only search for meaningful queries
            # Optimized search with prefix matching first, then partial matching
            items = WholesaleItem.objects.filter(
                Q(name__istartswith=query) |  # Faster prefix search
                Q(brand__istartswith=query) |
                Q(dosage_form__istartswith=query) |
                Q(name__icontains=query) |  # Fallback for partial matches
                Q(brand__icontains=query) |
                Q(dosage_form__icontains=query)
            ).distinct().order_by('name')[:50]  # Limit results for performance
        else:
            items = WholesaleItem.objects.all().order_by('name')[:50]  # Limit initial load

        # Add some context for the template
        context = {
            'items': items,
            'search_query': query,
            'total_items': items.count(),
            'title': 'Search Wholesale Items'
        }

        # Check if this is an HTMX request for partial update
        if request.headers.get('HX-Request'):
            return render(request, 'partials/wholesale_search.html', context)
        else:
            # Return full page for direct access
            return render(request, 'wholesale/search_wholesale_item.html', context)
    else:
        return redirect('store:index')


@login_required
def add_to_wholesale(request):
    if request.user.is_authenticated:
        from userauth.permissions import can_manage_items
        if not can_manage_items(request.user):
            messages.error(request, 'You do not have permission to add wholesale items.')
            return redirect('wholesale:wholesales')
        if request.method == 'POST':
            form = addWholesaleForm(request.POST)
            if form.is_valid():
                item = form.save(commit=False)
                item.save()
                messages.success(request, 'Item added successfully')
                return redirect('wholesale:wholesales')
        low_stock_threshold = 10  # Adjust this number as needed

        # Get items and low stock items
        items = WholesaleItem.objects.all()
        low_stock_items = [item for item in items if item.stock <= low_stock_threshold]

        context = {
            'items': items,
            'low_stock_items': low_stock_items,
        }

        # Only include financial data if user has permission
        if request.user.has_permission('view_financial_reports'):
            # Calculate total purchase value and total stock value
            total_purchase_value = sum(item.cost * item.stock for item in items)
            total_stock_value = sum(item.price * item.stock for item in items)
            total_profit = total_stock_value - total_purchase_value

            context.update({
                'total_purchase_value': total_purchase_value,
                'total_stock_value': total_stock_value,
                'total_profit': total_profit,
            })
        return render(request, 'wholesale/wholesales.html', context)
    else:
        return render(request, 'store/index.html')


@user_passes_test(is_admin_or_manager)
@login_required
def add_to_wholesale(request):
    if request.user.is_authenticated:
        if request.method == 'POST':
            # The form now uses hidden fields for dosage_form and unit
            # which are set by JavaScript, so we can use the form directly
            form = addWholesaleForm(request.POST)

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
                return redirect('wholesale:wholesales')
            else:
                print("Form errors:", form.errors)  # Debugging output
                messages.error(request, 'Error creating item')
        else:
            form = addWholesaleForm()
        if request.headers.get('HX-Request'):
            return render(request, 'partials/add_to_wholesale.html', {'form': form})
        else:
            return render(request, 'wholesale/wholesales.html', {'form': form})
    else:
        return redirect('store:index')



@login_required
def edit_wholesale_item(request, pk):
    if request.user.is_authenticated:
        from userauth.permissions import can_manage_items
        if not can_manage_items(request.user):
            if request.headers.get('HX-Request'):
                return HttpResponse("Permission denied", status=403)
            messages.error(request, 'You do not have permission to edit wholesale items.')
            return redirect('wholesale:wholesales')
        item = get_object_or_404(WholesaleItem, id=pk)

        if request.method == 'POST':
            form = addWholesaleForm(request.POST, instance=item)
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
                
                # Handle HTMX response - close modal and refresh page
                if request.headers.get('HX-Request'):
                    # Return a simple response with a script to close modal and refresh
                    response_content = """
                    <script>
                        window.location.reload();
                    </script>
                    """
                    return HttpResponse(response_content)
                
                return redirect('wholesale:wholesales')
            else:
                print("Form errors:", form.errors)  # Debugging output
                messages.error(request, 'Failed to update item')
                # If form has errors, re-render the modal with errors
                if request.headers.get('HX-Request'):
                    return render(request, 'partials/edit_wholesale_item.html', {'form': form, 'item': item})
        else:
            form = addWholesaleForm(instance=item)

        # Render the modal or full page based on request type
        if request.headers.get('HX-Request'):
            return render(request, 'partials/edit_wholesale_item.html', {'form': form, 'item': item})
        else:
            return render(request, 'wholesale/wholesales.html', {'form': form})
    else:
        return redirect('store:index')



@login_required
def return_wholesale_item(request, pk):
    if request.user.is_authenticated:
        item = get_object_or_404(WholesaleItem, id=pk)

        if request.method == 'POST':
            form = ReturnWholesaleItemForm(request.POST)
            if form.is_valid():
                return_quantity = form.cleaned_data.get('return_item_quantity')

                # Validate the return quantity
                if return_quantity <= 0:
                    messages.error(request, 'Invalid return item quantity.')
                    return redirect('wholesale:wholesales')

                try:
                    with transaction.atomic():
                        # Update item stock
                        item.stock += return_quantity
                        item.save()

                        # Find the sales item associated with the returned item
                        sales_item = WholesaleSalesItem.objects.filter(item=item).order_by('-quantity').first()
                        if not sales_item or sales_item.quantity < return_quantity:
                            messages.error(request, f'No valid sales record found for {item.name}.')
                            return redirect('wholesale:wholesales')

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

                        # Handle return tracking without automatic wallet refund for registered wholesale customers
                        if sales.customer and hasattr(sales.customer, 'wholesale_customer_wallet'):
                            wallet = sales.customer.wholesale_customer_wallet
                            # For registered wholesale customers, do NOT automatically refund to wallet
                            # Only log the return without wallet credit

                            # Log the return transaction without wallet refund
                            TransactionHistory.objects.create(
                                customer=sales.customer,
                                user=request.user,
                                transaction_type='refund',
                                amount=Decimal('0.00'),  # No wallet refund for registered customers
                                description=f'Return processed for {return_quantity} of {item.name} (₦{refund_amount}) - No automatic wallet refund for registered wholesale customer'
                            )
                            messages.success(
                                request,
                                f'{return_quantity} of {item.name} successfully returned (₦{refund_amount}). No automatic wallet refund applied for registered wholesale customers.'
                            )
                        else:
                            messages.error(request, 'Customer wallet not found or not associated.')


                        # Update dispensing log
                        logs = DispensingLog.objects.filter(
                            user=sales.user,
                            name=item.name,
                            status__in=['Dispensed', 'Partially Returned']
                        ).order_by('-created_at')

                        remaining_return_quantity = return_quantity

                        for log in logs:
                            if remaining_return_quantity <= 0:
                                break

                            if log.quantity <= remaining_return_quantity:
                                # Fully return this log's quantity
                                remaining_return_quantity -= log.quantity
                                log.status = 'Returned'
                                log.save()
                                # log.delete()  # Completely remove the log if returned in full
                            else:
                                # Partially return this log's quantity
                                log.quantity -= remaining_return_quantity
                                log.status = 'Partially Returned'
                                log.save()
                                remaining_return_quantity = 0

                        # Handle excess return quantities
                        if remaining_return_quantity > 0:
                            messages.warning(
                                request,
                                f"Some of the returned quantity ({remaining_return_quantity}) could not be processed as it exceeds the dispensed records."
                            )

                        # Create a new dispensing log entry for the return
                        # Get or create Formulation object for dosage_form
                        dosage_form_obj = None
                        if item.dosage_form:
                            from store.models import Formulation
                            dosage_form_obj, created = Formulation.objects.get_or_create(
                                dosage_form=item.dosage_form
                            )

                        # Calculate proportional discount for the return
                        proportional_discount = Decimal('0')
                        if sales_item.discount_amount > 0 and sales_item.quantity > 0:
                            discount_per_unit = sales_item.discount_amount / sales_item.quantity
                            proportional_discount = discount_per_unit * return_quantity

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

                        # Update daily and monthly sales data
                        daily_sales = get_daily_sales()
                        monthly_sales = get_monthly_sales_with_expenses()

                        # Render updated logs for HTMX requests
                        if request.headers.get('HX-Request'):
                            context = {
                                'logs': DispensingLog.objects.filter(user=sales.user).order_by('-created_at'),
                                'daily_sales': daily_sales,
                                'monthly_sales': monthly_sales
                            }
                            return render(request, 'store/dispensing_log.html', context)

                        messages.success(
                            request,
                            f'{return_quantity} of {item.name} successfully returned, sales and logs updated.'
                        )
                        return redirect('wholesale:wholesales')

                except Exception as e:
                    # Handle exceptions during atomic transaction
                    print(f'Error during item return: {e}')
                    messages.error(request, f'Error processing return: {e}')
                    return redirect('wholesale:wholesales')
            else:
                messages.error(request, 'Invalid input. Please correct the form and try again.')

        else:
            # Display the return form in a modal or a page
            form = ReturnWholesaleItemForm()

        # Return appropriate response for HTMX or full-page requests
        if request.headers.get('HX-Request'):
            return render(request, 'partials/return_wholesale_item.html', {'form': form, 'item': item})
        else:
            return render(request, 'wholesale/wholesales.html', {'form': form})
    else:
        return redirect('store:index')



@login_required
@user_passes_test(lambda user: user.is_authenticated and hasattr(user, 'profile') and user.profile and user.profile.user_type in ['Admin', 'Manager'])
def delete_wholesale_item(request, pk):
    if request.user.is_authenticated:
        item = get_object_or_404(WholesaleItem, id=pk)
        item.delete()
        messages.success(request, 'Item deleted successfully')
        return redirect('wholesale:wholesales')
    else:
        return redirect('store:index')





@login_required
def wholesale_exp_alert(request):
    if request.user.is_authenticated:
        from userauth.permissions import can_manage_wholesale_expiry
        if not can_manage_wholesale_expiry(request.user):
            messages.error(request, 'You do not have permission to manage wholesale expiry dates.')
            return redirect('store:index')

        alert_threshold = timezone.now() + timedelta(days=90)

        expiring_items = WholesaleItem.objects.filter(exp_date__lte=alert_threshold, exp_date__gt=timezone.now())

        expired_items = WholesaleItem.objects.filter(exp_date__lt=timezone.now())

        for expired_item in expired_items:

            if expired_item.stock > 0:

                expired_item.stock = 0
                expired_item.save()

        return render(request, 'partials/wholesale_exp_date_alert.html', {
            'expired_items': expired_items,
            'expiring_items': expiring_items,
        })
    else:
        return redirect('store:index')



def dispense_wholesale(request):
    print(f"DEBUG: dispense_wholesale view called by user: {request.user}")
    print(f"DEBUG: User authenticated: {request.user.is_authenticated}")
    print(f"DEBUG: Request path: {request.path}")
    print(f"DEBUG: Request method: {request.method}")

    # TEMPORARILY BYPASS AUTHENTICATION FOR DEBUGGING
    # if request.user.is_authenticated:
    if True:  # Always proceed for debugging
        if request.method == 'POST':
            form = wholesaleDispenseForm(request.POST)
            if form.is_valid():
                q = form.cleaned_data['q']
                results = WholesaleItem.objects.filter(
                    Q(name__icontains=q) | Q(brand__icontains=q)
                ).filter(stock__gt=0)  # Only show items with stock > 0
        else:
            form = wholesaleDispenseForm()
            results = None

        # Check if this is an HTMX request (for modal)
        if request.headers.get('HX-Request'):
            print(f"DEBUG: HTMX request detected")
            return render(request, 'partials/wholesale_dispense_modal.html', {'form': form, 'results': results})
        else:
            print(f"DEBUG: Regular page request")
            # Regular page request - get cart summary for the new dynamic interface
            cart_count = 0
            cart_total = 0

            # Only get cart data if user is authenticated
            if request.user.is_authenticated:
                cart_items = WholesaleCart.objects.filter(user=request.user)
                cart_count = cart_items.count()
                cart_total = sum(cart_item.subtotal for cart_item in cart_items)

            context = {
                'form': form,
                'results': results,
                'cart_count': cart_count,
                'cart_total': cart_total
            }
            print(f"DEBUG: Rendering wholesale/dispense_wholesale.html with context: {context}")
            return render(request, 'wholesale/dispense_wholesale.html', context)
    else:
        return redirect('store:index')


def dispense_wholesale_no_auth(request):
    """Wholesale dispensing without authentication for testing"""
    # Get cart summary (will be empty for unauthenticated users)
    cart_count = 0
    cart_total = 0

    if request.user.is_authenticated:
        cart_items = WholesaleCart.objects.filter(user=request.user)
        cart_count = cart_items.count()
        cart_total = sum(item.total_price for item in cart_items)

    context = {
        'cart_count': cart_count,
        'cart_total': cart_total,
        'form': None,
        'results': None
    }
    return render(request, 'wholesale/dispense_wholesale.html', context)


def minimal_test(request):
    """Minimal test view that just returns plain text"""
    from django.http import HttpResponse
    return HttpResponse("✅ MINIMAL TEST SUCCESSFUL! Wholesale URLs are working correctly.")


def test_template_view(request):
    """Test view to check if template rendering works"""
    print(f"DEBUG: test_template_view called")
    print(f"DEBUG: User: {request.user}")
    print(f"DEBUG: Authenticated: {request.user.is_authenticated}")

    context = {
        'cart_count': 0,
        'cart_total': 0,
        'user': request.user,
        'form': None,
        'results': [],
    }

    try:
        print(f"DEBUG: Attempting to render template...")
        return render(request, 'wholesale/dispense_wholesale.html', context)
    except Exception as e:
        print(f"DEBUG: Template error: {e}")
        from django.http import HttpResponse
        return HttpResponse(f"Template Error: {e}")


def super_simple_dispense(request):
    """Wholesale dispensing view with proper template and functionality"""
    print(f"DEBUG: super_simple_dispense view called by user: {request.user}")
    print(f"DEBUG: User authenticated: {request.user.is_authenticated}")
    print(f"DEBUG: Request path: {request.path}")

    # Get cart data if user is authenticated
    cart_count = 0
    cart_total = 0

    if request.user.is_authenticated:
        try:
            from store.models import WholesaleCart
            cart_items = WholesaleCart.objects.filter(user=request.user)
            cart_count = cart_items.count()
            cart_total = sum(cart_item.subtotal for cart_item in cart_items)
            print(f"DEBUG: Cart count: {cart_count}, total: {cart_total}")
        except Exception as e:
            print(f"DEBUG: Error getting cart data: {e}")

    # Prepare context for template
    context = {
        'cart_count': cart_count,
        'cart_total': cart_total,
        'user': request.user,
        'form': None,  # We'll add the form later
        'results': [],  # Empty results initially
    }

    print(f"DEBUG: Rendering dispense_wholesale.html with context: {context}")
    return render(request, 'wholesale/dispense_wholesale.html', context)


def simple_wholesale_test(request):
    """Simple test view with no authentication required"""
    print(f"DEBUG: simple_wholesale_test view called")
    print(f"DEBUG: User: {request.user}")
    print(f"DEBUG: Authenticated: {request.user.is_authenticated}")
    print(f"DEBUG: Request path: {request.path}")

    # Get cart data if user is authenticated
    cart_count = 0
    cart_total = 0

    if request.user.is_authenticated:
        try:
            cart_items = WholesaleCart.objects.filter(user=request.user)
            cart_count = cart_items.count()
            cart_total = sum(item.total_price for item in cart_items)
            print(f"DEBUG: Cart count: {cart_count}, total: {cart_total}")
        except Exception as e:
            print(f"DEBUG: Error getting cart data: {e}")

    context = {
        'cart_count': cart_count,
        'cart_total': cart_total,
        'user': request.user
    }

    print(f"DEBUG: Rendering simple_test.html with context: {context}")
    return render(request, 'wholesale/simple_test.html', context)


def test_wholesale_page(request):
    """Simple test page to verify wholesale URLs work"""
    from django.http import HttpResponse
    return HttpResponse("""
    <h1>✅ Wholesale URL Test Successful!</h1>
    <p>This confirms that wholesale URLs are working correctly.</p>
    <p>User: {}</p>
    <p>Authenticated: {}</p>
    <a href="/dispense_wholesale/">Try Wholesale Dispensing</a>
    """.format(request.user, request.user.is_authenticated))


def auth_test_wholesale(request):
    """Test authentication status"""
    from django.http import HttpResponse

    status = f"""
    <h1>Authentication Test</h1>
    <p><strong>User:</strong> {request.user}</p>
    <p><strong>Is Authenticated:</strong> {request.user.is_authenticated}</p>
    <p><strong>Is Anonymous:</strong> {request.user.is_anonymous}</p>
    <p><strong>User ID:</strong> {getattr(request.user, 'id', 'None')}</p>
    <p><strong>Username:</strong> {getattr(request.user, 'username', 'None')}</p>
    <p><strong>Session Key:</strong> {request.session.session_key}</p>
    <p><strong>Session Items:</strong> {dict(request.session.items())}</p>
    """

    return HttpResponse(status)


@login_required
def debug_dispense_wholesale(request):
    """Debug version of wholesale dispensing"""
    if request.user.is_authenticated:
        # Get cart summary
        cart_items = WholesaleCart.objects.filter(user=request.user)
        cart_count = cart_items.count()
        cart_total = sum(item.total_price for item in cart_items)

        context = {
            'cart_count': cart_count,
            'cart_total': cart_total,
            'form': None,
            'results': None
        }
        return render(request, 'wholesale/debug_dispense.html', context)
    else:
        return redirect('store:index')


@login_required
def dispense_wholesale_simple(request):
    """Simple version of wholesale dispensing for testing"""
    if request.user.is_authenticated:
        # Get cart summary
        cart_items = WholesaleCart.objects.filter(user=request.user)
        cart_count = cart_items.count()
        cart_total = sum(item.total_price for item in cart_items)

        context = {
            'cart_count': cart_count,
            'cart_total': cart_total
        }
        return render(request, 'wholesale/dispense_wholesale_simple.html', context)
    else:
        return redirect('store:index')


def wholesale_dispense_search_items(request):
    """HTMX endpoint for dynamic item search in wholesale dispensing"""
    print(f"DEBUG: wholesale_dispense_search_items called")
    print(f"DEBUG: Query: {request.GET.get('q', '')}")

    query = request.GET.get('q', '').strip()
    results = []

    if query and len(query) >= 2:
        try:
            # Use the same search logic as the original dispense view
            results = WholesaleItem.objects.filter(
                Q(name__icontains=query) | Q(brand__icontains=query)
            ).filter(stock__gt=0).order_by('name')[:50]  # Limit results for performance
            print(f"DEBUG: Found {len(results)} results")
        except Exception as e:
            print(f"DEBUG: Error searching items: {e}")
            results = []

    return render(request, 'partials/wholesale_dispense_search_results.html', {'results': results, 'query': query})


from django.views.decorators.http import require_POST
@login_required
@require_POST
def add_to_wholesale_cart(request, item_id):
    if request.user.is_authenticated:
        item = get_object_or_404(WholesaleItem, id=item_id)
        quantity = Decimal(request.POST.get('quantity', 0.5))
        unit = request.POST.get('unit')

        if quantity < 0.5:  # Minimum quantity is 0.5 units
            messages.warning(request, "Quantity must be greater than zero.")
            return redirect('wholesale:wholesale_cart')

        if quantity > item.stock:
            messages.warning(request, f"Not enough stock for {item.name}. Available stock: {item.stock}")
            return redirect('wholesale:wholesale_cart')

        # Add the item to the cart or update its quantity if it already exists
        cart_item, created = WholesaleCart.objects.get_or_create(
            user=request.user,
            item=item,
            unit=unit,
            defaults={'quantity': quantity, 'price': item.price}
        )
        if not created:
            cart_item.quantity += quantity

        # Always update the price to match the current item price
        cart_item.price = item.price
        cart_item.save()

        # Update stock quantity in the wholesale inventory
        item.stock -= quantity
        item.save()

        messages.success(request, f"{quantity} {item.unit} of {item.name} added to cart.")

        # Return the cart summary as JSON if this was an HTMX request
        if request.headers.get('HX-Request'):
            cart_items = WholesaleCart.objects.filter(user=request.user)
            total_price = sum(cart_item.subtotal for cart_item in cart_items)

            # Check if this is from the dispensing page (has specific header or parameter)
            if request.GET.get('from_dispense') or request.POST.get('from_dispense'):
                # Return HTML fragment for cart summary widget update
                context = {
                    'cart_count': cart_items.count(),
                    'cart_total': total_price,
                    'success_message': f"{quantity} {item.unit} of {item.name} added to cart."
                }
                return render(request, 'partials/wholesale_cart_summary_widget.html', context)
            else:
                # Return JSON for other HTMX requests
                return JsonResponse({
                    'cart_items_count': cart_items.count(),
                    'total_price': float(total_price),
                })

        # Redirect to the wholesale cart page if not an HTMX request
        return redirect('wholesale:wholesale_cart')
    else:
        return redirect('store:index')




@login_required
def wholesale_customer_history(request, customer_id):
    if request.user.is_authenticated:
        wholesale_customer = get_object_or_404(WholesaleCustomer, id=customer_id)

        histories = WholesaleSalesItem.objects.filter(
            sales__wholesale_customer=wholesale_customer
        ).select_related(
            'item', 'sales', 'sales__user'
        ).order_by('-sales__date')

        # Process histories and calculate totals
        processed_histories = []
        for history in histories:
            history.date = history.sales.date
            history.user = history.sales.user
            history.action = 'return' if history.quantity < 0 else 'purchase'
            processed_histories.append(history)

        # Group histories by year and month
        history_data = {}
        for history in processed_histories:
            year = history.date.year
            month = history.date.strftime('%B')  # Full month name

            if year not in history_data:
                history_data[year] = {'total': Decimal('0'), 'months': {}}

            if month not in history_data[year]['months']:
                history_data[year]['months'][month] = {'total': Decimal('0'), 'items': []}

            history_data[year]['total'] += history.subtotal
            history_data[year]['months'][month]['total'] += history.subtotal
            history_data[year]['months'][month]['items'].append(history)

        context = {
            'wholesale_customer': wholesale_customer,
            'history_data': history_data,
        }

        return render(request, 'partials/wholesale_customer_history.html', context)
    return redirect('store:index')




@transaction.atomic
@login_required
def select_wholesale_items(request, pk):
    if request.user.is_authenticated:
        customer = get_object_or_404(WholesaleCustomer, id=pk)
        # Store customer ID in user-specific session for later use (same as retail)
        from userauth.session_utils import set_user_customer_id
        set_user_customer_id(request, customer.id)

        # Check if this is a return action request
        action = request.GET.get('action', 'purchase')
        if request.method == 'POST':
            action = request.POST.get('action', 'purchase')

        # Filter items based on action
        if action == 'return':
            # For returns, show only items that were previously purchased by this customer
            purchased_item_ids = WholesaleSalesItem.objects.filter(
                sales__wholesale_customer=customer
            ).values_list('item_id', flat=True).distinct()
            items = WholesaleItem.objects.filter(id__in=purchased_item_ids).order_by('name')
        else:
            # For purchases, show all available items
            items = WholesaleItem.objects.all().order_by('name')

        # Fetch wallet balance
        wallet_balance = Decimal('0.0')
        try:
            wallet_balance = customer.wholesale_customer_wallet.balance
        except WholesaleCustomerWallet.DoesNotExist:
            messages.warning(request, 'This customer does not have an associated wallet.')

        if request.method == 'POST':
            action = request.POST.get('action', 'purchase')  # Default to purchase
            item_ids = request.POST.getlist('item_ids', [])
            quantities = request.POST.getlist('quantities', [])
            # discount_amounts = request.POST.getlist('discount_amounts', [])
            units = request.POST.getlist('units', [])

            if len(item_ids) != len(quantities):
                messages.warning(request, 'Mismatch between selected items and quantities.')
                return redirect('wholesale:select_wholesale_items', pk=pk)

            total_cost = Decimal('0.0')

            # Create a new Sales record only for purchases, not for returns
            sales = None
            if action == 'purchase':
                # Create a new Sales record for this transaction
                sales = Sales.objects.create(
                    user=request.user,
                    wholesale_customer=customer,
                    total_amount=Decimal('0.0')
                )

            # Fetch or create a Receipt only for purchases
            receipt = None
            if action == 'purchase' and sales:
                receipt = WholesaleReceipt.objects.filter(wholesale_customer=customer, sales=sales).first()

                if not receipt:
                    # Generate a unique receipt ID using uuid
                    import uuid
                    receipt_id = str(uuid.uuid4())[:5]  # Use first 5 characters of a UUID

                    # Get payment method and status from form
                    payment_method = request.POST.get('payment_method', 'Cash')
                    status = request.POST.get('status', 'Paid')

                    # Store in session for later use in receipt generation
                    request.session['payment_method'] = payment_method
                    request.session['payment_status'] = status

                    receipt = WholesaleReceipt.objects.create(
                        wholesale_customer=customer,
                        sales=sales,
                        receipt_id=receipt_id,
                        total_amount=Decimal('0.0'),
                        buyer_name=customer.name,
                        buyer_address=customer.address,
                        date=datetime.now(),
                        payment_method=payment_method,
                        status=status
                    )


            for i, item_id in enumerate(item_ids):
                try:
                    item = WholesaleItem.objects.get(id=item_id)
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
                        cart_item, created = WholesaleCart.objects.get_or_create(
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
                            cart_item = WholesaleCart.objects.get(user=request.user, item=item)
                            discount_amount = cart_item.discount_amount or Decimal('0.00')
                        except WholesaleCart.DoesNotExist:
                            pass

                        discounted_subtotal = base_subtotal - discount_amount
                        total_cost += discounted_subtotal

                        # Update or create WholesaleSalesItem
                        sales_item, created = WholesaleSalesItem.objects.get_or_create(
                            sales=sales,
                            item=item,
                            defaults={'quantity': quantity, 'price': item.price, 'discount_amount': discount_amount}
                        )
                        if not created:
                            sales_item.quantity += quantity
                            sales_item.discount_amount += discount_amount
                            sales_item.save()

                        # Update the receipt with discounted amount
                        receipt.total_amount += discounted_subtotal
                        receipt.save()

                        # Note: WholesaleSelectionHistory for purchases is now created in wholesale_receipt function
                        # to ensure it only happens when receipts are actually generated

                    elif action == 'return':
                        # Handle return logic - find existing sales items for this customer and item
                        item.stock += quantity
                        item.save()

                        # Find existing sales items for this customer and item (exclude already returned sales)
                        existing_sales_items = WholesaleSalesItem.objects.filter(
                            sales__wholesale_customer=customer,
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
                            from store.models import Formulation
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
                        WholesaleSelectionHistory.objects.create(
                            wholesale_customer=customer,
                            user=request.user,
                            item=item,
                            quantity=quantity,
                            action=action,
                            unit_price=item.price,
                        )

                        total_cost -= total_refund_amount

                        # Mark affected wholesale sales as returned and track return information
                        from django.utils import timezone
                        affected_sales = set()
                        for sales_item in existing_sales_items:
                            if sales_item.sales not in affected_sales:
                                affected_sales.add(sales_item.sales)

                        # Update return tracking for affected wholesale sales
                        for sales in affected_sales:
                            if not sales.is_returned:  # Only update if not already marked as returned
                                sales.is_returned = True
                                sales.return_date = timezone.now()
                                sales.return_amount += total_refund_amount
                                sales.return_processed_by = request.user
                                sales.save()

                except WholesaleItem.DoesNotExist:
                    messages.warning(request, 'One of the selected items does not exist.')
                    return redirect('wholesale:select_wholesale_items', pk=pk)

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

            # Handle return processing for registered wholesale customers
            if action == 'return':
                try:
                    wallet = customer.wholesale_customer_wallet
                    # Check if any of the returned items were originally paid with wallet
                    wallet_refund_amount = Decimal('0.00')
                    non_wallet_refund_amount = Decimal('0.00')

                    # Process each returned item to check original payment method
                    for item_id, quantity in zip(item_ids, quantities):
                        item = WholesaleItem.objects.get(id=item_id)
                        item_total = item.price * quantity

                        # Find the most recent wholesale sales item for this item and customer
                        sales_item = WholesaleSalesItem.objects.filter(
                            item=item,
                            sales__wholesale_customer=customer
                        ).order_by('-sales__date').first()

                        if sales_item and sales_item.sales:
                            # Check the payment method from the wholesale receipt
                            receipt = sales_item.sales.wholesale_receipts.first()
                            if receipt:
                                if receipt.payment_method == 'Wallet':
                                    wallet_refund_amount += item_total
                                elif receipt.payment_method == 'Split':
                                    # For split payments, check if wallet was used
                                    wallet_payments = receipt.wholesale_receipt_payments.filter(payment_method='Wallet')
                                    if wallet_payments.exists():
                                        # Calculate proportional wallet refund
                                        total_wallet_paid = sum(p.amount for p in wallet_payments)
                                        wallet_proportion = total_wallet_paid / receipt.total_amount
                                        wallet_refund_amount += item_total * wallet_proportion
                                        non_wallet_refund_amount += item_total * (1 - wallet_proportion)
                                    else:
                                        non_wallet_refund_amount += item_total
                                else:
                                    # Cash, Transfer, or other non-wallet payment
                                    non_wallet_refund_amount += item_total
                            else:
                                # No receipt found, assume non-wallet payment
                                non_wallet_refund_amount += item_total
                        else:
                            # No sales record found, assume non-wallet payment
                            non_wallet_refund_amount += item_total

                    # Only refund to wallet if there was original wallet payment
                    if wallet_refund_amount > 0:
                        wallet.balance += wallet_refund_amount
                        wallet.save()

                        # Create transaction history for wallet refund
                        TransactionHistory.objects.create(
                            wholesale_customer=customer,
                            user=request.user,
                            transaction_type='refund',
                            amount=wallet_refund_amount,
                            description=f'Wallet refund for returned items (₦{wallet_refund_amount})'
                        )
                        messages.success(request, f'Return processed. ₦{wallet_refund_amount} refunded to wallet.')

                    if non_wallet_refund_amount > 0:
                        # Create transaction history for non-wallet refund (informational)
                        TransactionHistory.objects.create(
                            wholesale_customer=customer,
                            user=request.user,
                            transaction_type='refund',
                            amount=Decimal('0.00'),  # No wallet credit for non-wallet payments
                            description=f'Return processed for non-wallet payment (₦{non_wallet_refund_amount}) - No wallet refund'
                        )
                        messages.info(request, f'₦{non_wallet_refund_amount} from non-wallet payments returned (no wallet refund).')
                        messages.success(request, f'Return processed for ₦{abs(total_cost)}. Amount refunded to wallet.')
                except WholesaleCustomerWallet.DoesNotExist:
                    messages.warning(request, 'Customer does not have a wallet.')
                    return redirect('wholesale:select_wholesale_items', pk=pk)

            # Note: Wallet deduction for purchases now happens during receipt generation, not here

            # Store payment method and status in session for receipt generation
            payment_method = request.POST.get('payment_method', 'Cash')
            status = request.POST.get('status', 'Paid')
            request.session['payment_method'] = payment_method
            request.session['payment_status'] = status

            action_message = 'added to cart' if action == 'purchase' else 'returned successfully'
            messages.success(request, f'Action completed: Items {action_message}.')
            return redirect('wholesale:wholesale_cart')

        return render(request, 'partials/select_wholesale_items.html', {
            'customer': customer,
            'items': items,
            'wallet_balance': wallet_balance,
            'action': action
        })
    else:
        return redirect('store:index')





@login_required
def wholesale_cart(request):
    if request.user.is_authenticated:
        cart_items = WholesaleCart.objects.select_related('item').filter(user=request.user)

        # Check if cart is empty and cleanup session if needed
        from store.cart_utils import auto_cleanup_empty_cart_session
        cleanup_summary = auto_cleanup_empty_cart_session(request, 'wholesale')
        if cleanup_summary:
            logger.info(f"Empty wholesale cart session cleaned up on cart view: {cleanup_summary}")

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

        # Get wholesale customer from user-specific session if it exists (same as retail)
        from userauth.session_utils import get_user_customer_id
        wholesale_customer = None
        customer_id = get_user_customer_id(request)
        if customer_id:
            try:
                wholesale_customer = WholesaleCustomer.objects.get(id=customer_id)
            except WholesaleCustomer.DoesNotExist:
                pass

        # Define available payment methods and statuses
        payment_methods = ["Cash", "Wallet", "Transfer"]
        statuses = ["Paid", "Unpaid"]

        return render(request, 'wholesale/wholesale_cart.html', {
            'cart_items': cart_items,
            'total_discount': total_discount,
            'total_price': total_price,
            'total_discounted_price': total_discounted_price,
            'final_total': final_total,
            'wholesale_customer': wholesale_customer,
            'payment_methods': payment_methods,
            'statuses': statuses,
        })
    else:
        return redirect('store:index')



@login_required
def update_wholesale_cart_quantity(request, pk):
    if request.user.is_authenticated:
        # Ensure user can only update their own cart items
        cart_item = get_object_or_404(WholesaleCart, id=pk, user=request.user)
        if request.method == 'POST':
            quantity_to_return = Decimal(request.POST.get('quantity', 0))
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
                    cleanup_summary = auto_cleanup_empty_cart_session(request, 'wholesale')
                    if cleanup_summary:
                        logger.info(f"Wholesale cart became empty after item removal, session cleaned up: {cleanup_summary}")

                messages.success(request, f"{quantity_to_return} {cart_item.item.unit} of {cart_item.item.name} removed from cart.")

        return redirect('wholesale:wholesale_cart')
    else:
        return redirect('store:index')




@login_required
def clear_wholesale_cart(request):
    if request.user.is_authenticated:
        if request.method == 'POST':
            try:
                with transaction.atomic():
                    # Get cart items specifically for wholesale
                    cart_items = WholesaleCart.objects.filter(user=request.user)

                    if not cart_items.exists():
                        messages.info(request, 'Cart is already empty.')
                        return redirect('wholesale:wholesale_cart')

                    # Get wholesale customer from user-specific session if it exists
                    from userauth.session_utils import get_user_customer_id
                    customer_id = get_user_customer_id(request)
                    current_wholesale_customer = None
                    if customer_id:
                        try:
                            current_wholesale_customer = WholesaleCustomer.objects.get(id=customer_id)
                        except WholesaleCustomer.DoesNotExist:
                            pass

                    # Check for completed sales (those WITH receipts) for the current wholesale customer
                    completed_sales = Sales.objects.filter(
                        user=request.user,
                        wholesale_customer=current_wholesale_customer,
                        wholesale_receipts__isnull=False  # Sales that have wholesale receipts (completed transactions)
                    ).distinct()

                    # Check for pending sales (those WITHOUT receipts) for the current wholesale customer
                    pending_sales = Sales.objects.filter(
                        user=request.user,
                        wholesale_customer=current_wholesale_customer,
                        wholesale_receipts__isnull=True  # Sales without wholesale receipts (incomplete transactions)
                    ).distinct()

                    # Always clear cart (preserve existing functionality) but only process refunds when receipts exist

                    # Calculate total amount to refund based on actual receipts (not cart items)
                    total_refund = Decimal('0.00')
                    if completed_sales.exists():
                        # Only calculate refunds when there are completed sales with receipts
                        for sale in completed_sales:
                            # Only refund wallet payments (as per business logic)
                            receipts = sale.wholesale_receipts.filter(payment_method='Wallet')
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
                    if current_wholesale_customer and total_refund > 0:
                        try:
                            wallet = current_wholesale_customer.wholesale_customer_wallet
                            if wallet:
                                # For registered wholesale customers, provide automatic wallet refund when cart is cleared
                                wallet.balance += total_refund
                                wallet.save()

                                # Create transaction history noting the cart clear with wallet refund
                                TransactionHistory.objects.create(
                                    wholesale_customer=current_wholesale_customer,
                                    user=request.user,
                                    transaction_type='refund',
                                    amount=total_refund,
                                    description=f'Cart cleared - Refund for returned items (₦{total_refund})'
                                )
                                messages.success(
                                    request,
                                    f'Cart cleared for customer {current_wholesale_customer.name}. Return value ₦{total_refund} refunded to wallet.'
                                )
                        except WholesaleCustomerWallet.DoesNotExist:
                            messages.warning(
                                request,
                                f'Wallet not found for customer {current_wholesale_customer.name}'
                            )

                    # Always clear cart items (preserve existing functionality)
                    cart_items.delete()

                    # Comprehensive cart session cleanup after clearing
                    from store.cart_utils import cleanup_cart_session_after_receipt
                    cleanup_summary = cleanup_cart_session_after_receipt(request, 'wholesale')
                    logger.info(f"Wholesale cart session cleanup after cart clear: {cleanup_summary}")

                    # Clean up orphaned sales records without receipts
                    if pending_sales.exists():
                        for sale in pending_sales:
                            # Delete associated sales items first
                            sale.wholesale_sales_items.all().delete()
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
                return redirect('wholesale:wholesale_cart')

        return redirect('wholesale:wholesale_cart')
    return redirect('store:index')



@transaction.atomic
@login_required
def wholesale_receipt(request):
    if request.user.is_authenticated:
        # IMPORTANT: Get payment method and status from POST data
        # These are the values selected by the user in the payment modal
        payment_method = request.POST.get('payment_method')
        status = request.POST.get('status')

        # Dump all POST data for debugging
        print("\n\n==== ALL POST DATA: =====")
        for key, value in request.POST.items():
            print(f"  {key}: {value}")
        print(f"\nDirect access - Payment Method: {payment_method}, Status: {status}\n")

        buyer_name = request.POST.get('buyer_name', '')
        buyer_address = request.POST.get('buyer_address', '')

        # Check if this is a split payment
        payment_type = request.POST.get('payment_type', 'single')

        if payment_type == 'split':
            # This is a split payment
            payment_method = 'Split'
            payment_method_1 = request.POST.get('payment_method_1')
            payment_method_2 = request.POST.get('payment_method_2')
            payment_amount_1 = Decimal(request.POST.get('payment_amount_1', '0'))
            payment_amount_2 = Decimal(request.POST.get('payment_amount_2', '0'))
            status = request.POST.get('split_status', 'Paid')

            # Validate the payment methods and amounts
            if not payment_method_1 or not payment_method_2:
                messages.error(request, "Please select both payment methods for split payment.")
                return redirect('wholesale:wholesale_cart')

            if payment_amount_1 <= 0:
                messages.error(request, "First payment amount must be greater than zero.")
                return redirect('wholesale:wholesale_cart')
        else:
            # This is a single payment
            payment_method = request.POST.get('payment_method')
            status = request.POST.get('status')
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

        cart_items = WholesaleCart.objects.filter(user=request.user)
        if not cart_items.exists():
            messages.warning(request, "No items in the cart.")
            return redirect('wholesale:wholesale_cart')

        total_price, total_discount = 0, 0

        for cart_item in cart_items:
            subtotal = cart_item.item.price * cart_item.quantity
            total_price += subtotal
            total_discount += getattr(cart_item, 'discount_amount', 0)

        total_discounted_price = total_price - total_discount
        final_total = total_discounted_price if total_discount > 0 else total_price

        # Get customer ID from user-specific session if it exists (same pattern as retail)
        from userauth.session_utils import get_user_customer_id
        customer_id = get_user_customer_id(request)
        wholesale_customer = None
        if customer_id:
            try:
                wholesale_customer = WholesaleCustomer.objects.get(id=customer_id)
            except WholesaleCustomer.DoesNotExist:
                pass

        # Always create a new Sales instance to avoid conflicts
        sales = Sales.objects.create(
            user=request.user,
            wholesale_customer=wholesale_customer,
            total_amount=final_total
        )
        


        try:
            receipt = WholesaleReceipt.objects.filter(sales=sales).first()
            if not receipt:
                # Set default values based on customer presence if not provided
                if not payment_method and payment_type != 'split':
                    # Default payment method is Wallet for registered customers, Cash for walk-in
                    if sales.wholesale_customer:  # If this is a registered customer
                        payment_method = "Wallet"  # Default for registered customers
                    else:  # For walk-in customers
                        payment_method = "Cash"  # Default for walk-in customers

                if not status:
                    # Default status is "Paid" for all customers
                    status = "Paid"

                print(f"After initial defaults - Payment Type: {payment_type}, Payment Method: {payment_method}, Status: {status}")

                # Ensure payment_method and status have valid values
                if payment_method not in ["Cash", "Wallet", "Transfer", "Split"]:
                    if sales.wholesale_customer:
                        payment_method = "Wallet"  # Default for registered customers
                    else:
                        payment_method = "Cash"  # Default for walk-in customers

                if status not in ["Paid", "Partially Paid", "Unpaid"]:
                    # Default status based on customer type
                    if sales.wholesale_customer:
                        status = "Paid"  # Registered customers default to Paid
                    else:
                        status = "Paid"  # Walk-in customers also default to Paid

                # Force the values for debugging purposes
                print(f"\n==== FORCING VALUES FOR RECEIPT =====")
                print(f"Customer: {sales.wholesale_customer}")
                print(f"Payment Method: {payment_method}")
                print(f"Status: {status}\n")

                # Generate a unique receipt ID using uuid
                import uuid
                receipt_id = str(uuid.uuid4())[:5]  # Use first 5 characters of a UUID

                # Create the receipt
                receipt = WholesaleReceipt.objects.create(
                    sales=sales,
                    receipt_id=receipt_id,
                    total_amount=final_total,
                    wholesale_customer=sales.wholesale_customer,
                    buyer_name=buyer_name if not sales.wholesale_customer else sales.wholesale_customer.name,
                    buyer_address=buyer_address if not sales.wholesale_customer else sales.wholesale_customer.address,
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
                    has_customer = sales.wholesale_customer is not None
                    if has_customer:
                        # Only deduct the amount specified for wallet payment method
                        if payment_method_1 == 'Wallet':
                            wallet_amount = Decimal(str(payment_amount_1))
                            # Deduct from customer's wallet
                            try:
                                wallet = WholesaleCustomerWallet.objects.get(customer=sales.wholesale_customer)
                                # Check if wallet will go negative
                                wallet_balance_before = wallet.balance
                                # Allow negative balance
                                wallet.balance -= wallet_amount
                                wallet.save()

                                # Check if wallet went negative and set flag
                                if wallet_balance_before >= 0 and wallet.balance < 0:
                                    receipt.wallet_went_negative = True
                                    receipt.save()

                                # Create transaction history
                                TransactionHistory.objects.create(
                                    wholesale_customer=sales.wholesale_customer,
                                    user=request.user,
                                    transaction_type='purchase',
                                    amount=wallet_amount,
                                    description=f'Purchase payment from wallet (Receipt ID: {receipt.receipt_id})'
                                )

                                print(f"Deducted {wallet_amount} from customer {sales.wholesale_customer.name}'s wallet for first payment")
                                # Inform if balance is negative
                                if wallet.balance < 0:
                                    print(f"Info: Customer {sales.wholesale_customer.name} now has a negative wallet balance of {wallet.balance}")
                                    messages.info(request, f"Customer {sales.wholesale_customer.name} now has a negative wallet balance of {wallet.balance}")
                            except WholesaleCustomerWallet.DoesNotExist:
                                print(f"Error: Wallet not found for customer {sales.wholesale_customer.name}")
                                messages.error(request, f"Error: Wallet not found for customer {sales.wholesale_customer.name}")

                        if payment_method_2 == 'Wallet':
                            wallet_amount = Decimal(str(payment_amount_2))
                            # Deduct from customer's wallet
                            try:
                                wallet = WholesaleCustomerWallet.objects.get(customer=sales.wholesale_customer)
                                # Check if wallet will go negative
                                wallet_balance_before = wallet.balance
                                # Allow negative balance
                                wallet.balance -= wallet_amount
                                wallet.save()

                                # Check if wallet went negative and set flag
                                if wallet_balance_before >= 0 and wallet.balance < 0:
                                    receipt.wallet_went_negative = True
                                    receipt.save()

                                # Create transaction history
                                TransactionHistory.objects.create(
                                    wholesale_customer=sales.wholesale_customer,
                                    transaction_type='purchase',
                                    amount=wallet_amount,
                                    description=f'Purchase payment from wallet (Receipt ID: {receipt.receipt_id})'
                                )

                                print(f"Deducted {wallet_amount} from customer {sales.wholesale_customer.name}'s wallet for second payment")
                                # Inform if balance is negative
                                if wallet.balance < 0:
                                    print(f"Info: Customer {sales.wholesale_customer.name} now has a negative wallet balance of {wallet.balance}")
                                    messages.info(request, f"Customer {sales.wholesale_customer.name} now has a negative wallet balance of {wallet.balance}")
                            except WholesaleCustomerWallet.DoesNotExist:
                                print(f"Error: Wallet not found for customer {sales.wholesale_customer.name}")
                                messages.error(request, f"Error: Wallet not found for customer {sales.wholesale_customer.name}")

                    # Create the first payment
                    WholesaleReceiptPayment.objects.create(
                        receipt=receipt,
                        amount=payment_amount_1,
                        payment_method=payment_method_1,
                        status=status,
                        date=datetime.now()
                    )

                    # Create the second payment
                    WholesaleReceiptPayment.objects.create(
                        receipt=receipt,
                        amount=payment_amount_2,
                        payment_method=payment_method_2,
                        status=status,
                        date=datetime.now()
                    )

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

                # Handle wallet deduction and transaction history for non-split payments
                if sales.wholesale_customer and payment_type != 'split':
                    if receipt.payment_method == 'Wallet':
                        # For wallet payments, deduct from wallet and create transaction history
                        try:
                            wallet = WholesaleCustomerWallet.objects.get(customer=sales.wholesale_customer)
                            # Check if wallet will go negative
                            wallet_balance_before = wallet.balance
                            wallet.balance -= sales.total_amount
                            wallet.save()

                            # Check if wallet went negative and set flag
                            if wallet_balance_before >= 0 and wallet.balance < 0:
                                receipt.wallet_went_negative = True
                                receipt.save()

                            # Create transaction history entry
                            from customer.models import TransactionHistory
                            TransactionHistory.objects.create(
                                wholesale_customer=sales.wholesale_customer,
                                user=request.user,
                                transaction_type='purchase',
                                amount=sales.total_amount,
                                description=f'Purchase payment from wallet (Receipt ID: {receipt.receipt_id})'
                            )
                        except WholesaleCustomerWallet.DoesNotExist:
                            messages.warning(request, f'Wallet not found for customer {sales.wholesale_customer.name}')
                    else:
                        # For non-wallet payments, only create transaction history
                        from customer.models import TransactionHistory
                        TransactionHistory.objects.create(
                            wholesale_customer=sales.wholesale_customer,
                            user=request.user,
                            transaction_type='purchase',
                            amount=sales.total_amount,
                            description=f'Purchase payment via {receipt.payment_method} (Receipt ID: {receipt.receipt_id})'
                        )
                    # Transaction history for wallet payments is already created in select_wholesale_items
                    # No need to create duplicate transaction history here
        except Exception as e:
            print(f"Error processing receipt: {e}")
            messages.error(request, "An error occurred while processing the receipt.")
            return redirect('wholesale:wholesale_cart')

        for cart_item in cart_items:
            WholesaleSalesItem.objects.get_or_create(
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
                from store.models import Formulation
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

            # Create WholesaleSelectionHistory entry for purchase (only when receipt is generated)
            if sales.wholesale_customer:
                from store.models import WholesaleSelectionHistory
                WholesaleSelectionHistory.objects.create(
                    wholesale_customer=sales.wholesale_customer,
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

        # Store cart items for receipt rendering before clearing
        cart_items_for_receipt = []
        for cart_item in cart_items:
            cart_items_for_receipt.append({
                'name': cart_item.item.name,
                'brand': cart_item.item.brand,
                'dosage_form': cart_item.item.dosage_form,
                'unit': cart_item.item.unit,
                'quantity': cart_item.quantity,
                'price': cart_item.item.price,
                'discount_amount': cart_item.discount_amount,
                'subtotal': cart_item.item.price * cart_item.quantity,
                'discounted_subtotal': (cart_item.item.price * cart_item.quantity) - cart_item.discount_amount
            })

        daily_sales_data = get_daily_sales()
        monthly_sales_data = get_monthly_sales_with_expenses()

        wholesale_sales_items = sales.wholesale_sales_items.all()

        payment_methods = ["Cash", "Wallet", "Transfer"]
        statuses = ["Paid", "Unpaid"]

        # Double-check the receipt values one more time before rendering
        receipt.refresh_from_db()
        print(f"\n==== FINAL RECEIPT VALUES BEFORE RENDERING =====")
        print(f"Receipt ID: {receipt.receipt_id}")
        print(f"Payment Method: {receipt.payment_method}")
        print(f"Status: {receipt.status}\n")

        # Set appropriate payment method and status based on customer type and payment type
        has_customer = sales.wholesale_customer is not None

        if has_customer and payment_type != 'split':
            # For registered customers with single payment, default to Wallet if not specified
            if not receipt.payment_method or receipt.payment_method == 'Cash':
                print(f"Setting payment method to Wallet for customer {receipt.wholesale_customer.name}")
                receipt.payment_method = 'Wallet'
                receipt.save()

            # Only set status to 'Paid' if it's not already set (preserve user selection)
            if not receipt.status:
                print(f"Setting default status to Paid for customer {receipt.wholesale_customer.name}")
                receipt.status = 'Paid'
                receipt.save()

            receipt.refresh_from_db()
        elif has_customer and payment_type == 'split':
            # For split payments with registered customers, ensure the payment method is 'Split'
            if receipt.payment_method != 'Split':
                print(f"Setting payment method to Split for customer {receipt.wholesale_customer.name}")
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
            request.session['wholesale_split_payment_details'] = split_payment_details
            request.session['wholesale_split_payment_receipt_id'] = receipt.receipt_id

        # Fetch receipt payments directly
        wholesale_receipt_payments = receipt.wholesale_receipt_payments.all() if receipt.payment_method == 'Split' else None

        # Debug: Check the final state before rendering
        print(f"\n=== FINAL DEBUG BEFORE TEMPLATE RENDERING ===")
        print(f"Final receipt.wholesale_customer: {receipt.wholesale_customer}")
        print(f"Final sales.wholesale_customer: {sales.wholesale_customer}")
        
        # Force refresh to make sure we have latest data
        receipt.refresh_from_db()
        sales.refresh_from_db()
        
        print(f"After refresh - receipt.wholesale_customer: {receipt.wholesale_customer}")
        print(f"After refresh - sales.wholesale_customer: {sales.wholesale_customer}")
        
        if receipt.wholesale_customer:
            print(f"Customer name should display: {receipt.wholesale_customer.name}")
        else:
            print("WARNING: receipt.wholesale_customer is None - will show 'Walk-in Customer'")
        
        print("="*50)

        # Render to the wholesale_receipt template
        response = render(request, 'wholesale/wholesale_receipt.html', {
            'receipt': receipt,
            'wholesale_sales_items': wholesale_sales_items,
            'total_price': total_price,
            'total_discount': total_discount,
            'total_discounted_price': total_discounted_price,
            'daily_sales': daily_sales_data,
            'monthly_sales': monthly_sales_data,
            'logs': DispensingLog.objects.filter(user=request.user),
            'payment_methods': payment_methods,
            'statuses': statuses,
            'split_payment_details': split_payment_details,
            'wholesale_receipt_payments': wholesale_receipt_payments,
            'payment_type': payment_type,
            'sales': sales,  # Add sales object for template access
        })

        # Now clear the cart after rendering the receipt
        cart_items.delete()

        # Clear session data AFTER receipt is fully created and rendered
        # This ensures wholesale_customer_id is available during receipt creation
        from store.cart_utils import cleanup_cart_session_after_receipt
        cleanup_summary = cleanup_cart_session_after_receipt(request, 'wholesale')
        logger.info(f"Wholesale cart session cleanup after receipt: {cleanup_summary}")

        print(f"Debug - Session keys after receipt cleanup: {list(request.session.keys())}")

        return response
    else:
        return redirect('store:index')






@transaction.atomic
@login_required
def return_wholesale_items_for_customer(request, pk):
    if request.user.is_authenticated:
        customer = get_object_or_404(WholesaleCustomer, id=pk)
        items = WholesaleItem.objects.all().order_by('name')

        # Fetch wallet balance
        wallet_balance = Decimal('0.0')
        try:
            wallet_balance = customer.wholesale_customer_wallet.balance
        except WholesaleCustomerWallet.DoesNotExist:
            messages.warning(request, 'This customer does not have an associated wallet.')

        if request.method == 'POST':
            item_ids = request.POST.getlist('item_ids', [])
            quantities = request.POST.getlist('quantities', [])
            units = request.POST.getlist('units', [])

            if len(item_ids) != len(quantities):
                messages.warning(request, 'Mismatch between selected items and quantities.')
                return redirect('wholesale:select_wholesale_items', pk=pk)

            total_refund = Decimal('0.0')

            # Create a new Sales record for this transaction
            # Instead of get_or_create, we always create a new record to avoid the MultipleObjectsReturned error
            sales = Sales.objects.create(
                user=request.user,
                wholesale_customer=customer,
                total_amount=Decimal('0.0')
            )

            # Fetch or create a Receipt
            receipt = WholesaleReceipt.objects.filter(wholesale_customer=customer, sales=sales).first()

            if not receipt:
                # Get payment method and status from form
                payment_method = request.POST.get('payment_method', 'Cash')
                status = request.POST.get('status', 'Paid')

                # Store in session for later use in receipt generation
                request.session['payment_method'] = payment_method
                request.session['payment_status'] = status

                receipt = WholesaleReceipt.objects.create(
                    wholesale_customer=customer,
                    sales=sales,
                    total_amount=Decimal('0.0'),
                    buyer_name=customer.name,
                    buyer_address=customer.address,
                    date=datetime.now(),
                    payment_method=payment_method,
                    status=status
                )

            for i, item_id in enumerate(item_ids):
                try:
                    item = WholesaleItem.objects.get(id=item_id)
                    quantity = Decimal(quantities[i])
                    unit = units[i] if i < len(units) else item.unit

                    # Handle return logic
                    item.stock += quantity
                    item.save()

                    try:
                        sales_item = WholesaleSalesItem.objects.get(sales=sales, item=item)

                        if sales_item.quantity < quantity:
                            messages.warning(request, f"Cannot return more {item.name} than purchased.")
                            return redirect('wholesale:wholesale_customers')

                        sales_item.quantity -= quantity
                        if sales_item.quantity == 0:
                            sales_item.delete()
                        else:
                            sales_item.save()

                        # Calculate refund amount considering discounts
                        base_refund = (item.price * quantity)
                        # Calculate proportional discount for the return
                        proportional_discount = Decimal('0')
                        if sales_item.discount_amount > 0 and sales_item.quantity > 0:
                            discount_per_unit = sales_item.discount_amount / (sales_item.quantity + quantity)  # Include returned quantity
                            proportional_discount = discount_per_unit * quantity

                        refund_amount = base_refund - proportional_discount
                        sales.total_amount -= refund_amount
                        sales.save()

                        DispensingLog.objects.create(
                            user=request.user,
                            name=item.name,
                            unit=unit,
                            quantity=quantity,
                            amount=refund_amount,  # This now includes discount consideration
                            discount_amount=proportional_discount,
                            status='Partially Returned' if sales_item.quantity > 0 else 'Returned'  # Status based on remaining quantity
                        )

                        # Log Item Selection History (Return)
                        WholesaleSelectionHistory.objects.create(
                            wholesale_customer=customer,
                            user=request.user,
                            item=item,
                            quantity=quantity,
                            action='return',
                            unit_price=item.price,
                        )

                        total_refund += refund_amount

                        # Update the receipt
                        receipt.total_amount -= refund_amount
                        receipt.save()

                    except WholesaleSalesItem.DoesNotExist:
                        messages.warning(request, f"Item {item.name} is not part of the sales.")
                        return redirect('wholesale:select_wholesale_items', pk=pk)

                except WholesaleItem.DoesNotExist:
                    messages.warning(request, 'One of the selected items does not exist.')
                    return redirect('wholesale:select_wholesale_items', pk=pk)

            # Get payment method and status from form
            payment_method = request.POST.get('payment_method', 'Cash')
            status = request.POST.get('status', 'Paid')

            # Store in session for later use in receipt generation
            request.session['payment_method'] = payment_method
            request.session['payment_status'] = status

            # Update receipt with payment method and status
            receipt.payment_method = payment_method
            receipt.status = status
            receipt.save()

            # Note: Wallet refund for registered wholesale customers is now handled in select_wholesale_items function
            messages.success(request, f'Action completed: Items returned successfully. Total refund: ₦{total_refund}')
            return redirect('wholesale:wholesale_cart')

        return render(request, 'partials/select_wholesale_items.html', {
            'customer': customer,
            'items': items,
            'wallet_balance': wallet_balance
        })
    else:
        return redirect('store:index')


def wholesale_receipt_list(request):
    if request.user.is_authenticated:
        receipts = WholesaleReceipt.objects.all().order_by('-date')  # Only wholesale receipts
        return render(request, 'partials/wholesale_receipt_list.html', {'receipts': receipts})
    else:
        return redirect('store:index')


def search_wholesale_receipts(request):
    if request.user.is_authenticated:
        from utils.date_utils import filter_queryset_by_date, get_date_filter_context

        # Get the date query from the GET request
        date_context = get_date_filter_context(request, 'date')
        date_query = date_context['date_string']

        receipts = WholesaleReceipt.objects.all()
        if date_query and date_context['is_valid_date']:
            receipts = filter_queryset_by_date(receipts, 'date', date_query)
        elif date_query and not date_context['is_valid_date']:
            print(f"Invalid date format: {date_query}")

        # Order receipts by date
        receipts = receipts.order_by('-date')

        return render(request, 'wholesale/search_wholesale_receipts.html', {'receipts': receipts})
    else:
        return redirect('store:index')



@login_required
def wholesale_receipt_detail(request, receipt_id):
    if request.user.is_authenticated:
        try:
            # Retrieve the existing receipt
            receipt = get_object_or_404(WholesaleReceipt, receipt_id=receipt_id)
        except Exception as e:
            logger.error(f"Error retrieving wholesale receipt {receipt_id}: {e}")
            messages.error(request, f"Error retrieving receipt: {receipt_id}")
            return redirect('wholesale:wholesale_receipt_list')

        # Preserve the receipt status as set by the user

        # Retrieve sales and sales items linked to the receipt
        sales = receipt.sales
        sales_items = sales.wholesale_sales_items.all() if sales else []

        # Calculate totals for the receipt
        total_price = sum(item.subtotal for item in sales_items)
        total_discount = Decimal('0.0')  # Modify if a discount amount is present in `Receipt`
        total_discounted_price = total_price - total_discount

        # Update and save the receipt with calculated totals
        receipt.total_amount = total_discounted_price
        receipt.total_discount = total_discount
        receipt.save()

        # If this is a split payment receipt but has no payment records, create them
        if receipt.payment_method == 'Split' and not receipt.wholesale_receipt_payments.exists():
            print(f"Creating payment records for split payment wholesale receipt {receipt.receipt_id}")

            # Check if we have stored split payment details for this receipt
            stored_details = None
            if request.session.get('wholesale_split_payment_receipt_id') == receipt.receipt_id:
                stored_details = request.session.get('wholesale_split_payment_details')
                print(f"Found stored wholesale split payment details: {stored_details}")

            if stored_details:
                # Use the stored payment details
                payment_method_1 = stored_details.get('payment_method_1')
                payment_method_2 = stored_details.get('payment_method_2')
                payment_amount_1 = Decimal(str(stored_details.get('payment_amount_1', 0)))
                payment_amount_2 = Decimal(str(stored_details.get('payment_amount_2', 0)))

                # Create the payment records using the stored details
                WholesaleReceiptPayment.objects.create(
                    receipt=receipt,
                    amount=payment_amount_1,
                    payment_method=payment_method_1,
                    status='Paid',
                    date=receipt.date
                )
                WholesaleReceiptPayment.objects.create(
                    receipt=receipt,
                    amount=payment_amount_2,
                    payment_method=payment_method_2,
                    status='Paid',
                    date=receipt.date
                )
                print(f"Created wholesale payment records using stored details: {payment_method_1}: {payment_amount_1}, {payment_method_2}: {payment_amount_2}")
            else:
                # No stored details, use reasonable defaults based on customer type
                if receipt.wholesale_customer:
                    # For registered customers, it's more likely they used their wallet
                    # Assume 70% wallet, 30% cash or transfer as a reasonable default
                    wallet_amount = receipt.total_amount * Decimal('0.7')
                    cash_amount = receipt.total_amount - wallet_amount

                    # Create the payment records
                    WholesaleReceiptPayment.objects.create(
                        receipt=receipt,
                        amount=wallet_amount,
                        payment_method='Wallet',
                        status='Paid',
                        date=receipt.date
                    )
                    WholesaleReceiptPayment.objects.create(
                        receipt=receipt,
                        amount=cash_amount,
                        payment_method='Cash',
                        status='Paid',
                        date=receipt.date
                    )
                    print(f"Created payment records for registered wholesale customer: Wallet: {wallet_amount}, Cash: {cash_amount}")
                else:
                    # For walk-in customers, it's more likely they used cash and transfer
                    # Assume 70% cash, 30% transfer as a reasonable default
                    cash_amount = receipt.total_amount * Decimal('0.7')
                    transfer_amount = receipt.total_amount - cash_amount

                    # Create the payment records
                    WholesaleReceiptPayment.objects.create(
                        receipt=receipt,
                        amount=cash_amount,
                        payment_method='Cash',
                        status='Paid',
                        date=receipt.date
                    )
                    WholesaleReceiptPayment.objects.create(
                        receipt=receipt,
                        amount=transfer_amount,
                        payment_method='Transfer',
                        status='Paid',
                        date=receipt.date
                    )
                    print(f"Created payment records for walk-in wholesale customer: Cash: {cash_amount}, Transfer: {transfer_amount}")

        payment_methods = ["Cash", "Wallet", "Transfer"]
        statuses = ["Paid", "Unpaid"]

        # Fetch receipt payments directly
        wholesale_receipt_payments = receipt.wholesale_receipt_payments.all() if receipt.payment_method == 'Split' else None

        # Debug information
        print(f"\n==== WHOLESALE RECEIPT DETAIL DEBUG =====")
        print(f"Receipt ID: {receipt.receipt_id}")
        print(f"Payment Method: {receipt.payment_method}")
        print(f"Has wholesale_receipt_payments: {wholesale_receipt_payments is not None}")
        if wholesale_receipt_payments:
            print(f"Number of wholesale_receipt_payments: {wholesale_receipt_payments.count()}")
            for i, payment in enumerate(wholesale_receipt_payments):
                print(f"Payment {i+1}: {payment.payment_method} - {payment.amount}")

        # Create split payment details if receipt payments exist
        split_payment_details = None
        if wholesale_receipt_payments and wholesale_receipt_payments.count() > 0:
            payments = list(wholesale_receipt_payments)
            if wholesale_receipt_payments.count() == 2:
                split_payment_details = {
                    'payment_method_1': payments[0].payment_method,
                    'payment_amount_1': payments[0].amount,
                    'payment_method_2': payments[1].payment_method,
                    'payment_amount_2': payments[1].amount,
                }
            elif wholesale_receipt_payments.count() == 1:
                # Handle case with only one payment record
                split_payment_details = {
                    'payment_method_1': payments[0].payment_method,
                    'payment_amount_1': payments[0].amount,
                    'payment_method_2': 'Unknown',
                    'payment_amount_2': receipt.total_amount - payments[0].amount,
                }

            print(f"Created split_payment_details: {split_payment_details}")

        return render(request, 'partials/wholesale_receipt_detail.html', {
            'receipt': receipt,
            'sales': sales,
            'sales_items': sales_items,
            'total_price': total_price,
            'total_discount': total_discount,
            'total_discounted_price': total_discounted_price,
            'payment_methods': payment_methods,
            'statuses': statuses,
            'user': request.user,
            'wholesale_receipt_payments': wholesale_receipt_payments,
            'split_payment_details': split_payment_details,
            'payment_type': 'split' if receipt.payment_method == 'Split' else 'single',
        })
    else:
        return redirect('store:index')



def get_wholesale_sales_by_user(date_from=None, date_to=None):
    # Filter wholesale sales by date range if provided
    filters = Q()
    if date_from:
        filters &= Q(date__gte=date_from)
    if date_to:
        filters &= Q(date__lte=date_to)

    # Aggregating wholesale sales for each user
    wholesales_by_user = (
        Sales.objects.filter(filters)
        .filter(wholesale_sales_items__isnull=False)  # Ensure only wholesale sales are considered
        .values('user__username')  # Group by user
        .annotate(
            total_wholesale_sales=Sum('total_amount'),  # Sum of total amounts
            total_items=Sum(F('wholesale_sales_items__quantity'))  # Sum of all quantities sold
        )
        .order_by('-total_wholesale_sales')  # Sort by total sales in descending order
    )
    return wholesales_by_user



@user_passes_test(is_admin_or_manager)
def wholesales_by_user(request):
    if request.user.is_authenticated:
        # Get the date range from the GET request
        date_from = request.GET.get('date_from')
        date_to = request.GET.get('date_to')

        # Parse dates if provided
        date_from = datetime.strptime(date_from, '%Y-%m-%d').date() if date_from else None
        date_to = datetime.strptime(date_to, '%Y-%m-%d').date() if date_to else None

        # Fetch wholesale sales data
        wholesale_user_sales = get_wholesale_sales_by_user(date_from=date_from, date_to=date_to)

        context = {
            'wholesale_user_sales': wholesale_user_sales,
            'date_from': date_from,
            'date_to': date_to,
        }
        return render(request, 'partials/wholesales_by_user.html', context)
    else:
        return redirect('store:index')


@login_required
def search_wholesale_items_for_procurement(request):
    """API endpoint for searching wholesale items for procurement"""
    query = request.GET.get('q', '')
    if query and len(query) >= 2:
        # Search for items in both WholesaleItem and StoreItem models
        wholesale_items = WholesaleItem.objects.filter(
            Q(name__icontains=query) |
            Q(brand__icontains=query) |
            Q(dosage_form__icontains=query)
        ).order_by('name')[:10]

        store_items = StoreItem.objects.filter(
            Q(name__icontains=query) |
            Q(brand__icontains=query) |
            Q(dosage_form__icontains=query)
        ).order_by('name')[:10]

        # Combine results
        results = []

        # Add WholesaleItem results
        for item in wholesale_items:
            results.append({
                'id': f'wholesale_{item.id}',
                'name': item.name,
                'brand': item.brand or '',
                'dosage_form': item.dosage_form or '',
                'unit': item.unit,
                'cost_price': float(item.cost),
                'markup': float(item.markup) if item.markup else 0,
                'expiry_date': item.exp_date.isoformat() if item.exp_date else '',
                'source': 'wholesale'
            })

        # Add StoreItem results
        for item in store_items:
            results.append({
                'id': f'store_{item.id}',
                'name': item.name,
                'brand': item.brand or '',
                'dosage_form': item.dosage_form or '',
                'unit': item.unit,
                'cost_price': float(item.cost_price),
                'markup': 0,  # Default markup for store items
                'expiry_date': item.expiry_date.isoformat() if item.expiry_date else '',
                'source': 'store'
            })

        return JsonResponse({'results': results})
    else:
        return JsonResponse({'results': []})


@login_required
def transfer_multiple_wholesale_items(request):
    """View for transferring multiple wholesale items at once"""
    if request.user.is_authenticated:
        if request.method == "GET":
            search_query = request.GET.get("search", "").strip()
            if search_query:
                wholesale_items = WholesaleItem.objects.filter(
                    Q(name__icontains=search_query) | 
                    Q(brand__icontains=search_query)
                ).distinct().order_by('name')
            else:
                wholesale_items = WholesaleItem.objects.all().order_by('name')

            # Check if there are any items to display
            if not wholesale_items.exists():
                messages.info(request, "No items found in wholesale. Please add items to wholesale first.")

            # Get unit choices from the UNIT constant
            unit_choices = UNIT

            # If this is an HTMX request triggered by search, return only the table body
            if request.headers.get("HX-Request") and "search" in request.GET:
                return render(request, "partials/_wholesale_items_table.html", {
                    "wholesale_items": wholesale_items,
                    "unit_choices": unit_choices
                })

            return render(request, "wholesale/transfer_multiple_wholesale_items.html", {
                "wholesale_items": wholesale_items,
                "unit_choices": unit_choices
            })

        elif request.method == "POST":
            processed_items = []
            errors = []
            wholesale_items = list(WholesaleItem.objects.all())  # materialize the queryset

            for item in wholesale_items:
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
                    if destination not in ['retail', 'store']:
                        errors.append(f"Invalid destination for {item.name}.")
                        continue
                    if transfer_unit not in [unit[0] for unit in UNIT]:
                        errors.append(f"Invalid unit for {item.name}.")
                        continue
                    if unit_conversion <= 0:
                        errors.append(f"Unit conversion must be positive for {item.name}.")
                        continue

                    # Get the original cost
                    original_cost = item.cost

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
                        new_price = Decimal(str(manual_price))
                    else:
                        new_price = cost + (cost * Decimal(markup) / Decimal(100))

                    # Calculate the final destination quantity (source quantity * conversion factor)
                    dest_qty = Decimal(str(qty)) * dest_qty_per_source

                    # Process transfer for this item.
                    if destination == "retail":
                        dest_item, created = Item.objects.get_or_create(
                            name=item.name,
                            brand=item.brand,
                            unit=transfer_unit,  # Use the selected transfer unit
                            defaults={
                                "dosage_form": item.dosage_form,
                                "cost": cost,
                                "price": new_price,
                                "markup": markup,
                                "stock": 0,
                                "exp_date": item.exp_date,
                            }
                        )
                    else:  # destination == "store"
                        dest_item, created = StoreItem.objects.get_or_create(
                            name=item.name,
                            brand=item.brand,
                            unit=transfer_unit,  # Use the selected transfer unit
                            dosage_form=item.dosage_form,
                            cost_price=cost,
                            defaults={
                                "subtotal": cost * dest_qty,
                                "stock": 0,
                                "expiry_date": item.exp_date,
                            }
                        )

                    # Update the destination item's stock and key fields.
                    dest_item.stock += dest_qty
                    if destination == "retail":
                        dest_item.cost = cost
                        if price_override:
                            dest_item.price = new_price
                        else:
                            dest_item.markup = markup
                            dest_item.price = new_price
                    else:  # destination == "store"
                        dest_item.cost_price = cost
                        dest_item.subtotal = dest_item.cost_price * dest_item.stock
                    dest_item.save()

                    # Deduct the transferred quantity from the wholesale item.
                    # Convert qty to Decimal to avoid type mismatch with item.stock
                    item.stock -= Decimal(str(qty))
                    item.save()

                    processed_items.append({
                        "name": item.name,
                        "qty": qty,
                        "destination": destination,
                        "dest_qty": dest_qty,
                        "original_cost": original_cost,
                        "adjusted_cost": cost,
                        "transfer_unit": transfer_unit,
                        "created": created
                    })

            # Display success or error messages.
            if processed_items:
                for item in processed_items:
                    messages.success(
                        request,
                        f"Transferred {item['qty']} of {item['name']} to {item['destination']} as {item['dest_qty']} {item['transfer_unit']}. "
                        f"Item was {'created' if item['created'] else 'updated'} in {item['destination']}. "
                        f"Cost adjusted from {item['original_cost']:.2f} to {item['adjusted_cost']:.2f} per {item['transfer_unit']}."
                    )
            if errors:
                for error in errors:
                    messages.error(request, error)

            # Refresh the wholesale items after processing.
            wholesale_items = WholesaleItem.objects.all()

            # Get unit choices from the UNIT constant
            unit_choices = UNIT

            if request.headers.get('HX-request'):
                return render(request, "partials/_transfer_multiple_wholesale_items.html", {
                    "wholesale_items": wholesale_items,
                    "unit_choices": unit_choices
                })
            else:
                return render(request, "wholesale/transfer_multiple_wholesale_items.html", {
                    "wholesale_items": wholesale_items,
                    "unit_choices": unit_choices
                })

        return JsonResponse({"success": False, "message": "Invalid request method."}, status=400)
    else:
        return redirect('store:index')



@login_required
def exp_date_alert(request):
    if request.user.is_authenticated:
        alert_threshold = timezone.now() + timedelta(days=90)
        expiring_items = WholesaleItem.objects.filter(exp_date__lte=alert_threshold, exp_date__gt=timezone.now())
        expired_items = WholesaleItem.objects.filter(exp_date__lt=timezone.now())

        for expired_item in expired_items:
            if expired_item.stock > 0:
                expired_item.stock = 0
                expired_item.save()

        return render(request, 'partials/wholesale_exp_date_alert.html', {
            'expired_items': expired_items,
            'expiring_items': expiring_items,
        })
    else:
        return redirect('store:index')



@login_required
def register_wholesale_customers(request):
    if request.user.is_authenticated:
        if request.method == 'POST':
            form = WholesaleCustomerForm(request.POST)
            if form.is_valid():
                # Save the customer instance first
                customer = form.save()

                # Check if the wallet already exists
                wallet_exists = WholesaleCustomerWallet.objects.filter(customer=customer).exists()
                if not wallet_exists:
                    # Create the wallet only if it does not exist
                    WholesaleCustomerWallet.objects.create(customer=customer)

                messages.success(request, 'Customer successfully registered')
                if request.headers.get('HX-Request'):
                    return JsonResponse({'success': True, 'message': 'Registration successful'})
                return redirect('wholesale:wholesale_customers')
        else:
            form = WholesaleCustomerForm()

        if request.headers.get('HX-Request'):
            return render(request, 'wholesale/register_wholesale_customers.html', {'form': form})

        return render(request, 'wholesale/register_wholesale_customers.html', {'form': form})
    else:
        return redirect('store:index')



def wholesale_customers(request):
    if request.user.is_authenticated:
        from userauth.permissions import can_manage_wholesale_customers
        if not can_manage_wholesale_customers(request.user):
            messages.error(request, 'You do not have permission to manage wholesale customers.')
            return redirect('store:index')

        # Check if this is a return action request
        action = request.GET.get('action')
        if action == 'return':
            # For return actions, redirect to a return-specific interface
            # For now, we'll show the customer list with a return indicator
            customers = WholesaleCustomer.objects.all().order_by('name')
            return render(request, 'wholesale/wholesale_customers.html', {
                'customers': customers,
                'action': 'return',
                'page_title': 'Select Customer for Returns'
            })

        customers = WholesaleCustomer.objects.all().order_by('name')  # Order by customer name in ascending order
        return render(request, 'wholesale/wholesale_customers.html', {'customers': customers})
    else:
        return redirect('store:index')


@login_required
def edit_wholesale_customer(request, pk):
    if request.user.is_authenticated:
        customer = get_object_or_404(WholesaleCustomer, id=pk)
        if request.method == 'POST':
            form = WholesaleCustomerForm(request.POST, instance=customer)
            if form.is_valid():
                form.save()
                messages.success(request, f'{customer.name} edited successfully.')
                return redirect('wholesale:wholesale_customers')
            else:
                messages.warning(request, f'{customer.name} failed to edit, please try again')
        else:
            form = WholesaleCustomerForm(instance=customer)
        if request.headers.get('HX-Request'):
            return render(request, 'partials/edit_wholesale_customer_modal.html', {'form': form, 'customer': customer})
        else:
            return render(request, 'wholesale/wholesale_customer.html')
    else:
        return redirect('store:index')


@login_required
@user_passes_test(is_admin_or_manager)
def delete_wholesale_customer(request, pk):
    if request.user.is_authenticated:
        customer = get_object_or_404(WholesaleCustomer, pk=pk)
        customer.delete()
        messages.success(request, 'Customer deleted successfully.')
        return redirect('wholesale:wholesale_customers')
    else:
        return redirect('store:index')


@login_required
def wholesale_customer_add_funds(request, pk):
    if request.user.is_authenticated:
        customer = get_object_or_404(WholesaleCustomer, pk=pk)

        # Get or create the wholesale customer's wallet
        wallet, created = WholesaleCustomerWallet.objects.get_or_create(customer=customer)

        if request.method == 'POST':
            form = WholesaleCustomerAddFundsForm(request.POST)
            if form.is_valid():
                amount = form.cleaned_data['amount']
                wallet.add_funds(amount, user=request.user)
                messages.success(request, f'Funds successfully added to {wallet.customer.name}\'s wallet.')
                return redirect('wholesale:wholesale_customers')
            else:
                messages.error(request, 'Error adding funds')
        else:
            form = WholesaleCustomerAddFundsForm()

        return render(request, 'partials/wholesale_customer_add_funds_modal.html', {'form': form, 'customer': customer})
    else:
        return redirect('store:index')


@login_required
def wholesale_customer_wallet_details(request, pk):
    if request.user.is_authenticated:
        customer = get_object_or_404(WholesaleCustomer, pk=pk)

        # Check if the customer has a wallet; create one if it doesn't exist
        wallet, created = WholesaleCustomerWallet.objects.get_or_create(customer=customer)

        return render(request, 'wholesale/wholesale_customer_wallet_details.html', {
            'customer': customer,
            'wallet': wallet
        })
    else:
        return redirect('store:index')




@login_required
@user_passes_test(is_admin_or_manager)
def reset_wholesale_customer_wallet(request, pk):
    if request.user.is_authenticated:
        wallet = get_object_or_404(WholesaleCustomerWallet, pk=pk)
        wallet.balance = 0
        wallet.save()
        messages.success(request, f'{wallet.customer.name}\'s wallet cleared successfully.')
        return redirect('wholesale:wholesale_customers')
    else:
        return redirect('store:index')



@login_required
def wholesale_customers_on_negative(request):
    if request.user.is_authenticated:
        wholesale_customers_on_negative = WholesaleCustomer.objects.filter(wholesale_customer_wallet__balance__lt=0)
        return render(request, 'partials/wholesale_customers_on_negative.html', {'customers': wholesale_customers_on_negative})
    else:
        return redirect('store:index')


@login_required
def add_items_to_wholesale_stock_check(request, stock_check_id):
    """Add more items to an existing wholesale stock check"""
    if request.user.is_authenticated:
        stock_check = get_object_or_404(WholesaleStockCheck, id=stock_check_id)

        # Only allow adding items to in-progress stock checks
        if stock_check.status != 'in_progress':
            messages.error(request, 'Cannot add items to a completed stock check.')
            return redirect('wholesale:update_wholesale_stock_check', stock_check.id)

        # Get items that are not already in this stock check
        existing_item_ids = stock_check.wholesale_items.values_list('item_id', flat=True)
        available_items = WholesaleItem.objects.exclude(id__in=existing_item_ids).order_by('name')

        if request.method == 'POST':
            selected_item_ids = request.POST.getlist('selected_items')
            zero_empty_items = request.POST.get('zero_empty_items', 'true').lower() == 'true'

            if not selected_item_ids:
                messages.error(request, 'Please select at least one item to add.')
                return redirect('wholesale:add_items_to_wholesale_stock_check', stock_check.id)

            # Create stock check items for selected items
            stock_check_items = []
            added_count = 0

            for item_id in selected_item_ids:
                try:
                    item = WholesaleItem.objects.get(id=item_id)

                    # Skip items with zero stock if zero_empty_items is True
                    if not zero_empty_items or item.stock > 0:
                        stock_check_items.append(
                            WholesaleStockCheckItem(
                                stock_check=stock_check,
                                item=item,
                                expected_quantity=item.stock,
                                actual_quantity=0,
                                status='pending'
                            )
                        )
                        added_count += 1
                except WholesaleItem.DoesNotExist:
                    continue

            if stock_check_items:
                WholesaleStockCheckItem.objects.bulk_create(stock_check_items)
                messages.success(request, f'{added_count} items added to stock check successfully.')
            else:
                messages.warning(request, 'No items were added. Items may have zero stock or already exist in the stock check.')

            return redirect('wholesale:update_wholesale_stock_check', stock_check.id)

        context = {
            'stock_check': stock_check,
            'available_items': available_items,
        }

        return render(request, 'wholesale/add_items_to_wholesale_stock_check.html', context)
    else:
        return redirect('store:index')



def wholesale_transactions(request, customer_id):
    # Get the wholesale customer
    customer = get_object_or_404(WholesaleCustomer, id=customer_id)

    # Get the wholesale customer's wallet
    wallet = getattr(customer, 'wholesale_customer_wallet', None)
    wallet_balance = wallet.balance if wallet else 0.00  # Set to 0.00 if wallet does not exist

    # Filter sales where customer is None, since wholesale sales may not be linked to Customer
    wholesale_sales = Sales.objects.filter(customer=None).prefetch_related('sales_items__item').order_by('-date')

    # Pass wallet balance to the template
    return render(request, 'partials/wholesale_transactions.html', {
        'customer': customer,
        'sales': wholesale_sales,
        'wallet_balance': wallet_balance,
    })




@user_passes_test(can_manage_wholesale_procurement)
@login_required
def add_wholesale_procurement(request):
    if request.user.is_authenticated:
        # Use the predefined formset from forms.py
        from .forms import WholesaleProcurementItemFormSet

        if request.method == 'POST':
            # Check if we're continuing a draft procurement
            draft_id = request.GET.get('draft_id') or request.POST.get('draft_id')
            procurement_form = WholesaleProcurementForm(request.POST)
            formset = WholesaleProcurementItemFormSet(request.POST, queryset=WholesaleProcurementItem.objects.none(), prefix='form')
            action = request.POST.get('action', 'save')

            if procurement_form.is_valid() and formset.is_valid():
                # Handle draft procurement continuation or create new procurement
                if draft_id:
                    try:
                        procurement = WholesaleProcurement.objects.get(id=draft_id, status='draft')
                        # Update the procurement with the form data
                        procurement.supplier = procurement_form.cleaned_data['supplier']
                        procurement.date = procurement_form.cleaned_data['date']

                        # Delete existing items to avoid duplicates
                        procurement.items.all().delete()
                    except WholesaleProcurement.DoesNotExist:
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
                    return redirect('wholesale:wholesale_procurement_list')
                else:
                    messages.success(request, "Procurement and items added successfully!")
                    return redirect('wholesale:wholesale_procurement_list')
            else:
                # Print form errors for debugging
                if not procurement_form.is_valid():
                    for field, errors in procurement_form.errors.items():
                        for error in errors:
                            messages.error(request, f"{field}: {error}")
                if not formset.is_valid():
                    for i, form in enumerate(formset):
                        for field, errors in form.errors.items():
                            for error in errors:
                                messages.error(request, f"Item {i+1} {field}: {error}")
                    if formset.non_form_errors():
                        for error in formset.non_form_errors():
                            messages.error(request, error)
        else:
            # Check if we're continuing a draft procurement
            draft_id = request.GET.get('draft_id')
            if draft_id:
                try:
                    draft_procurement = WholesaleProcurement.objects.get(id=draft_id, status='draft')
                    procurement_form = WholesaleProcurementForm(instance=draft_procurement)
                    formset = WholesaleProcurementItemFormSet(queryset=draft_procurement.items.all(), prefix='form')
                except WholesaleProcurement.DoesNotExist:
                    messages.error(request, "Draft procurement not found.")
                    procurement_form = WholesaleProcurementForm()
                    formset = WholesaleProcurementItemFormSet(queryset=WholesaleProcurementItem.objects.none(), prefix='form')
            else:
                procurement_form = WholesaleProcurementForm()
                formset = WholesaleProcurementItemFormSet(queryset=WholesaleProcurementItem.objects.none(), prefix='form')

        return render(
            request,
            'partials/add_wholesale_procurement.html',
            {
                'procurement_form': procurement_form,
                'formset': formset,
            }
        )
    else:
        return redirect('store:index')



@user_passes_test(can_manage_wholesale_procurement)
@login_required
def wholesale_procurement_form(request):
    if request.user.is_authenticated:
        # Create an empty formset for the items
        from .forms import WholesaleProcurementItemFormSet
        item_formset = WholesaleProcurementItemFormSet(queryset=WholesaleProcurementItem.objects.none(), prefix='form')  # Use the same prefix as in the add_wholesale_procurement view

        # Get the empty form (form for the new item)
        new_form = item_formset.empty_form

        # Render the HTML for the new form
        return render(request, 'wholesale/wholesale_procurement_form.html', {'form': new_form})
    else:
        return redirect('store:index')


@user_passes_test(can_view_procurement_history)
@login_required
def wholesale_procurement_list(request):
    if request.user.is_authenticated:
        procurements = (
            WholesaleProcurement.objects.annotate(calculated_total=Sum('items__subtotal'))
            .order_by('-date')
        )
        return render(request, 'partials/wholesale_procurement_list.html', {
            'procurements': procurements,
        })
    else:
        return redirect('store:index')


@user_passes_test(can_view_procurement_history)
@login_required
def search_wholesale_procurement(request):
    if request.user.is_authenticated:
        # Base query with calculated total and ordering
        procurements = (
            WholesaleProcurement.objects.annotate(calculated_total=Sum('items__subtotal'))
            .order_by('-date')
        )

        # Get search parameters from the request
        name_query = request.GET.get('name', '').strip()
        status_query = request.GET.get('status', '').strip()

        # Apply filters if search parameters are provided
        if name_query:
            procurements = procurements.filter(supplier__name__icontains=name_query)

        if status_query:
            procurements = procurements.filter(status=status_query)

        context = {
            'procurements': procurements,
            'search_query': name_query,
            'status_filter': status_query,
        }

        # Check if this is an HTMX request for partial update
        if request.headers.get('HX-Request'):
            return render(request, 'partials/search_wholesale_procurement.html', context)
        else:
            # Return full page for direct access
            return render(request, 'wholesale/search_wholesale_procurement.html', context)
    else:
        return redirect('store:index')


@user_passes_test(can_view_procurement_history)
@login_required
def wholesale_procurement_detail(request, procurement_id):
    if request.user.is_authenticated:
        procurement = get_object_or_404(WholesaleProcurement, id=procurement_id)

        # Calculate total from ProcurementItem objects
        total = procurement.items.aggregate(total=models.Sum('subtotal'))['total'] or 0

        return render(request, 'partials/wholesale_procurement_detail.html', {
            'procurement': procurement,
            'total': total,
        })
    else:
        return redirect('store:index')



@user_passes_test(lambda u: u.is_superuser or (hasattr(u, 'profile') and u.profile and u.profile.user_type in ['Admin', 'Manager']))
@login_required
def create_wholesale_stock_check(request):
    if request.user.is_authenticated:
        if request.method == "POST":
            # Get the zero_empty_items flag from the form
            zero_empty_items = request.POST.get('zero_empty_items', 'true').lower() == 'true'

            # Get selected items if any
            selected_items_str = request.POST.get('selected_items', '')

            if selected_items_str:
                # Filter items based on selection
                selected_item_ids = [int(id) for id in selected_items_str.split(',') if id]
                items = WholesaleItem.objects.filter(id__in=selected_item_ids)
            else:
                # Get all items
                items = WholesaleItem.objects.all()

            if not items.exists():
                messages.error(request, "No items found to check stock.")
                return redirect('wholesale:wholesales')

            stock_check = WholesaleStockCheck.objects.create(created_by=request.user, status='in_progress')

            stock_check_items = []
            for item in items:
                # Skip items with zero stock if zero_empty_items is True
                if not zero_empty_items or item.stock > 0:
                    stock_check_items.append(
                        WholesaleStockCheckItem(
                            stock_check=stock_check,
                            item=item,
                            expected_quantity=item.stock if item.stock else Decimal('0'),
                            actual_quantity=Decimal('0'),
                            status='pending'
                        )
                    )

            WholesaleStockCheckItem.objects.bulk_create(stock_check_items)

            messages.success(request, "Stock check created successfully.")
            return redirect('wholesale:update_wholesale_stock_check', stock_check.id)

        return render(request, 'wholesale/create_wholesale_stock_check.html')
    else:
        return redirect('store:index')


@login_required
def update_wholesale_stock_check(request, stock_check_id):
    if request.user.is_authenticated:
        stock_check = get_object_or_404(WholesaleStockCheck, id=stock_check_id)

        # Check if user can edit completed stock checks
        can_edit_completed = request.user.is_superuser or (hasattr(request.user, 'profile') and request.user.profile and request.user.profile.user_type in ['Admin', 'Manager'])

        # If stock check is completed and user doesn't have permission, redirect to report
        if stock_check.status == 'completed' and not can_edit_completed:
            messages.info(request, "This stock check has been completed and cannot be modified.")
            return redirect('wholesale:wholesale_stock_check_report', stock_check.id)

        if stock_check.status not in ['in_progress', 'completed']:
            messages.error(request, "Stock check status is invalid for updates.")
            return redirect('wholesale:wholesales')

        if request.method == "POST":
            # Get the zero_empty_items flag from the form
            zero_empty_items = request.POST.get('zero_empty_items', 'false').lower() == 'true'

            stock_items = []
            for item_id, actual_qty in request.POST.items():
                if item_id.startswith("item_"):
                    item_id = int(item_id.replace("item_", ""))
                    stock_item = WholesaleStockCheckItem.objects.get(stock_check=stock_check, item_id=item_id)

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

            WholesaleStockCheckItem.objects.bulk_update(stock_items, ['actual_quantity'])
            messages.success(request, "Stock check updated successfully.")
            return redirect('wholesale:wholesale_stock_check_report', stock_check.id)

        # Pass permission info to template
        context = {
            'stock_check': stock_check,
            'can_approve_adjust': can_edit_completed
        }
        return render(request, 'wholesale/update_wholesale_stock_check.html', context)
    else:
        return redirect('store:index')


# @user_passes_test(is_admin)
# @login_required
# def update_wholesale_stock_check(request, stock_check_id):
#     if request.user.is_authenticated:
#         stock_check = get_object_or_404(WholesaleStockCheck, id=stock_check_id)
#         # if stock_check.status == 'completed':
#         #     return redirect('wholesale:wholesale_stock_check_report', stock_check.id)

#         if request.method == "POST":
#             stock_items = []
#             for item_id, actual_qty in request.POST.items():
#                 if item_id.startswith("item_"):
#                     item_id = int(item_id.replace("item_", ""))
#                     stock_item = WholesaleStockCheckItem.objects.get(stock_check=stock_check, item_id=item_id)
#                     stock_item.actual_quantity = int(actual_qty)
#                     stock_items.append(stock_item)
#             WholesaleStockCheckItem.objects.bulk_update(stock_items, ['actual_quantity'])
#             messages.success(request, "Stock check updated successfully.")
#             return redirect('wholesale:update_wholesale_stock_check', stock_check.id)

#         return render(request, 'wholesale/update_wholesale_stock_check.html', {'stock_check': stock_check})
#     else:
#         return redirect('store:index')


# Duplicate function removed - using the main update_wholesale_stock_check function above


# @user_passes_test(is_admin)
# @login_required
# def approve_wholesale_stock_check(request, stock_check_id):
#     if request.user.is_authenticated:
#         stock_check = get_object_or_404(WholesaleStockCheck, id=stock_check_id)
#         if stock_check.status != 'in_progress':
#             messages.error(request, "Stock check is not in progress.")
#             return redirect('wholesale:wholesales')

#         if request.method == "POST":
#             selected_items = request.POST.getlist('item')
#             if not selected_items:
#                 messages.error(request, "Please select at least one item to approve.")
#                 return redirect('wholesale:update_wholesale_stock_check', stock_check.id)

#             stock_items = WholesaleStockCheckItem.objects.filter(id__in=selected_items, stock_check=stock_check)
#             stock_items.update(status='approved', approved_by=request.user, approved_at=datetime.now())

#             if stock_items.count() == stock_check.wholesale_items.count():
#                 stock_check.status = 'completed'
#                 stock_check.save()

#             messages.success(request, f"{stock_items.count()} items approved successfully.")
#             return redirect('wholesale:update_wholesale_stock_check', stock_check.id)

#         return redirect('wholesale:update_wholesale_stock_check', stock_check.id)
#     else:
#         return redirect('store:index')



@user_passes_test(lambda u: u.is_superuser or (hasattr(u, 'profile') and u.profile and u.profile.user_type in ['Admin', 'Manager']))
@login_required
def approve_wholesale_stock_check(request, stock_check_id):
    if request.user.is_authenticated:
        stock_check = get_object_or_404(WholesaleStockCheck, id=stock_check_id)
        if stock_check.status != 'in_progress':
            messages.error(request, "Stock check is not in progress.")
            return redirect('wholesale:wholesales')

        if request.method == "POST":
            selected_items = request.POST.getlist('item')
            if not selected_items:
                messages.error(request, "Please select at least one item to approve.")
                return redirect('wholesale:update_wholesale_stock_check', stock_check.id)

            stock_items = WholesaleStockCheckItem.objects.filter(id__in=selected_items, stock_check=stock_check)
            stock_items.update(status='approved', approved_by=request.user, approved_at=datetime.now())

            if stock_items.count() == stock_check.wholesale_items.count():
                stock_check.status = 'completed'
                stock_check.save()

            messages.success(request, f"{stock_items.count()} items approved successfully.")
            return redirect('wholesale:update_wholesale_stock_check', stock_check.id)

        return redirect('wholesale:update_wholesale_stock_check', stock_check.id)
    else:
        return redirect('store:index')



# @user_passes_test(is_admin)
# @login_required
# def wholesale_bulk_adjust_stock(request, stock_check_id):
#     if request.user.is_authenticated:
#         stock_check = get_object_or_404(WholesaleStockCheck, id=stock_check_id)
#         if stock_check.status not in ['in_progress', 'completed']:
#             messages.error(request, "Stock check status is invalid for adjustments.")
#             return redirect('wholesale:wholesales')

#         if request.method == "POST":
#             selected_items = request.POST.getlist('item')
#             if not selected_items:
#                 messages.error(request, "Please select at least one item to adjust.")
#                 return redirect('wholesale:update_wholesale_stock_check', stock_check.id)

#             stock_items = WholesaleStockCheckItem.objects.filter(id__in=selected_items, stock_check=stock_check)
#             for item in stock_items:
#                 discrepancy = item.discrepancy()
#                 if discrepancy != 0:
#                     item.item.stock += discrepancy
#                     item.status = 'adjusted'
#                     item.save()
#                     WholesaleItem.objects.filter(id=item.item.id).update(stock=item.item.stock)

#             messages.success(request, f"Stock adjusted for {stock_items.count()} items.")
#             return redirect('wholesale:wholesales')

#         return redirect('wholesale:update_wholesale_stock_check', stock_check.id)
#     else:
#         return redirect('store:index')


@user_passes_test(lambda u: u.is_superuser or (hasattr(u, 'profile') and u.profile and u.profile.user_type in ['Admin', 'Manager']))
@login_required
def wholesale_bulk_adjust_stock(request, stock_check_id):
    if request.user.is_authenticated:
        stock_check = get_object_or_404(WholesaleStockCheck, id=stock_check_id)
        if stock_check.status not in ['in_progress', 'completed']:
            messages.error(request, "Stock check status is invalid for adjustments.")
            return redirect('wholesale:wholesales')

        if request.method == "POST":
            selected_items = request.POST.getlist('item')
            if not selected_items:
                messages.error(request, "Please select at least one item to adjust.")
                return redirect('wholesale:update_wholesale_stock_check', stock_check.id)

            stock_items = WholesaleStockCheckItem.objects.filter(id__in=selected_items, stock_check=stock_check)
            for item in stock_items:
                discrepancy = item.discrepancy()
                if discrepancy != 0:
                    item.item.stock += discrepancy
                    item.status = 'adjusted'
                    item.save()
                    WholesaleItem.objects.filter(id=item.item.id).update(stock=item.item.stock)

            messages.success(request, f"Stock adjusted for {stock_items.count()} items.")
            return redirect('wholesale:wholesales')


@user_passes_test(lambda u: u.is_superuser or (hasattr(u, 'profile') and u.profile and u.profile.user_type in ['Admin', 'Manager']))
@login_required
def adjust_wholesale_stock(request, stock_item_id):
    """Handle individual wholesale stock check item adjustments"""
    stock_item = get_object_or_404(WholesaleStockCheckItem, id=stock_item_id)

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

            return redirect('wholesale:wholesale_stock_check_report', stock_item.stock_check.id)

        except ValueError:
            messages.error(request, 'Invalid quantity value provided')

    return render(request, 'wholesale/adjust_wholesale_stock.html', {'stock_item': stock_item})



# @user_passes_test(is_admin)
# @login_required
# def wholesale_stock_check_report(request, stock_check_id):
#     if request.user.is_authenticated:
#         stock_check = get_object_or_404(WholesaleStockCheck, id=stock_check_id)
#         return render(request, 'wholesale/wholesale_stock_check_report.html', {'stock_check': stock_check})
#     else:
#         return redirect('store:index')


@login_required
def wholesale_stock_check_report(request, stock_check_id):
    stock_check = get_object_or_404(WholesaleStockCheck, id=stock_check_id)
    total_cost_difference = 0

    # Loop through each stock check item and aggregate the cost difference.
    for item in stock_check.wholesale_items.all():
        discrepancy = item.discrepancy()  # Actual - Expected
        # Assuming each item has a 'price' attribute.
        unit_price = getattr(item.item, 'price', 0)
        cost_difference = discrepancy * unit_price
        total_cost_difference += cost_difference

    context = {
        'stock_check': stock_check,
        'total_cost_difference': total_cost_difference,
    }
    return render(request, 'wholesale/wholesale_stock_check_report.html', context)



@login_required
def list_wholesale_stock_checks(request):
    # Get all StockCheck objects ordered by date (newest first)
    stock_checks = WholesaleStockCheck.objects.all().order_by('-date')

    # Check if user can delete stock check reports
    from userauth.permissions import can_delete_stock_check_reports
    can_delete_reports = can_delete_stock_check_reports(request.user)

    context = {
        'stock_checks': stock_checks,
        'can_delete_reports': can_delete_reports,
    }
    return render(request, 'wholesale/wholesale_stock_check_list.html', context)

@login_required
@require_POST
def delete_wholesale_stock_check(request, stock_check_id):
    """Delete a wholesale stock check report"""
    if request.user.is_authenticated:
        from userauth.permissions import can_delete_stock_check_reports
        if not can_delete_stock_check_reports(request.user):
            messages.error(request, 'You do not have permission to delete wholesale stock check reports.')
            return redirect('wholesale:list_wholesale_stock_checks')

        stock_check = get_object_or_404(WholesaleStockCheck, id=stock_check_id)

        # Check if stock check can be deleted (only pending or in_progress)
        if stock_check.status == 'completed':
            messages.error(request, 'Cannot delete completed wholesale stock check reports.')
            return redirect('wholesale:list_wholesale_stock_checks')

        stock_check_id_display = stock_check.id
        stock_check.delete()
        messages.success(request, f'Wholesale stock check report #{stock_check_id_display} deleted successfully.')
        return redirect('wholesale:list_wholesale_stock_checks')
    else:
        return redirect('store:index')




logger = logging.getLogger(__name__)

# @login_required
# def create_transfer_request(request):
#     if request.user.is_authenticated:
#         if request.method == "GET":
#             # Render form for a wholesale user to request items from retail
#             retail_items = Item.objects.all().order_by('name')
#             return render(request, "wholesale/wholesale_transfer_request.html", {"retail_items": retail_items})

#         elif request.method == "POST":
#             try:
#                 requested_quantity = float(request.POST.get("requested_quantity", 0))
#                 item_id = request.POST.get("item_id")
#                 from_wholesale = request.POST.get("from_wholesale", "false").lower() == "true"

#                 if not item_id or requested_quantity <= 0:
#                     return JsonResponse({"success": False, "message": "Invalid input provided."}, status=400)

#                 source_item = get_object_or_404(Item, id=item_id)

#                 transfer = TransferRequest.objects.create(
#                     retail_item=source_item,
#                     requested_quantity=requested_quantity,
#                     from_wholesale=True,
#                     status="pending",
#                     created_at=timezone.now()
#                 )

#                 messages.success(request, "Transfer request created successfully.")
#                 return JsonResponse({"success": True, "message": "Transfer request created successfully."})

#             except (TypeError, ValueError) as e:
#                 return JsonResponse({"success": False, "message": str(e)}, status=400)
#             except Exception as e:
#                 return JsonResponse({"success": False, "message": "An error occurred."}, status=500)

#     return redirect('store:index')


@login_required
def create_transfer_request(request):
    if request.user.is_authenticated:
        if request.method == "GET":
            try:
                # Get search query
                search_query = request.GET.get('search', '').strip()
                logger.info(f"Search query received: '{search_query}'")
                
                # Filter wholesale items based on search
                if search_query:
                    wholesale_items = WholesaleItem.objects.filter(
                        Q(name__icontains=search_query) | 
                        Q(brand__icontains=search_query) |
                        Q(dosage_form__icontains=search_query)
                    ).order_by('name')
                    logger.info(f"Found {wholesale_items.count()} wholesale items matching search: '{search_query}'")
                else:
                    wholesale_items = WholesaleItem.objects.all().order_by('name')
                    logger.info(f"Rendering transfer request form with {wholesale_items.count()} wholesale items")
                
                context = {
                    "wholesale_items": wholesale_items,
                    "search_query": search_query
                }
                
                logger.info(f"Rendering template with context: {context}")
                return render(request, "store/retail_transfer_request.html", context)
                
            except Exception as e:
                logger.error(f"Error in create_transfer_request (GET): {str(e)}")
                logger.error(f"Exception type: {type(e).__name__}")
                import traceback
                logger.error(f"Traceback: {traceback.format_exc()}")
                
                # Fallback to showing all items without search
                wholesale_items = WholesaleItem.objects.all().order_by('name')
                return render(request, "store/retail_transfer_request.html", {
                    "wholesale_items": wholesale_items,
                    "search_query": "",
                    "error_message": f"Search functionality temporarily unavailable: {str(e)}"
                })

        elif request.method == "POST":
            logger.info(f"POST request received for transfer creation: {request.POST}")
            try:
                requested_quantity = float(request.POST.get("requested_quantity", 0))
                item_id = request.POST.get("item_id")
                from_wholesale = request.POST.get("from_wholesale", "false").lower() == "true"

                if not item_id or requested_quantity <= 0:
                    return JsonResponse({"success": False, "message": "Invalid input provided."}, status=400)

                # Get the source item based on transfer direction
                if from_wholesale:
                    # Wholesale requesting from Retail (Retail → Wholesale transfer)
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
                    logger.info(f"Created transfer request: Retail→Wholesale ({source_item.name} x{requested_quantity})")
                else:
                    # Retail requesting from Wholesale (Wholesale → Retail transfer)
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
                    logger.info(f"Created transfer request: Wholesale→Retail ({source_item.name} x{requested_quantity})")

                return JsonResponse({"success": True, "message": "Transfer request created successfully."})

            except (TypeError, ValueError) as e:
                logger.error(f"Validation error in create_transfer_request: {str(e)}")
                if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                    return JsonResponse({"success": False, "message": str(e)}, status=400)
                else:
                    messages.error(request, str(e))
                    return redirect('wholesale:create_transfer_request')
            except Exception as e:
                logger.error(f"Error in create_transfer_request: {str(e)}")
                if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                    return JsonResponse({"success": False, "message": "An error occurred."}, status=500)
                else:
                    messages.error(request, "An error occurred while creating the transfer request.")
                    return redirect('wholesale:create_transfer_request')

    return redirect('store:index')



@login_required
def wholesale_transfer_request_list(request):
    if request.user.is_authenticated:
        """
        Display all transfer requests and transfers.
        Optionally filter by a specific date (YYYY-MM-DD).
        """
        # Get the date filter from GET parameters.
        date_str = request.GET.get("date")
        transfers = TransferRequest.objects.all().order_by("-created_at")

        if date_str:
            try:
                # Parse the string into a date object.
                filter_date = datetime.strptime(date_str, "%Y-%m-%d").date()
                transfers = transfers.filter(created_at__date=filter_date)
            except ValueError:
                # If date parsing fails, ignore the filter.
                logger.warning("Invalid date format provided: %s", date_str)

        context = {
            "transfers": transfers,
            "search_date": date_str or ""
        }
        return render(request, "store/transfer_request_list.html", context)
    else:
        return redirect('store:index')



# Pending requests from retail to wholesale
@login_required
def pending_wholesale_transfer_requests(request):
    if request.user.is_authenticated:
        # Get transfer requests from retail to wholesale (from_wholesale=False)
        # These should have wholesale_item populated
        wholesale_pending_transfers = TransferRequest.objects.filter(
            status="pending", 
            from_wholesale=False
        ).select_related('wholesale_item').order_by('-created_at')
        
        # Debug logging
        logger.info(f"Found {wholesale_pending_transfers.count()} pending wholesale transfer requests")
        for transfer in wholesale_pending_transfers:
            logger.info(f"Transfer {transfer.id}: {transfer.wholesale_item.name if transfer.wholesale_item else 'No item'}")
            
        return render(request, "wholesale/pending_wholesale_transfer_requests.html", {"wholesale_pending_transfers": wholesale_pending_transfers})
    else:
        messages.error(request, "Please login to view pending transfer requests.")
        return redirect('store:index')


@login_required
def wholesale_approve_transfer(request, transfer_id):
    """
    Approves a transfer request.
    For a wholesale-initiated request (from_wholesale=True), the source is the retail item
    and the destination is a wholesale item.
    The retail user can adjust the approved quantity before approval.
    """
    if request.user.is_authenticated:
        logger.info(f"Approve transfer request received for transfer {transfer_id}")
        if request.method == "POST":
            try:
                transfer = get_object_or_404(TransferRequest, id=transfer_id)
                logger.info(f"Found transfer for approval: {transfer}")

                # Determine approved quantity (if adjusted) or use the originally requested amount.
                approved_qty_param = request.POST.get("approved_quantity")
                if approved_qty_param:
                    try:
                        approved_qty = int(approved_qty_param)
                    except ValueError:
                        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                            return JsonResponse({"success": False, "message": "Invalid quantity!"}, status=400)
                        else:
                            messages.error(request, 'Invalid quantity!')
                            return redirect('wholesale:pending_wholesale_transfer_requests')
                else:
                    approved_qty = transfer.requested_quantity

                if transfer.from_wholesale:
                    # Request initiated by wholesale: the source is the retail item.
                    source_item = transfer.retail_item
                    # Destination: corresponding wholesale item.
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
                else:
                    # Reverse scenario (if retail sends request to wholesale)
                    source_item = transfer.wholesale_item
                    destination_item, created = Item.objects.get_or_create(
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

                logger.info(f"Approving Transfer: Source {source_item.name} (Stock: {source_item.stock}) Requested Qty: {approved_qty}")

                # Check if there's enough stock before deducting
                if source_item.stock < approved_qty:
                    logger.error(f"Insufficient stock for transfer {transfer_id}: Available {source_item.stock}, Requested {approved_qty}")
                    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                        return JsonResponse({
                            "success": False,
                            "message": f"Not enough stock in source! Available: {source_item.stock}, Requested: {approved_qty}"
                        }, status=400)
                    else:
                        messages.error(request, f"Not enough stock in source! Available: {source_item.stock}, Requested: {approved_qty}")
                        return redirect('wholesale:pending_wholesale_transfer_requests')

                # Use transaction to ensure atomicity
                with transaction.atomic():
                    # Deduct approved quantity from the source item.
                    source_item.stock = F('stock') - approved_qty
                    source_item.save()
                    source_item.refresh_from_db()

                    # Increase stock in the destination item.
                    destination_item.stock = F('stock') + approved_qty
                    destination_item.cost = source_item.cost
                    destination_item.exp_date = source_item.exp_date
                    destination_item.markup = source_item.markup
                    destination_item.price = source_item.price
                    destination_item.save()
                    destination_item.refresh_from_db()

                    # Update the transfer request.
                    transfer.status = "approved"
                    transfer.approved_quantity = approved_qty
                    transfer.save()

                direction = "retail to wholesale" if transfer.from_wholesale else "wholesale to retail"
                logger.info(f"Transfer {transfer_id} approved successfully: {approved_qty} {source_item.name} from {direction}")

                if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                    return JsonResponse({
                        "success": True,
                        "message": f"Transfer approved with quantity {approved_qty}.",
                        "source_stock": str(source_item.stock),
                        "destination_stock": str(destination_item.stock),
                    })
                else:
                    messages.success(request, f"Transfer approved: {approved_qty} {source_item.name} moved from {direction}.")
                    return redirect('wholesale:pending_wholesale_transfer_requests')
                
            except (TypeError, ValueError) as e:
                logger.error(f"Validation error approving transfer {transfer_id}: {str(e)}")
                if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                    return JsonResponse({"success": False, "message": f"Validation error: {str(e)}"}, status=400)
                else:
                    messages.error(request, f"Validation error: {str(e)}")
                    return redirect('wholesale:pending_wholesale_transfer_requests')
            except Exception as e:
                logger.error(f"Error approving transfer {transfer_id}: {str(e)}")
                import traceback
                logger.error(f"Traceback: {traceback.format_exc()}")
                if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                    return JsonResponse({"success": False, "message": f"An error occurred: {str(e)}"}, status=500)
                else:
                    messages.error(request, f"Error approving transfer: {str(e)}")
                    return redirect('wholesale:pending_wholesale_transfer_requests')
        else:
            return JsonResponse({"success": False, "message": "Invalid request method!"}, status=400)
    else:
        return redirect('store:index')



# Reject a transfer request sent from retail
@login_required
def reject_wholesale_transfer(request, transfer_id):
    if request.user.is_authenticated:
        logger.info(f"Reject transfer request received for transfer {transfer_id}")
        """
        Rejects a transfer request.
        """
        if request.method == "POST":
            try:
                transfer = get_object_or_404(TransferRequest, id=transfer_id)
                logger.info(f"Found transfer: {transfer}")
                
                transfer.status = "rejected"
                transfer.save()
                logger.info(f"Transfer {transfer_id} rejected successfully")
                
                if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                    return JsonResponse({"success": True, "message": "Transfer request rejected successfully."})
                else:
                    messages.error(request, "Transfer request rejected.")
                    return redirect('wholesale:pending_wholesale_transfer_requests')
            except Exception as e:
                logger.error(f"Error rejecting transfer {transfer_id}: {str(e)}")
                if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                    return JsonResponse({"success": False, "message": str(e)}, status=400)
                else:
                    messages.error(request, f"Error rejecting transfer: {str(e)}")
                    return redirect('wholesale:pending_wholesale_transfer_requests')
        else:
            return JsonResponse({"success": False, "message": "Invalid request method!"}, status=400)
    else:
        return redirect('store:index')


# List of all the Requests and Transfers
@login_required
def transfer_request_list(request):
    if request.user.is_authenticated:
        """
        Display all transfer requests and transfers.
        Optionally filter by a specific date (YYYY-MM-DD).
        """
        # Get the date filter from GET parameters.
        date_str = request.GET.get("date")
        transfers = TransferRequest.objects.all().order_by("-created_at")

        if date_str:
            try:
                # Parse the string into a date object.
                filter_date = datetime.strptime(date_str, "%Y-%m-%d").date()
                transfers = transfers.filter(created_at__date=filter_date)
            except ValueError:
                # If date parsing fails, ignore the filter.
                logger.warning("Invalid date format provided: %s", date_str)

        context = {
            "transfers": transfers,
            "search_date": date_str or ""
        }
        return render(request, "store/transfer_request_list.html", context)
    else:
        return redirect('store:index')


@login_required
def complete_wholesale_customer_history(request, customer_id):
    if request.user.is_authenticated:
        customer = get_object_or_404(WholesaleCustomer, id=customer_id)

        # Get all wholesale selection history
        selection_history = WholesaleSelectionHistory.objects.filter(
            wholesale_customer=customer
        ).select_related(
            'item', 'user'
        ).order_by('-date')  # Changed from created_at to date

        # Process history
        history_data = {}

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
            'wholesale_customer': customer,
            'history_data': history_data,
        }

        return render(request, 'wholesale/complete_wholesale_customer_history.html', context)
    return redirect('store:index')


# Wholesale Cashier Functions - Adapted from Retail Implementation

@transaction.atomic
@login_required
def send_to_wholesale_cashier(request):
    """Send wholesale payment request to cashier/billing-point/pay-point"""
    if request.user.is_authenticated:
        from userauth.permissions import can_dispense_items
        
        # Check if user can dispense items (is a dispenser)
        if not can_dispense_items(request.user):
            messages.error(request, 'You do not have dispenser permissions to send wholesale payment requests.')
            return redirect('wholesale:wholesale_cart')
        try:
            # Get wholesale cart items
            cart_items = WholesaleCart.objects.filter(user=request.user)
            if not cart_items.exists():
                messages.error(request, "Your wholesale cart is empty. Cannot send payment request.")
                return redirect('wholesale:wholesale_cart')
            
            # Get customer info (same pattern as retail)
            from customer.models import WholesaleCustomer
            from userauth.session_utils import get_user_customer_id
            wholesale_customer = None
            customer_id = get_user_customer_id(request)
            if customer_id:
                try:
                    wholesale_customer = WholesaleCustomer.objects.get(id=customer_id)
                except WholesaleCustomer.DoesNotExist:
                    pass
            
            # Calculate total amount
            total_amount = sum(item.subtotal for item in cart_items)

            # Create wholesale payment request
            from store.models import PaymentRequest, PaymentRequestItem
            payment_request = PaymentRequest.objects.create(
                dispenser=request.user,
                customer=None,  # Not using retail customer for wholesale
                wholesale_customer=wholesale_customer,
                payment_type='wholesale',
                total_amount=total_amount,
                notes=request.POST.get('notes', ''),
                status='pending'
            )
            
            # Create payment request items
            for cart_item in cart_items:
                PaymentRequestItem.objects.create(
                    payment_request=payment_request,
                    item_name=cart_item.item.name,
                    brand=cart_item.item.brand,
                    dosage_form=str(cart_item.dosage_form.dosage_form) if cart_item.dosage_form else '',
                    unit=cart_item.unit,
                    quantity=cart_item.quantity,
                    unit_price=cart_item.price,
                    discount_amount=cart_item.discount_amount,
                    subtotal=cart_item.subtotal,
                    retail_item=None,  # Not using retail items
                    wholesale_item=cart_item.item
                )
            
            # Create notification for available cashiers
            from store.models import Notification, Cashier
            available_cashiers = Cashier.objects.filter(is_active=True)
            for cashier in available_cashiers:
                notification = Notification.objects.create(
                    user=cashier.user,
                    notification_type='payment_request',
                    priority='high',
                    title=f'New Wholesale Payment Request {payment_request.request_id}',
                    message=f'Wholesale payment request of ₦{total_amount} from {request.user.username} pending your review.',
                    related_payment_request=payment_request
                )
            
            # Mark cart items as sent to cashier (optional status change)
            # cart_items.update(status='sent_to_cashier')  # You'll need to add this field to WholesaleCart model
            
            messages.success(request, f'Wholesale payment request {payment_request.request_id} sent to cashier successfully.')
            return redirect('wholesale:wholesale_payment_requests')
            
        except Exception as e:
            messages.error(request, f'Error sending wholesale payment request: {str(e)}')
            return redirect('wholesale:wholesale_cart')
    
    return redirect('store:index')


@login_required
def wholesale_payment_requests(request):
    """Show dispenser's wholesale payment requests history"""
    if request.user.is_authenticated:
        from userauth.permissions import can_dispense_items
        
        # Check if user can dispense items (is a dispenser)
        if not can_dispense_items(request.user):
            messages.error(request, 'You do not have dispenser permissions to view wholesale payment requests.')
            return redirect('store:index')
        
        from store.models import PaymentRequest
        payment_requests = PaymentRequest.objects.filter(dispenser=request.user, payment_type='wholesale').order_by('-created_at')
        
        return render(request, 'wholesale/wholesale_payment_requests.html', {
            'payment_requests': payment_requests,
        })
    
    return redirect('store:index')


@login_required
def wholesale_payment_request_detail(request, request_id):
    """Show wholesale payment request details"""
    if request.user.is_authenticated:
        try:
            from store.models import PaymentRequest
            payment_request = PaymentRequest.objects.get(request_id=request_id, payment_type='wholesale')
            
            # Check if user is authorized (either the dispenser or a cashier)
            if payment_request.dispenser != request.user and not hasattr(request.user, 'cashier'):
                messages.error(request, 'You are not authorized to view this wholesale payment request.')
                return redirect('wholesale:wholesale_payment_requests')
            
            return render(request, 'wholesale/wholesale_payment_request_detail.html', {
                'payment_request': payment_request,
            })
            
        except PaymentRequest.DoesNotExist:
            messages.error(request, 'Wholesale payment request not found.')
            return redirect('wholesale:wholesale_payment_requests')
    
    return redirect('store:index')


@login_required
def wholesale_cashier_dashboard(request):
    """Enhanced wholesale cashier dashboard with comprehensive payment management"""
    if request.user.is_authenticated:
        try:
            from django.db.models import Count, Sum, Avg
            from store.models import Cashier, PaymentRequest
            from userauth.permissions import is_cashier
            
            # Check if user is a cashier
            cashier = None
            is_admin = False
            
            if not is_cashier(request.user):
                # Check if user is an admin/manager who can see cashier dashboard
                if request.user.is_superuser or (hasattr(request.user, 'profile') and
                    request.user.profile and request.user.profile.user_type in ['Admin', 'Manager']):
                    is_admin = True
                else:
                    messages.error(request, 'You need to be a cashier or admin/manager to access this page.')
                    return redirect('store:index')
            
            # Get cashier info if available
            try:
                cashier = request.user.cashier
                if cashier and not cashier.is_active:
                    messages.error(request, 'Your cashier account is deactivated.')
                    return redirect('store:index')
            except Cashier.DoesNotExist:
                pass  # User is a cashier through profile
            
            # Get pending wholesale payment requests (accessible by all authorized users)
            pending_requests = PaymentRequest.objects.filter(status='pending', payment_type='wholesale').order_by('-created_at')
            
            # Filter requests by cashier if this is a specific cashier (not admin)
            if cashier and not is_admin:
                my_requests = PaymentRequest.objects.filter(cashier=cashier, payment_type='wholesale').exclude(status='pending').order_by('-created_at')
                cashier_display_name = cashier.name
            else:
                # For admins, show all processed requests
                my_requests = PaymentRequest.objects.filter(payment_type='wholesale').exclude(status='pending').order_by('-created_at')
                cashier_display_name = "Admin View" if is_admin else request.user.get_full_name() or request.user.username
            
            # Calculate comprehensive statistics
            all_processed = PaymentRequest.objects.filter(payment_type='wholesale', status='completed')
            
            stats = {
                'pending_count': pending_requests.count(),
                'completed_today_count': all_processed.filter(completed_at__date=timezone.now().date()).count(),
                'total_processed_count': my_requests.count(),
                'total_value': my_requests.aggregate(total=Sum('total_amount'))['total'] or Decimal('0'),
                'pending_value': pending_requests.aggregate(total=Sum('total_amount'))['total'] or Decimal('0'),
                'average_transaction': my_requests.aggregate(avg=Avg('total_amount'))['avg'] or Decimal('0'),
                'high_value_count': pending_requests.filter(total_amount__gte=Decimal('50000')).count(),
            }
            
            # Get recent activity feed
            recent_activity = PaymentRequest.objects.filter(payment_type='wholesale').order_by('-created_at')[:10]
            
            # Add recent notifications for cashiers
            if cashier and not is_admin:
                from store.models import Notification
                recent_notifications = Notification.objects.filter(
                    user=request.user,
                    notification_type='payment_request'
                ).order_by('-created_at')[:5]
            else:
                recent_notifications = []
            
            # Get today's statistics
            today = timezone.now().date()
            today_stats = {
                'today_pending': pending_requests.filter(created_at__date=today).count(),
                'today_completed': all_processed.filter(completed_at__date=today).count(),
                'today_value': all_processed.filter(completed_at__date=today).aggregate(
                    total=Sum('total_amount')
                )['total'] or Decimal('0'),
            }
            
            # Quick summary for dashboard
            summary = {
                'total_requests_today': today_stats['today_pending'] + today_stats['today_completed'],
                'pending_percentage': (pending_requests.count() / max(pending_requests.count() + all_processed.count(), 1)) * 100,
                'payment_trend': 'up' if today_stats['today_completed'] > all_processed.filter(completed_at__date=today - timezone.timedelta(days=1)).count() else 'down',
            }
            
            # Get accepted wholesale payment requests
            accepted_requests = PaymentRequest.objects.filter(status='accepted', payment_type='wholesale').order_by('-accepted_at')
            # Filter for specific cashier if not admin
            if cashier and not is_admin:
                accepted_requests = accepted_requests.filter(cashier=cashier)
            
            return render(request, 'wholesale/wholesale_cashier_dashboard.html', {
                'pending_requests': pending_requests,
                'accepted_requests': accepted_requests,
                'my_requests': my_requests,
                'cashier': cashier,
                'is_admin': is_admin,
                'stats': stats,
                'recent_activity': recent_activity,
                'recent_notifications': recent_notifications,
                'cashier_display_name': cashier_display_name,
                'today_stats': today_stats,
                'summary': summary,
            })
            
        except Exception as e:
            logger.error(f"Error loading wholesale cashier dashboard: {str(e)}")
            messages.error(request, f'Error loading wholesale cashier dashboard: {str(e)}')
            return redirect('store:index')
    
    return redirect('store:index')


@login_required
def accept_wholesale_payment_request(request, request_id):
    """Accept a wholesale payment request"""
    if request.user.is_authenticated:
        try:
            from store.models import PaymentRequest, Cashier
            payment_request = PaymentRequest.objects.get(request_id=request_id, payment_type='wholesale')
            
            # Check if user is a cashier or admin
            if not (hasattr(request.user, 'cashier') or request.user.is_superuser or 
                (hasattr(request.user, 'profile') and request.user.profile and 
                 request.user.profile.user_type in ['Admin', 'Manager'])):
                messages.error(request, 'You are not authorized to accept wholesale payment requests.')
                return redirect('wholesale:wholesale_cashier_dashboard')
            
            if payment_request.status != 'pending':
                messages.error(request, 'This wholesale payment request has already been processed.')
                return redirect('wholesale:wholesale_cashier_dashboard')
            
            # Assign to cashier if not admin
            if hasattr(request.user, 'cashier'):
                payment_request.cashier = request.user.cashier
            
            payment_request.status = 'accepted'
            payment_request.accepted_at = timezone.now()
            payment_request.save()
            
            messages.success(request, f'Wholesale payment request {request_id} accepted successfully. You can now complete the payment.')
            return redirect('wholesale:wholesale_payment_request_detail', request_id=request_id)
            
        except PaymentRequest.DoesNotExist:
            messages.error(request, 'Wholesale payment request not found.')
            return redirect('wholesale:wholesale_cashier_dashboard')
    
    return redirect('store:index')


@login_required
def reject_wholesale_payment_request(request, request_id):
    """Reject a wholesale payment request"""
    if request.user.is_authenticated:
        try:
            from store.models import PaymentRequest, Cashier
            payment_request = PaymentRequest.objects.get(request_id=request_id, payment_type='wholesale')
            
            # Check if user is a cashier or admin
            if not (hasattr(request.user, 'cashier') or request.user.is_superuser or 
                (hasattr(request.user, 'profile') and request.user.profile and 
                 request.user.profile.user_type in ['Admin', 'Manager'])):
                messages.error(request, 'You are not authorized to reject wholesale payment requests.')
                return redirect('wholesale:wholesale_cashier_dashboard')
            
            if payment_request.status != 'pending':
                messages.error(request, 'This wholesale payment request has already been processed.')
                return redirect('wholesale:wholesale_cashier_dashboard')
            
            # Update status
            payment_request.status = 'rejected'
            payment_request.save()
            
            # Return items to stock and clear cart
            for payment_item in payment_request.items.all():
                if payment_item.wholesale_item:
                    payment_item.wholesale_item.stock += payment_item.quantity
                    payment_item.wholesale_item.save()
            
            # Clear the wholesale cart for the dispenser whose payment request was rejected
            try:
                # Clear all wholesale cart items for the original dispenser
                from store.models import WholesaleCart
                WholesaleCart.objects.filter(user=payment_request.dispenser).delete()
                
                # Comprehensive wholesale cart session cleanup for the dispenser
                from store.cart_utils import cleanup_cart_session_after_receipt
                # We need to create a mock request object for the cart cleanup
                # Since we can't access the original dispenser's request,
                # we'll clear the cart items directly
                logger.info(f"Cleared wholesale cart for user {payment_request.dispenser.username} after wholesale payment request rejection")
                
            except Exception as e:
                logger.warning(f"Error clearing wholesale cart after payment request rejection: {e}")
            
            messages.success(request, f'Wholesale payment request {request_id} rejected, items returned to stock, and cart cleared.')
            return redirect('wholesale:wholesale_cashier_dashboard')
            
        except PaymentRequest.DoesNotExist:
            messages.error(request, 'Wholesale payment request not found.')
            return redirect('wholesale:wholesale_cashier_dashboard')
    
    return redirect('store:index')


@transaction.atomic
@login_required
def complete_wholesale_payment_request(request, request_id):
    """Complete a wholesale payment request and generate wholesale receipt"""
    if request.user.is_authenticated:
        try:
            from store.models import PaymentRequest, Sales, Receipt, SalesItem, DispensingLog, Cashier, WholesaleReceiptPayment, WholesaleReceipt
            from customer.models import WholesaleCustomer, WholesaleCustomerWallet, TransactionHistory
            from decimal import Decimal
            payment_request = PaymentRequest.objects.get(request_id=request_id, payment_type='wholesale')
            
            # Check if user is the assigned cashier or admin
            if not (hasattr(request.user, 'cashier') or request.user.is_superuser or 
                (hasattr(request.user, 'profile') and request.user.profile and 
                 request.user.profile.user_type in ['Admin', 'Manager'])):
                messages.error(request, 'You are not authorized to complete this wholesale payment request.')
                return redirect('wholesale:wholesale_cashier_dashboard')
            
            if payment_request.status != 'accepted':
                messages.error(request, 'This wholesale payment request must be accepted first.')
                return redirect('wholesale:wholesale_cashier_dashboard')
            
            
            
            if request.method == 'POST':
                payment_method = request.POST.get('payment_method')
                payment_status = request.POST.get('payment_status', 'Paid')
                payment_type = request.POST.get('payment_type', 'single')
                
                if not payment_method:
                    messages.error(request, 'Payment method is required.')
                    return redirect('wholesale:wholesale_cashier_dashboard')
                
                # Validate payment method for split payments
                if payment_type == 'split':
                    payment_method_1 = request.POST.get('payment_method_1')
                    payment_method_2 = request.POST.get('payment_method_2')
                    if not payment_method_1 or not payment_method_2:
                        messages.error(request, 'Both payment methods are required for split payments.')
                        return redirect('wholesale:wholesale_cashier_dashboard')
                
                # Get cashier object if user is a cashier
                cashier = None
                if hasattr(request.user, 'cashier'):
                    cashier = request.user.cashier

                # Create wholesale sales and receipt
                sales = Sales.objects.create(
                    user=payment_request.dispenser,
                    wholesale_customer=payment_request.wholesale_customer,
                    total_amount=payment_request.total_amount
                )

                # Create wholesale receipt
                receipt = WholesaleReceipt.objects.create(
                    wholesale_customer=payment_request.wholesale_customer,
                    sales=sales,
                    cashier=cashier,
                    buyer_name=payment_request.wholesale_customer.name if payment_request.wholesale_customer else 'WALK-IN CUSTOMER',
                    buyer_address=payment_request.wholesale_customer.address if payment_request.wholesale_customer else '',
                    total_amount=payment_request.total_amount,
                    payment_method=payment_method if payment_type != 'split' else 'Split',
                    status=payment_status
                )
                
                # Handle wallet payments for registered wholesale customers
                wallet_went_negative = False
                if payment_request.wholesale_customer:
                    if payment_type == 'single' and payment_method == 'Wallet':
                        wallet = WholesaleCustomerWallet.objects.get(customer=payment_request.wholesale_customer)
                        wallet_balance_before = wallet.balance
                        wallet.balance -= payment_request.total_amount
                        wallet.save()
                        
                        # Check if wallet went negative
                        if wallet_balance_before >= 0 and wallet.balance < 0:
                            wallet_went_negative = True
                            receipt.wallet_went_negative = True
                            receipt.save()
                        
                        # Create transaction history
                        TransactionHistory.objects.create(
                            wholesale_customer=payment_request.wholesale_customer,
                            user=request.user,
                            transaction_type='purchase',
                            amount=payment_request.total_amount,
                            description=f'Wholesale purchase payment from wallet (Receipt ID: {receipt.receipt_id})'
                        )
                        
                    elif payment_type == 'split':
                        # Handle split payment with wallet
                        payment_amount_1 = Decimal(request.POST.get('payment_amount_1', '0'))
                        payment_amount_2 = Decimal(request.POST.get('payment_amount_2', '0'))
                        
                        if payment_method_1 == 'Wallet' or payment_method_2 == 'Wallet':
                            wallet = WholesaleCustomerWallet.objects.get(customer=payment_request.wholesale_customer)
                            
                            if payment_method_1 == 'Wallet':
                                wallet_balance_before = wallet.balance
                                wallet.balance -= payment_amount_1
                                wallet.save()
                                if wallet_balance_before >= 0 and wallet.balance < 0:
                                    wallet_went_negative = True
                                    receipt.wallet_went_negative = True
                                    receipt.save()
                                
                                TransactionHistory.objects.create(
                                    wholesale_customer=payment_request.wholesale_customer,
                                    user=request.user,
                                    transaction_type='purchase',
                                    amount=payment_amount_1,
                                    description=f'Wholesale purchase payment from wallet - Payment 1 (Receipt ID: {receipt.receipt_id})'
                                )
                            
                            if payment_method_2 == 'Wallet':
                                wallet_balance_before = wallet.balance
                                wallet.balance -= payment_amount_2
                                wallet.save()
                                if wallet_balance_before >= 0 and wallet.balance < 0:
                                    wallet_went_negative = True
                                    receipt.wallet_went_negative = True
                                    receipt.save()
                                
                                TransactionHistory.objects.create(
                                    wholesale_customer=payment_request.wholesale_customer,
                                    user=request.user,
                                    transaction_type='purchase',
                                    amount=payment_amount_2,
                                    description=f'Wholesale purchase payment from wallet - Payment 2 (Receipt ID: {receipt.receipt_id})'
                                )
                
                # Create WholesaleSalesItem records from payment request items
                for payment_item in payment_request.items.all():
                    if payment_item.wholesale_item:
                        # Create wholesale sales item
                        WholesaleSalesItem.objects.create(
                            sales=sales,
                            item=payment_item.wholesale_item,
                            price=payment_item.unit_price,
                            quantity=payment_item.quantity,
                            discount_amount=payment_item.discount_amount,
                            brand=payment_item.brand
                        )
                        
                        # Update stock
                        payment_item.wholesale_item.stock -= payment_item.quantity
                        payment_item.wholesale_item.save()
                        
                        # Create dispensing log for wholesale
                        DispensingLog.objects.create(
                            user=payment_request.dispenser,
                            name=payment_item.item_name,
                            brand=payment_item.brand,
                            dosage_form=None,  # Could be added if needed
                            unit=payment_item.unit,
                            quantity=payment_item.quantity,
                            amount=payment_item.subtotal,
                            discount_amount=payment_item.discount_amount,
                            status='Dispensed'
                        )
                
                # Create split payment records if this is a split payment
                if payment_type == 'split':
                    payment_amount_1 = Decimal(request.POST.get('payment_amount_1', '0'))
                    payment_amount_2 = Decimal(request.POST.get('payment_amount_2', '0'))
                    
                    WholesaleReceiptPayment.objects.create(
                        receipt=receipt,
                        amount=payment_amount_1,
                        payment_method=payment_method_1,
                        status='Paid',
                        date=receipt.date
                    )
                    
                    WholesaleReceiptPayment.objects.create(
                        receipt=receipt,
                        amount=payment_amount_2,
                        payment_method=payment_method_2,
                        status='Paid',
                        date=receipt.date
                    )
                else:
                    # For single payments, also create a payment record for consistency
                    WholesaleReceiptPayment.objects.create(
                        receipt=receipt,
                        amount=receipt.total_amount,
                        payment_method=payment_method,
                        status='Paid',
                        date=receipt.date
                    )
                
                # Update payment request and link to wholesale receipt
                payment_request.status = 'completed'
                payment_request.completed_at = timezone.now()
                payment_request.wholesale_receipt = receipt  # Link the wholesale receipt
                payment_request.notes = request.POST.get('notes', '')  # Save cashier notes
                payment_request.save()
                
                # Clear the original wholesale cart items that were used to create this payment request
                try:
                    cart_items = WholesaleCart.objects.filter(user=payment_request.dispenser)
                    # Remove cart items that correspond to the payment request items
                    for payment_item in payment_request.items.all():
                        if payment_item.wholesale_item:
                            cart_items.filter(item=payment_item.wholesale_item).delete()
                    
                    # Comprehensive cart session cleanup after receipt generation
                    from store.cart_utils import cleanup_cart_session_after_receipt
                    cleanup_summary = cleanup_cart_session_after_receipt(request, 'wholesale')
                    logger.info(f"Wholesale cart session cleanup after payment request completion: {cleanup_summary}")
                except Exception as e:
                    logger.warning(f"Error clearing wholesale cart after payment request completion: {e}")
                
                # Inform about negative wallet balance if applicable
                if wallet_went_negative:
                    messages.warning(request, f'The customer wallet went negative during this payment transaction.')
                
                messages.success(request, f'Wholesale payment request {request_id} completed successfully. Receipt generated.')
                return redirect('wholesale:wholesale_receipt_detail', receipt_id=receipt.receipt_id)
            
            else:
                # Show payment completion form for GET requests
                return render(request, 'wholesale/complete_wholesale_payment_request.html', {
                    'payment_request': payment_request,
                })
            
        except PaymentRequest.DoesNotExist:
            messages.error(request, 'Wholesale payment request not found.')
            return redirect('wholesale:wholesale_cashier_dashboard')
        except Exception as e:
            logger.error(f"Error completing wholesale payment request: {e}")
            messages.error(request, f'Error processing payment request: {str(e)}')
            return redirect('wholesale:wholesale_cashier_dashboard')
    
    return redirect('store:index')



