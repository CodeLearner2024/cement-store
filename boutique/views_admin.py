from django.views.generic import CreateView, UpdateView, ListView
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.urls import reverse_lazy
from django.contrib import messages
from django.utils.translation import gettext_lazy as _
from django.shortcuts import redirect

from .models import Product, Category, ProductImage
from .forms import ProductForm

class AdminRequiredMixin(LoginRequiredMixin, UserPassesTestMixin):
    """Vérifie que l'utilisateur est un administrateur."""
    login_url = reverse_lazy('account_login')
    
    def test_func(self):
        return self.request.user.is_staff or self.request.user.is_superuser

class ProductCreateView(AdminRequiredMixin, CreateView):
    """Vue pour l'ajout d'un nouveau produit."""
    model = Product
    form_class = ProductForm
    template_name = 'boutique/admin/product_create.html'
    success_url = reverse_lazy('boutique:admin_product_list')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['categories'] = Category.objects.all()
        return context
    
    def form_valid(self, form):
        # Définir l'utilisateur actuel comme créateur du produit
        form.instance.added_by = self.request.user
        
        # Sauvegarder d'abord le produit
        response = super().form_valid(form)
        
        # Gérer les images téléchargées
        images = self.request.FILES.getlist('images')
        for image in images:
            ProductImage.objects.create(product=self.object, image=image)
        
        messages.success(self.request, _('Le produit a été créé avec succès.'))
        return response
    
    def form_invalid(self, form):
        messages.error(self.request, _('Veuillez corriger les erreurs ci-dessous.'))
        return super().form_invalid(form)
