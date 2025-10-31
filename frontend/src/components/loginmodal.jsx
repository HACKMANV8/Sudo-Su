import React, { useState } from 'react';
// FIX: Re-adding the .jsx extension to be explicit for the bundler
import { LogoIcon } from './Icons.jsx';

// This is the modal component
const LoginModal = ({ onLoginSuccess }) => {
  const [isLoginView, setIsLoginView] = useState(true);

  // In a real app, this would handle API calls.
  // For the hackathon, we just call the success function.
  const handleSubmit = (e) => {
    e.preventDefault();
    onLoginSuccess();
  };

  return (
    // Full-screen dark overlay
    <div className="modal-overlay">
      
      {/* Modal Content Box */}
      <div className="modal-content">
        {/* The close button has been removed to force login/signup */}

        <div className="flex justify-center mb-6">
          <LogoIcon />
        </div>
        
        <h2 className="modal-title">
          {isLoginView ? 'Welcome Back' : 'Create Account'}
        </h2>
        
        <form onSubmit={handleSubmit}>
          {/* Form fields */}
          <div className="input-group">
            <label htmlFor="email">Email</label>
            <input type="email" id="email" placeholder="you@example.com" required />
          </div>
          <div className="input-group">
            <label htmlFor="password">Password</label>
            <input type="password" id="password" placeholder="••••••••" required />
          </div>

          {!isLoginView && (
            <div className="input-group">
              <label htmlFor="confirm-password">Confirm Password</label>
              <input type="password" id="confirm-password" placeholder="••••••••" required />
            </div>
          )}

          {/* Submit Button */}
          <button type="submit" className="modal-submit-btn">
            {isLoginView ? 'Login' : 'Sign Up'}
          </button>
        </form>

        {/* Toggle between Login / Sign Up */}
        <p className="modal-toggle-text">
          {isLoginView ? "Don't have an account?" : "Already have an account?"}
          <button 
            type="button"
            onClick={() => setIsLoginView(!isLoginView)}
            className="modal-toggle-btn"
          >
            {isLoginView ? 'Sign Up' : 'Login'}
          </button>
        </p>
      </div>
    </div>
  );
};

export default LoginModal;


