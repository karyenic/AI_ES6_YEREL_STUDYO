// static/js/api.js - Otomatik Güncellenmiş Merkezi API Sinyal Yöneticisi
const API_CONFIG = {
    BASE_URL: '/api', 
    
    async request(endpoint, options = {}) {
        // Gelen endpoint başındaki slash veya /api eklerini akıllıca yönet
        const cleanEndpoint = endpoint.startsWith('/') ? endpoint : `/${endpoint}`;
        const finalEndpoint = cleanEndpoint.startsWith('/api') ? cleanEndpoint : `${this.BASE_URL}${cleanEndpoint}`;
        
        const defaultHeaders = {
            'Content-Type': 'application/json',
            ...options.headers
        };

        try {
            const response = await fetch(finalEndpoint, {
                ...options,
                headers: defaultHeaders
            });

            if (!response.ok) {
                throw new Error(`HTTP Hatası! Durum: ${response.status} (${response.statusText})`);
            }

            const contentType = response.headers.get('content-type');
            if (contentType && contentType.includes('application/json')) {
                return await response.json();
            }
            return await response.text();

        } catch (error) {
            console.error(`API İstek Hatası [${finalEndpoint}]:`, error.message);
            throw error;
        }
    },

    get(endpoint) {
        return this.request(endpoint, { method: 'GET' });
    },
    
    post(endpoint, data) {
        return this.request(endpoint, {
            method: 'POST',
            body: JSON.stringify(data)
        });
    }
};

// Global kapsama açma
window.API_CONFIG = API_CONFIG;
