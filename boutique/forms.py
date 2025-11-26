from django import forms
from django.utils.translation import gettext_lazy as _
from django.core.validators import MinValueValidator, MaxValueValidator


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
