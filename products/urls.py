from django.urls import path
from . import views

app_name = 'products'

urlpatterns = [
    path('', views.product_list, name='list'),
    # We'll add create/edit/detail URLs tomorrow
]