from django.urls import path, include
from django.views.generic import RedirectView
from django.utils.translation import gettext_lazy as _
from . import views
from .admin_views import (
    CategoryListView, CategoryCreateView, CategoryUpdateView, CategoryDeleteView,
    ProductListView, ProductCreateView, ProductUpdateView, ProductDeleteView,
    UserListView, UserDetailView,
    OrderListView, OrderDetailView, OrderDeleteView
)

app_name = 'boutique'

urlpatterns = [
    # Page d'accueil
    path('', views.HomeView.as_view(), name='home'),
    
    # Produits
    path('produits/', views.ProductListView.as_view(), name='product_list'),
    path('categorie/<slug:category_slug>/', views.ProductListView.as_view(), name='product_list_by_category'),
    path('produit/<int:pk>/<slug:slug>/', views.ProductDetailView.as_view(), name='product_detail'),
    
    # Panier
    path('panier/', views.CartView.as_view(), name='cart'),
    path('panier/ajouter/<int:product_id>/', views.add_to_cart, name='add_to_cart'),
    path('panier/mettre-a-jour/<int:item_id>/', views.update_cart_item, name='update_cart_item'),
    path('panier/supprimer/<int:item_id>/', views.remove_from_cart, name='remove_from_cart'),
    
    # Commande
    path('commande/', views.CheckoutView.as_view(), name='checkout'),
    path('commande/succes/', views.PaymentSuccessView.as_view(), name='payment_success'),
    path('commande/annulee/', views.PaymentCancelledView.as_view(), name='payment_cancelled'),
    path('commande/webhook/', views.stripe_webhook, name='stripe_webhook'),
    
    # Historique des commandes
    path('mon-compte/commandes/', views.OrderHistoryView.as_view(), name='order_history'),
    path('mon-compte/commandes/<uuid:pk>/', views.OrderDetailView.as_view(), name='order_detail'),
    
    # Avis
    path('produit/<int:product_id>/ajouter-avis/', views.add_review, name='add_review'),
    
    # Administration
    path('admin/dashboard/', views.AdminDashboardView.as_view(), name='admin_dashboard'),
    
    # Gestion des catégories
    path('admin/categories/', CategoryListView.as_view(), name='admin_category_list'),
    path('admin/categories/ajouter/', CategoryCreateView.as_view(), name='admin_category_add'),
    path('admin/categories/<int:pk>/modifier/', CategoryUpdateView.as_view(), name='admin_category_edit'),
    path('admin/categories/<int:pk>/supprimer/', CategoryDeleteView.as_view(), name='admin_category_delete'),
    
    # Gestion des produits
    path('admin/produits/', ProductListView.as_view(), name='admin_product_list'),
    path('admin/produits/ajouter/', ProductCreateView.as_view(), name='admin_product_add'),
    path('admin/produits/<int:pk>/modifier/', ProductUpdateView.as_view(), name='admin_product_edit'),
    path('admin/produits/<int:pk>/supprimer/', ProductDeleteView.as_view(), name='admin_product_delete'),
    
    # Gestion des utilisateurs
    path('admin/utilisateurs/', UserListView.as_view(), name='admin_user_list'),
    path('admin/utilisateurs/<int:pk>/', UserDetailView.as_view(), name='admin_user_detail'),
    
    # Gestion des commandes
    path('admin/commandes/', OrderListView.as_view(), name='admin_order_list'),
    path('admin/commandes/<uuid:pk>/', OrderDetailView.as_view(), name='admin_order_detail'),
    path('admin/commandes/<uuid:pk>/supprimer/', OrderDeleteView.as_view(), name='admin_order_delete'),
    
    # Redirection pour les URLs de l'ancienne version
    path('catalog/', RedirectView.as_view(pattern_name='boutique:product_list', permanent=True)),
    path('catalog/category/<slug:category_slug>/', 
         RedirectView.as_view(pattern_name='boutique:product_list_by_category', permanent=True)),
    path('catalog/product/<int:pk>/<slug:slug>/', 
         RedirectView.as_view(pattern_name='boutique:product_detail', permanent=True)),
]
