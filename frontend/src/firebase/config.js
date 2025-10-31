// Import the functions you need from the SDKs you need
import { initializeApp } from "firebase/app";
import { getAuth } from "firebase/auth";

// Your web app's Firebase configuration
// Replace these with your Firebase project configuration
// For Firebase JS SDK v7.20.0 and later, measurementId is optional
const firebaseConfig = {
  apiKey: "AIzaSyAMAzFA3XrbkR463BzDxs2RBHSYfgPyFFQ",
  authDomain: "sudo-su-d3795.firebaseapp.com",
  projectId: "sudo-su-d3795",
  storageBucket: "sudo-su-d3795.firebasestorage.app",
  messagingSenderId: "1032892860909",
  appId: "1:1032892860909:web:9594a7eb260c2bb7c2bfe4",
  measurementId: "G-G185CZK70F"
};

// Initialize Firebase
const app = initializeApp(firebaseConfig);
export const auth = getAuth(app);
export default app;