from django.db import models
from django.conf import settings
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from django.core.validators import MinValueValidator, MaxValueValidator
from django.core.exceptions import ValidationError
from django.utils.text import slugify
from decimal import Decimal
import uuid
from django.core.validators import MinLengthValidator

# Create your models here.

class Category(models.Model):
    """Catégorie de produits"""
    name = models.CharField(_('nom'), max_length=200, db_index=True)
    slug = models.SlugField(_('slug'), max_length=200, unique=True)
    image = models.ImageField(_('image'), upload_to='categories/%Y/%m/%d', blank=True)
    description = models.TextField(_('description'), blank=True)
    created_at = models.DateTimeField(_('créé le'), auto_now_add=True)
    updated_at = models.DateTimeField(_('mis à jour le'), auto_now=True)

    class Meta:
        ordering = ('name',)
        verbose_name = _('catégorie')
        verbose_name_plural = _('catégories')

    def __str__(self):
        return self.name

    def get_absolute_url(self):
        return f'/boutique/category/{self.slug}/'


class ProductImage(models.Model):
    """Image supplémentaire pour un produit"""
    product = models.ForeignKey(
        'Product',
        related_name='additional_images',
        on_delete=models.CASCADE,
        verbose_name=_('produit')
    )
    image = models.ImageField(
        _('image'),
        upload_to='products/additional/%Y/%m/%d',
        blank=True
    )
    created_at = models.DateTimeField(_('créé le'), auto_now_add=True)
    updated_at = models.DateTimeField(_('mis à jour le'), auto_now=True)

    class Meta:
        verbose_name = _('image supplémentaire')
        verbose_name_plural = _('images supplémentaires')

    def __str__(self):
        return f"Image de {self.product.name}"


class Product(models.Model):
    """Produit de la boutique"""
    category = models.ForeignKey(
        Category,
        related_name='products',
        on_delete=models.CASCADE,
        verbose_name=_('catégorie')
    )
    name = models.CharField(_('nom'), max_length=200, db_index=True)
    slug = models.SlugField(_('slug'), max_length=200, db_index=True)
    image = models.ImageField(
        _('image principale'),
        upload_to='products/%Y/%m/%d',
        blank=True,
        help_text=_('Image principale du produit')
    )
    description = models.TextField(_('description'), blank=True)
    price = models.DecimalField(
        _('prix'),
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(0.01)]
    )
    available = models.BooleanField(_('disponible'), default=True)
    stock = models.PositiveIntegerField(_('stock'), default=0)
    created_at = models.DateTimeField(_('créé le'), auto_now_add=True)
    updated_at = models.DateTimeField(_('mis à jour le'), auto_now=True)

    class Meta:
        ordering = ('name',)
        indexes = [
            models.Index(fields=['id', 'slug']),
        ]
        verbose_name = _('produit')
        verbose_name_plural = _('produits')

    def __str__(self):
        return self.name

    def get_absolute_url(self):
        return f'/boutique/produits/{self.id}/{self.slug}/'
        
    def get_price_display(self):
        """Retourne le prix formaté avec le symbole Fbu"""
        if self.price == int(self.price):
            return f"{int(self.price):,} Fbu".replace(",", " ")
        return f"{self.price:,.2f} Fbu".replace(",", " ").replace(".", ",")

    @property
    def in_stock(self):
        return self.stock > 0
        
    def get_rating_count(self):
        """Retourne un dictionnaire avec le nombre d'avis par note"""
        from collections import defaultdict
        
        # Initialiser le dictionnaire avec des zéros pour toutes les notes possibles
        rating_count = {str(i): {'count': 0, 'percentage': 0} for i in range(1, 6)}
        
        # Compter les avis par note
        reviews = self.reviews.all()
        total_reviews = reviews.count()
        
        for review in reviews:
            rating = str(review.rating)
            rating_count[rating]['count'] += 1
        
        # Calculer les pourcentages
        for rating, data in rating_count.items():
            if total_reviews > 0:
                data['percentage'] = (data['count'] / total_reviews) * 100
            else:
                data['percentage'] = 0
        
        return rating_count


class Cart(models.Model):
    """Panier d'achat"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    created_at = models.DateTimeField(_('créé le'), auto_now_add=True)
    updated_at = models.DateTimeField(_('mis à jour le'), auto_now=True)

    class Meta:
        verbose_name = _('panier')
        verbose_name_plural = _('paniers')
        ordering = ('-created_at',)

    def __str__(self):
        return f'Panier {self.id}'

    @property
    def total_price(self):
        return sum(item.total_price for item in self.items.all())

    @property
    def total_quantity(self):
        return sum(item.quantity for item in self.items.all())
        
    @property
    def get_subtotal(self):
        return sum(item.total_price for item in self.items.all())
        
    @property
    def discount_amount(self):
        # À implémenter si vous avez un système de réduction
        return 0
        
    @property
    def discount_code(self):
        # À implémenter si vous avez un système de code de réduction
        return ""
        
    @property
    def tax_rate(self):
        # Taux de TVA en pourcentage
        return 20  # 20% de TVA par défaut
        
    @property
    def tax_amount(self):
        # Montant de la TVA
        return round(self.get_subtotal * (self.tax_rate / 100), 2)
        
    @property
    def get_shipping_cost(self):
        # Frais de livraison gratuits pour les commandes de plus de 100€, sinon 5.99€
        if self.get_subtotal > 100:
            return 0
        return 5.99
        
    @property
    def get_total(self):
        # Total TTC (sous-total + frais de livraison)
        return self.get_subtotal + self.get_shipping_cost


class CartItem(models.Model):
    """Article dans le panier"""
    cart = models.ForeignKey(
        Cart,
        related_name='items',
        on_delete=models.CASCADE,
        verbose_name=_('panier')
    )
    product = models.ForeignKey(
        Product,
        related_name='cart_items',
        on_delete=models.CASCADE,
        verbose_name=_('produit')
    )
    quantity = models.PositiveIntegerField(_('quantité'), default=1)
    price = models.DecimalField(
        _('prix unitaire'),
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(0.01)]
    )
    created_at = models.DateTimeField(_('créé le'), auto_now_add=True)
    updated_at = models.DateTimeField(_('mis à jour le'), auto_now=True)

    class Meta:
        verbose_name = _('article du panier')
        verbose_name_plural = _('articles du panier')
        unique_together = (('cart', 'product'),)

    def __str__(self):
        return f'{self.quantity} x {self.product.name}'

    @property
    def total_price(self):
        return self.quantity * self.price

    def clean(self):
        if self.quantity > self.product.stock:
            raise ValidationError({
                'quantity': _("La quantité demandée n'est pas disponible en stock.")
            })


class Order(models.Model):
    """Commande client"""
    STATUS_CHOICES = (
        ('en_attente', _('En attente de paiement')),
        ('payee', _('Payée')),
        ('en_preparation', _('En préparation')),
        ('prete', _('Prête à être récupérée')),  # Pour les commandes en magasin
        ('expediee', _('Expédiée')),  # Pour les livraisons
        ('en_livraison', _('En cours de livraison')),  # Pour le suivi des livraisons
        ('livree', _('Livrée')),  # Pour les livraisons
        ('recuperee', _('Récupérée')),  # Pour les retraits en magasin
        ('annulee', _('Annulée')),
    )
    
    DELIVERY_METHOD_CHOICES = (
        ('delivery', _('Livraison à domicile')),
        ('pickup', _('Retrait en magasin')),
    )

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='orders',
        verbose_name=_('utilisateur')
    )
    first_name = models.CharField(_('prénom'), max_length=50)
    last_name = models.CharField(_('nom'), max_length=50)
    email = models.EmailField(_('email'))
    address = models.CharField(_('adresse'), max_length=250)
    postal_code = models.CharField(_('code postal'), max_length=20)
    city = models.CharField(_('ville'), max_length=100)
    country = models.CharField(_('pays'), max_length=100)
    phone = models.CharField(_('téléphone'), max_length=20, blank=True)
    status = models.CharField(
        _('statut'),
        max_length=20,
        choices=STATUS_CHOICES,
        default='en_attente'
    )
    delivery_method = models.CharField(
        _('mode de livraison'),
        max_length=20,
        choices=DELIVERY_METHOD_CHOICES,
        default='delivery',
        help_text=_('Choisissez si le client souhaite se faire livrer ou récupérer sa commande en magasin.')
    )
    delivery_date = models.DateField(
        _('date de livraison souhaitée'),
        null=True,
        blank=True,
        help_text=_('Date à laquelle le client souhaite être livré ou récupérer sa commande.')
    )
    delivery_time = models.TimeField(
        _('heure de livraison souhaitée'),
        null=True,
        blank=True,
        help_text=_('Heure à laquelle le client souhaite être livré ou récupérer sa commande.')
    )
    delivery_address = models.TextField(
        _('adresse de livraison'),
        blank=True,
        help_text=_('Adresse complète de livraison (si différente de l\'adresse de facturation).')
    )
    pickup_location = models.CharField(
        _('point de retrait'),
        max_length=255,
        blank=True,
        help_text=_('Lieu où le client souhaite récupérer sa commande.')
    )
    tracking_number = models.CharField(
        _('numéro de suivi'),
        max_length=100,
        blank=True,
        help_text=_('Numéro de suivi de la commande (pour les livraisons).')
    )
    paid = models.BooleanField(_('payée'), default=False)
    notes = models.TextField(
        _('notes'),
        blank=True,
        help_text=_('Notes supplémentaires concernant la commande.')
    )
    stripe_payment_intent = models.CharField(
        _('ID de paiement Stripe'),
        max_length=100,
        blank=True
    )
    total_amount = models.DecimalField(
        _('montant total'),
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(0.01)]
    )
    created_at = models.DateTimeField(_('créée le'), default=timezone.now)
    updated_at = models.DateTimeField(_('mise à jour le'), auto_now=True)

    class Meta:
        ordering = ('-created_at',)
        verbose_name = _('commande')
        verbose_name_plural = _('commandes')

    def __str__(self):
        return f'Commande {self.id}'

    def get_total_cost(self):
        return sum(item.get_cost() for item in self.items.all())


class OrderItem(models.Model):
    """Article dans une commande"""
    order = models.ForeignKey(
        Order,
        related_name='items',
        on_delete=models.CASCADE,
        verbose_name=_('commande')
    )
    product = models.ForeignKey(
        Product,
        related_name='order_items',
        on_delete=models.SET_NULL,
        null=True,
        verbose_name=_('produit')
    )
    price = models.DecimalField(
        _('prix unitaire'),
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(0.01)]
    )
    quantity = models.PositiveIntegerField(_('quantité'), default=1)

    class Meta:
        verbose_name = _('article de commande')
        verbose_name_plural = _('articles de commande')

    def __str__(self):
        return f'{self.quantity} x {self.product.name}'

    def get_cost(self):
        return self.price * self.quantity


class Review(models.Model):
    """Avis client sur un produit"""
    RATING_CHOICES = (
        (1, '1 étoile'),
        (2, '2 étoiles'),
        (3, '3 étoiles'),
        (4, '4 étoiles'),
        (5, '5 étoiles'),
    )

    product = models.ForeignKey(
        Product,
        related_name='reviews',
        on_delete=models.CASCADE,
        verbose_name=_('produit')
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='reviews',
        verbose_name=_('utilisateur')
    )
    rating = models.PositiveSmallIntegerField(
        _('note'),
        choices=RATING_CHOICES,
        validators=[MinValueValidator(1), MaxValueValidator(5)]
    )
    comment = models.TextField(_('commentaire'), blank=True)
    approved = models.BooleanField(_('approuvé'), default=True)
    created_at = models.DateTimeField(_('créé le'), auto_now_add=True)
    updated_at = models.DateTimeField(_('mis à jour le'), auto_now=True)

    class Meta:
        ordering = ('-created_at',)
        verbose_name = _('avis')
        verbose_name_plural = _('avis')
        unique_together = (('product', 'user'),)

    def __str__(self):
        return f'Avis de {self.user} sur {self.product}'


class ProductSpecification(models.Model):
    """Spécification technique d'un produit"""
    product = models.ForeignKey(
        'Product',
        related_name='specifications',
        on_delete=models.CASCADE,
        verbose_name=_('produit')
    )
    name = models.CharField(
        _('nom de la spécification'),
        max_length=100,
        validators=[MinLengthValidator(2)]
    )
    value = models.CharField(
        _('valeur'),
        max_length=255,
        validators=[MinLengthValidator(1)]
    )
    created_at = models.DateTimeField(_('créé le'), auto_now_add=True)
    updated_at = models.DateTimeField(_('mis à jour le'), auto_now=True)

    class Meta:
        verbose_name = _('spécification technique')
        verbose_name_plural = _('spécifications techniques')
        ordering = ['name']
        unique_together = ['product', 'name']

    def __str__(self):
        return f"{self.name}: {self.value}"

    def clean(self):
        # Vérifier que le nom et la valeur ne sont pas vides
        if not self.name.strip():
            raise ValidationError({
                'name': _('Le nom de la spécification ne peut pas être vide.')
            })
        if not self.value.strip():
            raise ValidationError({
                'value': _('La valeur de la spécification ne peut pas être vide.')
            })


# Signal pour mettre à jour le stock après une commande
def update_stock(sender, instance, created, **kwargs):
    if created and instance.product:
        instance.product.stock -= instance.quantity
        instance.product.save()

models.signals.post_save.connect(update_stock, sender=OrderItem)
