from django.urls import path
from . import views

urlpatterns = [
    path('', views.loginpage, name='login'),
    path('register/', views.registerpage, name='register'),
    path('dashboard/', views.dashboard, name='dashboard'),
    path('logout/', views.logout_user, name='logout'),
    path('domicile/', views.domicile, name='domicile'),
    path('domicile/form/', views.domicile_form, name='domicile_form'),
    path(
    'domicile/download/<int:app_id>/',
    views.download_domicile_certificate,
    name='download_domicile'
    ),
   
]


