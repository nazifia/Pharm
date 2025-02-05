from django import forms
from .models import *
from customer.models import Customer
from supplier.models import *
from django.contrib.auth.forms import UserChangeForm
from django.forms import modelformset_factory


UNIT = [
    ('Amp', 'Amp'),
    ('Bottle', 'Bottle'),
    ('Tab', 'Tab'),
    ('Tin', 'Tin'),
    ('Caps', 'Caps'),
    ('Card', 'Card'),
    ('Carton', 'Carton'),
    ('Pack', 'Pack'),
    ('Pcs', 'Pcs'),
    ('Roll', 'Roll'),
    ('Vail', 'Vail'),
    ('1L', '1L'),
    ('2L', '2L'),
    ('4L', '4L'),
]



MARKUP_CHOICES = [
        (0, 'No markup'),
        (2.5, '2.5% markup'),
        (5, '5% markup'),
        (7.5, '7.5% markup'),
        (10, '10% markup'),
        (12.5, '12.5% markup'),
        (15, '15% markup'),
        (17.5, '17.5% markup'),
        (20, '20% markup'),
        (22.5, '22.5% markup'),
        (25, '25% markup'),
        (27.5, '27.5% markup'),
        (30, '30% markup'),
        (32.5, '32.5% markup'),
        (35, '35% markup'),
        (37.5, '37.5% markup'),
        (40, '40% markup'),
        (42.5, '42.5% markup'),
        (45, '45% markup'),
        (47.5, '47.5% markup'),
        (50, '50% markup'),
        (57.5, '57.5% markup'),
        (60, '60% markup'),
        (62.5, '62.5% markup'),
        (65, '65% markup'),
        (67.5, '67.5% markup'),
        (70, '70% markup'),
        (72., '72.% markup'),
        (75, '75% markup'),
        (77.5, '77.5% markup'),
        (80, '80% markup'),
        (82.5, '82.% markup'),
        (85, '85% markup'),
        (87.5, '87.5% markup'),
        (90, '90% markup'),
        (92., '92.% markup'),
        (95, '95% markup'),
        (97.5, '97.5% markup'),
        (100, '100% markup'),
    ]



class EditUserProfileForm(UserChangeForm):
    
    class Meta:
        model = User
        fields = ['username', 'password', 'first_name', 'last_name']


class addItemForm(forms.ModelForm):
    name = forms.CharField(max_length=200)
    dosage_form = forms.ChoiceField(
        choices=[
            ('Unit', 'Dosage form'),
            ('Tablet', 'Tablet'),
            ('Capsule', 'Capsule'),
            ('Consumable', 'Consumable'),
            ('Cream', 'Cream'),
            ('Syrup', 'Syrup'),
            ('Suspension', 'Suspension'),
            ('Eye-drop', 'Eye-drop'),
            ('Ear-drop', 'Ear-drop'),
            ('Eye-ointment', 'Eye-ointment'),
            ('Nasal', 'Nasal'),
            ('Injection', 'Injection'),
            ('Infusion', 'Infusion'),
            ('Inhaler', 'Inhaler'),
            ('Vaginal', 'Vaginal'),
            ('Rectal', 'Rectal'),
        ],
        widget=forms.Select(attrs={'class': 'form-control mt-3'}),
    )
    brand = forms.CharField(max_length=200)
    unit = forms.CharField(max_length=200)
    cost = forms.DecimalField(max_digits=12, decimal_places=2)
    markup = forms.DecimalField(max_digits=6, decimal_places=2)
    stock = forms.IntegerField()
    exp_date = forms.DateField()

    class Meta:
        model = Item
        fields = ('name', 'dosage_form', 'brand', 'unit', 'cost', 'markup', 'stock', 'exp_date')

        

class dispenseForm(forms.Form):
    q = forms.CharField(min_length=2, label='', widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder':'SEARCH  HERE...'}))


class CustomerForm(forms.ModelForm):
    class Meta:
        model = Customer
        exclude = ['user']


class AddFundsForm(forms.Form):
    amount = forms.DecimalField(max_digits=10, decimal_places=2)
    


class ReturnItemForm(forms.ModelForm):
    return_item_quantity = forms.IntegerField(min_value=1, label="Return Quantity")

    class Meta:
        model = Item
        fields = ['name', 'dosage_form', 'brand', 'price', 'exp_date']  # Fields to display (readonly)






class SupplierRegistrationForm(forms.ModelForm):
    class Meta:
        model = Supplier
        fields = ['name', 'phone', 'contact_info']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'phone': forms.TextInput(attrs={'class': 'form-control'}),
            'contact_info': forms.TextInput(attrs={'class': 'form-control'}),            
        }






class ProcurementForm(forms.ModelForm):
    class Meta:
        model = Procurement
        fields = ['supplier', 'date']
        widgets = {
            'supplier': forms.Select(attrs={'placeholder': 'Select supplier'}),
            'date': forms.DateInput(attrs={'placeholder': 'Select date', 'type': 'date'}),
        }
        labels = {
            'supplier': 'Supplier',
            'date': 'Date',
        }




class ProcurementItemForm(forms.ModelForm):
    class Meta:
        model = ProcurementItem
        fields = ['item_name', 'dosage_form', 'brand', 'unit', 'quantity', 'cost_price']
        widgets = {
            'item_name': forms.TextInput(attrs={'placeholder': 'Enter item name'}),
            'dosage_form': forms.Select(attrs={'placeholder': 'Dosage form'}),
            'brand': forms.TextInput(attrs={'placeholder': 'Enter brand name'}),
            'unit': forms.Select(attrs={'placeholder': 'Select unit'}),
            'quantity': forms.NumberInput(attrs={'placeholder': 'Enter quantity'}),
            'cost_price': forms.NumberInput(attrs={'placeholder': 'Enter cost price'}),
        }
        labels = {
            'item_name': 'Item Name',
            'dosage_form': 'D/form',
            'brand': 'Brand',
            'unit': 'Unit',
            'quantity': 'Quantity',
            'cost_price': 'Cost Price',
        }

ProcurementItemFormSet = modelformset_factory( ProcurementItem, form=ProcurementItemForm, extra=0)
