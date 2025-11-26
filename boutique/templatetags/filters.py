from django import template

register = template.Library()

@register.filter
def get_item(dictionary, key):
    """
    Récupère une valeur d'un dictionnaire en utilisant une clé variable.
    
    Exemple d'utilisation dans un template :
    {{ my_dict|get_item:key_variable }}
    """
    return dictionary.get(key, {})
