from django.views.generic import TemplateView
from django.utils.translation import gettext_lazy as _
from django.db.models import Count
from .models import Category, Product

class LandingPageView(TemplateView):
    template_name = 'boutique/landing.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['categories'] = Category.objects.annotate(
            num_products=Count('products')
        ).filter(num_products__gt=0).order_by('name')
        return context
