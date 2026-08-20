/**
 * API Client for CropVerse Backend
 * Handles all HTTP requests to Flask backend
 */

class CropVerseAPI {
    constructor(baseURL = API_CONFIG.BASE_URL) {
        this.baseURL = baseURL;
    }

    /**
     * Generic fetch wrapper with error handling
     */
    async request(endpoint, options = {}) {
        const url = `${this.baseURL}${endpoint}`;
        
        const defaultOptions = {
            headers: {
                'Content-Type': 'application/json',
            },
            ...options
        };

        try {
            const response = await fetch(url, defaultOptions);
            const data = await response.json();
            
            if (!response.ok) {
                throw new Error(data.message || `HTTP ${response.status}: ${response.statusText}`);
            }
            
            return data;
        } catch (error) {
            console.error(`API Error [${endpoint}]:`, error);
            throw error;
        }
    }

    // ========================================
    // DASHBOARD ENDPOINTS
    // ========================================

    /**
     * Get dashboard summary with latest readings
     */
    async getDashboardSummary() {
        return await this.request(API_CONFIG.ENDPOINTS.DASHBOARD_SUMMARY);
    }

    /**
     * Get latest sensor readings
     * @param {number} limit - Number of readings to fetch
     */
    async getLatestReadings(limit = 10) {
        return await this.request(`${API_CONFIG.ENDPOINTS.DASHBOARD_READINGS}?limit=${limit}`);
    }

    /**
     * Get recent alerts
     * @param {number} hours - Hours to look back (default 24)
     */
    async getRecentAlerts(hours = 24) {
        return await this.request(`${API_CONFIG.ENDPOINTS.DASHBOARD_ALERTS}?hours=${hours}`);
    }

    // ========================================
    // ANALYTICS ENDPOINTS
    // ========================================

    /**
     * Get sensor trends for specified days
     * @param {number} days - Number of days to analyze (default 7)
     */
    async getAnalyticsTrends(days = 7) {
        return await this.request(`${API_CONFIG.ENDPOINTS.ANALYTICS_TRENDS}?days=${days}`);
    }

    // ========================================
    // CHATBOT ENDPOINTS
    // ========================================

    /**
     * Send message to AI chatbot
     * @param {string} message - User message
     * @param {string} userId - User identifier
     */
    async sendChatMessage(message, userId = 'web_user') {
        return await this.request(API_CONFIG.ENDPOINTS.CHATBOT_MESSAGE, {
            method: 'POST',
            body: JSON.stringify({ message, user_id: userId })
        });
    }

    // ========================================
    // SETTINGS ENDPOINTS
    // ========================================

    /**
     * Get all system settings
     */
    async getSettings() {
        return await this.request(API_CONFIG.ENDPOINTS.SETTINGS);
    }

    // ========================================
    // HEALTH CHECK
    // ========================================

    /**
     * Check backend health status
     */
    async healthCheck() {
        return await this.request(API_CONFIG.ENDPOINTS.HEALTH);
    }
}

// Create global API instance
const api = new CropVerseAPI();