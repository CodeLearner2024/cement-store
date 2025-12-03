from django.contrib import admin
from django.urls import path
from django.utils.translation import gettext_lazy as _

# Import de la vue personnalisée
from boutique.admin_views_custom import CustomProductCreateView

# Surcharger la vue d'ajout de produit
def get_urls():
    from django.urls import path
    from django.contrib.admin import ModelAdmin
    
    # Importer les vues d'administration originales
    from django.contrib.admin.sites import AdminSite
    from django.contrib.admin.options import ModelAdmin
    
    # Créer une sous-classe personnalisée de ModelAdmin
    class CustomProductAdmin(ModelAdmin):
        def get_urls(self):
            # Obtenir les URLs par défaut
            urls = super().get_urls()
            
            # Remplacer la vue d'ajout par notre vue personnalisée
            custom_urls = [
                path(
                    'boutique/product/add/',
                    self.admin_site.admin_view(CustomProductCreateView.as_view()),
                    name='boutique_product_add',
                ),
            ]
            
            # Remplacer l'URL d'ajout par défaut
            return custom_urls + urls[1:]
    
    # Enregistrer notre admin personnalisé
    from django.contrib import admin
    from boutique.models import Product
    
    # Désenregistrer l'admin par défaut s'il est déjà enregistré
    if admin.site.is_registered(Product):
        admin.site.unregister(Product)
    
    # Enregistrer notre admin personnalisé
    admin.site.register(Product, CustomProductAdmin)
    
    # Retourner les URLs de l'admin
    return admin.site.get_urls()

# S'assurer que les URLs personnalisées sont chargées
admin.site.get_urls = get_urls
