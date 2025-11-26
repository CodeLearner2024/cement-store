from django.shortcuts import render, get_object_or_404, redirect
from django.views.generic import ListView, DetailView, View, TemplateView
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.contrib import messages
from django.utils import timezone
from django.db.models import Q, Sum, Count, Avg
from django.http import JsonResponse, HttpResponseRedirect
from django.urls import reverse, reverse_lazy
from django.views.decorators.http import require_POST
from django.contrib.auth.decorators import login_required
from django.views.decorators.csrf import csrf_exempt
from django.conf import settings
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.utils.translation import gettext_lazy as _

import stripe

from .models import Category, Product, Cart, CartItem, Order, OrderItem, Review
from .forms import AddToCartForm, CheckoutForm, ReviewForm

# Configuration de Stripe
stripe.api_key = settings.STRIPE_SECRET_KEY


class HomeView(ListView):
    template_name = 'boutique/home.html'
    model = Product
    context_object_name = 'products'
    paginate_by = 8

    def get_queryset(self):
        return Product.objects.filter(available=True).order_by('-created_at')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['featured_categories'] = Category.objects.annotate(
            num_products=Count('products')
        ).filter(num_products__gt=0).order_by('-created_at')[:6]
        return context


class ProductListView(ListView):
    model = Product
    template_name = 'boutique/product_list.html'
    context_object_name = 'products'
    paginate_by = 12

    def get_queryset(self):
        queryset = Product.objects.filter(available=True)
        
        # Filtrage par catégorie
        category_slug = self.kwargs.get('category_slug')
        if category_slug:
            category = get_object_or_404(Category, slug=category_slug)
            queryset = queryset.filter(category=category)
        
        # Filtrage par recherche
        query = self.request.GET.get('q')
        if query:
            queryset = queryset.filter(
                Q(name__icontains=query) | 
                Q(description__icontains=query) |
                Q(category__name__icontains=query)
            )
        
        # Tri
        sort_by = self.request.GET.get('sort_by', 'newest')
        if sort_by == 'price_asc':
            queryset = queryset.order_by('price')
        elif sort_by == 'price_desc':
            queryset = queryset.order_by('-price')
        elif sort_by == 'name':
            queryset = queryset.order_by('name')
        else:  # newest
            queryset = queryset.order_by('-created_at')
            
        return queryset
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['categories'] = Category.objects.all()
        context['current_category'] = self.kwargs.get('category_slug')
        context['sort_by'] = self.request.GET.get('sort_by', 'newest')
        context['q'] = self.request.GET.get('q', '')
        return context


class ProductDetailView(DetailView):
    model = Product
    template_name = 'boutique/product_detail.html'
    context_object_name = 'product'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['form'] = AddToCartForm(initial={'quantity': 1})
        context['related_products'] = Product.objects.filter(
            category=self.object.category,
            available=True
        ).exclude(id=self.object.id)[:4]
        
        # Récupérer les avis avec pagination
        reviews = self.object.reviews.all().order_by('-created_at')
        paginator = Paginator(reviews, 5)
        page = self.request.GET.get('page')
        
        try:
            reviews = paginator.page(page)
        except PageNotAnInteger:
            reviews = paginator.page(1)
        except EmptyPage:
            reviews = paginator.page(paginator.num_pages)
            
        context['reviews'] = reviews
        
        # Calculer la note moyenne
        if reviews:
            context['average_rating'] = self.object.reviews.aggregate(
                avg_rating=Avg('rating')
            )['avg_rating']
        
        return context


class CartView(View):
    def get(self, request, *args, **kwargs):
        cart_id = request.session.get('cart_id')
        
        if cart_id:
            cart = get_object_or_404(Cart, id=cart_id)
        else:
            cart = Cart.objects.create()
            request.session['cart_id'] = str(cart.id)
            
        return render(request, 'boutique/cart.html', {'cart': cart})


@require_POST
def add_to_cart(request, product_id):
    cart_id = request.session.get('cart_id')
    
    if not cart_id:
        cart = Cart.objects.create()
        request.session['cart_id'] = str(cart.id)
    else:
        cart = get_object_or_404(Cart, id=cart_id)
    
    product = get_object_or_404(Product, id=product_id)
    form = AddToCartForm(request.POST)
    
    if form.is_valid():
        quantity = form.cleaned_data['quantity']
        
        # Vérifier si le produit est déjà dans le panier
        cart_item, created = CartItem.objects.get_or_create(
            cart=cart,
            product=product,
            defaults={'quantity': quantity, 'price': product.price}
        )
        
        if not created:
            cart_item.quantity += quantity
            cart_item.save()
        
        messages.success(request, _("Le produit a été ajouté à votre panier."))
    
    return redirect('boutique:product_detail', pk=product_id, slug=product.slug)


@require_POST
def update_cart_item(request, item_id):
    cart_item = get_object_or_404(CartItem, id=item_id)
    
    if 'quantity' in request.POST:
        try:
            quantity = int(request.POST['quantity'])
            if quantity > 0:
                cart_item.quantity = quantity
                cart_item.save()
                messages.success(request, _("La quantité a été mise à jour."))
            else:
                cart_item.delete()
                messages.success(request, _("L'article a été retiré du panier."))
        except (ValueError, TypeError):
            messages.error(request, _("Quantité invalide."))
    
    return redirect('boutique:cart')


from django.views.decorators.http import require_http_methods

@require_http_methods(["DELETE", "POST"])
def remove_from_cart(request, item_id):
    try:
        cart_item = get_object_or_404(CartItem, id=item_id)
        cart_id = str(cart_item.cart.id)
        cart_item.delete()
        
        # Vérifier si le panier est vide après suppression
        cart = get_object_or_404(Cart, id=cart_id)
        is_cart_empty = cart.items.count() == 0
        
        # Préparer la réponse
        response_data = {
            'success': True,
            'message': 'L\'article a été retiré du panier.',
            'is_cart_empty': is_cart_empty,
            'item_id': item_id
        }
        
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            from django.template.loader import render_to_string
            from django.http import JsonResponse
            
            # Récupérer le panier mis à jour
            cart = get_object_or_404(Cart, id=cart_id)
            cart_items = cart.items.select_related('product')
            
            # Calculer les totaux
            cart_total = sum(item.total_price() for item in cart_items)
            
            # Mettre à jour les données de réponse
            response_data.update({
                'cart_total': f"{cart_total:.2f}",
                'item_count': cart_items.count(),
                'html': render_to_string('boutique/partials/cart_items.html', {
                    'cart': cart,
                    'cart_items': cart_items
                }) if not is_cart_empty else ''
            })
            
            return JsonResponse(response_data)
        
        messages.success(request, _("L'article a été retiré du panier."))
        return redirect('boutique:cart')
        
    except Exception as e:
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({
                'success': False,
                'message': str(e)
            }, status=400)
        messages.error(request, _("Une erreur est survenue lors de la suppression de l'article."))
        return redirect('boutique:cart')


class CheckoutView(LoginRequiredMixin, View):
    login_url = reverse_lazy('account_login')
    
    def get(self, request, *args, **kwargs):
        cart_id = request.session.get('cart_id')
        
        if not cart_id:
            messages.warning(request, _("Votre panier est vide."))
            return redirect('boutique:home')
        
        cart = get_object_or_404(Cart, id=cart_id)
        
        if cart.items.count() == 0:
            messages.warning(request, _("Votre panier est vide."))
            return redirect('boutique:home')
        
        # Pré-remplir le formulaire avec les informations de l'utilisateur connecté
        initial_data = {
            'first_name': request.user.first_name,
            'last_name': request.user.last_name,
            'email': request.user.email,
        }
        
        form = CheckoutForm(initial=initial_data)
        return render(request, 'boutique/checkout.html', {
            'cart': cart,
            'form': form,
            'stripe_public_key': settings.STRIPE_PUBLIC_KEY
        })
    
    def post(self, request, *args, **kwargs):
        cart_id = request.session.get('cart_id')
        
        if not cart_id:
            messages.warning(request, _("Votre panier est vide."))
            return redirect('boutique:home')
        
        cart = get_object_or_404(Cart, id=cart_id)
        
        if cart.items.count() == 0:
            messages.warning(request, _("Votre panier est vide."))
            return redirect('boutique:home')
        
        form = CheckoutForm(request.POST)
        
        if form.is_valid():
            # Créer la commande
            order = form.save(commit=False)
            order.user = request.user
            order.total_amount = cart.total_price
            order.save()
            
            # Ajouter les articles de la commande
            for item in cart.items.all():
                OrderItem.objects.create(
                    order=order,
                    product=item.product,
                    price=item.price,
                    quantity=item.quantity
                )
            
            # Créer la session de paiement Stripe
            try:
                checkout_session = stripe.checkout.Session.create(
                    payment_method_types=['card'],
                    line_items=[{
                        'price_data': {
                            'currency': 'eur',
                            'product_data': {
                                'name': f"Commande #{order.id}",
                            },
                            'unit_amount': int(order.total_amount * 100),  # Montant en centimes
                        },
                        'quantity': 1,
                    }],
                    mode='payment',
                    success_url=request.build_absolute_uri(
                        reverse('boutique:payment_success')
                    ) + f"?session_id={{CHECKOUT_SESSION_ID}}&order_id={order.id}",
                    cancel_url=request.build_absolute_uri(
                        reverse('boutique:payment_cancelled')
                    ),
                    metadata={
                        'order_id': str(order.id)
                    }
                )
                
                # Rediriger vers Stripe Checkout
                return redirect(checkout_session.url, code=303)
                
            except Exception as e:
                # En cas d'erreur avec Stripe, marquer la commande comme échouée
                order.status = 'annulee'
                order.save()
                messages.error(
                    request,
                    _("Une erreur est survenue lors du traitement de votre paiement. Veuillez réessayer.")
                )
                return redirect('boutique:checkout')
        
        return render(request, 'boutique/checkout.html', {
            'cart': cart,
            'form': form,
            'stripe_public_key': settings.STRIPE_PUBLIC_KEY
        })


class PaymentSuccessView(TemplateView):
    template_name = 'boutique/payment_success.html'
    
    def get(self, request, *args, **kwargs):
        session_id = request.GET.get('session_id')
        order_id = request.GET.get('order_id')
        
        if not session_id or not order_id:
            messages.error(request, _("Session de paiement invalide."))
            return redirect('boutique:home')
        
        try:
            # Récupérer la session Stripe
            session = stripe.checkout.Session.retrieve(session_id)
            
            # Vérifier que la commande existe
            order = get_object_or_404(Order, id=order_id)
            
            # Mettre à jour le statut de la commande
            if session.payment_status == 'paid':
                order.status = 'payee'
                order.paid = True
                order.stripe_payment_intent = session.payment_intent
                order.save()
                
                # Vider le panier
                if 'cart_id' in request.session:
                    del request.session['cart_id']
                
                # Envoyer un email de confirmation (à implémenter)
                # send_order_confirmation_email(order)
                
                messages.success(
                    request,
                    _("Votre commande a été passée avec succès. Un email de confirmation vous a été envoyé.")
                )
            
            return render(request, self.template_name, {'order': order})
            
        except Exception as e:
            messages.error(
                request,
                _("Une erreur est survenue lors de la vérification de votre paiement. "
                  "Veuillez nous contacter si vous avez des questions.")
            )
            return redirect('boutique:order_history')


class AdminDashboardView(LoginRequiredMixin, UserPassesTestMixin, TemplateView):
    template_name = 'boutique/admin/dashboard.html'
    login_url = reverse_lazy('account_login')
    
    def test_func(self):
        return self.request.user.is_superuser
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        from django.apps import apps
        
        # Récupérer les commandes récentes
        context['latest_orders'] = Order.objects.select_related('user').order_by('-created_at')[:5]
        
        # Récupérer les modèles à afficher dans le tableau de bord
        context['models'] = [
            {
                'name': 'Produits',
                'count': apps.get_model('boutique', 'Product').objects.count(),
                'url_name': 'admin:boutique_product_changelist',
                'add_url': reverse('admin:boutique_product_add'),
                'icon': 'box-seam',
                'app_label': 'boutique',
                'model_name': 'product'
            },
            {
                'name': 'Catégories',
                'count': apps.get_model('boutique', 'Category').objects.count(),
                'url_name': 'admin:boutique_category_changelist',
                'add_url': reverse('admin:boutique_category_add'),
                'icon': 'tags',
                'app_label': 'boutique',
                'model_name': 'category'
            },
            {
                'name': 'Commandes',
                'count': apps.get_model('boutique', 'Order').objects.count(),
                'url_name': 'admin:boutique_order_changelist',
                'add_url': reverse('admin:boutique_order_add'),
                'icon': 'cart-check',
                'app_label': 'boutique',
                'model_name': 'order'
            },
            {
                'name': 'Utilisateurs',
                'count': apps.get_model('auth', 'User').objects.count(),
                'url_name': 'admin:auth_user_changelist',
                'add_url': reverse('admin:auth_user_add'),
                'icon': 'people',
                'app_label': 'auth',
                'model_name': 'user'
            }
        ]
        return context


class PaymentCancelledView(TemplateView):
    template_name = 'boutique/payment_cancelled.html'


class OrderHistoryView(LoginRequiredMixin, ListView):
    template_name = 'boutique/order_history.html'
    context_object_name = 'orders'
    paginate_by = 10
    
    def get_queryset(self):
        return Order.objects.filter(user=self.request.user).order_by('-created_at')


class OrderDetailView(LoginRequiredMixin, DetailView):
    template_name = 'boutique/order_detail.html'
    context_object_name = 'order'
    
    def get_queryset(self):
        return Order.objects.filter(user=self.request.user)


@login_required
def add_review(request, product_id):
    product = get_object_or_404(Product, id=product_id)
    
    if request.method == 'POST':
        form = ReviewForm(request.POST)
        
        if form.is_valid():
            # Vérifier si l'utilisateur a déjà laissé un avis pour ce produit
            existing_review = Review.objects.filter(
                product=product,
                user=request.user
            ).exists()
            
            if existing_review:
                messages.error(
                    request,
                    _("Vous avez déjà laissé un avis pour ce produit.")
                )
            else:
                review = form.save(commit=False)
                review.product = product
                review.user = request.user
                review.save()
                
                messages.success(
                    request,
                    _("Merci pour votre avis ! Il sera publié après modération.")
                )
            
            return redirect('boutique:product_detail', pk=product.id, slug=product.slug)
    else:
        form = ReviewForm()
    
    return render(request, 'boutique/add_review.html', {
        'form': form,
        'product': product
    })


@csrf_exempt
def stripe_webhook(request):
    payload = request.body
    sig_header = request.META.get('HTTP_STRIPE_SIGNATURE')
    event = None
    
    try:
        event = stripe.Webhook.construct_event(
            payload, sig_header, settings.STRIPE_WEBHOOK_SECRET
        )
    except ValueError as e:
        # Données invalides
        return JsonResponse({'status': 'error', 'error': str(e)}, status=400)
    except stripe.error.SignatureVerificationError as e:
        # Signature invalide
        return JsonResponse({'status': 'error', 'error': str(e)}, status=400)
    
    # Gérer les événements de paiement réussis
    if event['type'] == 'checkout.session.completed':
        session = event['data']['object']
        
        # Récupérer l'ID de la commande depuis les métadonnées
        order_id = session.get('metadata', {}).get('order_id')
        
        if order_id:
            try:
                order = Order.objects.get(id=order_id)
                
                if session.payment_status == 'paid':
                    order.status = 'payee'
                    order.paid = True
                    order.stripe_payment_intent = session.payment_intent
                    order.save()
                    
                    # Envoyer un email de confirmation (à implémenter)
                    # send_order_confirmation_email(order)
            except Order.DoesNotExist:
                pass
    
    return JsonResponse({'status': 'success'})
