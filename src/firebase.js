import { initializeApp, getApps } from "firebase/app";
import { getAuth } from "firebase/auth";

const firebaseConfig = {
  apiKey: "AIzaSyBKo1ARTlZogol02rbGuEUVFYy9kx50hAU",
  authDomain: "sih25-e0dad.firebaseapp.com",
  projectId: "sih25-e0dad",
  storageBucket: "sih25-e0dad.appspot.com",
  messagingSenderId: "780946494287",
  appId: "1:780946494287:web:e583c8cf507bc445e92b3a",
  measurementId: "G-2XVV6FMMTP"
};

// Initialize Firebase only once
const app = !getApps().length ? initializeApp(firebaseConfig) : getApps()[0];
const auth = getAuth(app);

// Do NOT set up recaptchaVerifier globally here. Do it in your component when needed.

export { auth };
