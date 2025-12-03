"""
URL configuration for ecommerce project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.2/topics/http/urls/
"""
from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.contrib.auth import views as auth_views
from django.urls import path, include
from django.views.generic import RedirectView
from django.views.i18n import set_language

urlpatterns = [
    # Admin
    path('admin/', admin.site.urls),
    
    # Allauth URLs (gestion des comptes utilisateurs)
    path('comptes/', include('allauth.urls')),
    
    # Application boutique
    path('boutique/', include('boutique.urls', namespace='boutique')),
    
    # Gestion des langues
    path('i18n/', include('django.conf.urls.i18n')),
    
    # Redirection de la racine vers la boutique
    path('', RedirectView.as_view(pattern_name='boutique:home', permanent=False)),
]

# URLs pour les médias en mode développement
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    
    # Debug toolbar
    import debug_toolbar
    urlpatterns = [
        path('__debug__/', include(debug_toolbar.urls)),
    ] + urlpatterns
