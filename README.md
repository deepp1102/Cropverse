# CropVerse 🌱

> **Smart Environment Monitoring & Control System for Precision Agriculture**

CropVerse is an integrated IoT solution combining intelligent hardware sensors with cloud-based analytics to revolutionize post-harvest storage management and reduce agricultural losses.

---

## 🔧 Hardware System (IoT Sensors & Control)

### 🌡️ Environmental Monitoring
Our Arduino-based sensor nodes continuously monitor critical storage parameters:
- **Temperature sensing** - Real-time thermal monitoring
- **Humidity tracking** - Precise RH% measurement with DHT22/industrial probes
- **Methane detection** - Early spoilage detection through gas analysis (MQ-x sensors)

### ⚡ Automated Control Systems
**Climate Control:**
- **Exhaust fans** (2× 300mm, 1000 CFM) - Automatic ventilation on threshold breach
- **Circulation fans** (4× 18" industrial) - Uniform air distribution
- **Dehumidifier** (50-90 L/day) - Moisture control during humid conditions
- **Humidifier** - Humidity boost when needed
- **Cooling blowers** (2× ducted) - Targeted cooling along storage trays
- **Heating system** - Temperature stabilization during cold periods

**Preservation Systems:**
- **Natural preservative release** - Controlled dispensing of eugenol & thymol sachets
- **PCO air sanitizer** - Photocatalytic oxidation (UV+TiO₂) for air purification

### 🏗️ Physical Infrastructure
- **8 galvanized steel racks** - Robust GI tubing/angle construction
- **40 FRP storage trays** - Corrosion-resistant, food-grade molded trays
- **Solar power system** (4-5 kW) - Sustainable energy generation (~20 kWh/day)
- **Battery backup** (10 kWh Li-ion) - Uninterrupted operation during outages

### 🔌 IoT Controller Architecture
- **Microcontroller**: Arduino/Raspberry Pi based control unit
- **Relay modules** - Automated device switching
- **Contactors & surge protection** - Safe electrical integration
- **WiFi/GSM connectivity** - Real-time data transmission to cloud
- **Compact JSON protocol** - Optimized for low-bandwidth IoT environments

### 🎯 Hardware Functionality
- Continuous 24/7 environmental monitoring
- Automatic ventilation control on threshold exceed
- Ideal humidity balance via coordinated dehumidifier + humidifier operation
- Smart cooling and heating for stable temperature maintenance
- Early spoilage detection through methane spike analysis
- Immediate removal of contaminated air to prevent chain-rotting
- Controlled release of natural preservatives
- Real-time alerts sent to farmer's phone
- Automated system that extends shelf life and reduces losses

---

## 💻 Software System (Cloud Platform & Analytics)

### 🔌 Secure Device Integration
- **Authenticated device onboarding** with unique credentials for each sensor node
- **Resilient data ingestion** tolerating intermittent connectivity and network issues
- **Batch and real-time submission** support for flexible deployment scenarios
- **Schema validation** ensuring data consistency and quality

### 📊 Real-Time Monitoring & Analytics Dashboard
- **Live dashboard updates** via Firebase real-time listeners
- **Time-series trend analysis** with configurable aggregation windows (minute/hour/day)
- **Statistical anomaly detection** using moving averages and z-score analysis
- **Cross-sensor correlation matrices** to identify environmental relationships
- **Pre-computed aggregations** for instant historical query performance
- **Interactive data visualization** - Charts, graphs, and trend indicators

### 🚨 Intelligent Alerting System
- **Multi-tier threshold configuration** (info/warning/critical severity levels)
- **Dynamic thresholding with hysteresis** to prevent alert flapping
- **Complete alert lifecycle management** (acknowledgement, escalation, auto-closure)
- **Multi-channel notifications** via email, SMS, and push notifications
- **Smart grouping and throttling** to reduce operator alert fatigue

### 🤖 AI-Powered Operational Assistant
- **Context-aware chatbot** seeded with current system state and recent events
- **Guided troubleshooting workflows** for rapid issue resolution
- **Natural language queries** for system data and historical trends
- **Proactive recommendations** based on detected patterns and anomalies

### 🔐 Enterprise Security & Access Control
- **Firebase Authentication integration** for secure user identity management
- **Role-based access control** (operator/admin) with granular permissions
- **Firestore security rules** enforcing data access policies
- **Comprehensive audit logging** for compliance and traceability

### 📈 Advanced Data Management
- **Sanity checks** filtering malformed or spurious readings
- **UTC timestamp normalization** with timezone-aware reporting
- **Optimized indexing strategy** balancing performance and cost
- **Configurable retention policies** for long-term data archival

---

## 🏗️ System Architecture

```
┌─────────────────────────────────────────────────────┐
│         IoT Hardware Layer (On-Site)                │
│  ┌──────────────────────────────────────────────┐  │
│  │  Arduino/RPi Controller                       │  │
│  │  - Temp/Humidity/Gas Sensors                  │  │
│  │  - Relay Controls (fans, HVAC, preservatives) │  │
│  │  - Solar Power + Battery Management           │  │
│  └─────────────────┬────────────────────────────┘  │
└────────────────────┼───────────────────────────────┘
                     │ HTTPS/JSON over WiFi/GSM
                     ▼
┌─────────────────────────────────────────────────────┐
│           Firebase Cloud Functions                  │
│  ┌──────────────┐  ┌─────────────┐  ┌───────────┐ │
│  │  Ingestion   │  │ Analytics   │  │  Alerts   │ │
│  │  Service     │  │ Service     │  │  Service  │ │
│  └──────┬───────┘  └──────┬──────┘  └─────┬─────┘ │
│         │                  │                │       │
│         └──────────────────┼────────────────┘       │
│                            ▼                        │
│                    ┌──────────────┐                 │
│                    │   Firestore  │                 │
│                    │   Database   │                 │
│                    └──────┬───────┘                 │
└───────────────────────────┼─────────────────────────┘
                            │ Real-time Sync
                            ▼
                ┌─────────────────────┐
                │   Web Dashboard     │
                │  - Live Monitoring  │
                │  - Analytics Views  │
                │  - AI Chatbot       │
                │  - Alert Management │
                └─────────────────────┘
```

---

## 🚀 Getting Started

### Hardware Setup

1. **Assemble the physical infrastructure**
   - Install galvanized steel racks and FRP trays
   - Mount all HVAC equipment (fans, dehumidifier, humidifier, blowers)
   - Set up solar panels and battery system

2. **Wire the IoT controller**
   - Connect all sensors to Arduino/RPi (temperature, humidity, methane)
   - Wire relay modules to control fans, HVAC, and preservation systems
   - Install contactors and surge protection
   - Configure WiFi/GSM connectivity

3. **Flash Arduino firmware**
   - Open `arduino/sensor_node/sensor_node.ino` in Arduino IDE
   - Configure WiFi credentials and API endpoint
   - Upload to your Arduino board

4. **Test hardware systems**
   - Verify all sensors are reading correctly
   - Test automated control responses (fan activation, etc.)
   - Confirm data transmission to cloud

### Backend Setup

1. **Clone the repository**
```bash
git clone https://github.com/yourusername/cropverse-firebase.git
cd cropverse-firebase
```

2. **Install dependencies**
```bash
cd functions
pip install -r requirements.txt
```

3. **Configure Firebase**
```bash
firebase login
firebase init
```

4. **Set environment variables**
```bash
cp .env.example .env.yaml
# Edit .env.yaml with your Firebase credentials and API keys
```

5. **Deploy to Firebase**
```bash
firebase deploy --only functions
```

### Frontend Setup

1. **Navigate to public directory**
```bash
cd public
```

2. **Configure Firebase**
Edit `js/firebase-config.js` with your Firebase project credentials:
```javascript
const firebaseConfig = {
  apiKey: "YOUR_API_KEY",
  authDomain: "YOUR_AUTH_DOMAIN",
  projectId: "YOUR_PROJECT_ID",
  // ...
};
```

3. **Serve locally**
```bash
firebase serve
```

4. **Deploy**
```bash
firebase deploy --only hosting
```

### Device Registration

1. **Register device in admin dashboard**
   - Use the admin dashboard to register new devices
   - Note the device credentials for configuration
   - Configure threshold parameters for your crop type


## 🧪 Testing & Development

### Simulate Sensor Data
```bash
python scripts/simulate_arduino.py --count 100 --interval 5
```

### Analyze Backend Health
```bash
python scripts/analyze_backend.py
```

### Seed Test Data
```bash
python scripts/seed_firestore.py --dataset sample_farm
```

### Run Tests
```bash
pytest tests/ --cov=functions
```

---

## 👥 Team

CropVerse is developed by a dedicated cross-functional team of six engineers and researchers:

| Role | Name | Responsibilities |
|------|------|------------------|
| 🔬 **Hardware Engineering & Research Specialist** | **Deep Kanade** | Sensor calibration and testing, environmental control system optimization, preservation technology research (eugenol, thymol, PCO), agricultural domain analysis, post-harvest storage methodologies, hardware component selection and procurement, prototype testing and validation |
| 📋 **Project Coordination & Agricultural Research** | **Rohit Rode** | Project management and strategic planning, stakeholder communication, agricultural domain research, farmer requirement analysis, market feasibility studies, documentation and presentation, compliance and regulatory research, team coordination and resource planning |
| 🔧 **Systems Integration Engineer** | **Rahul Mathe** | Hardware–software integration troubleshooting, system testing and quality assurance, research validation and experimentation, deployment assistance, cross-subsystem performance optimization, technical documentation, backup development support |




## 🤝 Contributing

We welcome contributions from the community! Please follow these steps:

1. Fork the repository
2. Create a feature branch 
3. Commit your changes 
4. Push to the branch 
5. Open a Pull Request


- Firebase and Google Cloud Platform teams
- Open-source community for invaluable tools and libraries
- Agricultural experts who provided domain guidance
