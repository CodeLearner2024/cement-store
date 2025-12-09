// Gestion du header fixe au défilement
let lastScroll = 0;
const navbar = document.querySelector('.navbar');
const navbarHeight = navbar ? navbar.offsetHeight : 0;
const SCROLL_THRESHOLD = 100; // Seuil de défilement pour afficher/cacher le header

// Fonction pour gérer le défilement
function handleScroll() {
    if (!navbar) return;
    
    const currentScroll = window.pageYOffset;
    
    // Si on descend et qu'on a dépassé le seuil
    if (currentScroll > lastScroll && currentScroll > SCROLL_THRESHOLD) {
        // On cache le header
        navbar.classList.add('hide');
    } else if (currentScroll < lastScroll) {
        // On remonte, on affiche le header
        navbar.classList.remove('hide');
    }
    
    lastScroll = currentScroll;
}

// Attendre que le DOM soit complètement chargé
document.addEventListener('DOMContentLoaded', function() {
    // Ajouter l'écouteur d'événement de défilement
    if (navbar) {
        window.addEventListener('scroll', handleScroll, { passive: true });
    }
    // Activer les tooltips Bootstrap
    var tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
    var tooltipList = tooltipTriggerList.map(function (tooltipTriggerEl) {
        return new bootstrap.Tooltip(tooltipTriggerEl);
    });

    // Gestion de la quantité dans le panier
    document.querySelectorAll('.quantity-btn').forEach(function(button) {
        button.addEventListener('click', function() {
            const input = this.parentNode.querySelector('.quantity-input');
            let value = parseInt(input.value) || 0;
            
            if (this.classList.contains('decrease')) {
                value = value > 1 ? value - 1 : 1;
            } else if (this.classList.contains('increase')) {
                value = value < 100 ? value + 1 : 100; // Limite à 100
            }
            
            input.value = value;
        });
    });

    // Gestion de l'ajout au panier avec AJAX
    const addToCartForms = document.querySelectorAll('.add-to-cart-form');
    addToCartForms.forEach(function(form) {
        form.addEventListener('submit', function(e) {
            e.preventDefault();
            
            const button = this.querySelector('button[type="submit"]');
            const originalText = button.innerHTML;
            
            // Afficher un indicateur de chargement
            button.disabled = true;
            button.innerHTML = '<span class="spinner-border spinner-border-sm" role="status" aria-hidden="true"></span> Ajout en cours...';
            
            // Récupérer les données du formulaire
            const formData = new FormData(this);
            
            // Envoyer la requête AJAX
            fetch(this.action, {
                method: 'POST',
                body: formData,
                headers: {
                    'X-Requested-With': 'XMLHttpRequest',
                    'X-CSRFToken': formData.get('csrfmiddlewaretoken')
                },
                credentials: 'same-origin'
            })
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    // Mettre à jour le compteur du panier
                    const cartCount = document.querySelector('.cart-count');
                    if (cartCount) {
                        cartCount.textContent = data.cart_total_quantity;
                    }
                    
                    // Afficher un message de succès
                    showAlert('Le produit a été ajouté à votre panier', 'success');
                } else {
                    // Afficher un message d'erreur
                    showAlert('Une erreur est survenue lors de l\'ajout au panier', 'danger');
                }
            })
            .catch(error => {
                console.error('Erreur:', error);
                showAlert('Une erreur est survenue', 'danger');
            })
            .finally(() => {
                // Réactiver le bouton et réinitialiser le texte
                button.disabled = false;
                button.innerHTML = originalText;
            });
        });
    });

    // Fonction pour afficher des messages d'alerte
    function showAlert(message, type = 'info') {
        const alertDiv = document.createElement('div');
        alertDiv.className = `alert alert-${type} alert-dismissible fade show`;
        alertDiv.role = 'alert';
        alertDiv.innerHTML = `
            ${message}
            <button type="button" class="btn-close" data-bs-dismiss="alert" aria-label="Close"></button>
        `;
        
        const container = document.querySelector('.alerts-container');
        if (container) {
            container.prepend(alertDiv);
            
            // Supprimer l'alerte après 5 secondes
            setTimeout(() => {
                const alert = bootstrap.Alert.getOrCreateInstance(alertDiv);
                if (alert) {
                    alert.close();
                }
            }, 5000);
        }
    }

    // Gestion des onglets avec persistance dans l'URL
    const url = new URL(window.location);
    const activeTab = url.searchParams.get('tab');
    if (activeTab) {
        const tabTrigger = document.querySelector(`[data-bs-target="#${activeTab}"]`);
        if (tabTrigger) {
            const tab = new bootstrap.Tab(tabTrigger);
            tab.show();
        }
    }

    // Mettre à jour l'URL lorsque l'onglet change
    const tabTriggers = document.querySelectorAll('button[data-bs-toggle="tab"]');
    tabTriggers.forEach(trigger => {
        trigger.addEventListener('click', function() {
            const target = this.getAttribute('data-bs-target').substring(1);
            url.searchParams.set('tab', target);
            window.history.pushState({}, '', url);
        });
    });

    // Gestion de la prévisualisation de l'image de profil
    const imageInput = document.getElementById('id_image');
    if (imageInput) {
        imageInput.addEventListener('change', function(e) {
            const file = e.target.files[0];
            if (file) {
                const reader = new FileReader();
                const preview = document.getElementById('image-preview');
                
                reader.onload = function(e) {
                    preview.src = e.target.result;
                    preview.style.display = 'block';
                }
                
                reader.readAsDataURL(file);
            }
        });
    }

    // Gestion du formulaire de recherche
    const searchForm = document.querySelector('.search-form');
    if (searchForm) {
        searchForm.addEventListener('submit', function(e) {
            const query = this.querySelector('input[name="q"]').value.trim();
            if (!query) {
                e.preventDefault();
                // Afficher un message d'erreur ou autre action
            }
        });
    }

    // Initialiser les sélecteurs de date
    const dateInputs = document.querySelectorAll('input[type="date"]');
    dateInputs.forEach(input => {
        if (!input.value) {
            const today = new Date().toISOString().split('T')[0];
            input.value = today;
        }
    });

    // Gestion du chargement paresseux des images
    const lazyImages = document.querySelectorAll('img.lazy-load');
    if ('IntersectionObserver' in window) {
        const imageObserver = new IntersectionObserver((entries, observer) => {
            entries.forEach(entry => {
                if (entry.isIntersecting) {
                    const img = entry.target;
                    img.src = img.dataset.src;
                    img.classList.remove('lazy-load');
                    imageObserver.unobserve(img);
                }
            });
        });

        lazyImages.forEach(img => imageObserver.observe(img));
    } else {
        // Fallback pour les navigateurs qui ne supportent pas IntersectionObserver
        lazyImages.forEach(img => {
            img.src = img.dataset.src;
            img.classList.remove('lazy-load');
        });
    }

    // Gestion des modales avec chargement AJAX
    document.querySelectorAll('[data-bs-toggle="modal"]').forEach(button => {
        button.addEventListener('click', function() {
            const modalTarget = this.getAttribute('data-bs-target');
            const modal = document.querySelector(modalTarget);
            const modalBody = modal.querySelector('.modal-body');
            const url = this.getAttribute('data-url');
            
            if (url) {
                modalBody.innerHTML = `
                    <div class="text-center p-5">
                        <div class="spinner-border text-primary" role="status">
                            <span class="visually-hidden">Chargement...</span>
                        </div>
                    </div>
                `;
                
                fetch(url)
                    .then(response => response.text())
                    .then(html => {
                        modalBody.innerHTML = html;
                    })
                    .catch(error => {
                        console.error('Erreur lors du chargement du contenu:', error);
                        modalBody.innerHTML = `
                            <div class="alert alert-danger">
                                Une erreur est survenue lors du chargement du contenu.
                            </div>
                        `;
                    });
            }
        });
    });
});

// Fonction pour formater les prix
function formatPrice(price) {
    // Formatage personnalisé pour le franc burundais (BIF)
    return new Intl.NumberFormat('fr-BI', {
        style: 'decimal',
        minimumFractionDigits: 0,
        maximumFractionDigits: 0
    }).format(price) + ' FBu';
}

// Fonction pour ajouter un produit au panier via AJAX
function addToCart(productId, quantity = 1) {
    const url = `/boutique/panier/ajouter/${productId}/`;
    const csrftoken = getCookie('csrftoken');
    
    return fetch(url, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/x-www-form-urlencoded',
            'X-Requested-With': 'XMLHttpRequest',
            'X-CSRFToken': csrftoken
        },
        body: `quantity=${quantity}`,
        credentials: 'same-origin'
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            // Mettre à jour le compteur du panier
            updateCartCount(data.cart_total_quantity);
            return { success: true, data };
        } else {
            return { success: false, error: data.error || 'Une erreur est survenue' };
        }
    })
    .catch(error => {
        console.error('Erreur:', error);
        return { success: false, error: 'Erreur réseau' };
    });
}

// Fonction utilitaire pour récupérer un cookie
function getCookie(name) {
    let cookieValue = null;
    if (document.cookie && document.cookie !== '') {
        const cookies = document.cookie.split(';');
        for (let i = 0; i < cookies.length; i++) {
            const cookie = cookies[i].trim();
            if (cookie.substring(0, name.length + 1) === (name + '=')) {
                cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                break;
            }
        }
    }
    return cookieValue;
}

// Fonction pour mettre à jour le compteur du panier
function updateCartCount(count) {
    const cartCountElements = document.querySelectorAll('.cart-count');
    cartCountElements.forEach(element => {
        element.textContent = count;
    });
    
    // Ajouter une animation au compteur
    const cartIcon = document.querySelector('.cart-icon');
    if (cartIcon) {
        cartIcon.classList.add('animate__animated', 'animate__rubberBand');
        setTimeout(() => {
            cartIcon.classList.remove('animate__animated', 'animate__rubberBand');
        }, 1000);
    }
}

// Initialiser les sélecteurs de quantité
function initQuantitySelectors() {
    document.querySelectorAll('.quantity-selector').forEach(selector => {
        const input = selector.querySelector('.quantity-input');
        const minusBtn = selector.querySelector('.quantity-minus');
        const plusBtn = selector.querySelector('.quantity-plus');
        
        if (minusBtn) {
            minusBtn.addEventListener('click', () => {
                let value = parseInt(input.value) || 1;
                if (value > 1) {
                    input.value = value - 1;
                    triggerChangeEvent(input);
                }
            });
        }
        
        if (plusBtn) {
            plusBtn.addEventListener('click', () => {
                let value = parseInt(input.value) || 1;
                const max = parseInt(input.getAttribute('max')) || 999;
                if (value < max) {
                    input.value = value + 1;
                    triggerChangeEvent(input);
                }
            });
        }
        
        input.addEventListener('change', function() {
            let value = parseInt(this.value) || 1;
            const min = parseInt(this.getAttribute('min')) || 1;
            const max = parseInt(this.getAttribute('max')) || 999;
            
            if (value < min) value = min;
            if (value > max) value = max;
            
            this.value = value;
        });
    });
}

// Déclencher un événement change personnalisé
function triggerChangeEvent(element) {
    const event = new Event('change', { bubbles: true });
    element.dispatchEvent(event);
}

// Initialiser les tooltips
function initTooltips() {
    const tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
    tooltipTriggerList.map(function (tooltipTriggerEl) {
        return new bootstrap.Tooltip(tooltipTriggerEl);
    });
}

// Initialiser les popovers
function initPopovers() {
    const popoverTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="popover"]'));
    popoverTriggerList.map(function (popoverTriggerEl) {
        return new bootstrap.Popover(popoverTriggerEl);
    });
}

// Gestion de la sélection des catégories
function initCategorySelector() {
    const categorySelect = document.getElementById('categorySelect');
    if (categorySelect) {
        categorySelect.addEventListener('change', function() {
            const categorySlug = this.value;
            if (categorySlug) {
                // Rediriger vers la page de la catégorie sélectionnée
                window.location.href = `/boutique/categorie/${categorySlug}/`;
            } else {
                // Si aucune catégorie n'est sélectionnée, aller à la liste des produits
                window.location.href = '/boutique/produits/';
            }
        });
    }
}

// Initialiser les composants au chargement du DOM
document.addEventListener('DOMContentLoaded', function() {
    initCategorySelector();
    initQuantitySelectors();
    initTooltips();
    initPopovers();
});
