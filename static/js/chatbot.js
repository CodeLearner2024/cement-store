// Configuration du chatbot
document.addEventListener('DOMContentLoaded', function() {
    // Initialisation des variables
    const chatToggle = document.querySelector('.chatbot-toggle');
    
    // Vérifier si l'élément du bouton existe
    if (!chatToggle) return;
    
    // Fonction pour afficher un message de bienvenue
    function showWelcomeMessage() {
        if (typeof Tawk_API === 'undefined') return;
        
        // Vérifier si l'utilisateur est connecté
        const isAuthenticated = document.body.getAttribute('data-user-authenticated') === 'true';
        
        if (isAuthenticated) {
            const userName = document.body.getAttribute('data-username') || 'Client';
            Tawk_API.setChatMessage(`Bonjour ${userName}, comment puis-je vous aider aujourd'hui ?`);
        } else {
            Tawk_API.setChatMessage('Bonjour, comment puis-je vous aider aujourd\'hui ?');
        }
    }
    
    // Fonction pour basculer le chat
    function toggleChat() {
        if (typeof Tawk_API === 'undefined') return;
        
        if (Tawk_API.isChatMinimized()) {
            Tawk_API.maximize();
            chatToggle.classList.add('active');
            showWelcomeMessage();
        } else {
            Tawk_API.minimize();
            chatToggle.classList.remove('active');
        }
    }
    
    // Gestionnaire d'événements pour le bouton
    chatToggle.addEventListener('click', toggleChat);
    
    // Initialisation de Tawk.to
    if (typeof Tawk_API !== 'undefined') {
        Tawk_API.onLoad = function() {
            // Configuration de base
            Tawk_API.setAttributes({
                'name': document.body.getAttribute('data-user-name') || 'Visiteur',
                'email': document.body.getAttribute('data-user-email') || '',
                'hash': document.body.getAttribute('data-user-id') || ''
            });
            
            // Masquer sur les pages d'administration
            if (window.location.pathname.includes('admin') || 
                window.location.pathname.includes('checkout')) {
                Tawk_API.hideWidget();
            }
            
            // Gestion des événements
            Tawk_API.onChatMaximized = function() {
                chatToggle.style.display = 'none';
                showWelcomeMessage();
            };
            
            Tawk_API.onChatMinimized = function() {
                chatToggle.style.display = 'flex';
            };
            
            Tawk_API.onChatHidden = function() {
                chatToggle.style.display = 'flex';
            };
        };
    }
    
    // Vérifier les messages non lus
    setInterval(function() {
        if (typeof Tawk_API !== 'undefined' && Tawk_API.getStatus() === 'chatting') {
            Tawk_API.getChatStatus(function(status) {
                const notification = document.querySelector('.chatbot-notification');
                if (!notification) return;
                
                if (status === 'unread') {
                    notification.classList.remove('d-none');
                } else {
                    notification.classList.add('d-none');
                }
            });
        }
    }, 5000);
});
