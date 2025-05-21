// Tailwind Configuration
tailwind.config = {
    theme: {
        extend: {
            fontFamily: {
                sans: ['Inter', 'sans-serif'],
            },
            colors: {
                primary: {
                    50: '#f0f9ff',
                    100: '#e0f2fe',
                    200: '#bae6fd',
                    300: '#7dd3fc',
                    400: '#38bdf8',
                    500: '#0ea5e9',
                    600: '#0284c7',
                    700: '#0369a1',
                    800: '#075985',
                    900: '#0c4a6e',
                },
            },
        },
    },
};

// Auto-hide messages after 5 seconds
document.addEventListener('DOMContentLoaded', () => {
    setTimeout(() => {
        const messages = document.querySelectorAll('.toast > div');
        messages.forEach(msg => {
            msg.style.animation = 'slideOut 0.3s ease-in-out forwards';
            setTimeout(() => msg.remove(), 300);
        });
    }, 5000);
});

// Loading State Management
window.loadingState = {
    show() {
        document.querySelector('.loading').classList.add('active');
    },
    hide() {
        document.querySelector('.loading').classList.remove('active');
    }
};

// Form Submission Handler
document.addEventListener('submit', (e) => {
    if (!e.target.classList.contains('no-loading')) {
        loadingState.show();
    }
});

// AJAX Request Helper
window.makeRequest = async (url, method = 'GET', data = null) => {
    loadingState.show();
    try {
        const response = await fetch(url, {
            method,
            headers: {
                'X-CSRFToken': document.querySelector('[name=csrfmiddlewaretoken]').value,
                'Content-Type': 'application/json'
            },
            body: data ? JSON.stringify(data) : null
        });
        return await response.json();
    } finally {
        loadingState.hide();
    }
}; 