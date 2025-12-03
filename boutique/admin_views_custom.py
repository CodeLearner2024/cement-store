from django.views.generic import CreateView
from django.contrib.admin.views.decorators import staff_member_required
from django.utils.decorators import method_decorator
from django.contrib import messages
from django.urls import reverse_lazy
from django.utils.translation import gettext_lazy as _

from .models import Product, ProductImage, Category
from .forms import ProductForm

@method_decorator(staff_member_required, name='dispatch')
class CustomProductCreateView(CreateView):
    """Vue personnalisée pour l'ajout d'un produit."""
    model = Product
    form_class = ProductForm
    template_name = 'boutique/admin/product_create.html'
    success_url = reverse_lazy('admin:boutique_product_changelist')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update({
            'title': _('Ajouter un produit'),
            'opts': self.model._meta,
            'has_view_permission': True,
            'has_add_permission': True,
            'has_change_permission': True,
            'has_delete_permission': True,
            'has_file_field': True,
            'has_editable_inline_admin_formsets': True,
            'is_popup': False,
            'is_nav_sidebar_enabled': True,
            'categories': Category.objects.all(),
        })
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
        
        # Message de succès personnalisé
        messages.success(
            self.request,
            _('Le produit "%s" a été ajouté avec succès.') % self.object.name,
            extra_tags='',
            fail_silently=True,
        )
        
        return response
    
    def form_invalid(self, form):
        messages.error(
            self.request,
            _('Veuillez corriger les erreurs ci-dessous.'),
            extra_tags='',
            fail_silently=True,
        )
        return super().form_invalid(form)
