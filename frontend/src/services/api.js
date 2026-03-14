// ============================================================================
// IMPORTS (Must be at the top)
// ============================================================================
import axios from 'axios';

// ============================================================================
// TOKEN REFRESH QUEUE MANAGEMENT
// ============================================================================
let isRefreshing = false;
let failedQueue = [];

const processQueue = (error, token = null) => {
    failedQueue.forEach(prom => {
        if (error) {
            prom.reject(error);
        } else {
            prom.resolve(token);
        }
    });
    failedQueue = [];
};

// ============================================================================
// CREATE AXIOS INSTANCE
// ============================================================================
const api = axios.create({
    baseURL: 'http://localhost:5001/api',
    headers: { 'Content-Type': 'application/json' }
});

// ============================================================================
// REQUEST INTERCEPTOR - Add token to requests
// ============================================================================
api.interceptors.request.use(
    (config) => {
        const token = localStorage.getItem('accessToken');
        if (token) {
            config.headers.Authorization = `Bearer ${token}`;
        }
        return config;
    },
    (error) => Promise.reject(error)
);

// ============================================================================
// RESPONSE INTERCEPTOR - Handle token refresh
// ============================================================================
api.interceptors.response.use(
    (response) => response,
    async (error) => {
        const originalRequest = error.config;
        
        // Check if error is 401 and token is expired
        if (error.response?.status === 401 && error.response.data?.expired && !originalRequest._retry) {
            
            // If already refreshing, queue this request
            if (isRefreshing) {
                return new Promise((resolve, reject) => {
                    failedQueue.push({ resolve, reject });
                })
                .then(token => {
                    originalRequest.headers.Authorization = `Bearer ${token}`;
                    return api(originalRequest);
                })
                .catch(err => Promise.reject(err));
            }

            originalRequest._retry = true;
            isRefreshing = true;

            try {
                // Attempt to refresh the token
                const refreshToken = localStorage.getItem('refreshToken');
                const response = await axios.post('http://localhost:5001/api/auth/refresh', { 
                    refreshToken 
                });

                const { accessToken, refreshToken: newRefreshToken } = response.data;
                
                // Store new tokens
                localStorage.setItem('accessToken', accessToken);
                localStorage.setItem('refreshToken', newRefreshToken);

                // Process queued requests with new token
                processQueue(null, accessToken);

                // Retry original request with new token
                originalRequest.headers.Authorization = `Bearer ${accessToken}`;
                return api(originalRequest);

            } catch (refreshError) {
                // Refresh failed - clear tokens and redirect to login
                processQueue(refreshError, null);
                localStorage.clear();
                window.location.href = '/login';
                return Promise.reject(refreshError);

            } finally {
                isRefreshing = false;
            }
        }

        return Promise.reject(error);
    }
);

export const authAPI = {
    register: (data) => api.post('/auth/register', data),
    login: (data) => api.post('/auth/login', data),
    logout: () => api.post('/auth/logout'),
    refresh: (refreshToken) => api.post('/auth/refresh', { refreshToken }),
};

// ============================================================================
// PRODUCTS API ENDPOINTS
// ============================================================================
export const productsAPI = {
    // GET /api/products
    getAll: () => api.get('/products'),
    
    // GET /api/products/:id
    getById: (id) => api.get(`/products/${id}`),
    
    // POST /api/products
    create: (data) => api.post('/products', data),
    
    // PUT /api/products/:id
    update: (id, data) => api.put(`/products/${id}`, data),
    
    // DELETE /api/products/:id
    delete: (id) => api.delete(`/products/${id}`),
};


// ============================================================================
// EXPORT
// ============================================================================
export default api;