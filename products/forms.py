from django import forms
from django.core.exceptions import ValidationError
from .models import Product, Category


class ProductForm(forms.ModelForm):
    """Main product create/edit form."""

    class Meta:
        model = Product
        fields = [
            'sku', 'barcode', 'name', 'generic_name', 'brand',
            'category', 'drug_schedule', 'dosage_form', 'strength',
            'description',
            'cost_price', 'selling_price', 'mrp', 'tax_rate', 'discount_percent',
            'unit_type', 'min_stock_level', 'max_stock_level', 'storage_location',
            'is_cold_chain', 'is_controlled', 'is_active',
            'image',
        ]
        widgets = {
            'sku': forms.TextInput(attrs={
                'class': 'input-field',
                'placeholder': 'e.g. MED-PCM-500',
            }),
            'barcode': forms.TextInput(attrs={
                'class': 'input-field',
                'placeholder': 'e.g. 479502847192',
            }),
            'name': forms.TextInput(attrs={
                'class': 'input-field',
                'placeholder': 'e.g. Panadol 500mg',
            }),
            'generic_name': forms.TextInput(attrs={
                'class': 'input-field',
                'placeholder': 'e.g. Paracetamol',
            }),
            'brand': forms.TextInput(attrs={
                'class': 'input-field',
                'placeholder': 'e.g. GSK',
            }),
            'category': forms.Select(attrs={'class': 'input-field'}),
            'drug_schedule': forms.Select(attrs={'class': 'input-field'}),
            'dosage_form': forms.TextInput(attrs={
                'class': 'input-field',
                'placeholder': 'e.g. Tablet / Capsule / Syrup',
            }),
            'strength': forms.TextInput(attrs={
                'class': 'input-field',
                'placeholder': 'e.g. 500mg',
            }),
            'description': forms.Textarea(attrs={
                'class': 'input-field h-auto py-2',
                'rows': 3,
                'placeholder': 'Optional notes about this product',
            }),
            'cost_price': forms.NumberInput(attrs={
                'class': 'input-field',
                'step': '0.01',
                'min': '0',
                'placeholder': '0.00',
            }),
            'selling_price': forms.NumberInput(attrs={
                'class': 'input-field',
                'step': '0.01',
                'min': '0',
                'placeholder': '0.00',
            }),
            'mrp': forms.NumberInput(attrs={
                'class': 'input-field',
                'step': '0.01',
                'min': '0',
                'placeholder': '0.00',
            }),
            'tax_rate': forms.NumberInput(attrs={
                'class': 'input-field',
                'step': '0.01',
                'min': '0',
                'max': '100',
            }),
            'discount_percent': forms.NumberInput(attrs={
                'class': 'input-field',
                'step': '0.01',
                'min': '0',
                'max': '100',
            }),
            'unit_type': forms.Select(attrs={'class': 'input-field'}),
            'min_stock_level': forms.NumberInput(attrs={'class': 'input-field', 'min': '0'}),
            'max_stock_level': forms.NumberInput(attrs={'class': 'input-field', 'min': '0'}),
            'storage_location': forms.TextInput(attrs={
                'class': 'input-field',
                'placeholder': 'e.g. Rack B-04-A',
            }),
            'image': forms.FileInput(attrs={
                'class': 'input-field',
                'accept': 'image/*',
            }),
        }

    def clean_sku(self):
        sku = self.cleaned_data['sku'].strip().upper()
        qs = Product.objects.filter(sku__iexact=sku)
        if self.instance.pk:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise ValidationError(f'A product with SKU "{sku}" already exists.')
        return sku

    def clean_barcode(self):
        barcode = (self.cleaned_data.get('barcode') or '').strip()
        if not barcode:
            return barcode
        qs = Product.objects.filter(barcode=barcode)
        if self.instance.pk:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise ValidationError(f'A product with barcode "{barcode}" already exists.')
        return barcode

    def clean(self):
        cleaned = super().clean()
        cost = cleaned.get('cost_price')
        selling = cleaned.get('selling_price')
        mrp = cleaned.get('mrp')
        min_level = cleaned.get('min_stock_level')
        max_level = cleaned.get('max_stock_level')

        if cost is not None and selling is not None and selling < cost:
            self.add_error(
                'selling_price',
                f'Selling price (LKR {selling}) cannot be less than cost price (LKR {cost}).'
            )

        if mrp and selling and mrp < selling:
            self.add_error(
                'mrp',
                f'MRP (LKR {mrp}) should be >= selling price (LKR {selling}).'
            )

        if min_level is not None and max_level is not None and max_level <= min_level:
            self.add_error(
                'max_stock_level',
                f'Max stock level ({max_level}) must be greater than min stock level ({min_level}).'
            )

        return cleaned


class CategoryForm(forms.ModelForm):
    class Meta:
        model = Category
        fields = ['name', 'description', 'is_active']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'input-field', 'placeholder': 'e.g. Analgesics'}),
            'description': forms.Textarea(attrs={'class': 'input-field h-auto py-2', 'rows': 3}),
        }

    def clean_name(self):
        name = self.cleaned_data['name'].strip()
        qs = Category.objects.filter(name__iexact=name)
        if self.instance.pk:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise ValidationError(f'A category named "{name}" already exists.')
        return name