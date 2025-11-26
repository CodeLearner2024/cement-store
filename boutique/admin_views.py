from django.views.generic import ListView, CreateView, UpdateView, DeleteView, DetailView
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.urls import reverse_lazy
from django.contrib import messages
from django.utils.translation import gettext_lazy as _
from django.db.models import Count, Sum, Q
from django.utils import timezone
from django.shortcuts import redirect, get_object_or_404
from django.views.generic.edit import FormMixin

from .models import Category, Product, Order, OrderItem
from .forms import CategoryForm, ProductForm, OrderStatusForm
from django.contrib.auth import get_user_model

User = get_user_model()

class AdminRequiredMixin(LoginRequiredMixin, UserPassesTestMixin):
    login_url = reverse_lazy('account_login')
    
    def test_func(self):
        return self.request.user.is_superuser

# Vues pour les catégories
class CategoryListView(AdminRequiredMixin, ListView):
    model = Category
    template_name = 'boutique/admin/category_list.html'
    context_object_name = 'categories'
    paginate_by = 10

class CategoryCreateView(AdminRequiredMixin, CreateView):
    model = Category
    form_class = CategoryForm
    template_name = 'boutique/admin/category_form.html'
    success_url = reverse_lazy('boutique:admin_category_list')
    
    def form_valid(self, form):
        messages.success(self.request, _('La catégorie a été créée avec succès.'))
        return super().form_valid(form)

class CategoryUpdateView(AdminRequiredMixin, UpdateView):
    model = Category
    form_class = CategoryForm
    template_name = 'boutique/admin/category_form.html'
    success_url = reverse_lazy('boutique:admin_category_list')
    
    def form_valid(self, form):
        messages.success(self.request, _('La catégorie a été mise à jour avec succès.'))
        return super().form_valid(form)

class CategoryDeleteView(AdminRequiredMixin, DeleteView):
    model = Category
    template_name = 'boutique/admin/category_confirm_delete.html'
    success_url = reverse_lazy('boutique:admin_category_list')
    
    def delete(self, request, *args, **kwargs):
        messages.success(self.request, _('La catégorie a été supprimée avec succès.'))
        return super().delete(request, *args, **kwargs)

# Vues pour les produits
class ProductListView(AdminRequiredMixin, ListView):
    model = Product
    template_name = 'boutique/admin/product_list.html'
    context_object_name = 'products'
    paginate_by = 12
    
    def get_queryset(self):
        queryset = super().get_queryset().select_related('category')
        search_query = self.request.GET.get('q')
        category_id = self.request.GET.get('category')
        
        if search_query:
            queryset = queryset.filter(
                Q(name__icontains=search_query) |
                Q(description__icontains=search_query)
            )
        
        if category_id:
            queryset = queryset.filter(category_id=category_id)
            
        return queryset
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['categories'] = Category.objects.all()
        return context

class ProductCreateView(AdminRequiredMixin, CreateView):
    model = Product
    form_class = ProductForm
    template_name = 'boutique/admin/product_form.html'
    success_url = reverse_lazy('boutique:admin_product_list')
    
    def form_valid(self, form):
        messages.success(self.request, _('Le produit a été créé avec succès.'))
        return super().form_valid(form)

class ProductUpdateView(AdminRequiredMixin, UpdateView):
    model = Product
    form_class = ProductForm
    template_name = 'boutique/admin/product_form.html'
    success_url = reverse_lazy('boutique:admin_product_list')
    
    def form_valid(self, form):
        messages.success(self.request, _('Le produit a été mis à jour avec succès.'))
        return super().form_valid(form)

class ProductDeleteView(AdminRequiredMixin, DeleteView):
    model = Product
    template_name = 'boutique/admin/product_confirm_delete.html'
    success_url = reverse_lazy('boutique:admin_product_list')
    
    def delete(self, request, *args, **kwargs):
        messages.success(self.request, _('Le produit a été supprimé avec succès.'))
        return super().delete(request, *args, **kwargs)

# Vues pour les utilisateurs
class UserListView(AdminRequiredMixin, ListView):
    model = User
    template_name = 'boutique/admin/user_list.html'
    context_object_name = 'users'
    paginate_by = 15
    
    def get_queryset(self):
        queryset = super().get_queryset().order_by('-date_joined')
        search_query = self.request.GET.get('q')
        
        if search_query:
            queryset = queryset.filter(
                Q(username__icontains=search_query) |
                Q(email__icontains=search_query) |
                Q(first_name__icontains=search_query) |
                Q(last_name__icontains=search_query)
            )
            
        return queryset

class UserDetailView(AdminRequiredMixin, DetailView):
    model = User
    template_name = 'boutique/admin/user_detail.html'
    context_object_name = 'user_profile'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.get_object()
        context['orders'] = Order.objects.filter(user=user).order_by('-created_at')[:10]
        return context

# Vues pour les commandes
class OrderListView(AdminRequiredMixin, ListView):
    model = Order
    template_name = 'boutique/admin/order_list.html'
    context_object_name = 'orders'
    paginate_by = 15
    
    def get_queryset(self):
        queryset = super().get_queryset().select_related('user')
        status = self.request.GET.get('status')
        search_query = self.request.GET.get('q')
        
        if status:
            queryset = queryset.filter(status=status)
            
        if search_query:
            queryset = queryset.filter(
                Q(id__icontains=search_query) |
                Q(user__username__icontains=search_query) |
                Q(user__email__icontains=search_query) |
                Q(first_name__icontains=search_query) |
                Q(last_name__icontains=search_query)
            )
            
        return queryset.order_by('-created_at')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['status_choices'] = dict(Order.STATUS_CHOICES)
        return context

class OrderDetailView(AdminRequiredMixin, FormMixin, DetailView):
    model = Order
    template_name = 'boutique/admin/order_detail.html'
    context_object_name = 'order'
    form_class = OrderStatusForm
    
    def get_success_url(self):
        return reverse_lazy('boutique:admin_order_detail', kwargs={'pk': self.object.pk})
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['status_choices'] = dict(Order.STATUS_CHOICES)
        return context
    
    def post(self, request, *args, **kwargs):
        self.object = self.get_object()
        form = self.get_form()
        
        if form.is_valid():
            return self.form_valid(form)
        else:
            return self.form_invalid(form)
    
    def form_valid(self, form):
        new_status = form.cleaned_data['status']
        self.object.status = new_status
        
        # Mettre à jour la date de mise à jour
        self.object.updated_at = timezone.now()
        
        # Si la commande est marquée comme payée, mettre à jour la date de paiement
        if new_status == 'payee' and not self.object.paid:
            self.object.paid = True
            
        self.object.save()
        
        messages.success(
            self.request,
            _(f'Le statut de la commande a été mis à jour: {dict(Order.STATUS_CHOICES).get(new_status)}')
        )
        
        return super().form_valid(form)

class OrderDeleteView(AdminRequiredMixin, DeleteView):
    model = Order
    template_name = 'boutique/admin/order_confirm_delete.html'
    success_url = reverse_lazy('boutique:admin_order_list')
    
    def delete(self, request, *args, **kwargs):
        messages.success(self.request, _('La commande a été supprimée avec succès.'))
        return super().delete(request, *args, **kwargs)
