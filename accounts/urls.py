
from django.urls import path
from . import views

urlpatterns = [
    path('callback/', views.callback),
    path('auth-connect/', views.auth_connect),
    path('auth/tokens/', views.tokens),
    path('ringcentral/access/', views.get_auth_from_jwt)
]