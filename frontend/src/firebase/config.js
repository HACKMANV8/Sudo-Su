// Import the functions you need from the SDKs you need
import { initializeApp } from "firebase/app";
import { getAuth, setPersistence, browserLocalPersistence } from "firebase/auth";
import { getFirestore } from 'firebase/firestore';
import { getDatabase } from 'firebase/database';

// Your web app's Firebase configuration
// Replace these with your Firebase project configuration
// For Firebase JS SDK v7.20.0 and later, measurementId is optional
const firebaseConfig = {
    apiKey: "AIzaSyAMAzFA3XrbkR463BzDxs2RBHSYfgPyFFQ",
    authDomain: "sudo-su-d3795.firebaseapp.com",
    projectId: "sudo-su-d3795",
    storageBucket: "sudo-su-d3795.firebasestorage.app",
    databaseURL: "https://sudo-su-d3795-default-rtdb.firebaseio.com",
    messagingSenderId: "1032892860909",
    appId: "1:1032892860909:web:9594a7eb260c2bb7c2bfe4",
    measurementId: "G-G185CZK70F"
};

// Initialize Firebase
const app = initializeApp(firebaseConfig);
export const auth = getAuth(app);

// Firestore (for chat history)
export const db = getFirestore(app);

// Realtime Database (for per-user chat buckets)
export const rtdb = getDatabase(app);

// Enable persistent auth state
setPersistence(auth, browserLocalPersistence)
    .catch((error) => {
        console.error("Auth persistence error:", error);
    });

export default app;