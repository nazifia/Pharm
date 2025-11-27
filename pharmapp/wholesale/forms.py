from django import forms
from store.models import *
from supplier.models import *
from django.forms import modelformset_factory



class addWholesaleForm(forms.ModelForm):
    name = forms.CharField(max_length=100)
    dosage_form = forms.CharField(max_length=200)  # Changed to CharField to allow any value
    brand = forms.CharField(max_length=100)
    cost = forms.DecimalField(max_digits=10, decimal_places=2)
    price = forms.DecimalField(max_digits=10, decimal_places=2, required=False)
    stock = forms.IntegerField()
    exp_date = forms.DateField()
    markup = forms.DecimalField(max_digits=6, decimal_places=2)
    unit = forms.CharField(max_length=200)
    barcode = forms.CharField(max_length=200, required=False)
    barcode_type = forms.ChoiceField(
        choices=[('', 'Select Type'), ('UPC', 'UPC'), ('EAN13', 'EAN-13'), ('CODE128', 'Code-128'), ('QR', 'QR Code')],
        required=False
    )

    class Meta:
        model = WholesaleItem
        fields = ('name', 'dosage_form', 'brand', 'unit', 'cost', 'markup', 'price', 'stock', 'exp_date', 'barcode', 'barcode_type')



class wholesaleDispenseForm(forms.Form):
    q = forms.CharField(min_length=2, label='', widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder':'SEARCH  HERE...'}))



class ReturnWholesaleItemForm(forms.ModelForm):
    return_item_quantity = forms.IntegerField(min_value=1, label="Return Quantity")

    class Meta:
        model = WholesaleItem
        fields = ['name', 'price', 'exp_date']  # Fields to display (readonly)


class WholesaleCustomerForm(forms.ModelForm):
    class Meta:
        model = WholesaleCustomer
        exclude = ['user']


class WholesaleCustomerAddFundsForm(forms.Form):
    amount = forms.DecimalField(max_digits=10, decimal_places=2)




class WholesaleProcurementForm(forms.ModelForm):
    class Meta:
        model = WholesaleProcurement
        fields = ['supplier', 'date']
        widgets = {
            'supplier': forms.Select(attrs={'placeholder': 'Select supplier'}),
            'date': forms.DateInput(attrs={'placeholder': 'Select date', 'type': 'date'}),
        }
        labels = {
            'supplier': 'Supplier',
            'date': 'Date',
        }


class WholesaleProcurementItemForm(forms.ModelForm):
    # Add a hidden field for markup with a default value
    markup = forms.FloatField(initial=0, required=False, widget=forms.HiddenInput())

    class Meta:
        model = WholesaleProcurementItem
        fields = ['item_name', 'dosage_form', 'brand', 'unit', 'quantity', 'cost_price', 'markup', 'expiry_date']
        exclude = ['id', 'procurement', 'subtotal']
        widgets = {
            'item_name': forms.TextInput(attrs={'placeholder': 'Enter item name'}),
            'dosage_form': forms.Select(attrs={'placeholder': 'Dosage form'}),
            'brand': forms.TextInput(attrs={'placeholder': 'Enter brand name'}),
            'unit': forms.Select(attrs={'placeholder': 'Select unit'}),
            'quantity': forms.NumberInput(attrs={'placeholder': 'Enter quantity'}),
            'cost_price': forms.NumberInput(attrs={'placeholder': 'Enter cost price'}),
            'expiry_date': forms.DateInput(attrs={'placeholder': 'Select expiry date', 'type': 'date', 'required': False}),
            # Override the markup field to use a hidden input with a default value
            'markup': forms.HiddenInput(),
        }
        labels = {
            'item_name': 'Item Name',
            'dosage_form': 'D/form',
            'brand': 'Brand',
            'unit': 'Unit',
            'quantity': 'Quantity',
            'cost_price': 'Cost Price',
            'expiry_date': 'Expiry Date',
        }

    def clean(self):
        cleaned_data = super().clean()
        # If the form is empty (no item_name), don't validate other fields
        if not cleaned_data.get('item_name'):
            return cleaned_data

        # Validate required fields only if item_name is provided
        required_fields = ['dosage_form', 'unit', 'quantity', 'cost_price']
        for field in required_fields:
            if not cleaned_data.get(field):
                self.add_error(field, f'{field} is required when adding an item')

        # Validate quantity and cost_price are positive
        quantity = cleaned_data.get('quantity')
        if quantity is not None and quantity <= 0:
            self.add_error('quantity', 'Quantity must be greater than zero')

        cost_price = cleaned_data.get('cost_price')
        if cost_price is not None and cost_price <= 0:
            self.add_error('cost_price', 'Cost price must be greater than zero')

        # Set default value for markup if not provided
        if 'markup' not in cleaned_data or cleaned_data.get('markup') is None:
            cleaned_data['markup'] = 0

        return cleaned_data

    def save(self, commit=True):
        instance = super().save(commit=False)
        # Ensure markup has a default value
        if not hasattr(instance, 'markup') or instance.markup is None:
            instance.markup = 0
        if commit:
            instance.save()
        return instance


# Create a custom formset that validates only non-empty forms
class BaseWholesaleProcurementItemFormSet(forms.BaseModelFormSet):
    def clean(self):
        super().clean()
        # Check that at least one form is filled
        if not any(form.cleaned_data.get('item_name') for form in self.forms if hasattr(form, 'cleaned_data')):
            raise forms.ValidationError('At least one item must be added to the procurement.')

    def _should_delete_form(self, form):
        # Override to consider empty forms as to be deleted
        if not form.has_changed() and not form.cleaned_data.get('item_name'):
            return True
        return super()._should_delete_form(form)

WholesaleProcurementItemFormSet = modelformset_factory(
    WholesaleProcurementItem,
    form=WholesaleProcurementItemForm,
    formset=BaseWholesaleProcurementItemFormSet,
    extra=1,         # Provide an extra blank form for new entries
    can_delete=True,  # Allow deletion of items dynamically
    fields=['item_name', 'dosage_form', 'brand', 'unit', 'quantity', 'cost_price', 'markup', 'expiry_date'],
    exclude=['id', 'procurement', 'subtotal'],  # Explicitly exclude these fields
    validate_min=False  # Don't validate minimum number of forms
)


class WholesaleSettingsForm(forms.ModelForm):
    class Meta:
        model = WholesaleSettings
        fields = ['low_stock_threshold']
        widgets = {
            'low_stock_threshold': forms.NumberInput(attrs={'class': 'form-control'})
        }

