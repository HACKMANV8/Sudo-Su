import React, { useState } from 'react';
import { LogoIcon } from './Icons.jsx';
import { signIn, signUp } from '../firebase/auth';

const LoginModal = ({ onLoginSuccess }) => {
  const [isLoginView, setIsLoginView] = useState(true);
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');
    setLoading(true);

    if (!isLoginView && password !== confirmPassword) {
      setError('Passwords do not match');
      setLoading(false);
      return;
    }

    try {
      const { user, error } = isLoginView
        ? await signIn(email, password)
        : await signUp(email, password);

      if (error) {
        setError(error);
      } else if (user) {
        onLoginSuccess();
      }
    } catch (err) {
      setError('An error occurred. Please try again.');
    } finally {
      setLoading(false);
    }
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
          {error && (
            <div className="text-red-500 text-sm mb-4">
              {error}
            </div>
          )}

          <div className="input-group">
            <label htmlFor="email">Email</label>
            <input
              type="email"
              id="email"
              placeholder="you@example.com"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              required
            />
          </div>
          <div className="input-group">
            <label htmlFor="password">Password</label>
            <input
              type="password"
              id="password"
              placeholder="••••••••"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              required
            />
          </div>

          {!isLoginView && (
            <div className="input-group">
              <label htmlFor="confirm-password">Confirm Password</label>
              <input
                type="password"
                id="confirm-password"
                placeholder="••••••••"
                value={confirmPassword}
                onChange={(e) => setConfirmPassword(e.target.value)}
                required
              />
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


