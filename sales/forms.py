from django import forms


class CustomerAttachForm(forms.Form):
    """Optional customer attach for POS."""
    customer_name = forms.CharField(
        max_length=200, required=False,
        widget=forms.TextInput(attrs={
            'class': 'input-field',
            'placeholder': 'Walk-in Customer',
        })
    )
    customer_mobile = forms.CharField(
        max_length=20, required=False,
        widget=forms.TextInput(attrs={
            'class': 'input-field',
            'placeholder': '+94 77 XXX XXXX',
        })
    )
    customer_email = forms.EmailField(
        required=False,
        widget=forms.EmailInput(attrs={
            'class': 'input-field',
            'placeholder': 'customer@example.com',
        })
    )