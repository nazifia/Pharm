from decimal import Decimal
from django.http import JsonResponse
from django.db.models.functions import TruncMonth, TruncDay
from django.shortcuts import get_object_or_404, render, redirect
from customer.models import Wallet
from .models import *
from .forms import *
from django.contrib import messages
from django.db import transaction
from datetime import datetime,  timedelta
from django.views.decorators.http import require_POST
from django.db.models import Q, F, ExpressionWrapper, Sum, DecimalField
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib.auth import authenticate, login, logout, update_session_auth_hash




# Create your views here.
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
    return redirect('store:index')



def is_admin(user):
    return user.is_authenticated and user.is_superuser or user.is_staff


@login_required
def store(request):
    items = Item.objects.all().order_by('name')
    low_stock_threshold = 10  # Adjust this number as needed

    # Ensure correct field values for cost and price
    total_purchase_value = sum(item.cost * item.stock for item in items)
    total_stock_value = sum(item.price * item.stock for item in items)
    total_profit = total_stock_value - total_purchase_value

    # Identify low-stock items
    low_stock_items = [item for item in items if item.stock <= low_stock_threshold]

    context = {
        'items': items,
        'low_stock_items': low_stock_items,
        'low_stock_threshold': low_stock_threshold,
        'total_purchase_value': total_purchase_value,
        'total_stock_value': total_stock_value,
        'total_profit': total_profit,
    }
    return render(request, 'store/store.html', context)



@user_passes_test(is_admin)
@login_required
def add_item(request):
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
    
    
    
@login_required
def search_item(request):
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



@user_passes_test(is_admin)
def edit_item(request, pk):
    item = get_object_or_404(Item, id=pk)

    if request.method == 'POST':
        form = addItemForm(request.POST, instance=item)
        if form.is_valid():
            # Convert markup_percentage to Decimal to ensure compatible types
            markup = Decimal(form.cleaned_data.get("markup", 0))
            item.markup = markup
            
            # Calculate and update the price
            item.price = item.cost + (item.cost * markup / Decimal(100))
            
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



@login_required
def dispense(request):
    if request.method == 'POST':
        form = dispenseForm(request.POST)
        if form.is_valid():
            q = form.cleaned_data['q']
            results = Item.objects.filter(Q(name__icontains=q) | Q(brand__icontains=q))
    else:
        form = dispenseForm()
        results = None
    return render(request, 'partials/dispense_modal.html', {'form': form, 'results': results})



@login_required
def cart(request):
    cart_items = Cart.objects.all()
    total_price = sum(item.item.price * item.quantity for item in cart_items)
    return render(request, 'store/cart.html', {'cart_items': cart_items, 'total_price': total_price})



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
            cart_item.subtotal = cart_item.item.price * cart_item.quantity
            total_price += cart_item.subtotal
            # total_discount += cart_item.discount_amount

        
        final_total = total_price - total_discount

        total_discounted_price = total_price - total_discount
        return render(request, 'store/cart.html', {
            'cart_items': cart_items,
            'total_discount': total_discount,
            'total_price': total_price,
            'total_discounted_price': total_discounted_price,
            'final_total': final_total,
        })
    else:
        return redirect('store:index')



@login_required
def update_cart_quantity(request, pk):
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



@login_required
def clear_cart(request):
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



@login_required
def receipt(request):
    buyer_name = request.POST.get('buyer_name', '')
    buyer_address = request.POST.get('buyer_address', '')

    cart_items = Cart.objects.all()
    if not cart_items.exists():
        messages.warning(request, "No items in the cart.")
        return redirect('store:cart')

    total_price, total_discount = 0, 0

    for cart_item in cart_items:
        subtotal = cart_item.item.price * cart_item.quantity
        total_price += subtotal
        total_discount += getattr(cart_item, 'discount_amount', 0)  # Handle missing discount_amount field

    total_discounted_price = total_price - total_discount
    final_total = total_discounted_price if total_discount > 0 else total_price

    sales, created = Sales.objects.get_or_create(user=request.user, total_amount=final_total)

    try:
        receipt = Receipt.objects.filter(sales=sales).first()
        if not receipt:
            payment_method = request.POST.get('payment_method', 'Cash')
            status = request.POST.get('status', 'Paid')  # Default to 'Paid'
            receipt = Receipt.objects.create(
                sales=sales,
                receipt_id=ShortUUIDField().generate(),
                total_amount=final_total,
                buyer_name=buyer_name if not sales.customer else None,
                buyer_address=buyer_address,
                date=datetime.now(),
                payment_method=payment_method,
                status=status
            )

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
            brand=cart_item.item.brand,
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

    daily_sales_data = get_daily_sales()
    monthly_sales_data = get_monthly_sales()

    sales_items = sales.sales_items.all()
    
    payment_methods = ["Cash", "Wallet", "Transfer"]
    statuses = ["Paid", "Unpaid"]

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



@login_required
def receipt_detail(request, receipt_id):
    
    # Retrieve the existing receipt
    receipt = get_object_or_404(Receipt, receipt_id=receipt_id)

    # If the form is submitted, update buyer details and other fields
    if request.method == 'POST':
        buyer_name = request.POST.get('buyer_name')
        buyer_address = request.POST.get('buyer_address')
        payment_method = request.POST.get('payment_method')
        payment_status = request.POST.get('payment_status')  # New: Capture payment status

        # Update receipt buyer info if provided
        if buyer_name:
            receipt.buyer_name = buyer_name
        if buyer_address:
            receipt.buyer_address = buyer_address
        if payment_method:
            receipt.payment_method = payment_method
        if payment_status:
            receipt.paid = (payment_status == 'Paid')  # Update Paid/Unpaid status

        # Save the updated receipt
        receipt.save()

        # Redirect to the same page to reflect updated details
        return redirect('store:receipt_detail', receipt_id=receipt_id.replace('RID:', ''))

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

    # Render the receipt details template
    return render(request, 'partials/receipt_detail.html', {
        'receipt': receipt,
        'sales_items': sales_items,
        'total_price': total_price,
        'total_discount': total_discount,
        'total_discounted_price': total_discounted_price,
    })


@login_required
def return_item(request, pk):
    item = get_object_or_404(Item, id=pk)

    if request.method == 'POST':
        form = ReturnItemForm(request.POST)
        if form.is_valid():
            return_quantity = form.cleaned_data.get('return_item_quantity')

            # Validate the return quantity
            if return_quantity <= 0:
                messages.warning(request, 'Invalid return item quantity.')
                return redirect('store:store')

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

                    # Process wallet refund if applicable
                    if sales.customer and hasattr(sales.customer, 'wallet'):
                        wallet = sales.customer.wallet
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
                    dispensing_log = DispensingLog.objects.filter(user=sales.user, name=item.name).last()
                    if dispensing_log:
                        if dispensing_log.quantity == return_quantity:
                            dispensing_log.quantity = 0
                            dispensing_log.status = 'Returned'
                        elif dispensing_log.quantity > return_quantity:
                            dispensing_log.quantity -= return_quantity
                            dispensing_log.status = 'Partially Returned'
                        else:
                            messages.warning(
                                request,
                                f'Returned quantity exceeds dispensed quantity for {item.name}.'
                            )
                            return redirect('store:store')

                        dispensing_log.save()

                    # Update daily and monthly sales data
                    daily_sales = get_daily_sales()
                    monthly_sales = get_monthly_sales()

                    # Render updated logs for HTMX requests
                    if request.headers.get('HX-Request'):
                        context = {
                            'logs': DispensingLog.objects.all().order_by('-created_at'),
                            'daily_sales': daily_sales,
                            'monthly_sales': monthly_sales
                        }
                        return render(request, 'partials/partials_dispensing_log.html', context)

                    messages.success(
                        request,
                        f'{return_quantity} of {item.name} successfully returned, sales and logs updated.'
                    )
                    return redirect('store:store')

            except Exception as e:
                # Handle exceptions during atomic transaction
                print(f'Error during item return: {e}')
                messages.error(request, f'Error processing return: {e}')
                return redirect('store:store')
        else:
            messages.warning(request, 'Invalid input. Please correct the form and try again.')

    else:
        # Display the return form in a modal or a page
        form = ReturnItemForm()

    # Return appropriate response for HTMX or full-page requests
    if request.headers.get('HX-Request'):
        return render(request, 'partials/return_item_modal.html', {'form': form, 'item': item})
    else:
        return render(request, 'store/store.html', {'form': form})
    


@login_required
@user_passes_test(is_admin)
def delete_item(request, pk):
    item = get_object_or_404(Item, id=pk)
    item.delete()
    messages.success(request, 'Item deleted successfully')
    return redirect('store:store')





# Function to get daily sales, including wholesale
from collections import defaultdict
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

    # Combine results
    combined_sales = defaultdict(lambda: {'total_sales': 0, 'total_cost': 0, 'total_profit': 0})

    for sale in regular_sales:
        day = sale['day']
        combined_sales[day]['total_sales'] += sale['total_sales']
        combined_sales[day]['total_cost'] += sale['total_cost']
        combined_sales[day]['total_profit'] += sale['total_profit']

    for sale in wholesale_sales:
        day = sale['day']
        combined_sales[day]['total_sales'] += sale['total_sales']
        combined_sales[day]['total_cost'] += sale['total_cost']
        combined_sales[day]['total_profit'] += sale['total_profit']

    # Convert combined sales to a sorted list by date in descending order
    sorted_combined_sales = sorted(combined_sales.items(), key=lambda x: x[0], reverse=True)

    return sorted_combined_sales


def get_monthly_sales():
    # Fetch monthly sales data
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

    # Combine results
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

    # Sort combined sales by month in descending order (most recent first)
    return sorted(combined_sales.items(), key=lambda x: x[0], reverse=True)



@user_passes_test(is_admin)
def daily_sales(request):
    daily_sales = get_daily_sales()  # Already sorted by date in descending order
    context = {'daily_sales': daily_sales}
    return render(request, 'store/daily_sales.html', context)



@user_passes_test(is_admin)
def monthly_sales(request):
    monthly_sales = get_monthly_sales()  # This is already sorted
    context = {'monthly_sales': monthly_sales}
    return render(request, 'store/monthly_sales.html', context)



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



@login_required
def register_customers(request):
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


@login_required
def customer_list(request):
    customers = Customer.objects.all()
    return render(request, 'partials/customer_list.html', {'customers': customers})


@login_required
def wallet_details(request, pk):
    customer = get_object_or_404(Customer, pk=pk)
    wallet = customer.wallet
    return render(request, 'partials/wallet_details.html', {'customer': customer, 'wallet': wallet})


@login_required
@user_passes_test(is_admin)
def delete_customer(request, pk):
    customer = get_object_or_404(Customer, pk=pk)
    customer.delete()
    messages.success(request, 'Customer deleted successfully.')
    return redirect('store:customer_list')


@login_required
def add_funds(request, pk):
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


@login_required
# @user_passes_test(is_admin)
def reset_wallet(request, pk):
    wallet = get_object_or_404(Wallet, pk=pk)
    wallet.balance = 0
    wallet.save()
    messages.success(request, f'{wallet.customer.name}\'s wallet reset successfully.')
    return redirect('store:customer_list')


@login_required
def customers_on_negative(request):
    customers_on_negative = Customer.objects.filter(wallet__balance__lt=0)
    return render(request, 'partials/customers_on_negative.html', {'customers': customers_on_negative})


@login_required
def edit_customer(request, pk):
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


@transaction.atomic
@login_required
def select_items(request, pk):
    customer = get_object_or_404(Customer, id=pk)
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
        discount_amounts = request.POST.getlist('discount_amounts', [])
        units = request.POST.getlist('units', [])

        if len(item_ids) != len(quantities):
            messages.warning(request, 'Mismatch between selected items and quantities.')
            return redirect('store:select_items', pk=pk)

        total_cost = Decimal('0.0')

        # Fetch or create a Sales record
        sales, created = Sales.objects.get_or_create(
            user=request.user,
            customer=customer,
            defaults={'total_amount': Decimal('0.0')}
        )

        # Fetch or create a Receipt
        receipt, receipt_created = Receipt.objects.get_or_create(
            customer=customer,
            sales=sales,
            defaults={
                'total_amount': Decimal('0.0'),
                'buyer_name': customer.name,
                'buyer_address': customer.address,
                'date': datetime.now(),
                'printed': False,
            }
        )

        for i, item_id in enumerate(item_ids):
            try:
                item = Item.objects.get(id=item_id)
                quantity = int(quantities[i])
                # discount = Decimal(discount_amounts[i]) if i < len(discount_amounts) else Decimal('0.0')
                unit = units[i] if i < len(units) else item.unit

                if action == 'purchase':
                    # Check stock and update inventory
                    if quantity > item.stock:
                        messages.warning(request, f'Not enough stock for {item.name}.')
                        return redirect('store:select_items', pk=pk)

                    item.stock -= quantity
                    item.save()

                    # Update or create a CartItem
                    cart_item, created = Cart.objects.get_or_create(
                        item=item,
                        defaults={'quantity': quantity, 'unit': unit}
                    )
                    if not created:
                        cart_item.quantity += quantity
                        # cart_item.discount_amount += discount
                        cart_item.unit = unit
                    cart_item.save()

                    # Calculate subtotal
                    subtotal = (item.price * quantity)
                    total_cost += subtotal

                    # Update or create SalesItem
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
                            return redirect('store:customer_list')

                        sales_item.quantity -= quantity
                        if sales_item.quantity == 0:
                            sales_item.delete()
                        else:
                            sales_item.save()

                        refund_amount = (item.price * quantity)

                        # Update sales total
                        sales.total_amount -= refund_amount
                        sales.save()

                        # Log dispensing action
                        DispensingLog.objects.create(
                            user=request.user,
                            name=item.name,
                            unit=unit,
                            quantity=quantity,
                            amount=refund_amount,
                            status='Partially Returned' if sales_item.quantity > 0 else 'Returned'
                        )

                        # **Log Item Selection History (Return)**
                        ItemSelectionHistory.objects.create(
                            customer=customer,
                            user=request.user,
                            item=item,
                            quantity=quantity,
                            action=action,
                            unit_price=item.price,
                            # subtotal=quantity * item.price,
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

        action_message = 'added to cart' if action == 'purchase' else 'returned successfully'
        messages.success(request, f'Action completed: Items {action_message}.')
        return redirect('store:cart')

    return render(request, 'partials/select_items.html', {
        'customer': customer,
        'items': items,
        'wallet_balance': wallet_balance
    })
    


@login_required
def dispensing_log(request):
    # Retrieve all dispensing logs ordered by the most recent
    logs = DispensingLog.objects.all().order_by('-created_at')

    # Filter logs by the selected date if provided
    if date_filter := request.GET.get('date'):
        selected_date = parse_date(date_filter)
        if selected_date:
            logs = logs.filter(created_at__date=selected_date)
            return render(request, 'partials/partials_dispensing_log.html', {'logs': logs})

    # Filter logs by status if provided
    if status_filter := request.GET.get('status'):
        logs = logs.filter(status=status_filter)

        return render(request, 'partials/partials_dispensing_log.html', {'logs': logs})

    # Render the full template for non-HTMX requests
    return render(request, 'store/dispensing_log.html', {'logs': logs})



def receipt_list(request):
    receipts = Receipt.objects.all().order_by('-date')  # Order by date, latest first
    return render(request, 'partials/receipt_list.html', {'receipts': receipts})


def search_receipts(request):
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



@login_required
def receipt_detail(request, receipt_id):
    # Retrieve the existing receipt
    receipt = get_object_or_404(Receipt, receipt_id=receipt_id)

    # If the form is submitted, update buyer details and other fields
    if request.method == 'POST':
        buyer_name = request.POST.get('buyer_name')
        buyer_address = request.POST.get('buyer_address')
        payment_method = request.POST.get('payment_method')
        payment_status = request.POST.get('payment_status')  # New: Capture payment status

        # Update receipt buyer info if provided
        if buyer_name:
            receipt.buyer_name = buyer_name
        if buyer_address:
            receipt.buyer_address = buyer_address
        if payment_method:
            receipt.payment_method = payment_method
        if payment_status:
            receipt.paid = (payment_status == 'Paid')  # Update Paid/Unpaid status

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

    # Render the receipt details template
    return render(request, 'partials/receipt_detail.html', {
        'receipt': receipt,
        'sales_items': sales_items,
        'total_price': total_price,
        'total_discount': total_discount,
        'total_discounted_price': total_discounted_price,
    })


@login_required
def exp_date_alert(request):
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



@login_required
def customer_history(request, pk):
    customer = get_object_or_404(Customer, id=pk)
    histories = ItemSelectionHistory.objects.filter(customer=customer).select_related('customer__user').order_by('-date')
    
    # Add a 'subtotal' field to each history
    for history in histories:
        history.subtotal = history.quantity * history.unit_price

    return render(request, 'partials/customer_history.html', {
        'customer': customer,
        'histories': histories,
    })



@login_required
def register_supplier_view(request):
    if request.method == 'POST':
        form = SupplierRegistrationForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect('partials/supplier_list.html')
    else:
        form = SupplierRegistrationForm()
    return render(request, 'partials/supplier_reg_form.html', {'form': form})


def supplier_list_partial(request):
    suppliers = Supplier.objects.all()  # Get all suppliers
    return render(request, 'partials/supplier_list.html', {'suppliers': suppliers})


@login_required
def list_suppliers_view(request):
    suppliers = Supplier.objects.all()  # Get all suppliers
    return render(request, 'partials/supplier_list.html', {'suppliers': suppliers})




@user_passes_test(is_admin)
@login_required
def add_procurement(request):
    ProcurementItemFormSet = modelformset_factory(
        ProcurementItem,
        form=ProcurementItemForm,
        extra=1,  # Allow at least one empty form to be displayed
        can_delete=True  # Allow deleting items dynamically
    )

    if request.method == 'POST':
        procurement_form = ProcurementForm(request.POST)
        formset = ProcurementItemFormSet(request.POST, queryset=ProcurementItem.objects.none())

        if procurement_form.is_valid() and formset.is_valid():
            procurement = procurement_form.save(commit=False)
            procurement.created_by = request.user  # Assuming the user is authenticated
            procurement.save()

            for form in formset:
                if form.cleaned_data.get('item_name'):  # Save only valid items
                    procurement_item = form.save(commit=False)
                    procurement_item.procurement = procurement
                    procurement_item.save()

            messages.success(request, "Procurement and items added successfully!")
            return redirect('store:procurement_list')  # Replace with your actual URL name
        else:
            messages.error(request, "Please correct the errors below.")
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



def procurement_form(request):
    # Create an empty formset for the items
    item_formset = ProcurementItemFormSet(queryset=ProcurementItem.objects.none())  # Replace with your model if needed

    # Get the empty form (form for the new item)
    new_form = item_formset.empty_form

    # Render the HTML for the new form
    return render(request, 'partials/procurement_form.html', {'form': new_form})


def procurement_list(request):
    procurements = (
        Procurement.objects.annotate(calculated_total=Sum('items__subtotal'))
        .order_by('-date')
    )
    return render(request, 'partials/procurement_list.html', {
        'procurements': procurements,
    })



def search_procurement(request):
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
    

@login_required
def procurement_detail(request, procurement_id):
    procurement = get_object_or_404(Procurement, id=procurement_id)

    # Calculate total from ProcurementItem objects
    total = procurement.items.aggregate(total=models.Sum('subtotal'))['total'] or 0

    return render(request, 'partials/procurement_detail.html', {
        'procurement': procurement,
        'total': total,
    })


