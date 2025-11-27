from django import forms
from django.utils.translation import gettext_lazy as _
from django.core.validators import MinValueValidator, MaxValueValidator
from django.conf import settings
import stripe
from datetime import datetime


class AddToCartForm(forms.Form):
    quantity = forms.IntegerField(
        label=_('Quantité'),
        min_value=1,
        initial=1,
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'min': '1',
            'style': 'width: 80px;',
        })
    )


class CheckoutForm(forms.ModelForm):
    class Meta:
        from .models import Order
        model = Order
        fields = [
            'first_name', 'last_name', 'email', 'address',
            'postal_code', 'city', 'country', 'phone'
        ]
        widgets = {
            'first_name': forms.TextInput(attrs={'class': 'form-control'}),
            'last_name': forms.TextInput(attrs={'class': 'form-control'}),
            'email': forms.EmailInput(attrs={'class': 'form-control'}),
            'address': forms.TextInput(attrs={'class': 'form-control'}),
            'postal_code': forms.TextInput(attrs={'class': 'form-control'}),
            'city': forms.TextInput(attrs={'class': 'form-control'}),
            'country': forms.TextInput(attrs={'class': 'form-control'}),
            'phone': forms.TextInput(attrs={'class': 'form-control'}),
        }
        labels = {
            'first_name': _('Prénom'),
            'last_name': _('Nom'),
            'email': _('Email'),
            'address': _('Adresse'),
            'postal_code': _('Code postal'),
            'city': _('Ville'),
            'country': _('Pays'),
            'phone': _('Téléphone'),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['country'].initial = 'France'


class PaymentForm(forms.Form):
    """
    Formulaire de paiement sécurisé avec Stripe
    """
    CARD_MONTH_CHOICES = [
        ('01', '01 - Janvier'), ('02', '02 - Février'), 
        ('03', '03 - Mars'), ('04', '04 - Avril'),
        ('05', '05 - Mai'), ('06', '06 - Juin'),
        ('07', '07 - Juillet'), ('08', '08 - Août'),
        ('09', '09 - Septembre'), ('10', '10 - Octobre'),
        ('11', '11 - Novembre'), ('12', '12 - Décembre')
    ]
    
    CARD_YEAR_CHOICES = [
        (str(y), str(y)) for y in range(
            datetime.now().year, 
            datetime.now().year + 11
        )
    ]
    
    # Informations de la carte
    card_number = forms.CharField(
        label=_('Numéro de carte'),
        max_length=19,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': '4242 4242 4242 4242',
            'data-stripe': 'number'
        })
    )
    
    card_exp_month = forms.ChoiceField(
        label=_('Mois d\'expiration'),
        choices=CARD_MONTH_CHOICES,
        widget=forms.Select(attrs={
            'class': 'form-select',
            'data-stripe': 'exp-month'
        })
    )
    
    card_exp_year = forms.ChoiceField(
        label=_('Année d\'expiration'),
        choices=CARD_YEAR_CHOICES,
        widget=forms.Select(attrs={
            'class': 'form-select',
            'data-stripe': 'exp-year'
        })
    )
    
    card_cvv = forms.CharField(
        label=_('Code de sécurité (CVV)'),
        max_length=4,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': '123',
            'data-stripe': 'cvc'
        })
    )
    
    save_card = forms.BooleanField(
        label=_('Enregistrer cette carte pour de futurs achats'),
        required=False,
        widget=forms.CheckboxInput(attrs={
            'class': 'form-check-input'
        })
    )
    
    def get_js(self):
        """Retourne le code JavaScript pour initialiser Stripe"""
        return f"""
        <script src="https://js.stripe.com/v3/"></script>
        <script>
            var stripe = Stripe('{settings.STRIPE_PUBLIC_KEY}');
            var elements = stripe.elements();
            
            // Style personnalisé pour les champs de carte
            var style = {{
                base: {{
                    color: '#32325d',
                    fontFamily: '"Helvetica Neue", Helvetica, sans-serif',
                    fontSmoothing: 'antialiased',
                    fontSize: '16px',
                    '::placeholder': {{
                        color: '#aab7c4'
                    }}
                }},
                invalid: {{
                    color: '#fa755a',
                    iconColor: '#fa755a'
                }}
            }};
            
            // Créer et monter les éléments de carte
            var card = elements.create('card', {{style: style}});
            card.mount('#card-element');
            
            // Gérer les erreurs de saisie de la carte
            card.addEventListener('change', function(event) {{
                var displayError = document.getElementById('card-errors');
                if (event.error) {{
                    displayError.textContent = event.error.message;
                }} else {{
                    displayError.textContent = '';
                }}
            }});
            
            // Soumission du formulaire
            var form = document.getElementById('payment-form');
            form.addEventListener('submit', function(event) {{
                event.preventDefault();
                
                // Désactiver le bouton de soumission pour éviter les soumissions multiples
                var submitButton = document.getElementById('submit-button');
                submitButton.disabled = true;
                submitButton.value = 'Traitement en cours...';
                
                stripe.createToken(card).then(function(result) {{
                    if (result.error) {{
                        // Afficher les erreurs
                        var errorElement = document.getElementById('card-errors');
                        errorElement.textContent = result.error.message;
                        submitButton.disabled = false;
                        submitButton.value = 'Payer maintenant';
                    }} else {{
                        // Ajouter le token au formulaire et le soumettre
                        var tokenInput = document.createElement('input');
                        tokenInput.setAttribute('type', 'hidden');
                        tokenInput.setAttribute('name', 'stripeToken');
                        tokenInput.setAttribute('value', result.token.id);
                        form.appendChild(tokenInput);
                        
                        // Soumettre le formulaire
                        form.submit();
                    }}
                }});
            }});
        </script>
        """
        
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
    
    def clean_card_number(self):
        card_number = self.cleaned_data.get('card_number')
        # Nettoyer le numéro de carte (supprimer les espaces et tirets)
        card_number = card_number.replace(' ', '').replace('-', '')
        # Vérifier que le numéro de carte est valide (exemple basique)
        if not card_number.isdigit() or len(card_number) < 13 or len(card_number) > 19:
            raise forms.ValidationError(_('Numéro de carte invalide'))
        return card_number
    
    def clean_card_cvv(self):
        cvv = self.cleaned_data.get('card_cvv')
        if not cvv.isdigit() or len(cvv) < 3 or len(cvv) > 4:
            raise forms.ValidationError(_('Code de sécurité invalide'))
        return cvv


class ReviewForm(forms.ModelForm):
    class Meta:
        from .models import Review
        model = Review
        fields = ['rating', 'comment']
        widgets = {
            'rating': forms.RadioSelect(choices=[
                (1, '1 étoile'),
                (2, '2 étoiles'),
                (3, '3 étoiles'),
                (4, '4 étoiles'),
                (5, '5 étoiles'),
            ]),
            'comment': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 4,
                'placeholder': _('Partagez votre avis sur ce produit...')
            }),
        }
        labels = {
            'rating': _('Note'),
            'comment': _('Commentaire'),
        }

    def clean_rating(self):
        rating = self.cleaned_data.get('rating')
        if rating not in [1, 2, 3, 4, 5]:
            raise forms.ValidationError(_('Veuillez sélectionner une note valide.'))
        return rating


from allauth.account.forms import SignupForm, LoginForm

class CustomSignupForm(SignupForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['username'].widget.attrs.update({
            'class': 'form-control',
            'placeholder': _("Nom d'utilisateur")
        })
        self.fields['email'].widget.attrs.update({
            'class': 'form-control',
            'placeholder': _('Adresse email')
        })
        self.fields['password1'].widget.attrs.update({
            'class': 'form-control',
            'placeholder': _('Mot de passe')
        })

    def save(self, request):
        user = super().save(request)
        return user


class CustomLoginForm(LoginForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['login'].widget.attrs.update({
            'class': 'form-control',
            'placeholder': _("Nom d'utilisateur ou email")
        })
        self.fields['password'].widget.attrs.update({
            'class': 'form-control',
            'placeholder': _('Mot de passe')
        })
        self.fields['remember'].widget.attrs.update({
            'class': 'form-check-input'
        })


# Formulaires pour l'administration
class CategoryForm(forms.ModelForm):
    class Meta:
        from .models import Category
        model = Category
        fields = ['name', 'slug', 'image', 'description']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'slug': forms.TextInput(attrs={'class': 'form-control'}),
            'image': forms.ClearableFileInput(attrs={'class': 'form-control'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }
        labels = {
            'name': _('Nom'),
            'slug': _('Slug'),
            'image': _('Image'),
            'description': _('Description'),
        }


class ProductForm(forms.ModelForm):
    class Meta:
        from .models import Product
        model = Product
        fields = [
            'category', 'name', 'slug', 'image', 'description',
            'price', 'available', 'stock'
        ]
        widgets = {
            'category': forms.Select(attrs={'class': 'form-select'}),
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'slug': forms.TextInput(attrs={'class': 'form-control'}),
            'image': forms.ClearableFileInput(attrs={'class': 'form-control'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'price': forms.NumberInput(attrs={
                'class': 'form-control',
                'step': '0.01',
                'min': '0.01'
            }),
            'stock': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': '0'
            }),
        }
        labels = {
            'category': _('Catégorie'),
            'name': _('Nom'),
            'slug': _('Slug'),
            'image': _('Image principale'),
            'description': _('Description'),
            'price': _('Prix'),
            'available': _('Disponible'),
            'stock': _('Stock'),
        }


class OrderStatusForm(forms.Form):
    status = forms.ChoiceField(
        label=_('Statut'),
        choices=[],
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    
    def __init__(self, *args, **kwargs):
        from .models import Order
        super().__init__(*args, **kwargs)
        self.fields['status'].choices = Order.STATUS_CHOICES
