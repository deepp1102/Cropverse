import { collection, onSnapshot, query, orderBy } from "https://www.gstatic.com/firebasejs/9.22.1/firebase-firestore.js";
import { db } from "./firebase-config.js";

const sensorsCol = collection(db, "sensors");
const sensorsQuery = query(sensorsCol, orderBy("timestamp", "desc"));

export function startRealtimeListeners(onSensorsUpdate, onDashboardUpdate) {
  return onSnapshot(sensorsQuery, (snapshot) => {
    const sensors = [];
    snapshot.forEach(doc => sensors.push({ id: doc.id, ...doc.data() }));
    if (typeof onSensorsUpdate === "function") onSensorsUpdate(sensors);
    if (typeof onDashboardUpdate === "function") onDashboardUpdate(sensors);
  }, (err) => {
    console.error("Firestore listener error:", err);
  });
}