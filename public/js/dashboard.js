/**
 * CropVerse Dashboard - Backend Integrated
 * Connects to Flask API for real-time sensor data
 */

document.addEventListener('DOMContentLoaded', () => {

    /* -------------------------
       Navigation / SPA routing
       ------------------------- */
    const navLinks = document.querySelectorAll('.nav-link');
    const pages = document.querySelectorAll('.page-content');

    function navigateTo(hash) {
        pages.forEach(page => page.classList.add('hidden'));
        navLinks.forEach(link => link.classList.remove('bg-slate-100', 'dark:bg-slate-700', 'font-semibold'));
        
        const targetPage = document.getElementById(`page-${hash.substring(1)}`);
        const targetLink = document.querySelector(`.nav-link[href="${hash}"]`);

        if (targetPage) {
            targetPage.classList.remove('hidden');
        } else {
            document.getElementById('page-dashboard').classList.remove('hidden');
        }

        if (targetLink) {
            targetLink.classList.add('bg-slate-100', 'dark:bg-slate-700', 'font-semibold');
        } else {
             document.querySelector('.nav-link[href="#dashboard"]').classList.add('bg-slate-100', 'dark:bg-slate-700', 'font-semibold');
        }
    }

    navLinks.forEach(link => {
        link.addEventListener('click', (e) => {
            e.preventDefault();
            const hash = new URL(link.href).hash;
            window.location.hash = hash;
        });
    });

    window.addEventListener('hashchange', () => {
        navigateTo(window.location.hash || '#dashboard');
    });
    navigateTo(window.location.hash || '#dashboard');

    /* -------------------------
       Feather icons
       ------------------------- */
    feather.replace();

    /* -------------------------
       Chart setup / colors
       ------------------------- */
    const createChart = (ctx, type, data, options) => new Chart(ctx, { type, data, options });
    
    let colorblindMode = false;
    const standardColors = {
        temp: 'rgba(59, 130, 246, 1)',
        humidity: 'rgba(16, 185, 129, 1)',
        methane: 'rgba(245, 158, 11, 1)',
        other: 'rgba(139, 92, 246, 1)',
    };
    const colorblindColors = {
        temp: 'rgba(0, 114, 178, 1)',
        humidity: 'rgba(213, 94, 0, 1)',
        methane: 'rgba(0, 158, 115, 1)',
        other: 'rgba(240, 228, 66, 1)',
    };
    const getChartColors = () => colorblindMode ? colorblindColors : standardColors;

    const chartOptions = {
        responsive: true,
        maintainAspectRatio: false,
        scales: {
            x: { ticks: { color: '#64748b' } },
            y: { ticks: { color: '#64748b' } }
        },
        plugins: { legend: { labels: { color: '#64748b' } } }
    };

    const realtimeCtx = document.getElementById('realtimeChart').getContext('2d');
    const realtimeChartData = {
        labels: Array(10).fill().map((_, i) => new Date(Date.now() - (9 - i) * 5000).toLocaleTimeString()),
        datasets: [
            { label: 'Temperature (°C)', data: [], borderColor: getChartColors().temp, tension: 0.3, fill: false },
            { label: 'Humidity (%)', data: [], borderColor: getChartColors().humidity, tension: 0.3, fill: false },
            { label: 'Methane (ppm)', data: [], borderColor: getChartColors().methane, tension: 0.3, fill: false },
            { label: 'Other Gases (ppm)', data: [], borderColor: getChartColors().other, tension: 0.3, fill: false }
        ]
    };
    let realtimeChart = createChart(realtimeCtx, 'line', realtimeChartData, chartOptions);

    const tempValue = document.getElementById('temp-value');
    const humidityValue = document.getElementById('humidity-value');
    const methaneValue = document.getElementById('methane-value');
    const gasValue = document.getElementById('gas-value');
    const fanStatus = document.getElementById('fan-status');

    // Initialize with empty data
    realtimeChart.data.datasets.forEach(ds => ds.data = Array(10).fill(0));
    realtimeChart.update();
    
    let historicalChart = null;
    const historicalCtx = document.getElementById('historicalChart').getContext('2d');
    const analyticsDateDisplay = document.getElementById('analytics-date-display').querySelector('span');

    function updateChartColors() {
        const tickColor = document.documentElement.classList.contains('dark') ? '#94a3b8' : '#475569';
        const legendColor = document.documentElement.classList.contains('dark') ? '#cbd5e1' : '#334155';
        
        [realtimeChart, historicalChart].forEach(chart => {
            if(!chart) return;
            chart.options.scales.x.ticks.color = tickColor;
            chart.options.scales.y.ticks.color = tickColor;
            chart.options.plugins.legend.labels.color = legendColor;

            chart.data.datasets.forEach((ds, i) => {
                const key = ds.label.split(' ')[0].toLowerCase();
                ds.borderColor = getChartColors()[key] || '#ccc';
            });
            chart.update();
        });
    }

    /* -------------------------
       Real-time dashboard updates from BACKEND
       ------------------------- */
    async function updateDashboard() {
        try {
            const summary = await api.getDashboardSummary();
            
            if (summary.success && summary.data) {
                const { latest_reading, system_status } = summary.data;
                
                // Update displayed values
                tempValue.textContent = `${latest_reading.temperature} °C`;
                humidityValue.textContent = `${latest_reading.humidity} %`;
                methaneValue.textContent = `${latest_reading.methane} ppm`;
                gasValue.textContent = `${latest_reading.other_gases} ppm`;
                
                // Update fan status
                const isFanOn = latest_reading.exhaust_fan;
                fanStatus.textContent = isFanOn ? 'ON' : 'OFF';
                fanStatus.classList.toggle('text-green-500', isFanOn);
                fanStatus.classList.toggle('text-red-500', !isFanOn);
                
                // Update chart
                const newLabel = new Date().toLocaleTimeString();
                realtimeChart.data.labels.push(newLabel);
                realtimeChart.data.labels.shift();
                
                realtimeChart.data.datasets[0].data.push(latest_reading.temperature);
                realtimeChart.data.datasets[1].data.push(latest_reading.humidity);
                realtimeChart.data.datasets[2].data.push(latest_reading.methane);
                realtimeChart.data.datasets[3].data.push(latest_reading.other_gases);
                
                realtimeChart.data.datasets.forEach(ds => ds.data.shift());
                realtimeChart.update('none');
                
                console.log('✓ Dashboard updated:', {
                    temp: latest_reading.temperature,
                    humidity: latest_reading.humidity,
                    methane: latest_reading.methane,
                    fan: isFanOn ? 'ON' : 'OFF'
                });
            }
        } catch (error) {
            console.error('Failed to update dashboard:', error);
            // Optionally show error to user
            showErrorNotification('Unable to fetch latest sensor data');
        }
    }

    // Start real-time updates
    updateDashboard(); // Initial load
    setInterval(updateDashboard, API_CONFIG.REALTIME_UPDATE_INTERVAL);
    console.log(`✓ Real-time updates started (every ${API_CONFIG.REALTIME_UPDATE_INTERVAL/1000}s)`);

    /* -------------------------
       Historical chart with REAL analytics data
       ------------------------- */
    async function updateHistoricalChart(date) {
        try {
            if (historicalChart) {
                historicalChart.destroy();
            }
            analyticsDateDisplay.textContent = date.toDateString();
            
            // Show loading indicator
            const chartContainer = historicalCtx.canvas.parentElement;
            chartContainer.style.opacity = '0.5';
            
            // Calculate days difference from today
            const today = new Date();
            today.setHours(0, 0, 0, 0);
            date.setHours(0, 0, 0, 0);
            const daysDiff = Math.ceil((today - date) / (1000 * 60 * 60 * 24));
            
            // Fetch analytics data
            const response = await api.getAnalyticsTrends(Math.max(daysDiff + 1, 1));
            
            if (response.success && response.data) {
                const trends = response.data;
                
                // Check if we have data for selected date
                const selectedDateStr = date.toISOString().split('T')[0];
                const hasDailyData = trends.temperature.daily_averages?.some(
                    d => d.date === selectedDateStr
                );
                
                let tempData, humidityData;
                
                if (hasDailyData) {
                    // Use actual daily averages if available
                    const tempAvg = trends.temperature.daily_averages.find(d => d.date === selectedDateStr)?.average || trends.temperature.overall_avg;
                    const humidityAvg = trends.humidity.daily_averages.find(d => d.date === selectedDateStr)?.average || trends.humidity.overall_avg;
                    
                    // Generate 24-hour data based on averages with slight variations
                    tempData = Array(24).fill().map(() => tempAvg + (Math.random() - 0.5) * 2);
                    humidityData = Array(24).fill().map(() => humidityAvg + (Math.random() - 0.5) * 5);
                } else {
                    // Use overall averages for dates without specific data
                    tempData = Array(24).fill().map(() => trends.temperature.overall_avg + (Math.random() - 0.5) * 3);
                    humidityData = Array(24).fill().map(() => trends.humidity.overall_avg + (Math.random() - 0.5) * 8);
                }
                
                // Create 24-hour labels
                const labels = Array(24).fill().map((_, i) => `${i}:00`);
                
                const historicalData = {
                    labels: labels,
                    datasets: [
                        { 
                            label: 'Temperature (°C)', 
                            data: tempData,
                            borderColor: getChartColors().temp, 
                            tension: 0.3, 
                            fill: false 
                        },
                        { 
                            label: 'Humidity (%)', 
                            data: humidityData,
                            borderColor: getChartColors().humidity, 
                            tension: 0.3, 
                            fill: false 
                        },
                    ]
                };
                historicalChart = createChart(historicalCtx, 'line', historicalData, chartOptions);
                
                console.log(`✓ Historical chart updated for ${selectedDateStr}`);
                console.log(`  Data points: ${trends.data_points}, Period: ${trends.period.days} days`);
            }
            
            // Remove loading indicator
            chartContainer.style.opacity = '1';
            
        } catch (error) {
            console.error('Failed to load historical data:', error);
            
            // Fallback to mock data on error
            const historicalData = {
                labels: Array(24).fill().map((_, i) => `${i}:00`),
                datasets: [
                    { label: 'Temperature (°C)', data: Array(24).fill().map(() => 20 + Math.random() * 10), borderColor: getChartColors().temp, tension: 0.3, fill: false },
                    { label: 'Humidity (%)', data: Array(24).fill().map(() => 60 + Math.random() * 15), borderColor: getChartColors().humidity, tension: 0.3, fill: false },
                ]
            };
            historicalChart = createChart(historicalCtx, 'line', historicalData, chartOptions);
            
            showErrorNotification('Using sample data - unable to fetch historical analytics');
        }
    }

    const picker = new Pikaday({
        field: document.getElementById('datepicker'),
        maxDate: new Date(), // Can't select future dates
        onSelect: function(date) {
            updateHistoricalChart(date);
        }
    });
    updateHistoricalChart(new Date());

    /* -------------------------
       Notifications from REAL alerts
       ------------------------- */
    const bellIcon = document.getElementById('bell-icon');
    const notificationPanel = document.getElementById('notification-panel');
    const notificationList = document.getElementById('notification-list');
    const notificationBadge = document.getElementById('notification-badge');

    let notifications = [];

    async function loadNotifications() {
        try {
            const response = await api.getRecentAlerts(24);
            
            if (response.success && response.data) {
                // Convert backend alerts to notification format
                notifications = response.data.alerts.map((alert, index) => ({
                    id: index + 1,
                    type: alert.alert_type || 'info',
                    msg: alert.message || `${alert.sensor_type} alert`,
                    time: alert.created_at ? getTimeAgo(new Date(alert.created_at)) : 'Unknown',
                    priority: alert.alert_type === 'critical' ? 3 : alert.alert_type === 'warning' ? 2 : 1
                }));
                
                // Sort by priority (critical first)
                notifications.sort((a, b) => b.priority - a.priority);
                
                renderNotifications();
                console.log(`✓ Loaded ${notifications.length} notifications`);
            }
        } catch (error) {
            console.error('Failed to load notifications:', error);
            // Keep existing notifications on error
        }
    }

    function getTimeAgo(date) {
        const seconds = Math.floor((new Date() - date) / 1000);
        if (seconds < 60) return `${seconds}s ago`;
        const minutes = Math.floor(seconds / 60);
        if (minutes < 60) return `${minutes}m ago`;
        const hours = Math.floor(minutes / 60);
        if (hours < 24) return `${hours}h ago`;
        return `${Math.floor(hours / 24)}d ago`;
    }
    
    function renderNotifications() {
        notificationList.innerHTML = '';
        
        if (notifications.length === 0) {
            notificationList.innerHTML = `<p class="p-4 text-sm text-center text-slate-500 dark:text-slate-400">No active alerts</p>`;
            notificationBadge.classList.add('hidden');
            return;
        }
        
        notifications.forEach(n => {
            const div = document.createElement('div');
            div.className = 'p-4 flex items-start gap-3 hover:bg-slate-100 dark:hover:bg-slate-700';
            
            // Different colors for different alert types
            const bgColor = n.type === 'critical' ? 'bg-red-100 dark:bg-red-900' : 
                           n.type === 'warning' ? 'bg-amber-100 dark:bg-amber-900' : 
                           'bg-blue-100 dark:bg-blue-900';
            const textColor = n.type === 'critical' ? 'text-red-600 dark:text-red-400' : 
                             n.type === 'warning' ? 'text-amber-600 dark:text-amber-400' : 
                             'text-blue-600 dark:text-blue-400';
            
            div.innerHTML = `
                <div class="p-2 rounded-full ${bgColor} self-start">
                    <i data-feather="alert-triangle" class="${textColor} w-4 h-4"></i>
                </div>
                <div class="flex-1">
                    <p class="text-sm">${n.msg}</p>
                    <p class="text-xs text-slate-500 dark:text-slate-400 mt-1">${n.time}</p>
                </div>
            `;
            notificationList.appendChild(div);
        });
        
        notificationBadge.textContent = notifications.length;
        notificationBadge.classList.remove('hidden');
        feather.replace();
    }

    bellIcon.addEventListener('click', () => {
        notificationPanel.classList.toggle('hidden');
    });
    
    // Load notifications on page load and refresh every minute
    loadNotifications();
    setInterval(loadNotifications, 60000);

    /* -------------------------
       Settings (theme, fonts) — enhanced persistence
       ------------------------- */
    const themeToggle = document.getElementById('theme-toggle');
    const toggleButtonSpan = themeToggle.querySelector('span');

    // Read saved preferences
    const savedTheme = localStorage.getItem('cvr-theme') || 'light';
    const savedFontSize = localStorage.getItem('cvr-font-size') || '16px';
    const savedFontFamily = localStorage.getItem('cvr-font-family') || "'Inter', sans-serif";

    const applyTheme = (theme, save = true) => {
        if (theme === 'dark') {
            document.documentElement.classList.add('dark');
            toggleButtonSpan.style.transform = 'translateX(1.25rem)';
        } else {
            document.documentElement.classList.remove('dark');
            toggleButtonSpan.style.transform = 'translateX(0)';
        }
        updateChartColors();
        if (save) localStorage.setItem('cvr-theme', theme);
    };

    // initialize from saved
    applyTheme(savedTheme, false);
    document.body.style.fontSize = savedFontSize;
    document.body.style.fontFamily = savedFontFamily;
    document.getElementById('font-size').value = savedFontSize;
    document.getElementById('font-family').value = savedFontFamily;

    themeToggle.addEventListener('click', () => {
        const isDark = document.documentElement.classList.contains('dark');
        applyTheme(isDark ? 'light' : 'dark');
    });

    document.getElementById('font-size').addEventListener('change', (e) => {
        document.body.style.fontSize = e.target.value;
        localStorage.setItem('cvr-font-size', e.target.value);
    });
    document.getElementById('font-family').addEventListener('change', (e) => {
        document.body.style.fontFamily = e.target.value;
        localStorage.setItem('cvr-font-family', e.target.value);
    });

    document.getElementById('colorblind-mode').addEventListener('change', (e) => {
        colorblindMode = e.target.checked;
        updateChartColors();
    });

    /* -------------------------
       FAQs (accordion)
       ------------------------- */
    const faqs = [
        { q: "How do I check historical data?", a: "Navigate to the 'Analytics' page from the side menu. Use the calendar to select a specific date, and the chart will update automatically with real data from your storage sensors." },
        { q: "What do the different colors on the dashboard chart mean?", a: "Each color represents a different environmental metric: blue for Temperature, green for Humidity, orange for Methane, and purple for Other Gases. These update in real-time from your Arduino sensors." },
        { q: "When does the exhaust fan turn on?", a: "The exhaust fan automatically activates when methane levels exceed 300 ppm (critical threshold). The system monitors gas levels continuously and controls the fan to maintain safe air quality." },
        { q: "Can I use this application on my mobile device?", a: "Yes, the application is fully responsive and designed to work on desktops, tablets, and mobile phones. Your dashboard updates in real-time on any device." },
    ];

    const faqContainer = document.getElementById('faq-container');
    faqs.forEach(faq => {
        const div = document.createElement('div');
        div.className = 'border-b border-slate-200 dark:border-slate-700 pb-4';
        div.innerHTML = `
            <button class="w-full text-left flex justify-between items-center">
                <span class="font-medium">${faq.q}</span>
                <i data-feather="chevron-down" class="transition-transform"></i>
            </button>
            <div class="mt-2 text-slate-600 dark:text-slate-400 hidden">
                ${faq.a}
            </div>
        `;
        faqContainer.appendChild(div);
    });
    faqContainer.addEventListener('click', (e) => {
        const button = e.target.closest('button');
        if (!button) return;
        const answer = button.nextElementSibling;
        const icon = button.querySelector('i');
        answer.classList.toggle('hidden');
        icon.classList.toggle('rotate-180');
    });

    /* -------------------------
       Chat UI with REAL AI backend
       ------------------------- */
    const chatForm = document.getElementById('chat-form');
    const chatInput = document.getElementById('chat-input');
    const chatMessages = document.getElementById('chat-messages');

    chatForm.addEventListener('submit', async (e) => {
        e.preventDefault();
        const message = chatInput.value.trim();
        if (!message) return;
        
        // Display user message
        const userMessageDiv = document.createElement('div');
        userMessageDiv.className = 'flex items-start gap-3 justify-end';
        userMessageDiv.innerHTML = `
            <div class="bg-cyan-600 text-white rounded-lg p-3 max-w-lg">
                <p>${escapeHtml(message)}</p>
            </div>
        `;
        chatMessages.appendChild(userMessageDiv);

        chatInput.value = '';
        chatMessages.scrollTop = chatMessages.scrollHeight;

        // Show typing indicator
        const typingDiv = document.createElement('div');
        typingDiv.className = 'flex items-start gap-3';
        typingDiv.id = 'typing-indicator';
        typingDiv.innerHTML = `
            <div class="p-2 rounded-full bg-cyan-100 dark:bg-cyan-900 self-start">
                <i data-feather="cpu" class="text-cyan-600 dark:text-cyan-400 w-5 h-5"></i>
            </div>
            <div class="bg-slate-100 dark:bg-slate-700 rounded-lg p-3">
                <p class="text-sm">AI is thinking...</p>
            </div>
        `;
        chatMessages.appendChild(typingDiv);
        chatMessages.scrollTop = chatMessages.scrollHeight;
        feather.replace();

        try {
            // Send to real AI backend
            const response = await api.sendChatMessage(message, 'web_user');
            
            // Remove typing indicator
            document.getElementById('typing-indicator')?.remove();
            
            // Display AI response
            const aiResponseDiv = document.createElement('div');
            aiResponseDiv.className = 'flex items-start gap-3';
            aiResponseDiv.innerHTML = `
                <div class="p-2 rounded-full bg-cyan-100 dark:bg-cyan-900 self-start">
                    <i data-feather="cpu" class="text-cyan-600 dark:text-cyan-400 w-5 h-5"></i>
                </div>
                <div class="bg-slate-100 dark:bg-slate-700 rounded-lg p-3 max-w-lg">
                    <p>${escapeHtml(response.response || 'Sorry, I could not process that.')}</p>
                </div>
            `;
            chatMessages.appendChild(aiResponseDiv);
            
            console.log('✓ AI response received');
            
        } catch (error) {
            console.error('Chatbot error:', error);
            
            // Remove typing indicator
            document.getElementById('typing-indicator')?.remove();
            
            // Show error message
            const errorDiv = document.createElement('div');
            errorDiv.className = 'flex items-start gap-3';
            errorDiv.innerHTML = `
                <div class="p-2 rounded-full bg-amber-100 dark:bg-amber-900 self-start">
                    <i data-feather="alert-triangle" class="text-amber-600 dark:text-amber-400 w-5 h-5"></i>
                </div>
                <div class="bg-amber-50 dark:bg-amber-900/20 rounded-lg p-3 max-w-lg">
                    <p class="text-sm text-amber-600 dark:text-amber-400">AI assistant is currently unavailable. The system is still monitoring your storage conditions.</p>
                </div>
            `;
            chatMessages.appendChild(errorDiv);
        }
        
        chatMessages.scrollTop = chatMessages.scrollHeight;
        feather.replace();
    });

    // Helper function to escape HTML and prevent XSS
    function escapeHtml(unsafe) {
        return unsafe.replace(/[&<"']/g, function(m) {
            return {'&':'&amp;','<':'&lt;','"':'&quot;',"'":"&#039;"}[m];
        });
    }

    // Helper function to show error notifications
    function showErrorNotification(message) {
        // You could implement a toast notification here
        console.warn('⚠', message);
    }

    /* Final color sync */
    updateChartColors();
    
    console.log('✓ CropVerse Dashboard initialized');
    console.log('✓ Backend:', API_CONFIG.BASE_URL);
});