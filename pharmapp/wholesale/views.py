from django.db import transaction
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.utils import timezone
from django.utils.timezone import now
from datetime import timedelta, datetime
from decimal import Decimal
from store.models import *
from store.forms import *
from supplier.models import *
from customer.models import *
from .forms import *
from django.db import transaction
from django.http import JsonResponse
from django.contrib.auth.decorators import login_required, user_passes_test
from django.views.decorators.http import require_POST
import uuid
from store.views import get_daily_sales, get_monthly_sales_with_expenses
from django.db.models import Sum, Q, F
from django.contrib.auth.decorators import login_required, user_passes_test
from django.shortcuts import render, get_object_or_404
from django.http import HttpResponse
from django.contrib import messages
from django.db.models import Q
from store.models import WholesaleItem  # Updated import path
import logging

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
    query = request.GET.get('q', '')
    if query:
        items = WholesaleItem.objects.filter(
            Q(name__icontains=query) |
            Q(brand__icontains=query) |
            Q(dosage_form__icontains=query)
        ).order_by('name')
    else:
        items = WholesaleItem.objects.all().order_by('name')[:20]  # Limit to 20 items if no query

    # Convert items to JSON-serializable format
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

# Admin check
def is_admin(user):
    return user.is_authenticated and user.is_superuser or user.is_staff

def wholesale_page(request):
    return render(request, 'wholesale_page.html')

@login_required
def wholesales(request):
    if request.user.is_authenticated:
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

        # Calculate values using the threshold from settings
        total_purchase_value = sum(item.cost * item.stock for item in items)
        total_stock_value = sum(item.price * item.stock for item in items)
        total_profit = total_stock_value - total_purchase_value

        # Identify low-stock items using the threshold from settings
        low_stock_items = [item for item in items if item.stock <= low_stock_threshold]

        context = {
            'items': items,
            'low_stock_items': low_stock_items,
            'settings_form': settings_form,
            'low_stock_threshold': low_stock_threshold,
            'total_purchase_value': total_purchase_value,
            'total_stock_value': total_stock_value,
            'total_profit': total_profit,
        }
        return render(request, 'wholesale/wholesales.html', context)
    else:
        return redirect('store:index')

@login_required
def search_wholesale_item(request):
    if request.user.is_authenticated:
        query = request.GET.get('search', '').strip()
        if query:
            # Search across multiple fields using Q objects
            items = WholesaleItem.objects.filter(
                Q(name__icontains=query) |  # Search by name
                Q(brand__icontains=query) #|  # Search by brand name
                # Q(category__icontains=query)  # Search by category
            )
        else:
            items = WholesaleItem.objects.filter(name__icontains=query) if query else WholesaleItem.objects.all()
        return render(request, 'partials/wholesale_search.html', {'items': items})
    else:
        return redirect('store:index')


@user_passes_test(is_admin)
@login_required
def add_to_wholesale(request):
    if request.user.is_authenticated:
        if request.method == 'POST':
            form = addWholesaleForm(request.POST)
            if form.is_valid():
                item = form.save(commit=False)
                item.save()
                messages.success(request, 'Item added successfully')
                return redirect('wholesale:wholesales')
        low_stock_threshold = 10  # Adjust this number as needed

        # Calculate total purchase value and total stock value
        items = WholesaleItem.objects.all()
        total_purchase_value = sum(item.cost * item.stock for item in items)
        total_stock_value = sum(item.price * item.stock for item in items)
        total_profit = total_stock_value - total_purchase_value

        low_stock_items = [item for item in items if item.stock <= low_stock_threshold]


        context = {
            'items': items,
            'low_stock_items': low_stock_items,
            'total_purchase_value': total_purchase_value,
            'total_stock_value': total_stock_value,
            'total_profit': total_profit,
        }
        return render(request, 'wholesale/wholesales.html', context)
    else:
        return render(request, 'store/index.html')

@login_required
def search_wholesale_item(request):
    if request.user.is_authenticated:
        query = request.GET.get('search', '').strip()
        if query:
            # Search across multiple fields using Q objects
            items = WholesaleItem.objects.filter(
                Q(name__icontains=query) |  # Search by name
                Q(brand__icontains=query) #|  # Search by brand name
                # Q(category__icontains=query)  # Search by category
            )
        else:
            items = WholesaleItem.objects.filter(name__icontains=query) if query else WholesaleItem.objects.all()
        return render(request, 'partials/wholesale_search.html', {'items': items})
    else:
        return redirect('store:index')


@user_passes_test(is_admin)
@login_required
def add_to_wholesale(request):
    if request.user.is_authenticated:
        if request.method == 'POST':
            form = addWholesaleForm(request.POST)
            if form.is_valid():
                item = form.save(commit=False)
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



@user_passes_test(is_admin)
def edit_wholesale_item(request, pk):
    if request.user.is_authenticated:
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
                return redirect('wholesale:wholesales')
            else:
                print("Form errors:", form.errors)  # Debugging output
                messages.error(request, 'Failed to update item')
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

                        # Process wallet refund if applicable
                        if sales.customer and hasattr(sales.customer, 'wholesale_customer_wallet'):
                            wallet = sales.customer.wholesale_customer_wallet
                            wallet.balance += refund_amount
                            wallet.save()

                            # Log the refund transaction
                            TransactionHistory.objects.create(
                                customer=sales.customer,
                                transaction_type='refund',
                                amount=refund_amount,
                                description=f'Refund for {return_quantity} of {item.name}'
                            )
                            messages.success(
                                request,
                                f'{return_quantity} of {item.name} successfully returned, and ₦{refund_amount} refunded to the wallet.'
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
@user_passes_test(is_admin)
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
def dispense_wholesale(request):
    if request.user.is_authenticated:
        if request.method == 'POST':
            form = wholesaleDispenseForm(request.POST)
            if form.is_valid():
                q = form.cleaned_data['q']
                results = WholesaleItem.objects.filter(name__icontains=q)
        else:
            form = wholesaleDispenseForm()
            results = None
        return render(request, 'partials/wholesale_dispense_modal.html', {'form': form, 'results': results})
    else:
        return redirect('store:index')


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
            cart_items = Cart.objects.all()
            total_price = sum(cart_item.item.price * cart_item.quantity for cart_item in cart_items)
            # total_discount = sum(cart_item.discount_amount for cart_item in cart_items)
            # total_discounted_price = total_price - total_discount

            # Return JSON data for HTMX update
            return JsonResponse({
                'cart_items_count': cart_items.count(),
                'total_price': float(total_price),
                # 'total_discount': float(total_discount),
                # 'total_discounted_price': float(total_discounted_price),
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
        # Store wholesale customer ID in session for later use
        request.session['wholesale_customer_id'] = customer.id
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
                        subtotal = (item.price * quantity)
                        total_cost += subtotal

                        # Update or create WholesaleSalesItem
                        sales_item, created = WholesaleSalesItem.objects.get_or_create(
                            sales=sales,
                            item=item,
                            defaults={'quantity': quantity, 'price': item.price}
                        )
                        if not created:
                            sales_item.quantity += quantity
                            sales_item.save()

                        # Update the receipt
                        receipt.total_amount += subtotal
                        receipt.save()

                        # **Log Item Selection History (Purchase)**
                        WholesaleSelectionHistory.objects.create(
                            wholesale_customer=customer,
                            user=request.user,
                            item=item,
                            quantity=quantity,
                            action=action,
                            unit_price=item.price,
                        )

                    elif action == 'return':
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

                            refund_amount = (item.price * quantity)
                            sales.total_amount -= refund_amount
                            sales.save()

                            DispensingLog.objects.create(
                                user=request.user,
                                name=item.name,
                                unit=unit,
                                quantity=quantity,
                                amount=refund_amount,
                                status='Partially Returned' if sales_item.quantity > 0 else 'Returned'  # Status based on remaining quantity
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

                            total_cost -= refund_amount

                            # Update the receipt
                            receipt.total_amount -= refund_amount
                            receipt.save()

                        except WholesaleSalesItem.DoesNotExist:
                            messages.warning(request, f"Item {item.name} is not part of the sales.")
                            return redirect('wholesale:select_wholesale_items', pk=pk)

                except WholesaleItem.DoesNotExist:
                    messages.warning(request, 'One of the selected items does not exist.')
                    return redirect('wholesale:select_wholesale_items', pk=pk)

            # Update customer's wallet balance
            try:
                wallet = customer.wholesale_customer_wallet
                if action == 'purchase':
                    wallet.balance -= total_cost
                elif action == 'return':
                    wallet.balance += abs(total_cost)
                wallet.save()
            except WholesaleCustomerWallet.DoesNotExist:
                messages.warning(request, 'Customer does not have a wallet.')
                return redirect('wholesale:select_wholesale_items', pk=pk)

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
            'wallet_balance': wallet_balance
        })
    else:
        return redirect('store:index')





@login_required
def wholesale_cart(request):
    if request.user.is_authenticated:
        cart_items = WholesaleCart.objects.select_related('item').all()
        total_price, total_discount = 0, 0

        if request.method == 'POST':
            # Process each discount form submission
            for cart_item in cart_items:
                # Fetch the discount amount using cart_item.id in the input name
                discount = int(request.POST.get(f'discount_amount-{cart_item.id}', 0))
                # cart_item.discount_amount = max(discount, 0)
                cart_item.save()

        # Calculate totals
        for cart_item in cart_items:
            # Update the price field to match the item's current price
            if cart_item.price != cart_item.item.price:
                cart_item.price = cart_item.item.price
                # This will trigger the save method which recalculates subtotal
                cart_item.save()

            # Add to total price
            total_price += cart_item.subtotal
            # total_discount += cart_item.discount_amount

        final_total = total_price - total_discount

        total_discounted_price = total_price - total_discount
        return render(request, 'wholesale/wholesale_cart.html', {
            'cart_items': cart_items,
            'total_discount': total_discount,
            'total_price': total_price,
            'total_discounted_price': total_discounted_price,
            'final_total': final_total,
        })
    else:
        return redirect('store:index')



@login_required
def update_wholesale_cart_quantity(request, pk):
    if request.user.is_authenticated:
        cart_item = get_object_or_404(WholesaleCart, id=pk)
        if request.method == 'POST':
            quantity_to_return = Decimal(request.POST.get('quantity', 0))
            if 0 < quantity_to_return <= cart_item.quantity:
                cart_item.item.stock += quantity_to_return
                cart_item.item.save()

                # Adjust DispensingLog entries
                DispensingLog.objects.filter(
                    user=request.user,
                    name=cart_item.item.name,
                    quantity=quantity_to_return,
                    amount=cart_item.item.price * quantity_to_return
                ).delete()

                # Update cart item quantity or remove it
                cart_item.quantity -= quantity_to_return
                cart_item.save() if cart_item.quantity > 0 else cart_item.delete()
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

                    # Calculate total amount to potentially refund
                    total_refund = sum(
                        item.item.price * item.quantity
                        for item in cart_items
                    )

                    for cart_item in cart_items:
                        # Return items to stock
                        cart_item.item.stock += cart_item.quantity
                        cart_item.item.save()

                        # Remove DispensingLog entries
                        DispensingLog.objects.filter(
                            user=request.user,
                            name=cart_item.item.name,
                            quantity=cart_item.quantity,
                            status='Dispensed'  # Only remove dispensed logs
                        ).delete()

                    # Find any pending sales entries (those without receipts)
                    sales_entries = Sales.objects.filter(
                        user=request.user,
                        wholesale_customer__isnull=False,  # Only wholesale sales
                        receipts__isnull=True  # Pending sales have no receipts
                    ).distinct()

                    for sale in sales_entries:
                        if sale.wholesale_customer:
                            try:
                                wallet = sale.wholesale_customer.wholesale_customer_wallet
                                if wallet and total_refund > 0:
                                    wallet.balance += total_refund
                                    wallet.save()

                                    # Create transaction history for the refund
                                    TransactionHistory.objects.create(
                                        customer=sale.wholesale_customer,
                                        transaction_type='refund',
                                        amount=total_refund,
                                        description='Cart cleared - items returned'
                                    )
                            except WholesaleCustomerWallet.DoesNotExist:
                                messages.warning(
                                    request,
                                    f'Wallet not found for customer {sale.wholesale_customer.name}'
                                )

                        # Delete associated sales items first
                        sale.wholesale_sales_items.all().delete()
                        # Delete the sale
                        sale.delete()

                    # Clear cart items
                    cart_items.delete()

                    messages.success(
                        request,
                        'Cart cleared successfully. All items returned to stock and transactions reversed.'
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

        cart_items = WholesaleCart.objects.all()
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

        # Get wholesale customer ID from session if it exists
        wholesale_customer_id = request.session.get('wholesale_customer_id')
        wholesale_customer = None
        if wholesale_customer_id:
            try:
                wholesale_customer = WholesaleCustomer.objects.get(id=wholesale_customer_id)
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
                if not payment_method:
                    # Default payment method is Wallet for registered customers, Cash for walk-in
                    if sales.wholesale_customer:  # If this is a registered customer
                        payment_method = "Wallet"  # Default for registered customers
                    else:  # For walk-in customers
                        payment_method = "Cash"  # Default for walk-in customers

                if not status:
                    # Default status is "Paid" for all customers
                    status = "Paid"

                print(f"After initial defaults - Payment Method: {payment_method}, Status: {status}")

                # Ensure payment_method and status have valid values
                if payment_method not in ["Cash", "Wallet", "Transfer"]:
                    if sales.wholesale_customer:
                        payment_method = "Wallet"  # Default for registered customers
                    else:
                        payment_method = "Cash"  # Default for walk-in customers

                if status not in ["Paid", "Unpaid"]:
                    status = "Paid"  # Default status

                # Force the values for debugging purposes
                print(f"\n==== FORCING VALUES FOR RECEIPT =====")
                print(f"Customer: {sales.wholesale_customer}")
                print(f"Payment Method: {payment_method}")
                print(f"Status: {status}\n")

                # Generate a unique receipt ID using uuid
                import uuid
                receipt_id = str(uuid.uuid4())[:5]  # Use first 5 characters of a UUID

                # Create the receipt WITHOUT payment method and status first
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
                receipt.save()

                # Double-check that the payment method and status were set correctly
                # Refresh from database to ensure we see the actual saved values
                receipt.refresh_from_db()
                print(f"\n==== CREATED RECEIPT =====")
                print(f"Receipt ID: {receipt.receipt_id}")
                print(f"Payment Method: {receipt.payment_method}")
                print(f"Status: {receipt.status}\n")
        except Exception as e:
            print(f"Error processing receipt: {e}")
            messages.error(request, "An error occurred while processing the receipt.")
            return redirect('wholesale:wholesale_cart')

        for cart_item in cart_items:
            WholesaleSalesItem.objects.get_or_create(
                sales=sales,
                item=cart_item.item,
                defaults={'quantity': cart_item.quantity, 'price': cart_item.item.price}
            )

            subtotal = cart_item.item.price * cart_item.quantity
            DispensingLog.objects.create(
                user=request.user,
                name=cart_item.item.name,
                unit=cart_item.item.unit,
                quantity=cart_item.quantity,
                amount=subtotal,
                status="Dispensed"
            )

        request.session['receipt_data'] = {
            'total_price': float(total_price),
            'total_discount': float(total_discount),
            'buyer_address': buyer_address,
        }
        request.session['receipt_id'] = str(receipt.receipt_id)

        cart_items.delete()

        # Clear wholesale_customer_id from session after receipt is created
        if 'wholesale_customer_id' in request.session:
            del request.session['wholesale_customer_id']

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

        # Force the payment method and status one last time if needed
        has_customer = sales.wholesale_customer is not None
        if has_customer:
            if receipt.payment_method != 'Wallet':
                print(f"Forcing payment method to Wallet for customer {receipt.wholesale_customer.name}")
                receipt.payment_method = 'Wallet'
                receipt.save()

            # Status is always "Paid" for all customers
            if receipt.status != 'Paid':
                print(f"Forcing status to Paid for customer {receipt.wholesale_customer.name}")
                receipt.status = 'Paid'
                receipt.save()

            receipt.refresh_from_db()

        # Render to the wholesale_receipt template
        return render(request, 'wholesale/wholesale_receipt.html', {
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
        })
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

                        refund_amount = (item.price * quantity)
                        sales.total_amount -= refund_amount
                        sales.save()

                        DispensingLog.objects.create(
                            user=request.user,
                            name=item.name,
                            unit=unit,
                            quantity=quantity,
                            amount=refund_amount,
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

            # Update customer's wallet balance
            try:
                wallet = customer.wholesale_customer_wallet
                wallet.balance += abs(total_refund)
                wallet.save()
            except WholesaleCustomerWallet.DoesNotExist:
                messages.warning(request, 'Customer does not have a wallet.')
                return redirect('wholesale:select_wholesale_items', pk=pk)

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
        # Get the date query from the GET request
        date_query = request.GET.get('date', '').strip()


        receipts = WholesaleReceipt.objects.all()
        if date_query:
            try:
                # Parse date query
                date_object = datetime.strptime(date_query, '%Y-%m-%d').date()
                # Adjust filtering for DateTimeField (if necessary)
                receipts = receipts.filter(date__date=date_object)
            except ValueError:
                print("Invalid date format")

        # Order receipts by date
        receipts = receipts.order_by('-date')

        return render(request, 'wholesale/search_wholesale_receipts.html', {'receipts': receipts})
    else:
        return redirect('store:index')



@login_required
def wholesale_receipt_detail(request, receipt_id):
    if request.user.is_authenticated:
        # Retrieve the existing receipt
        receipt = get_object_or_404(WholesaleReceipt, receipt_id=receipt_id)

        # If the form is submitted, update buyer details
        if request.method == 'POST':
            # Only update buyer_name if there's no wholesale_customer associated
            if not receipt.wholesale_customer:
                buyer_name = request.POST.get('buyer_name', '').strip() or 'WALK-IN CUSTOMER'
                receipt.buyer_name = buyer_name

            buyer_address = request.POST.get('buyer_address')
            if buyer_address:
                receipt.buyer_address = buyer_address

            payment_method = request.POST.get('payment_method')
            if payment_method:
                receipt.payment_method = payment_method

            status = request.POST.get('status')
            if status:
                receipt.status = status

            receipt.save()

            # Redirect to the same page to reflect updated details
            return redirect('wholesale:wholesale_receipt_detail', receipt_id=receipt.receipt_id)

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

        payment_methods = ["Cash", "Wallet", "Transfer"]
        statuses = ["Paid", "Unpaid"]

        return render(request, 'partials/wholesale_receipt_detail.html', {
            'receipt': receipt,
            'sales_items': sales_items,
            'total_price': total_price,
            'total_discount': total_discount,
            'total_discounted_price': total_discounted_price,
            'payment_methods': payment_methods,
            'statuses': statuses,
            'user': request.user,
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



@user_passes_test(is_admin)
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
@user_passes_test(is_admin)
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
                wallet.add_funds(amount)
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
@user_passes_test(is_admin)
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




@user_passes_test(is_admin)
@login_required
def add_wholesale_procurement(request):
    if request.user.is_authenticated:
        ProcurementItemFormSet = modelformset_factory(
            WholesaleProcurementItem,
            form=WholesaleProcurementItemForm,
            extra=1,  # Allow at least one empty form to be displayed
            can_delete=True  # Allow deleting items dynamically
        )

        if request.method == 'POST':
            procurement_form = WholesaleProcurementForm(request.POST)
            formset = ProcurementItemFormSet(request.POST, queryset=WholesaleProcurementItem.objects.none())
            action = request.POST.get('action', 'save')

            if procurement_form.is_valid() and formset.is_valid():
                procurement = procurement_form.save(commit=False)
                procurement.created_by = request.user  # Assuming the user is authenticated

                # Set status based on action
                if action == 'pause':
                    procurement.status = 'draft'
                else:
                    procurement.status = 'completed'

                procurement.save()

                for form in formset:
                    if form.cleaned_data.get('item_name'):  # Save only valid items
                        procurement_item = form.save(commit=False)
                        procurement_item.procurement = procurement
                        procurement_item.save()

                # Calculate and update the total
                procurement.calculate_total()

                if action == 'pause':
                    messages.success(request, "Procurement saved as draft. You can continue later.")
                    return redirect('wholesale:wholesale_procurement_list')  # Replace with your actual URL name
                else:
                    messages.success(request, "Procurement and items added successfully!")
                    return redirect('wholesale:wholesale_procurement_list')  # Replace with your actual URL name
            else:
                messages.error(request, "Please correct the errors below.")
        else:
            # Check if we're continuing a draft procurement
            draft_id = request.GET.get('draft_id')
            if draft_id:
                try:
                    draft_procurement = WholesaleProcurement.objects.get(id=draft_id, status='draft')
                    procurement_form = WholesaleProcurementForm(instance=draft_procurement)
                    formset = ProcurementItemFormSet(queryset=draft_procurement.items.all())
                except WholesaleProcurement.DoesNotExist:
                    messages.error(request, "Draft procurement not found.")
                    procurement_form = WholesaleProcurementForm()
                    formset = ProcurementItemFormSet(queryset=WholesaleProcurementItem.objects.none())
            else:
                procurement_form = WholesaleProcurementForm()
                formset = ProcurementItemFormSet(queryset=WholesaleProcurementItem.objects.none())

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



def wholesale_procurement_form(request):
    if request.user.is_authenticated:
        # Create an empty formset for the items
        item_formset = ProcurementItemFormSet(queryset=WholesaleProcurementItem.objects.none())  # Replace with your model if needed

        # Get the empty form (form for the new item)
        new_form = item_formset.empty_form

        # Render the HTML for the new form
        return render(request, 'wholesale/wholesale_procurement_form.html', {'form': new_form})
    else:
        return redirect('store:index')


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


def search_wholesale_procurement(request):
    if request.user.is_authenticated:
        # Base query with calculated total and ordering
        procurements = (
            WholesaleProcurement.objects.annotate(calculated_total=Sum('items__subtotal'))
            .order_by('-date')
        )

        # Get search parameters from the request
        name_query = request.GET.get('name', '').strip()

        # Apply filters if search parameters are provided
        if name_query:
            procurements = procurements.filter(supplier__name__icontains=name_query)

        # Render the filtered results
        return render(request, 'partials/search_wholesale_procurement.html', {
            'procurements': procurements,
        })
    else:
        return redirect('store:index')


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



@user_passes_test(is_admin)
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
                            expected_quantity=item.stock,
                            actual_quantity=0,
                            status='pending'
                        )
                    )

            WholesaleStockCheckItem.objects.bulk_create(stock_check_items)

            messages.success(request, "Stock check created successfully.")
            return redirect('wholesale:update_wholesale_stock_check', stock_check.id)

        return render(request, 'wholesale/create_wholesale_stock_check.html')
    else:
        return redirect('store:index')


@user_passes_test(is_admin)
@login_required
def update_wholesale_stock_check(request, stock_check_id):
    if request.user.is_authenticated:
        stock_check = get_object_or_404(WholesaleStockCheck, id=stock_check_id)
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

                    # If zero_empty_items is True and both expected and actual are 0, set to 0
                    if zero_empty_items and stock_item.expected_quantity == 0 and int(actual_qty) == 0:
                        stock_item.actual_quantity = 0
                    else:
                        stock_item.actual_quantity = int(actual_qty)

                    stock_items.append(stock_item)

            WholesaleStockCheckItem.objects.bulk_update(stock_items, ['actual_quantity'])
            messages.success(request, "Stock check updated successfully.")
            return redirect('wholesale:wholesale_stock_check_report', stock_check.id)

        return render(request, 'wholesale/update_wholesale_stock_check.html', {'stock_check': stock_check})
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


@user_passes_test(is_admin)
@login_required
def update_wholesale_stock_check(request, stock_check_id):
    if request.user.is_authenticated:
        stock_check = get_object_or_404(WholesaleStockCheck, id=stock_check_id)
        # if stock_check.status == 'completed':
        #     return redirect('store:stock_check_report', stock_check.id)

        if request.method == "POST":
            stock_items = []
            for item_id, actual_qty in request.POST.items():
                if item_id.startswith("item_"):
                    item_id = int(item_id.replace("item_", ""))
                    stock_item = WholesaleStockCheckItem.objects.get(stock_check=stock_check, item_id=item_id)
                    stock_item.actual_quantity = int(actual_qty)
                    stock_items.append(stock_item)
            WholesaleStockCheckItem.objects.bulk_update(stock_items, ['actual_quantity'])
            messages.success(request, "Stock check updated successfully.")
            return redirect('wholesale:update_wholesale_stock_check', stock_check.id)

        return render(request, 'wholesale/update_wholesale_stock_check.html', {'stock_check': stock_check})
    else:
        return redirect('store:index')


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



@user_passes_test(is_admin)
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


@user_passes_test(is_admin)
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


@user_passes_test(is_admin)
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


@user_passes_test(is_admin)
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



@user_passes_test(is_admin)
@login_required
def list_wholesale_stock_checks(request):
    # Get all StockCheck objects ordered by date (newest first)
    stock_checks = WholesaleStockCheck.objects.all().order_by('-date')
    context = {
        'stock_checks': stock_checks,
    }
    return render(request, 'wholesale/wholesale_stock_check_list.html', context)




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
#                 requested_quantity = int(request.POST.get("requested_quantity", 0))
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
            # Render form for a retail user to request items from wholesale
            wholesale_items = WholesaleItem.objects.all().order_by('name')
            return render(request, "store/retail_transfer_request.html", {"wholesale_items": wholesale_items})

        elif request.method == "POST":
            try:
                requested_quantity = int(request.POST.get("requested_quantity", 0))
                item_id = request.POST.get("item_id")
                from_wholesale = request.POST.get("from_wholesale", "false").lower() == "true"

                if not item_id or requested_quantity <= 0:
                    return JsonResponse({"success": False, "message": "Invalid input provided."}, status=400)

                # Get the source item based on transfer direction
                if from_wholesale:
                    source_item = get_object_or_404(Item, id=item_id)
                    transfer = TransferRequest.objects.create(
                        retail_item=source_item,
                        requested_quantity=requested_quantity,
                        from_wholesale=True,
                        status="pending",
                        created_at=timezone.now()
                    )
                else:
                    source_item = get_object_or_404(WholesaleItem, id=item_id)
                    transfer = TransferRequest.objects.create(
                        wholesale_item=source_item,
                        requested_quantity=requested_quantity,
                        from_wholesale=False,
                        status="pending",
                        created_at=timezone.now()
                    )

                messages.success(request, "Transfer request created successfully.")
                return JsonResponse({"success": True, "message": "Transfer request created successfully."})

            except (TypeError, ValueError) as e:
                return JsonResponse({"success": False, "message": str(e)}, status=400)
            except Exception as e:
                logger.error(f"Error in create_transfer_request: {str(e)}")
                return JsonResponse({"success": False, "message": "An error occurred."}, status=500)

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
        # For a wholesale-initiated request, the retail_item field is set.
        wholesale_pending_transfers = TransferRequest.objects.filter(status="pending", from_wholesale=False)
        return render(request, "wholesale/pending_wholesale_transfer_requests.html", {"wholesale_pending_transfers": wholesale_pending_transfers})
    else:
        return redirect('store:index')


@login_required
def wholesale_approve_transfer(request, transfer_id):
    if request.user.is_authenticated:
        """
        Approves a transfer request.
        For a wholesale-initiated request (from_wholesale=True), the source is the retail item
        and the destination is a wholesale item.
        The retail user can adjust the approved quantity before approval.
        """
        if request.method == "POST":
            transfer = get_object_or_404(TransferRequest, id=transfer_id)

            # Determine approved quantity (if adjusted) or use the originally requested amount.
            approved_qty_param = request.POST.get("approved_quantity")
            if approved_qty_param:
                try:
                    approved_qty = int(approved_qty_param)
                except ValueError:
                    messages.error(request, 'Invalid Qty!')
                    return render(request, 'wholesale/create_wholesale_transfer_request.html')
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
                messages.error(request, "Not enough stock in source!")
                return JsonResponse({"success": False, "message": "Not enough stock in source!"}, status=400)

            # Deduct approved quantity from the source item.
            source_item.stock -= approved_qty
            source_item.save()

            # Increase stock in the destination item.
            destination_item.stock += approved_qty
            destination_item.cost = source_item.cost
            destination_item.exp_date = source_item.exp_date
            destination_item.markup = source_item.markup
            destination_item.price = source_item.price
            destination_item.save()

            # Update the transfer request.
            transfer.status = "approved"
            transfer.approved_quantity = approved_qty
            transfer.save()

            messages.success(request, f"Transfer approved: {approved_qty} {source_item.name} moved from wholesale to retail.")
            return JsonResponse({
                "success": True,
                "message": f"Transfer approved with quantity {approved_qty}.",
                "destination_stock": destination_item.stock,
            })
        return JsonResponse({"success": False, "message": "Invalid request method!"}, status=400)
    else:
        return redirect('store:index')



# Reject a transfer request sent from retail
@login_required
def reject_wholesale_transfer(request, transfer_id):
    if request.user.is_authenticated:
        """
        Rejects a transfer request.
        """
        if request.method == "POST":
            transfer = get_object_or_404(TransferRequest, id=transfer_id)
            transfer.status = "rejected"
            transfer.save()
            messages.error(request, "Transfer request rejected.")
            return JsonResponse({"success": True, "message": "Transfer rejected."})
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




