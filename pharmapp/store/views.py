from django.views.decorators.http import require_http_methods
from django.core.cache import cache
from django.db import transaction, IntegrityError
from collections import defaultdict
from decimal import Decimal
import json
from django.views.decorators.csrf import csrf_exempt
from django.http import HttpResponse, JsonResponse
from django.db.models.functions import TruncMonth, TruncDay
from django.shortcuts import get_object_or_404, render, redirect
from customer.models import Wallet
from django.forms import formset_factory
from .models import *
from .forms import *
from django.contrib import messages
from django.db import transaction
from datetime import datetime,  timedelta
from django.views.decorators.http import require_POST
from django.db.models import Q, F, ExpressionWrapper, Sum, DecimalField
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib.auth import authenticate, login, logout, update_session_auth_hash
import logging

logger = logging.getLogger(__name__)





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
        user = authenticate(request, mobile=mobile, password=password)

        if user is not None:
            login(request, user)
            next_url = request.GET.get('next', 'store:dashboard')
            return redirect(next_url)
        else:
            return render(request, 'store/index.html', {
                'error': 'Invalid credentials'
            })

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
        mobile = request.POST['mobile']
        password = request.POST['password']

        # Perform any necessary authentication logic here
        user = authenticate(mobile=mobile, password=password)
        if user is not None:
            login(request, user)
            return redirect('store:dashboard')
        else:
            messages.error(request, 'Invalid mobile number or password')
            return redirect('store:index')
    return render(request, 'store/index.html')


def dashboard(request):
    return render(request, 'store/dashboard.html')


def logout_user(request):
    logout(request)
    return redirect('store:dashboard')





@login_required
def store(request):
    if request.user.is_authenticated:
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
        return render(request, 'store/store.html', context)
    else:
        return redirect('store:index')



@user_passes_test(is_admin)
@login_required
def add_item(request):
    if request.user.is_authenticated:
        if request.method == 'POST':
            form = addItemForm(request.POST)
            if form.is_valid():
                item = form.save(commit=False)
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


@login_required
def search_item(request):
    if request.user.is_authenticated:
        query = request.GET.get('search', '').strip()
        if query:
            # Search across multiple fields using Q objects
            items = Item.objects.filter(
                Q(name__icontains=query) |  # Search by name
                Q(brand__icontains=query) #|  # Search by brand name
                # Q(category__icontains=query)  # Search by category
            )
        else:
            items = Item.objects.all()
        return render(request, 'partials/search_item.html', {'items': items})
    else:
        return redirect('store:index')

@user_passes_test(is_admin)
def edit_item(request, pk):
    if request.user.is_authenticated:
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


@login_required
def dispense(request):
    if request.user.is_authenticated:
        if request.method == 'POST':
            form = dispenseForm(request.POST)
            if form.is_valid():
                q = form.cleaned_data['q']
                results = Item.objects.filter(Q(name__icontains=q) | Q(brand__icontains=q))
        else:
            form = dispenseForm()
            results = None
        return render(request, 'partials/dispense_modal.html', {'form': form, 'results': results})
    else:
        return redirect('store:index')


@login_required
def cart(request):
    if request.user.is_authenticated:
        cart_items = Cart.objects.all()
        total_price = sum(item.item.price * item.quantity for item in cart_items)
        return render(request, 'store/cart.html', {'cart_items': cart_items, 'total_price': total_price})
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
        cart_item, created = Cart.objects.get_or_create(
            user=request.user,
            item=item,
            unit=unit,
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
            cart_items = Cart.objects.all()
            total_price = sum(cart_item.subtotal for cart_item in cart_items)

            return JsonResponse({
                'cart_items_count': cart_items.count(),
                'total_price': float(total_price),
            })

        # Redirect to the wholesale cart page if not an HTMX request
        return redirect('store:cart')
    else:
        return redirect('store:index')



@login_required
def view_cart(request):
    if request.user.is_authenticated:
        cart_items = Cart.objects.select_related('item').all()
        total_price, total_discount = 0, 0

        if request.method == 'POST':
            # Process each discount form submission
            for cart_item in cart_items:
                # Fetch the discount amount using cart_item.id in the input name
                discount = Decimal(request.POST.get(f'discount_amount-{cart_item.id}', 0))
                cart_item.discount_amount = max(discount, 0)
                cart_item.save()

        # Calculate totals
        for cart_item in cart_items:
            # Update the price field to match the item's current price
            if cart_item.price != cart_item.item.price:
                cart_item.price = cart_item.item.price
                # This will trigger the save method which recalculates subtotal
                cart_item.save()
            else:
                # Ensure subtotal is correctly calculated even if price hasn't changed
                cart_item.subtotal = cart_item.price * cart_item.quantity
                cart_item.save(update_fields=['subtotal'])

            # Add to total price
            total_price += cart_item.subtotal
            # total_discount += cart_item.discount_amount


        final_total = total_price - total_discount
        total_discounted_price = total_price - total_discount

        # Get customer from session if it exists
        customer = None
        customer_id = request.session.get('customer_id')
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
        cart_item = get_object_or_404(Cart, id=pk)
        if request.method == 'POST':
            quantity_to_return = int(request.POST.get('quantity', 0))
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

        return redirect('store:cart')

    else:
        return redirect('store:index')

@login_required
def clear_cart(request):
    if request.user.is_authenticated:
        if request.method == 'POST':
            cart_items = Cart.objects.all()

            for cart_item in cart_items:
                # Return items to stock
                cart_item.item.stock += cart_item.quantity
                cart_item.item.save()

                # Remove DispensingLog entries
                DispensingLog.objects.filter(
                    user=request.user,
                    name=cart_item.item.name,
                    quantity=cart_item.quantity,
                    amount=cart_item.item.price * cart_item.quantity
                ).delete()

            # Remove associated Sales entries if no other cart items exist
            Sales.objects.filter(user=request.user).delete()

            # Clear cart items
            cart_items.delete()
            messages.success(request, 'Cart cleared and items returned to stock.')

        return redirect('store:cart')
    else:
        return redirect('store:index')



@transaction.atomic
@login_required
def receipt(request):
    if request.user.is_authenticated:
        buyer_name = request.POST.get('buyer_name', '')
        buyer_address = request.POST.get('buyer_address', '')

        # IMPORTANT: Get payment method and status from POST data
        # These are the values selected by the user in the payment modal
        payment_method = request.POST.get('payment_method')
        status = request.POST.get('status')

        # Dump all POST data for debugging
        print("\n\n==== ALL POST DATA: =====")
        for key, value in request.POST.items():
            print(f"  {key}: {value}")
        print(f"\nDirect access - Payment Method: {payment_method}, Status: {status}\n")

        # Get customer ID from session if it exists
        customer_id = request.session.get('customer_id')
        has_customer = False
        if customer_id:
            try:
                customer = Customer.objects.get(id=customer_id)
                has_customer = True
            except Customer.DoesNotExist:
                pass

        # Set default values based on customer presence if not provided
        if not payment_method:
            if has_customer:  # If this is a registered customer
                payment_method = "Wallet"  # Default for registered customers
            else:  # For walk-in customers
                payment_method = "Cash"  # Default for walk-in customers

        if not status:
            # Default status is "Paid" for all customers (both registered and walk-in)
            status = "Paid"

        print(f"After initial defaults - Payment Method: {payment_method}, Status: {status}")

        cart_items = Cart.objects.all()
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

        # Get wholesale customer ID from session if it exists
        customer_id = request.session.get('customer_id')
        customer = None
        if customer_id:
            try:
                customer = Customer.objects.get(id=customer_id)
            except Customer.DoesNotExist:
                pass

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
                if payment_method not in ["Cash", "Wallet", "Transfer"]:
                    if sales.customer:
                        payment_method = "Wallet"  # Default for registered customers
                    else:
                        payment_method = "Cash"  # Default for walk-in customers

                if status not in ["Paid", "Unpaid"]:
                    # Default status is "Paid" for all customers (both registered and walk-in)
                    status = "Paid"

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
            return redirect('store:cart')

        for cart_item in cart_items:
            SalesItem.objects.get_or_create(
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
        if 'customer_id' in request.session:
            del request.session['customer_id']

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

        # Force the payment method and status one last time if needed
        if has_customer:
            if receipt.payment_method != 'Wallet':
                print(f"Forcing payment method to Wallet for customer {receipt.customer.name}")
                receipt.payment_method = 'Wallet'
                receipt.save()

            if receipt.status != 'Paid':
                print(f"Forcing status to Paid for customer {receipt.customer.name}")
                receipt.status = 'Paid'
                receipt.save()

            receipt.refresh_from_db()

        # Render to the receipt template
        return render(request, 'store/receipt.html', {
            'receipt': receipt,
            'sales_items': sales_items,
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



@login_required
def receipt_detail(request, receipt_id):
    if request.user.is_authenticated:
        # Retrieve the existing receipt
        receipt = get_object_or_404(Receipt, receipt_id=receipt_id)

        # If the form is submitted, update buyer details only
        if request.method == 'POST':
            # Only update buyer_name if there's no customer associated
            if not receipt.customer:
                buyer_name = request.POST.get('buyer_name', '').strip() or 'WALK-IN CUSTOMER'
                receipt.buyer_name = buyer_name

            buyer_address = request.POST.get('buyer_address')
            if buyer_address:
                receipt.buyer_address = buyer_address

            # Save the updated receipt
            receipt.save()

            # Redirect to the same page to reflect updated details
            return redirect('store:receipt_detail', receipt_id=receipt.receipt_id)

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

        # Define available payment methods and statuses
        payment_methods = ["Cash", "Wallet", "Transfer"]
        statuses = ["Paid", "Unpaid"]

        # Render the receipt details template
        return render(request, 'partials/receipt_detail.html', {
            'receipt': receipt,
            'sales_items': sales_items,
            'total_price': total_price,
            'total_discount': total_discount,
            'total_discounted_price': total_discounted_price,
            'user': request.user,
            'payment_methods': payment_methods,
            'statuses': statuses,
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

                        # Get payment method and status for the receipt
                        payment_method = request.POST.get('payment_method', 'Cash')
                        status = request.POST.get('status', 'Paid')

                        # Store in session for later use in receipt generation
                        request.session['payment_method'] = payment_method
                        request.session['payment_status'] = status

                        # Handle customer wallet refund if applicable
                        if sales.customer:
                            try:
                                wallet = Wallet.objects.get(customer=sales.customer)
                                wallet.balance += refund_amount
                                wallet.save()
                                messages.success(
                                    request,
                                    f'{return_quantity} of {item.name} successfully returned, and ₦{refund_amount} refunded to the wallet.'
                                )
                            except Wallet.DoesNotExist:
                                messages.error(request, 'Customer wallet not found or not associated.')

                        messages.success(
                            request,
                            f'{return_quantity} of {item.name} successfully returned.'
                        )
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
@user_passes_test(is_admin)
def delete_item(request, pk):
    if request.user.is_authenticated:
        item = get_object_or_404(Item, id=pk)
        item.delete()
        messages.success(request, 'Item deleted successfully')
        return redirect('store:store')
    else:
        return redirect('store:index')

def get_daily_sales():
    # Fetch daily sales data
    regular_sales = (
        SalesItem.objects
        .annotate(day=TruncDay('sales__date'))
        .values('day')
        .annotate(
            total_sales=Sum(F('price') * F('quantity')),
            total_cost=Sum(F('item__cost') * F('quantity')),
            total_profit=ExpressionWrapper(
                Sum(F('price') * F('quantity')) - Sum(F('item__cost') * F('quantity')),
                output_field=DecimalField()
            )
        )
    )

    wholesale_sales = (
        WholesaleSalesItem.objects
        .annotate(day=TruncDay('sales__date'))
        .values('day')
        .annotate(
            total_sales=Sum(F('price') * F('quantity')),
            total_cost=Sum(F('item__cost') * F('quantity')),
            total_profit=ExpressionWrapper(
                Sum(F('price') * F('quantity')) - Sum(F('item__cost') * F('quantity')),
                output_field=DecimalField()
            )
        )
    )

    # Get retail sales by payment method - using TruncDay to match the day format from sales queries
    payment_method_sales = (
        Receipt.objects
        .filter(Q(status='Paid') | Q(status='Unpaid'))  # Include both paid and unpaid receipts
        .annotate(day=TruncDay('date'))
        .values('day', 'payment_method')
        .annotate(
            total_amount=Sum('total_amount')
        )
        .order_by('day', 'payment_method')
    )

    # Get wholesale sales by payment method - using TruncDay to match the day format
    wholesale_payment_method_sales = (
        WholesaleReceipt.objects
        .filter(Q(status='Paid') | Q(status='Unpaid'))  # Include both paid and unpaid receipts
        .annotate(day=TruncDay('date'))
        .values('day', 'payment_method')
        .annotate(
            total_amount=Sum('total_amount')
        )
        .order_by('day', 'payment_method')
    )

    # Combine results
    combined_sales = defaultdict(lambda: {
        'total_sales': Decimal('0.00'),
        'total_cost': Decimal('0.00'),
        'total_profit': Decimal('0.00'),
        'payment_methods': {
            'Cash': Decimal('0.00'),
            'Wallet': Decimal('0.00'),
            'Transfer': Decimal('0.00')
        }
    })

    # Helper function to normalize dates to date objects (not datetime)
    def normalize_date(date_obj):
        if hasattr(date_obj, 'date'):
            # If it's a datetime object, convert to date
            return date_obj.date()
        return date_obj

    # Add regular sales data
    for sale in regular_sales:
        day = normalize_date(sale['day'])
        combined_sales[day]['total_sales'] += sale['total_sales'] or Decimal('0.00')
        combined_sales[day]['total_cost'] += sale['total_cost'] or Decimal('0.00')
        combined_sales[day]['total_profit'] += sale['total_profit'] or Decimal('0.00')

    # Add wholesale sales data
    for sale in wholesale_sales:
        day = normalize_date(sale['day'])
        combined_sales[day]['total_sales'] += sale['total_sales'] or Decimal('0.00')
        combined_sales[day]['total_cost'] += sale['total_cost'] or Decimal('0.00')
        combined_sales[day]['total_profit'] += sale['total_profit'] or Decimal('0.00')

    # Add retail payment method data
    for sale in payment_method_sales:
        day = normalize_date(sale['day'])
        payment_method = sale['payment_method']
        if payment_method in combined_sales[day]['payment_methods']:
            combined_sales[day]['payment_methods'][payment_method] += sale['total_amount'] or Decimal('0.00')

    # Add wholesale payment method data
    for sale in wholesale_payment_method_sales:
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

def get_monthly_sales_with_expenses():
    # Fetch regular sales data per month
    regular_sales = (
        SalesItem.objects
        .annotate(month=TruncMonth('sales__date'))
        .values('month')
        .annotate(
            total_sales=Sum(F('price') * F('quantity')),
            total_cost=Sum(F('item__cost') * F('quantity')),
            total_profit=ExpressionWrapper(
                Sum(F('price') * F('quantity')) - Sum(F('item__cost') * F('quantity')),
                output_field=DecimalField()
            )
        )
    )

    # Fetch wholesale sales data per month
    wholesale_sales = (
        WholesaleSalesItem.objects
        .annotate(month=TruncMonth('sales__date'))
        .values('month')
        .annotate(
            total_sales=Sum(F('price') * F('quantity')),
            total_cost=Sum(F('item__cost') * F('quantity')),
            total_profit=ExpressionWrapper(
                Sum(F('price') * F('quantity')) - Sum(F('item__cost') * F('quantity')),
                output_field=DecimalField()
            )
        )
    )

    # Get monthly expenses as a dictionary: {month_date: total_expense}
    monthly_expenses = get_monthly_expenses()

    # Combine the two types of sales into one dict
    combined_sales = defaultdict(lambda: {'total_sales': 0, 'total_cost': 0, 'total_profit': 0})

    for sale in regular_sales:
        month = sale['month']
        combined_sales[month]['total_sales'] += sale['total_sales']
        combined_sales[month]['total_cost'] += sale['total_cost']
        combined_sales[month]['total_profit'] += sale['total_profit']

    for sale in wholesale_sales:
        month = sale['month']
        combined_sales[month]['total_sales'] += sale['total_sales']
        combined_sales[month]['total_cost'] += sale['total_cost']
        combined_sales[month]['total_profit'] += sale['total_profit']

    # Add expense data and calculate net profit for each month
    for month, data in combined_sales.items():
        data['total_expense'] = monthly_expenses.get(month, 0)
        data['net_profit'] = data['total_profit'] - data['total_expense']

    # Sort results by month (descending)
    sorted_sales = sorted(combined_sales.items(), key=lambda x: x[0], reverse=True)
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
                profit_expr = ExpressionWrapper(
                    F('price') * F('quantity') - F('item__cost') * F('quantity'),
                    output_field=DecimalField()
                )

                total_profit_regular = SalesItem.objects.filter(
                    sales__date__year=selected_month.year,
                    sales__date__month=selected_month.month
                ).aggregate(
                    profit=Sum(profit_expr)
                )['profit'] or 0

                total_profit_wholesale = WholesaleSalesItem.objects.filter(
                    sales__date__year=selected_month.year,
                    sales__date__month=selected_month.month
                ).aggregate(
                    profit=Sum(profit_expr)
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
                selected_month = datetime.datetime.strptime(selected_month_str, '%Y-%m').date()
                # Filter for the selected month only
                filtered_sales = [entry for entry in sales_data if entry[0] == selected_month]
            except ValueError:
                # If parsing fails, leave filtered_sales unchanged (or handle the error as needed)
                pass

        context = {
            'monthly_sales': filtered_sales,
            'selected_month': selected_month_str  # pass back to pre-fill the form field
        }
        return render(request, 'store/monthly_sales.html', context)
    else:
        return redirect('store:index')




@user_passes_test(is_admin)
def daily_sales(request):
    if request.user.is_authenticated:
        daily_sales = get_daily_sales()  # Already sorted by date in descending order
        context = {'daily_sales': daily_sales}
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
        customers = Customer.objects.all()
        return render(request, 'partials/customer_list.html', {'customers': customers})
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
                wallet.add_funds(amount)
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
        # Store wholesale customer ID in session for later use
        request.session['customer_id'] = customer.id
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

            # Create a new Sales record for this transaction
            # Instead of get_or_create, we always create a new record to avoid the MultipleObjectsReturned error
            sales = Sales.objects.create(
                user=request.user,
                customer=customer,
                total_amount=Decimal('0.0')
            )

            # Fetch or create a Receipt
            receipt = Receipt.objects.filter(customer=customer, sales=sales).first()

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

                receipt = Receipt.objects.create(
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
                        subtotal = (item.price * quantity)
                        total_cost += subtotal

                        # Update or create WholesaleSalesItem
                        sales_item, created = SalesItem.objects.get_or_create(
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
                        ItemSelectionHistory.objects.create(
                            customer=customer,
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
                            sales_item = SalesItem.objects.get(sales=sales, item=item)

                            if sales_item.quantity < quantity:
                                messages.warning(request, f"Cannot return more {item.name} than purchased.")
                                return redirect('store:customers')

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
                            ItemSelectionHistory.objects.create(
                                customer=customer,
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

                        except SalesItem.DoesNotExist:
                            messages.warning(request, f"Item {item.name} is not part of the sales.")
                            return redirect('store:select_items', pk=pk)

                except Item.DoesNotExist:
                    messages.warning(request, 'One of the selected items does not exist.')
                    return redirect('store:select_items', pk=pk)

            # Update customer's wallet balance
            try:
                wallet = customer.wallet
                if action == 'purchase':
                    wallet.balance -= total_cost
                elif action == 'return':
                    wallet.balance += abs(total_cost)
                wallet.save()
            except Wallet.DoesNotExist:
                messages.warning(request, 'Customer does not have a wallet.')
                return redirect('store:select_items', pk=pk)

            # Store payment method and status in session for receipt generation
            payment_method = request.POST.get('payment_method', 'Cash')
            status = request.POST.get('status', 'Paid')
            request.session['payment_method'] = payment_method
            request.session['payment_status'] = status

            action_message = 'added to cart' if action == 'purchase' else 'returned successfully'
            messages.success(request, f'Action completed: Items {action_message}.')
            return redirect('store:cart')

        return render(request, 'partials/select_items.html', {
            'customer': customer,
            'items': items,
            'wallet_balance': wallet_balance
        })
    else:
        return redirect('store:index')



@login_required
def dispensing_log(request):
    if request.user.is_authenticated:
        # Retrieve all dispensing logs ordered by the most recent
        logs = DispensingLog.objects.all().order_by('-created_at')

        # Filter logs by the selected date if provided
        if date_filter := request.GET.get('date'):
            selected_date = parse_date(date_filter)
            if selected_date:
                logs = logs.filter(created_at__date=selected_date)

        # Filter logs by status if provided
        if status_filter := request.GET.get('status'):
            logs = logs.filter(status=status_filter)

        # Check if this is an HTMX request
        if request.headers.get('HX-Request'):
            # Return only the partial template with filtered logs
            return render(request, 'partials/partials_dispensing_log.html', {'logs': logs})
        else:
            # Render the full template for non-HTMX requests
            return render(request, 'store/dispensing_log.html', {'logs': logs})
    else:
        return redirect('store:index')


def receipt_list(request):
    if request.user.is_authenticated:
        receipts = Receipt.objects.all().order_by('-date')  # Order by date, latest first
        return render(request, 'partials/receipt_list.html', {'receipts': receipts})
    else:
        return redirect('store:index')

def search_receipts(request):
    if request.user.is_authenticated:
        # Get the date query from the GET request
        date_query = request.GET.get('date', '').strip()

        # Debugging log
        print(f"Date Query: {date_query}")

        receipts = Receipt.objects.all()
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

        # Debugging log for queryset
        print(f"Filtered Receipts: {receipts.query}")

        return render(request, 'partials/search_receipts.html', {'receipts': receipts})
    else:
        return redirect('store:index')




@login_required
def exp_date_alert(request):
    if request.user.is_authenticated:
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

        return render(request, 'partials/customer_history.html', context)
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



@user_passes_test(is_admin)
@login_required
def add_procurement(request):
    if request.user.is_authenticated:
        ProcurementItemFormSet = modelformset_factory(
            ProcurementItem,
            form=ProcurementItemForm,
            extra=1,  # Allow at least one empty form to be displayed
            can_delete=True  # Allow deleting items dynamically
        )

        if request.method == 'POST':
            procurement_form = ProcurementForm(request.POST)
            formset = ProcurementItemFormSet(request.POST, queryset=ProcurementItem.objects.none())
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
                    return redirect('store:procurement_list')  # Replace with your actual URL name
                else:
                    messages.success(request, "Procurement and items added successfully!")
                    return redirect('store:procurement_list')  # Replace with your actual URL name
            else:
                messages.error(request, "Please correct the errors below.")
        else:
            # Check if we're continuing a draft procurement
            draft_id = request.GET.get('draft_id')
            if draft_id:
                try:
                    draft_procurement = Procurement.objects.get(id=draft_id, status='draft')
                    procurement_form = ProcurementForm(instance=draft_procurement)
                    formset = ProcurementItemFormSet(queryset=draft_procurement.items.all())
                except Procurement.DoesNotExist:
                    messages.error(request, "Draft procurement not found.")
                    procurement_form = ProcurementForm()
                    formset = ProcurementItemFormSet(queryset=ProcurementItem.objects.none())
            else:
                procurement_form = ProcurementForm()
                formset = ProcurementItemFormSet(queryset=ProcurementItem.objects.none())

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

        # Render the filtered results
        return render(request, 'partials/search_procurement.html', {
            'procurements': procurements,
        })
    else:
        return redirect('store:index')

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
                store_items = StoreItem.objects.filter(name__icontains=search_query)
            else:
                store_items = StoreItem.objects.all()

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
                        qty = int(request.POST.get(f'quantity_{item.id}', 0))
                        markup = float(request.POST.get(f'markup_{item.id}', 0))
                        transfer_unit = request.POST.get(f'transfer_unit_{item.id}', item.unit)
                        unit_conversion = float(request.POST.get(f'unit_conversion_{item.id}', 1))
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

                    # Calculate the new selling price using the markup.
                    cost = item.cost_price
                    new_price = cost + (cost * Decimal(markup) / Decimal(100))

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
                                "exp_date": item.expiry_date,
                            }
                        )
                    else:  # destination == "wholesale"
                        dest_item, created = WholesaleItem.objects.get_or_create(
                            name=item.name,
                            brand=item.brand,
                            unit=transfer_unit,  # Use the selected transfer unit
                            defaults={
                                "dosage_form": item.dosage_form,
                                "cost": cost,
                                "price": new_price,
                                "markup": markup,
                                "stock": 0,
                                "exp_date": item.expiry_date,
                            }
                        )

                    # Calculate the destination quantity using the unit conversion
                    dest_qty = qty * Decimal(str(unit_conversion))

                    # Update the destination item's stock and key fields.
                    dest_item.stock += dest_qty
                    dest_item.cost = cost
                    dest_item.markup = markup
                    dest_item.price = new_price
                    dest_item.save()

                    # Deduct the transferred quantity from the store item.
                    item.stock -= qty
                    item.save()

                    # Remove the store item if its stock is zero or less.
                    if item.stock <= 0:
                        item.delete()
                        processed_items.append(
                            f"Transferred {qty} {item.unit} of {item.name} to {destination} as {dest_qty} {transfer_unit} and removed {item.name} from the store (stock reached zero)."
                        )
                    else:
                        processed_items.append(f"Transferred {qty} {item.unit} of {item.name} to {destination} as {dest_qty} {transfer_unit}.")

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

@user_passes_test(is_admin)
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
                            expected_quantity=item.stock,
                            actual_quantity=0,
                            status='pending'
                        )
                    )

            StockCheckItem.objects.bulk_create(stock_check_items)

            messages.success(request, "Stock check created successfully.")
            return redirect('store:update_stock_check', stock_check.id)

        return render(request, 'store/create_stock_check.html')
    else:
        return redirect('store:index')


@user_passes_test(is_admin)
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

                    # If zero_empty_items is True and both expected and actual are 0, set to 0
                    if zero_empty_items and stock_item.expected_quantity == 0 and int(actual_qty) == 0:
                        stock_item.actual_quantity = 0
                    else:
                        stock_item.actual_quantity = int(actual_qty)

                    stock_items.append(stock_item)

            StockCheckItem.objects.bulk_update(stock_items, ['actual_quantity'])
            messages.success(request, "Stock check updated successfully.")
            return redirect('store:stock_check_report', stock_check.id)

        return render(request, 'store/update_stock_check.html', {'stock_check': stock_check})
    else:
        return redirect('store:index')



@user_passes_test(is_admin)
@login_required
def update_stock_check(request, stock_check_id):
    if request.user.is_authenticated:
        stock_check = get_object_or_404(StockCheck, id=stock_check_id)
        # if stock_check.status == 'completed':
        #     return redirect('store:stock_check_report', stock_check.id)

        if request.method == "POST":
            stock_items = []
            for item_id, actual_qty in request.POST.items():
                if item_id.startswith("item_"):
                    item_id = int(item_id.replace("item_", ""))
                    stock_item = StockCheckItem.objects.get(stock_check=stock_check, item_id=item_id)
                    stock_item.actual_quantity = int(actual_qty)
                    stock_items.append(stock_item)
            StockCheckItem.objects.bulk_update(stock_items, ['actual_quantity'])
            messages.success(request, "Stock check updated successfully.")
            return redirect('store:update_stock_check', stock_check.id)

        return render(request, 'store/update_stock_check.html', {'stock_check': stock_check})
    else:
        return redirect('store:index')



@user_passes_test(is_admin)
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

@user_passes_test(is_admin)
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


@user_passes_test(is_admin)
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


@user_passes_test(is_admin)
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


@user_passes_test(is_admin)
@login_required
def list_stock_checks(request):
    # Get all StockCheck objects ordered by date (newest first)
    stock_checks = StockCheck.objects.all().order_by('-date')
    context = {
        'stock_checks': stock_checks,
    }
    return render(request, 'store/stock_check_list.html', context)




import logging
logger = logging.getLogger(__name__)

@login_required
def create_transfer_request_wholesale(request):
    if request.user.is_authenticated:
        if request.method == "GET":
            # Render form for a wholesale user to request items from retail
            retail_items = Item.objects.all().order_by('name')
            return render(request, "wholesale/wholesale_transfer_request.html", {"retail_items": retail_items})

        elif request.method == "POST":
            try:
                requested_quantity = int(request.POST.get("requested_quantity", 0))
                item_id = request.POST.get("item_id")
                from_wholesale = request.POST.get("from_wholesale", "false").lower() == "true"

                if not item_id or requested_quantity <= 0:
                    return JsonResponse({"success": False, "message": "Invalid input provided."}, status=400)

                source_item = get_object_or_404(Item, id=item_id)

                transfer = TransferRequest.objects.create(
                    retail_item=source_item,
                    requested_quantity=requested_quantity,
                    from_wholesale=True,
                    status="pending",
                    created_at=timezone.now()
                )

                messages.success(request, "Transfer request created successfully.")
                return JsonResponse({"success": True, "message": "Transfer request created successfully."})

            except (TypeError, ValueError) as e:
                return JsonResponse({"success": False, "message": str(e)}, status=400)
            except Exception as e:
                return JsonResponse({"success": False, "message": "An error occurred."}, status=500)

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
                    approved_qty = int(approved_qty_param) if approved_qty_param else transfer.requested_quantity
                    if approved_qty <= 0:
                        return JsonResponse({
                            "success": False,
                            "message": "Quantity must be greater than zero."
                        }, status=400)
                except ValueError:
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

                    messages.success(
                        request,
                        f"Transfer approved: {approved_qty} {source_item.name} moved from retail to wholesale."
                    )

                    return JsonResponse({
                        "success": True,
                        "message": f"Transfer approved with quantity {approved_qty}.",
                        "source_stock": source_item.stock,
                        "destination_stock": destination_item.stock,
                    })

            except Exception as e:
                logger.error(f"Error in approve_transfer: {str(e)}")
                return JsonResponse({
                    "success": False,
                    "message": "An error occurred while processing the transfer."
                }, status=500)

        return JsonResponse({
            "success": False,
            "message": "Invalid request method."
        }, status=400)

    return redirect('store:index')



@login_required
def reject_transfer(request, transfer_id):
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


@user_passes_test(is_admin)
@login_required
# def expense_list(request):
#     if request.user.is_authenticated:
#         """Display all expenses."""
#         expenses = Expense.objects.all().order_by('-date')
#         return render(request, 'store/expense_list.html', {'expenses': expenses})
#     else:
#         return redirect('store:index')

def expense_list(request):
    if request.user.is_authenticated:
        expenses = Expense.objects.all().order_by('-date')
        expense_categories = ExpenseCategory.objects.all().order_by('name')
        return render(request, 'store/expense_list.html', {
            'expenses': expenses,
            'expense_categories': expense_categories,
        })
    else:
        return redirect('store:index')


@user_passes_test(is_admin)
@login_required
def add_expense_form(request):
    if request.user.is_authenticated:
        """Return the modal form for adding expenses."""
        form = ExpenseForm()
        return render(request, 'partials/_expense_form.html', {'form': form})
    else:
        return redirect('store:index')


@user_passes_test(is_admin)
@login_required
def add_expense(request):
    if request.user.is_authenticated:
        """Handle expense form submission."""
        if request.method == 'POST':
            form = ExpenseForm(request.POST)
            if form.is_valid():
                form.save()
                return render(request, 'partials/_expense_list.html', {'expenses': Expense.objects.all()})
        else:
            form = ExpenseForm()

        return render(request, 'partials/_expense_form.html', {'form': form})
    else:
        return redirect('store:index')

@user_passes_test(is_admin)
@login_required
def edit_expense_form(request, expense_id):
    if request.user.is_authenticated:
        """Return the modal form for editing an expense."""
        expense = get_object_or_404(Expense, id=expense_id)
        form = ExpenseForm(instance=expense)
        return render(request, 'partials/_expense_form.html', {'form': form, 'expense_id': expense.id})
    else:
        return redirect('store:index')

@user_passes_test(is_admin)
@login_required
@require_POST
def update_expense(request, expense_id):
    if request.user.is_authenticated:
        """Handle updating an expense."""
        expense = get_object_or_404(Expense, id=expense_id)
        form = ExpenseForm(request.POST, instance=expense)
        if form.is_valid():
            form.save()
            expenses = Expense.objects.all().order_by('-date')  # Refresh list
            return render(request, 'partials/_expense_list.html', {'expenses': expenses})
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
    return render(request, 'store/search_for_adjustment.html', {'items': items})


@login_required
def search_items(request):
    """API endpoint for searching items for stock check"""
    query = request.GET.get('q', '')
    if query:
        items = Item.objects.filter(
            Q(name__icontains=query) |
            Q(brand__icontains=query) |
            Q(dosage_form__icontains=query)
        ).order_by('name')
    else:
        items = Item.objects.all().order_by('name')[:20]  # Limit to 20 items if no query

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

@user_passes_test(is_admin)
@login_required
@require_POST
def delete_expense(request, expense_id):
    if request.user.is_authenticated:
        """Handle deleting an expense."""
        expense = get_object_or_404(Expense, id=expense_id)
        expense.delete()
        expenses = Expense.objects.all().order_by('-date')  # Refresh list
        return render(request, 'partials/_expense_list.html', {'expenses': expenses})
    else:
        return redirect('store:index')




@user_passes_test(is_admin)
@login_required
def add_expense_category_form(request):
    """Return the modal form for adding an expense category."""
    form = ExpenseCategoryForm()
    return render(request, 'partials/_expense_category_form.html', {'form': form})

@user_passes_test(is_admin)
@login_required
def add_expense_category(request):
    """Handle expense category form submission."""
    if request.method == 'POST':
        form = ExpenseCategoryForm(request.POST)
        if form.is_valid():
            form.save()
            # Optionally, get all categories to update a list on the page
            categories = ExpenseCategory.objects.all().order_by('name')
            return render(request, 'partials/_expense_category_list.html', {'categories': categories})
        else:
            return render(request, 'partials/_expense_category_form.html', {'form': form})
    else:
        form = ExpenseCategoryForm()
    return render(request, 'partials/_expense_category_form.html', {'form': form})

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
