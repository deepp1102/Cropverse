import { initializeApp } from "https://www.gstatic.com/firebasejs/9.1.3/firebase-app.js";
import { getFirestore, onSnapshot } from "https://www.gstatic.com/firebasejs/9.1.3/firebase-firestore.js";

const firebaseConfig = {
  apiKey: "AIza...",
  authDomain: "cropverse-sih.firebaseapp.com",
  projectId: "cropverse-sih",
  storageBucket: "cropverse-sih.appspot.com",
  messagingSenderId: "123456789",
  appId: "1:123456789:web:abcdef"
};


// Initialize Firebase
const app = initializeApp(firebaseConfig);
console.log("Firebase initialized with projectId:", firebaseConfig.projectId);
export const db = getFirestore(app);

// API Base URL (change for production)
const API_BASE_URL = 'http://localhost:8080/api';

console.log('✅ Firebase initialized');
console.log('✅ API URL:', API_BASE_URL);



// filepath: [realtime-listeners.js](http://_vscodecontentref_/0)
import { db } from "./firebase-config.js";
import { collection, query, onSnapshot } from "https://www.gstatic.com/firebasejs/9.1.3/firebase-firestore.js";

const sensorsQuery = query(collection(db, "sensors"));

export function startRealtimeListeners(onSensorsUpdate, onDashboardUpdate) {
  console.log("Starting realtime listeners for 'sensors' collection...");
  return onSnapshot(sensorsQuery, (snapshot) => {
    const sensors = [];
    snapshot.forEach(doc => sensors.push({ id: doc.id, ...doc.data() }));
    console.log("Firestore snapshot received. docs:", snapshot.size);
    if (typeof onSensorsUpdate === "function") onSensorsUpdate(sensors);
    if (typeof onDashboardUpdate === "function") onDashboardUpdate(sensors);
  }, (err) => {
    console.error("Firestore listener error:", err);
  });
}


// filepath: c:\Users\atharv\Desktop\SIH_2025\public\script.js
import { startRealtimeListeners } from "./realtime-listeners.js";

function handleSensorsUpdate(sensors) {
  console.log("handleSensorsUpdate() — sensors:", sensors.length);
  if (typeof renderSensors === "function") renderSensors(sensors);
  if (typeof updateCharts === "function") updateCharts(sensors);
}

function handleDashboardUpdate(sensors) {
  console.log("handleDashboardUpdate() — computing metrics...");
  if (typeof computeMetricsFromSensors === "function" && typeof renderDashboard === "function") {
    const metrics = computeMetricsFromSensors(sensors);
    renderDashboard(metrics);
  }
}

function initApp() {
  console.log("App init starting...");
  startRealtimeListeners(handleSensorsUpdate, handleDashboardUpdate);
  console.log("Realtime listeners attached.");
}

initApp();