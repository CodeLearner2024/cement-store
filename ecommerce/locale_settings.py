import os
from pathlib import Path

# Chemin de base du projet
BASE_DIR = Path(__file__).resolve().parent

# Configuration des chemins de traduction
LOCALE_PATHS = [
    os.path.join(BASE_DIR, 'locale'),
]

# Langues supportées
LANGUAGES = [
    ('fr', 'Français'),
    ('en', 'English'),
    ('es', 'Español'),
]
