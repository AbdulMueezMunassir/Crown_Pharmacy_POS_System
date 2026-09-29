from django.urls import path
from . import views

app_name = 'inventory'

urlpatterns = [
    # Overview
    path('', views.overview, name='overview'),

    # Batches
    path('batches/', views.batch_list, name='batch_list'),
    path('batches/<int:pk>/', views.batch_detail, name='batch_detail'),

    # Stock Receiving (GRN)
    path('receiving/', views.grn_list, name='grn_list'),
    path('receiving/new/', views.grn_create, name='grn_create'),
    path('receiving/<int:pk>/', views.grn_detail, name='grn_detail'),
    path('receiving/<int:pk>/post/', views.grn_post, name='grn_post'),
    path('receiving/<int:pk>/cancel/', views.grn_cancel, name='grn_cancel'),
]