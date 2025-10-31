// File: frontend/src/components/LoginModal.jsx (Updated)

import React, { useState } from 'react';
// IMPORT CHANGE: Replace LogoIcon with LogoSVG
import LogoSVG from './LogoSVG.jsx'; // <--- UPDATED IMPORT
import LoadingDots from './LoadingDots.jsx';
import { signIn, signUp, sendPasswordReset } from '../firebase/auth.js';

const LoginModal = () => {
  const [isLoginView, setIsLoginView] = useState(true);
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);
  const [isResetView, setIsResetView] = useState(false);
  const [resetMessage, setResetMessage] = useState('');

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');
    setLoading(true);

    // Password reset flow
    if (isResetView) {
      try {
        const { error } = await sendPasswordReset(email);
        if (error) {
          setError(error);
        } else {
          // Generic success message for security
          setResetMessage('If an account exists for that email, a reset link has been sent.');
        }
      } catch (err) {
        setError('An error occurred. Please try again.');
      } finally {
        setLoading(false);
      }
      return;
    }

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
      }
      // Assuming successful login/signup would navigate away,
      // or a message would be sent to the extension here.
      // (This logic needs to be added if not already handled by a parent component)

    } catch (err) {
      setError('An error occurred. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="modal-overlay">
      <div className="modal-content">
        <div className="flex justify-center mb-6">
          {/* USAGE CHANGE: Replace LogoIcon with LogoSVG */}
          <LogoSVG width="60px" height="60px" /> {/* Adjust size as needed */}
        </div>

        <h2 className="modal-title">
          {isResetView ? 'Reset Password' : isLoginView ? 'Welcome Back' : 'Create Account'}
        </h2>

        <form onSubmit={handleSubmit}>
          {error && (
            <div className="text-red-500 text-sm mb-4">
              {error}
            </div>
          )}

          {resetMessage && (
            <div className="text-green-500 text-sm mb-4">
              {resetMessage}
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

          {!isResetView && (
            <>
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
            </>
          )}

          <button 
            type="submit" 
            className="modal-submit-btn flex items-center justify-center gap-2"
            disabled={loading}
          >
            {loading ? (
              <>
                <LoadingDots size="w-2 h-2" color="bg-white" />
                <span>Loading...</span>
              </>
            ) : (
              isResetView ? 'Send Reset Email' : isLoginView ? 'Login' : 'Sign Up'
            )}
          </button>
        </form>

        <p className="modal-toggle-text">
          {isResetView ? (
            <>
              Need to login?{' '}
              <button
                type="button"
                onClick={() => { setIsResetView(false); setIsLoginView(true); setResetMessage(''); setError(''); }}
                className="modal-toggle-btn"
              >
                Back to Login
              </button>
            </>
          ) : (
            <>
              {isLoginView ? "Don't have an account?" : "Already have an account?"}
              <button
                type="button"
                onClick={() => { setIsLoginView(!isLoginView); setError(''); }}
                className="modal-toggle-btn"
              >
                {isLoginView ? 'Sign Up' : 'Login'}
              </button>
              {isLoginView && (
                <button
                  type="button"
                  onClick={() => { setIsResetView(true); setError(''); setResetMessage(''); }}
                  className="modal-toggle-btn"
                >
                  Forgot password?
                </button>
              )}
            </>
          )}
        </p>
      </div>
    </div>
  );
};

export default LoginModal;