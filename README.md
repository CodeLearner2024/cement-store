"# E-commerce de Ciment

Bienvenue dans l'application e-commerce pour la vente de ciment. Cette plateforme permet aux utilisateurs de parcourir, rechercher et acheter différents types de ciment en ligne.

## Fonctionnalités principales

- **Catalogue de produits** : Parcourir les différents types de ciment disponibles
- **Recherche avancée** : Trouver facilement les produits par nom, catégorie ou mot-clé
- **Panier d'achat** : Ajouter des produits au panier et procéder au paiement
- **Système de commande** : Passer des commandes en toute sécurité
- **Espace client** : Gérer son compte, ses commandes et ses informations personnelles
- **Interface d'administration** : Gérer les produits, les catégories et les commandes
- **Paiement en ligne** : Intégration avec Stripe pour des paiements sécurisés
- **Gestion des stocks** : Suivi en temps réel des quantités disponibles
- **Livraison** : Options de livraison flexibles selon la quantité commandée

## Prérequis

- Python 3.8 ou supérieur
- Django 5.2
- PostgreSQL (recommandé pour la production)
- Compte Stripe (pour les paiements en ligne)
- Espace de stockage adapté pour les commandes en gros volume

## Installation

1. **Cloner le dépôt**
   ```bash
   git clone [URL_DU_DEPOT]
   cd ecommerce
   ```

2. **Créer un environnement virtuel**
   ```bash
   python -m venv venv
   source venv/bin/activate  # Sur Windows: venv\Scripts\activate
   ```

3. **Installer les dépendances**
   ```bash
   pip install -r requirements.txt
   ```

4. **Configurer les variables d'environnement**
   Créez un fichier `.env` à la racine du projet avec les variables suivantes :
   ```
   SECRET_KEY=votre_secret_key
   DEBUG=True
   STRIPE_PUBLIC_KEY=votre_cle_publique_stripe
   STRIPE_SECRET_KEY=votre_cle_secrete_stripe
   STRIPE_WEBHOOK_SECRET=votre_webhook_secret_stripe
   DATABASE_URL=postgres://user:password@localhost:5432/dbname
   ```

5. **Appliquer les migrations**
   ```bash
   python manage.py migrate
   ```

6. **Créer un superutilisateur**
   ```bash
   python manage.py createsuperuser
   ```

7. **Lancer le serveur de développement**
   ```bash
   python manage.py runserver
   ```

## Structure du projet

```
ecommerce/
├── boutique/                 # Application principale
│   ├── migrations/          # Fichiers de migration
│   ├── static/              # Fichiers statiques (CSS, JS, images)
│   ├── templates/           # Templates HTML
│   ├── admin.py            # Configuration de l'interface d'administration
│   ├── models.py           # Modèles de données
│   ├── urls.py             # URLs de l'application
│   └── views.py            # Vues de l'application
├── ecommerce/              # Configuration du projet
├── media/                  # Fichiers média téléchargés
├── staticfiles/            # Fichiers statiques collectés
└── manage.py               # Script de gestion Django
```

## Configuration de l'environnement de production

1. **Paramètres de sécurité**
   - Mettre `DEBUG = False` dans les paramètres
   - Configurer une `SECRET_KEY` sécurisée
   - Configurer `ALLOWED_HOSTS` avec votre domaine

2. **Base de données**
   - Utiliser PostgreSQL en production
   - Configurer les sauvegardes automatiques

3. **Fichiers statiques et médias**
   ```python
   STATIC_ROOT = os.path.join(BASE_DIR, 'staticfiles')
   MEDIA_ROOT = os.path.join(BASE_DIR, 'media')
   ```
   Puis exécutez :
   ```bash
   python manage.py collectstatic
   ```

## Déploiement

### Avec Docker (recommandé)

1. Construire l'image Docker :
   ```bash
   docker-compose build
   ```

2. Démarrer les conteneurs :
   ```bash
   docker-compose up -d
   ```

### Déploiement manuel

1. Installer les dépendances système :
   ```bash
   sudo apt-get update
   sudo apt-get install python3-pip python3-venv postgresql postgresql-contrib nginx
   ```

2. Configurer Gunicorn :
   ```bash
   pip install gunicorn
   gunicorn --bind 0.0.0.0:8000 ecommerce.wsgi
   ```

3. Configurer Nginx comme reverse proxy

## Tests

Pour exécuter les tests :
```bash
python manage.py test
```

## Contribution

1. Forkez le projet
2. Créez une branche pour votre fonctionnalité (`git checkout -b feature/nouvelle-fonctionnalite`)
3. Committez vos modifications (`git commit -am 'Ajout d\'une nouvelle fonctionnalité'`)
4. Poussez vers la branche (`git push origin feature/nouvelle-fonctionnalite`)
5. Créez une Pull Request

## Licence

Ce projet est sous licence MIT. Voir le fichier `LICENSE` pour plus de détails.

## Support

Pour toute question ou problème, veuillez ouvrir une issue sur le dépôt ou contacter l'équipe de développement." 
