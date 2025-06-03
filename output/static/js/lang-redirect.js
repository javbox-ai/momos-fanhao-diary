// Language auto-redirect script
document.addEventListener('DOMContentLoaded', function() {
    // Check if this is the first visit (no language preference stored)
    if(!localStorage.getItem('lang_preference')) {
        // Get browser language
        const userLang = navigator.language || navigator.userLanguage;
        
        // If current path is root
        if(window.location.pathname.endsWith('/') || window.location.pathname.endsWith('/index.html')) {
            // If browser language starts with zh, redirect to Chinese
            if(userLang.startsWith('zh')) {
                localStorage.setItem('lang_preference', 'cn');
                window.location.href = 'index_p1.html';
            } else {
                // Otherwise redirect to English
                localStorage.setItem('lang_preference', 'en');
                window.location.href = 'en/index_p1.html';
            }
        }
    }
});
