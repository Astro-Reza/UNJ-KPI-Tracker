// Firebase Configuration and Initialization
// Note: Using CDN imports for browser compatibility without a bundler (Vite/Webpack)
import { initializeApp } from "https://www.gstatic.com/firebasejs/10.8.0/firebase-app.js";
import { getAnalytics } from "https://www.gstatic.com/firebasejs/10.8.0/firebase-analytics.js";

const firebaseConfig = {
  apiKey: "AIzaSyAxV35KihzneIPIostBxYDqGcLZ2XNC0EA",
  authDomain: "kpi-dashboard-5795b.firebaseapp.com",
  projectId: "kpi-dashboard-5795b",
  storageBucket: "kpi-dashboard-5795b.firebasestorage.app",
  messagingSenderId: "186470479528",
  appId: "1:186470479528:web:03b646916d81341a59349d",
  measurementId: "G-JCTKSFS5BQ"
};

// Initialize Firebase
const app = initializeApp(firebaseConfig);
const analytics = getAnalytics(app);

console.log("Firebase initialized successfully");

export { app, analytics };
