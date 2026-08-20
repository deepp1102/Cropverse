// API Configuration
const API_CONFIG = {
    // Local development
    BASE_URL: 'http://localhost:8080',
    
    // Production (after deployment)
    // BASE_URL: 'https://YOUR_PROJECT_ID.web.app',
    
    ENDPOINTS: {
        // Arduino
        ARDUINO_DATA: '/api/arduino/data',
        
        // Dashboard
        DASHBOARD_SUMMARY: '/api/dashboard/summary',
        DASHBOARD_READINGS: '/api/dashboard/latest-readings',
        DASHBOARD_ALERTS: '/api/dashboard/alerts',
        
        // Analytics
        ANALYTICS_TRENDS: '/api/analytics/trends',
        
        // Chatbot
        CHATBOT_MESSAGE: '/api/chatbot/message',
        
        // Settings
        SETTINGS: '/api/settings',
        
        // Health
        HEALTH: '/health'
    },
    
    // Polling intervals (milliseconds)
    REALTIME_UPDATE_INTERVAL: 5000,  // 5 seconds
    DASHBOARD_REFRESH_INTERVAL: 10000, // 10 seconds
};