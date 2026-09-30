from django.urls import path
from . import views

app_name = 'sales'

urlpatterns = [
    # POS
    path('pos/', views.pos, name='pos'),

    # APIs
    path('api/search/', views.api_product_search, name='api_search'),
    path('api/product/<int:product_id>/batches/', views.api_product_batches, name='api_batches'),
    path('api/checkout/', views.api_checkout, name='api_checkout'),

    # History & Invoices
    path('', views.sale_list, name='list'),
    path('<int:pk>/', views.sale_detail, name='detail'),
    path('<int:pk>/invoice/', views.invoice_view, name='invoice'),
]