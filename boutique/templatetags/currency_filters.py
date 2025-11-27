from django import template

register = template.Library()

@register.filter(name='currency')
def currency(value):
    """
    Formate un nombre en tant que devise avec le symbole Fbu
    Exemple: {{ value|currency }} -> 25000 Fbu
    """
    if value is None:
        return "0 Fbu"
    try:
        # Supprimer les décimales si elles sont à zéro
        if float(value) == int(float(value)):
            return f"{int(value):,} Fbu".replace(",", " ")
        return f"{float(value):,.2f} Fbu".replace(",", " ").replace(".", ",")
    except (ValueError, TypeError):
        return f"{value} Fbu"
