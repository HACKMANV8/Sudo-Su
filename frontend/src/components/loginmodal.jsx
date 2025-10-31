import React, { useState } from 'react';
import { LogoIcon } from './Icons.jsx';
import { signIn, signUp, sendPasswordReset } from '../firebase/auth';

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
          {isResetView ? 'Reset Password' : isLoginView ? 'Welcome Back' : 'Create Account'}
        </h2>

        <form onSubmit={handleSubmit}>
          {/* Form fields */}
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

          {/* Email field (used by login, signup, and reset) */}
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

          {/* Show password fields only for login/signup */}
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

          {/* Submit Button */}
          <button type="submit" className="modal-submit-btn">
            {isResetView ? 'Send Reset Email' : isLoginView ? 'Login' : 'Sign Up'}
          </button>
        </form>

        {/* Toggle between Login / Sign Up */}
        <p className="modal-toggle-text">
          {/* When in reset view show a back-to-login button */}
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
              {/* Forgot password link shown only on login view */}
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


