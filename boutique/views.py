from django.shortcuts import render, get_object_or_404, redirect, reverse
from django.views.generic import ListView, DetailView, View, TemplateView, CreateView
from django.views.decorators.http import require_POST, require_http_methods
from django.contrib import messages
from django.utils.translation import gettext_lazy as _
from django.http import JsonResponse, HttpResponse, HttpResponseRedirect
from django.db.models import Q, Count, Avg
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.contrib.auth.decorators import login_required, user_passes_test
from django.urls import reverse_lazy
from django.views.generic.edit import CreateView, UpdateView, DeleteView
from django.contrib.auth import get_user_model
from django.db.models import Sum
from django.conf import settings
from django.views.decorators.csrf import csrf_exempt
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.utils import timezone
from django.utils.text import slugify
from decimal import Decimal
import os
import json
import stripe

from .models import Category, Product, Cart, CartItem, Order, OrderItem, Review, ProductImage, ProductSpecification
from .forms import AddToCartForm, PaymentForm, CheckoutForm, ProductForm, CategoryForm

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
        context['all_categories'] = Category.objects.annotate(
            num_products=Count('products')
        ).filter(num_products__gt=0).order_by('name')
        context['featured_categories'] = context['all_categories'][:6]  # Garder les catégories en vedette pour d'autres parties du site
        return context


class ProductListView(ListView):
    model = Product
    template_name = 'boutique/product_list.html'
    context_object_name = 'products'
    paginate_by = 12

    def get_queryset(self):
        # Par défaut, trier par date de création (du plus récent au plus ancien)
        queryset = Product.objects.filter(available=True).order_by('-created_at')
        
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
            
        return queryset
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['categories'] = Category.objects.all()
        context['current_category'] = self.kwargs.get('category_slug')
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
            cart_items = cart.items.all().select_related('product')
        else:
            cart = Cart.objects.create()
            request.session['cart_id'] = str(cart.id)
            cart_items = []
            
        # Calculer les totaux
        cart_total = sum(item.total_price for item in cart_items)
        cart_total_quantity = sum(item.quantity for item in cart_items)
            
        return render(request, 'boutique/cart.html', {
            'cart': cart,
            'cart_items': cart_items,
            'cart_total': cart_total,
            'cart_total_quantity': cart_total_quantity
        })


@require_POST
def add_to_cart(request, product_id):
    # Vérifier si l'utilisateur est connecté
    if not request.user.is_authenticated:
        messages.info(request, _("Veuillez vous connecter pour ajouter des articles à votre panier."))
        return redirect('{}?next={}'.format(
            reverse('account_login'),
            request.path
        ))
    
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
        
        # Rediriger vers la page du panier après l'ajout
        return redirect('boutique:cart')
    
    # En cas d'erreur de formulaire, rediriger vers la page du produit
    messages.error(request, _("Une erreur s'est produite lors de l'ajout au panier."))
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
                
                # Calculer les totaux mis à jour
                cart = cart_item.cart
                cart_items = cart.items.all()
                cart_total = sum(item.total_price for item in cart_items)
                cart_total_quantity = sum(item.quantity for item in cart_items)
                
                response_data = {
                    'success': True,
                    'quantity': cart_item.quantity,
                    'item_total': str(cart_item.total_price),
                    'cart_total': str(cart_total),
                    'cart_total_quantity': cart_total_quantity,
                    'message': _("La quantité a été mise à jour.")
                }
                
                return JsonResponse(response_data)
                
            else:
                # Si la quantité est 0, supprimer l'article
                cart = cart_item.cart
                cart_item.delete()
                
                # Vérifier si le panier est vide
                cart_items = cart.items.all()
                if not cart_items.exists():
                    response_data = {
                        'success': True,
                        'quantity': 0,
                        'cart_empty': True,
                        'message': _("L'article a été retiré du panier.")
                    }
                else:
                    # Calculer les totaux mis à jour
                    cart_total = sum(item.total_price for item in cart_items)
                    cart_total_quantity = sum(item.quantity for item in cart_items)
                    
                    response_data = {
                        'success': True,
                        'quantity': 0,
                        'cart_total': str(cart_total),
                        'cart_total_quantity': cart_total_quantity,
                        'message': _("L'article a été retiré du panier.")
                    }
                
                return JsonResponse(response_data)
                
        except (ValueError, TypeError):
            return JsonResponse({
                'success': False,
                'message': _("Quantité invalide.")
            }, status=400)
    
    return JsonResponse({
        'success': False,
        'message': _("Requête invalide.")
    }, status=400)


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
        
    except CartItem.DoesNotExist:
        error_msg = _("L'article demandé n'existe pas ou a déjà été supprimé.")
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({
                'success': False,
                'message': error_msg
            }, status=404)
        messages.error(request, error_msg)
        return redirect('boutique:cart')
    except Exception as e:
        import traceback
        error_msg = _("Une erreur est survenue lors de la suppression de l'article: {}").format(str(e))
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({
                'success': False,
                'message': error_msg,
                'error_details': str(e),
                'traceback': traceback.format_exc()
            }, status=500)
        messages.error(request, error_msg)
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
                            'currency': 'bif',
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


class CheckoutView(LoginRequiredMixin, View):
    """Vue pour le processus de paiement"""
    login_url = reverse_lazy('account_login')
    
    def get(self, request, *args, **kwargs):
        cart_id = request.session.get('cart_id')
        if not cart_id:
            messages.warning(request, _("Votre panier est vide."))
            return redirect('boutique:home')
            
        cart = get_object_or_404(Cart, id=cart_id)
        cart_items = cart.items.all()
        
        if not cart_items.exists():
            messages.warning(request, _("Votre panier est vide."))
            return redirect('boutique:home')
        
        # Vérifier le stock des produits
        for item in cart_items:
            if item.quantity > item.product.stock:
                messages.error(
                    request, 
                    _("Désolé, la quantité demandée pour %(product)s n'est plus disponible.") % 
                    {'product': item.product.name}
                )
                return redirect('boutique:cart')
        
        # Initialiser le formulaire avec les données de l'utilisateur connecté
        initial_data = {}
        if request.user.is_authenticated:
            initial_data = {
                'first_name': request.user.first_name,
                'last_name': request.user.last_name,
                'email': request.user.email,
            }
            
            # Ajouter l'adresse de l'utilisateur si elle existe
            try:
                profile = request.user.profile
                if profile.phone:
                    initial_data['phone'] = profile.phone
                if profile.address:
                    initial_data['address'] = profile.address
                if profile.postal_code:
                    initial_data['postal_code'] = profile.postal_code
                if profile.city:
                    initial_data['city'] = profile.city
                if profile.country:
                    initial_data['country'] = profile.country
            except AttributeError:
                pass
        
        # Initialiser les formulaires
        checkout_form = CheckoutForm(initial=initial_data)
        payment_form = PaymentForm()
        
        context = {
            'cart': cart,
            'cart_items': cart_items,
            'form': checkout_form,  # Changé de 'checkout_form' à 'form' pour correspondre au template
            'payment_form': payment_form,
        }
        
        return render(request, 'boutique/checkout.html', context)
    
    def post(self, request, *args, **kwargs):
        cart_id = request.session.get('cart_id')
        if not cart_id:
            messages.warning(request, _("Votre panier est vide."))
            return redirect('boutique:home')
            
        cart = get_object_or_404(Cart, id=cart_id)
        
        # Vérifier si le panier n'est pas vide
        cart_items = cart.items.all()
        if not cart_items.exists():
            messages.warning(request, _("Votre panier est vide."))
            return redirect('boutique:cart')
        
        # Vérifier le stock des produits
        for item in cart_items:
            if item.quantity > item.product.stock:
                messages.error(
                    request, 
                    _("Désolé, la quantité demandée pour %(product)s n'est plus disponible.") % 
                    {'product': item.product.name}
                )
                return redirect('boutique:cart')
        
        checkout_form = CheckoutForm(request.POST or None)
        payment_form = PaymentForm(request.POST or None)
        
        if checkout_form.is_valid() and payment_form.is_valid():
            try:
                # Créer la commande
                order = checkout_form.save(commit=False)
                order.user = request.user
                order.total_amount = cart.get_total()
                order.save()
                
                # Ajouter les articles de la commande
                for item in cart_items:
                    OrderItem.objects.create(
                        order=order,
                        product=item.product,
                        price=item.product.price,
                        quantity=item.quantity
                    )
                    
                    # Mettre à jour le stock
                    item.product.stock -= item.quantity
                    item.product.save()
                
                # Vider le panier
                cart.items.all().delete()
                
                # Créer un paiement Stripe
                stripe.api_key = settings.STRIPE_SECRET_KEY
                intent = stripe.PaymentIntent.create(
                    amount=int(cart.get_total()),  # Montant en FBu (pas de centimes pour le BIF)
                    currency='bif',
                    metadata={
                        'order_id': order.id,
                        'user_id': request.user.id
                    }
                )
                
                # Mettre à jour la commande avec l'ID de l'intention de paiement
                order.stripe_payment_intent = intent.id
                order.save()
                
                # Rediriger vers la page de paiement
                return redirect('boutique:payment', order_id=order.id)
                
            except Exception as e:
                messages.error(
                    request, 
                    _("Une erreur est survenue lors de la création de votre commande. Veuillez réessayer.")
                )
                logger.error(f"Erreur lors de la création de la commande: {str(e)}")
                return redirect('boutique:checkout')
        
        # Si le formulaire n'est pas valide, réafficher le formulaire avec les erreurs
        context = {
            'cart': cart,
            'cart_items': cart.items.all(),
            'form': checkout_form,  # Changé de 'checkout_form' à 'form' pour correspondre au template
            'payment_form': payment_form,
        }
        return render(request, 'boutique/checkout.html', context)


class PaymentView(LoginRequiredMixin, View):
    """Vue pour le traitement du paiement"""
    login_url = reverse_lazy('account_login')
    
    def get(self, request, order_id, *args, **kwargs):
        order = get_object_or_404(Order, id=order_id, user=request.user)
        
        # Vérifier que la commande n'est pas déjà payée
        if order.paid:
            messages.warning(request, _("Cette commande a déjà été payée."))
            return redirect('boutique:order_detail', order_id=order.id)
        
        # Initialiser le formulaire de paiement
        payment_form = PaymentForm()
        
        context = {
            'order': order,
            'payment_form': payment_form,
            'stripe_public_key': settings.STRIPE_PUBLIC_KEY,
        }
        
        return render(request, 'boutique/payment.html', context)
    
    def post(self, request, order_id, *args, **kwargs):
        order = get_object_or_404(Order, id=order_id, user=request.user)
        payment_form = PaymentForm(request.POST)
        
        if payment_form.is_valid():
            try:
                stripe.api_key = settings.STRIPE_SECRET_KEY
                
                # Créer un token de carte
                token = stripe.Token.create(
                    card={
                        'number': payment_form.cleaned_data['card_number'],
                        'exp_month': payment_form.cleaned_data['card_exp_month'],
                        'exp_year': payment_form.cleaned_data['card_exp_year'],
                        'cvc': payment_form.cleaned_data['card_cvv'],
                    },
                )
                
                # Créer un client Stripe
                customer = stripe.Customer.create(
                    email=order.email,
                    source=token.id
                )
                
                # Enregistrer le client pour les paiements futurs si demandé
                if payment_form.cleaned_data['save_card'] and request.user.customer_id:
                    request.user.customer_id = customer.id
                    request.user.save()
                
                # Payer la commande
                charge = stripe.Charge.create(
                    customer=customer.id,
                    amount=int(order.total),  # Montant en FBu (pas de centimes pour le BIF)
                    currency='bif',
                    description=f'Paiement de la commande #{order.id}',
                    metadata={'order_id': order.id}
                )
                
                # Mettre à jour la commande
                order.paid = True
                order.payment_id = charge.id
                order.save()
                
                # Vider le panier
                cart_id = request.session.get('cart_id')
                if cart_id:
                    try:
                        cart = Cart.objects.get(id=cart_id)
                        cart.delete()
                        del request.session['cart_id']
                    except Cart.DoesNotExist:
                        pass
                
                # Rediriger vers la page de confirmation
                messages.success(request, _("Votre paiement a été traité avec succès !"))
                return redirect('boutique:payment_success', order_id=order.id)
                
            except stripe.error.CardError as e:
                body = e.json_body
                err = body.get('error', {})
                messages.error(request, f"Erreur de carte : {err.get('message')}")
            except stripe.error.RateLimitError:
                messages.error(request, _("Trop de requêtes. Veuillez réessayer plus tard."))
            except stripe.error.InvalidRequestError as e:
                messages.error(request, _("Requête invalide. Veuillez réessayer."))
            except stripe.error.AuthenticationError:
                messages.error(request, _("Erreur d'authentification avec le processeur de paiement."))
            except stripe.error.APIConnectionError:
                messages.error(request, _("Erreur de connexion au réseau. Veuillez vérifier votre connexion."))
            except stripe.error.StripeError as e:
                messages.error(request, _("Une erreur est survenue lors du traitement de votre paiement. Veuillez réessayer."))
            except Exception as e:
                messages.error(request, _("Une erreur inattendue est survenue. Veuillez réessayer."))
                logger.error(f"Erreur lors du paiement: {str(e)}")
        
        # Si le formulaire n'est pas valide ou s'il y a une erreur, réafficher le formulaire
        context = {
            'order': order,
            'payment_form': payment_form,
            'stripe_public_key': settings.STRIPE_PUBLIC_KEY,
        }
        return render(request, 'boutique/payment.html', context)


class PaymentSuccessView(LoginRequiredMixin, View):
    """Vue pour la page de confirmation de paiement"""
    login_url = reverse_lazy('account_login')
    
    def get(self, request, order_id, *args, **kwargs):
        order = get_object_or_404(Order, id=order_id, user=request.user, paid=True)
        
        # Envoyer un email de confirmation (à implémenter)
        # send_order_confirmation_email(order)
        
        context = {
            'order': order,
        }
        return render(request, 'boutique/payment_success.html', context)


class OrderHistoryView(LoginRequiredMixin, ListView):
    """Vue pour l'historique des commandes"""
    model = Order
    template_name = 'boutique/order_history.html'
    context_object_name = 'orders'
    paginate_by = 10
    
    def get_queryset(self):
        return Order.objects.filter(user=self.request.user).order_by('-created_at')


class OrderDetailView(LoginRequiredMixin, DetailView):
    """Vue pour les détails d'une commande"""
    model = Order
    template_name = 'boutique/order_detail.html'
    context_object_name = 'order'
    
    def get_queryset(self):
        return Order.objects.filter(user=self.request.user)


@require_http_methods(["POST"])
def clear_cart(request):
    cart_id = request.session.get('cart_id')
    if cart_id:
        try:
            cart = Cart.objects.get(id=cart_id)
            cart.items.all().delete()  # Supprimer tous les articles du panier
            cart.delete()  # Supprimer le panier
            del request.session['cart_id']  # Nettoyer la session
            
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({
                    'success': True,
                    'message': _("Le panier a été vidé avec succès."),
                    'cart_empty': True,
                })
            
            messages.success(request, _("Le panier a été vidé avec succès."))
            return redirect('boutique:cart')
            
        except Cart.DoesNotExist:
            pass
    
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return JsonResponse({
            'success': False,
            'message': _("Le panier est déjà vide."),
            'cart_empty': True,
        }, status=400)
    
    messages.warning(request, _("Le panier est déjà vide."))
    return redirect('boutique:cart')


def is_admin(user):
    """Vérifie si l'utilisateur est un administrateur."""
    return user.is_authenticated and (user.is_superuser or user.is_staff)


class ProductAddView(LoginRequiredMixin, UserPassesTestMixin, CreateView):
    """
    Vue personnalisée pour l'ajout de produits avec une interface utilisateur moderne.
    """
    model = Product
    form_class = ProductForm
    template_name = 'boutique/add_product.html'
    success_url = reverse_lazy('boutique:admin_product_list')
    login_url = reverse_lazy('account_login')
    
    def test_func(self):
        return is_admin(self.request.user)
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['categories'] = Category.objects.all()
        context['CURRENCY'] = '€'  # Vous pouvez remplacer par votre devise
        return context
    
    def form_valid(self, form):
        # Sauvegarder d'abord le produit sans le commit pour pouvoir ajouter les images
        self.object = form.save(commit=False)
        self.object.added_by = self.request.user
        self.object.save()
        
        # Gérer les images téléchargées
        images = self.request.FILES.getlist('images')
        for image in images:
            ProductImage.objects.create(product=self.object, image=image)
        
        # Gérer les spécifications techniques
        spec_names = self.request.POST.getlist('spec_name[]')
        spec_values = self.request.POST.getlist('spec_value[]')
        
        for name, value in zip(spec_names, spec_values):
            if name.strip() and value.strip():
                ProductSpecification.objects.create(
                    product=self.object,
                    name=name,
                    value=value
                )
        
        # Sauvegarder les relations many-to-many (comme les catégories)
        form.save_m2m()
        
        messages.success(self.request, _('Le produit a été ajouté avec succès.'))
        
        # Rediriger en fonction du bouton cliqué
        if 'save_and_add_another' in self.request.POST:
            return redirect('boutique:add_product')
        
        return super().form_valid(form)
    
    def form_invalid(self, form):
        messages.error(self.request, _('Veuillez corriger les erreurs ci-dessous.'))
        return super().form_invalid(form)
    
    def handle_no_permission(self):
        if not self.request.user.is_authenticated:
            messages.warning(self.request, _('Veuvez-vous vous connecter pour accéder à cette page ?'))
            return super().handle_no_permission()
        messages.error(self.request, _("Vous n'avez pas la permission d'accéder à cette page."))
        return redirect('boutique:home')


@login_required
def delete_product_image(request, pk):
    """
    Vue pour supprimer une image de produit via AJAX.
    """
    if request.method == 'POST' and request.is_ajax():
        try:
            image = get_object_or_404(ProductImage, pk=pk)
            # Vérifier que l'utilisateur a les droits pour supprimer l'image
            if request.user.is_staff:
                image.delete()
                return JsonResponse({'success': True})
            return JsonResponse({'success': False, 'error': 'Permission denied'}, status=403)
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)}, status=500)
    return JsonResponse({'success': False, 'error': 'Invalid request'}, status=400)


class CategoryAddView(LoginRequiredMixin, UserPassesTestMixin, CreateView):
    """Vue pour l'ajout de nouvelles catégories."""
    model = Category
    form_class = CategoryForm
    template_name = 'boutique/category_form.html'
    success_url = reverse_lazy('boutique:admin_dashboard')
    login_url = reverse_lazy('account_login')

    def test_func(self):
        return self.request.user.is_staff or self.request.user.is_superuser

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = _('Ajouter une catégorie')
        context['form_title'] = _('Nouvelle catégorie')
        context['submit_text'] = _('Ajouter la catégorie')
        return context

    def form_valid(self, form):
        if not (self.request.user.is_staff or self.request.user.is_superuser):
            messages.error(self.request, _("Vous n'avez pas la permission d'ajouter des catégories."))
            return self.handle_no_permission()

        # Générer automatiquement le slug à partir du nom
        if not form.instance.slug:
            form.instance.slug = slugify(form.cleaned_data['name'], allow_unicode=True)

        messages.success(self.request, _('La catégorie a été ajoutée avec succès.'))
        return super().form_valid(form)

    def form_invalid(self, form):
        messages.error(self.request, _('Veuillez corriger les erreurs ci-dessous.'))
        return super().form_invalid(form)

    def handle_no_permission(self):
        messages.error(self.request, _("Vous n'êtes pas autorisé à accéder à cette page."))
        return redirect(reverse_lazy('boutique:home'))


class AddCategoryView(LoginRequiredMixin, UserPassesTestMixin, View):
    """Vue personnalisée pour l'ajout de catégories"""
    template_name = 'boutique/admin/add_category.html'
    login_url = reverse_lazy('account_login')
    
    def test_func(self):
        return self.request.user.is_staff or self.request.user.is_superuser
    
    def get(self, request, *args, **kwargs):
        form = CategoryForm()
        return render(request, self.template_name, {'form': form})
    
    def post(self, request, *args, **kwargs):
        form = CategoryForm(request.POST, request.FILES)
        if form.is_valid():
            category = form.save(commit=False)
            # Générer automatiquement le slug si vide
            if not category.slug:
                category.slug = slugify(category.name, allow_unicode=True)
            category.save()
            
            messages.success(request, _('La catégorie a été ajoutée avec succès.'))
            
            if 'save_and_add_another' in request.POST:
                return redirect('boutique:add_category')
                
            return redirect('boutique:admin_category_list')
            
        return render(request, self.template_name, {'form': form})
    
    def handle_no_permission(self):
        if not self.request.user.is_authenticated:
            messages.warning(self.request, _('Veuvez-vous vous connecter pour accéder à cette page ?'))
            return super().handle_no_permission()
        messages.error(self.request, _("Vous n'avez pas la permission d'accéder à cette page."))
        return redirect('boutique:home')


class LegalNoticeView(TemplateView):
    """Vue pour afficher les mentions légales"""
    template_name = 'boutique/legal_notice.html'
