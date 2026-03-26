from django.urls import path
from . import views

urlpatterns = [
    # Auth
    path('', views.loginpage, name='login'),
    path('register/', views.registerpage, name='register'),
    path('logout/', views.logout_user, name='logout'),

    # Dashboard
    path('dashboard/', views.dashboard, name='dashboard'),

    # Domicile Certificate
    path('domicile/', views.domicile, name='domicile'),
    path('domicile/ocr/', views.domicile_ocr_ajax, name='domicile_ocr_ajax'),
    path('domicile/form/', views.domicile_form, name='domicile_form'),
    path('domicile/download/<int:app_id>/', views.download_domicile_certificate, name='download_domicile'),

    # Income Certificate
    path('income/', views.income, name='income'),
    path('income/ocr/', views.income_ocr_ajax, name='income_ocr_ajax'),
    path('income/form/', views.income_form, name='income_form'),
    path('income/download/<int:app_id>/', views.download_income_certificate, name='download_income'),
]
