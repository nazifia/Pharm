"""JSON API for retail and wholesale items, consumed by static/js/app/store-items.js.
Session auth + CSRF (X-CSRFToken header). Reuses addItemForm and existing permission helpers."""
import json
from decimal import Decimal

from django.http import JsonResponse
from django.shortcuts import get_object_or_404, render
from django.views.decorators.cache import never_cache
from django.views.decorators.csrf import ensure_csrf_cookie
from django.views.decorators.http import require_http_methods
from django.contrib.auth.decorators import login_required

from store.forms import addItemForm
from wholesale.forms import addWholesaleForm
from store.gs1_parser import is_gs1_barcode, parse_barcode
from store.models import Item, WholesaleItem
from userauth.permissions import can_manage_items, can_operate_retail, can_operate_wholesale

FIELDS = ('id', 'name', 'dosage_form', 'brand', 'unit', 'cost', 'markup', 'price',
          'stock', 'low_stock_threshold', 'exp_date', 'barcode', 'barcode_type')


def _ser(i):
    d = {f: getattr(i, f) for f in FIELDS}
    for k in ('cost', 'markup', 'price', 'stock', 'low_stock_threshold'):
        d[k] = str(d[k]) if d[k] is not None else None
    d['exp_date'] = i.exp_date.isoformat() if i.exp_date else None
    return d


def _err(msg, status):
    return JsonResponse({'error': msg}, status=status)


SCOPES = {
    'store': (Item, addItemForm, can_operate_retail, 'Store Items'),
    'wholesale': (WholesaleItem, addWholesaleForm, can_operate_wholesale, 'Wholesale Items'),
}


def _guard(request, scope, manage=False):
    if not request.user.is_authenticated:
        return _err('Authentication required', 401)
    if scope not in SCOPES:
        return _err('Not found', 404)
    if not SCOPES[scope][2](request.user):
        return _err('Access denied', 403)
    if manage and not can_manage_items(request.user):
        return _err('Permission denied', 403)


def _save(request, scope, instance=None):
    try:
        data = json.loads(request.body or b'{}')
    except ValueError:
        return _err('Invalid JSON', 400)
    form = SCOPES[scope][1](data, instance=instance)
    if not form.is_valid():
        return JsonResponse({'errors': form.errors}, status=422)
    item = form.save(commit=False)
    markup = Decimal(form.cleaned_data.get('markup') or 0)
    item.markup = markup
    if data.get('manual_price_override'):
        item.price = Decimal(form.cleaned_data.get('price') or 0)
    else:
        item.price = item.cost + item.cost * markup / Decimal(100)
    if item.barcode and is_gs1_barcode(item.barcode):
        p = parse_barcode(item.barcode)
        item.gtin = p.get('gtin') or item.gtin
        item.batch_number = p.get('batch_number') or item.batch_number
        item.serial_number = p.get('serial_number') or item.serial_number
    item.save()
    return item


@never_cache
@require_http_methods(['GET', 'POST'])
def items(request, scope):
    denied = _guard(request, scope, manage=request.method == 'POST')
    if denied:
        return denied
    if request.method == 'GET':
        qs = SCOPES[scope][0].objects.all()
        q = request.GET.get('q', '').strip()
        if q:
            from django.db.models import Q
            qs = qs.filter(Q(name__icontains=q) | Q(brand__icontains=q) | Q(barcode=q))
        return JsonResponse({'items': [_ser(i) for i in qs.order_by('name')[:500]]})
    res = _save(request, scope)
    return res if isinstance(res, JsonResponse) else JsonResponse(_ser(res), status=201)


@never_cache
@require_http_methods(['GET', 'PUT', 'DELETE'])
def item_detail(request, scope, pk):
    denied = _guard(request, scope, manage=request.method != 'GET')
    if denied:
        return denied
    item = get_object_or_404(SCOPES[scope][0], pk=pk)
    if request.method == 'GET':
        return JsonResponse(_ser(item))
    if request.method == 'DELETE':
        # matches delete_item view: Admin/Manager only (can_manage_items)
        item.delete()
        return JsonResponse({'ok': True})
    res = _save(request, scope, instance=item)
    return res if isinstance(res, JsonResponse) else JsonResponse(_ser(res))


@login_required
@ensure_csrf_cookie
def items_page(request, scope):
    """Serves the static vanilla-JS shell; all data comes from the JSON API."""
    if scope not in SCOPES:
        return _err('Not found', 404)
    return render(request, 'app/items.html', {'scope': scope, 'title': SCOPES[scope][3]})
