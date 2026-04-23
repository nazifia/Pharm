from django.urls import path
from . import views

app_name = 'subscription'

urlpatterns = [
    path('', views.subscription_status, name='status'),
    path('expired/', views.expired_view, name='expired'),
    path('setup/', views.setup_trial, name='setup'),
    path('record-payment/', views.record_payment, name='record_payment'),
]
