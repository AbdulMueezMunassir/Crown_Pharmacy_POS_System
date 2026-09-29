from django import forms
from django.forms import inlineformset_factory
from datetime import date

from .models import GRN, GRNItem
from products.models import Product
from suppliers.models import Supplier


class GRNForm(forms.ModelForm):
    """Header form for Goods Received Note."""

    class Meta:
        model = GRN
        fields = [
            'supplier', 'supplier_invoice', 'do_number', 'po_number',
            'inward_date', 'notes',
        ]
        widgets = {
            'supplier': forms.Select(attrs={'class': 'input-field'}),
            'supplier_invoice': forms.TextInput(attrs={
                'class': 'input-field',
                'placeholder': 'e.g. GSK-INV-89104',
            }),
            'do_number': forms.TextInput(attrs={
                'class': 'input-field',
                'placeholder': 'Delivery Order number',
            }),
            'po_number': forms.TextInput(attrs={
                'class': 'input-field',
                'placeholder': 'Purchase Order number',
            }),
            'inward_date': forms.DateInput(attrs={
                'class': 'input-field',
                'type': 'date',
            }),
            'notes': forms.Textarea(attrs={
                'class': 'input-field h-auto py-2',
                'rows': 2,
                'placeholder': 'Optional receiving notes',
            }),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['supplier'].queryset = Supplier.objects.filter(status='active')
        if not self.instance.pk:
            self.fields['inward_date'].initial = date.today()


class GRNItemForm(forms.ModelForm):
    """Inline form for a GRN line item."""

    class Meta:
        model = GRNItem
        fields = [
            'product', 'batch_number', 'quantity', 'free_quantity',
            'cost_price', 'discount_percent', 'selling_price',
            'manufacturing_date', 'expiry_date',
        ]
        widgets = {
            'product': forms.Select(attrs={'class': 'input-field text-xs'}),
            'batch_number': forms.TextInput(attrs={
                'class': 'input-field text-xs',
                'placeholder': 'e.g. BATCH-2024-A',
            }),
            'quantity': forms.NumberInput(attrs={
                'class': 'input-field text-xs text-right',
                'min': '1',
                'placeholder': '0',
            }),
            'free_quantity': forms.NumberInput(attrs={
                'class': 'input-field text-xs text-right',
                'min': '0',
                'placeholder': '0',
            }),
            'cost_price': forms.NumberInput(attrs={
                'class': 'input-field text-xs text-right',
                'step': '0.01',
                'min': '0',
                'placeholder': '0.00',
            }),
            'discount_percent': forms.NumberInput(attrs={
                'class': 'input-field text-xs text-right',
                'step': '0.01',
                'min': '0',
                'max': '100',
                'placeholder': '0',
            }),
            'selling_price': forms.NumberInput(attrs={
                'class': 'input-field text-xs text-right',
                'step': '0.01',
                'min': '0',
                'placeholder': '0.00',
            }),
            'manufacturing_date': forms.DateInput(attrs={
                'class': 'input-field text-xs',
                'type': 'date',
            }),
            'expiry_date': forms.DateInput(attrs={
                'class': 'input-field text-xs',
                'type': 'date',
            }),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['product'].queryset = Product.objects.filter(is_active=True).order_by('name')
        # Make non-essential fields optional for rows that are empty
        for field_name in ['product', 'batch_number', 'quantity', 'cost_price', 'selling_price', 'expiry_date']:
            self.fields[field_name].required = False

    def clean(self):
        cleaned = super().clean()
        # If nothing was entered, skip validation (empty formset row)
        if not cleaned.get('product') and not cleaned.get('batch_number'):
            return cleaned

        # If any field is set, require the critical ones
        if not cleaned.get('product'):
            self.add_error('product', 'Product is required.')
        if not cleaned.get('batch_number'):
            self.add_error('batch_number', 'Batch number is required.')
        if not cleaned.get('quantity'):
            self.add_error('quantity', 'Quantity is required.')
        if not cleaned.get('cost_price'):
            self.add_error('cost_price', 'Cost price is required.')
        if not cleaned.get('selling_price'):
            self.add_error('selling_price', 'Selling price is required.')
        if not cleaned.get('expiry_date'):
            self.add_error('expiry_date', 'Expiry date is required.')

        # Validate expiry > today
        if cleaned.get('expiry_date') and cleaned['expiry_date'] <= date.today():
            self.add_error('expiry_date', 'Expiry date must be in the future.')

        # Validate selling >= cost
        cost = cleaned.get('cost_price')
        selling = cleaned.get('selling_price')
        if cost and selling and selling < cost:
            self.add_error('selling_price', f'Selling price cannot be less than cost ({cost}).')

        return cleaned


# Inline formset for GRN items
GRNItemFormSet = inlineformset_factory(
    GRN,
    GRNItem,
    form=GRNItemForm,
    extra=3,          # 3 empty rows
    can_delete=True,
    min_num=1,
    validate_min=True,
)