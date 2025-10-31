// File: frontend/src/components/PageHeader.jsx

import React, { useState } from 'react';
// FIX: Remove LogoIcon, import LogoSVG
import { MenuIcon, LogoutIcon } from './Icons.jsx';
import LogoSVG from './LogoSVG.jsx'; // <-- New Logo Import
// Assuming AuthContext is correct, keep these imports
import { useAuth } from '../context/AuthContext.jsx';
import { signOutUser } from '../firebase/auth.js';

const PageHeader = ({ onMenuClick }) => {
  const { currentUser } = useAuth();
  const [showConfirm, setShowConfirm] = useState(false);

  const handleLogoutClick = () => {
    setShowConfirm(true);
  };

  const handleConfirmLogout = () => {
    // Assuming signOutUser() is defined in your auth file and works
    signOutUser(); 
    setShowConfirm(false);
  };

  const handleCancel = () => {
    setShowConfirm(false);
  };

  return (
    <header className="py-5 px-4 text-center flex-shrink-0 bg-[#171717]">
      <div className="flex items-center justify-center relative">
        <button
          onClick={onMenuClick}
          className="md:hidden absolute left-4 p-1 text-[#A0A0A0] hover:text-[#F1F1F1]"
          aria-label="Open menu"
        >
          <MenuIcon />
        </button>

        <div className="flex flex-col items-center relative w-full">
          <div className="flex items-center justify-center gap-3 text-2xl font-semibold text-[#F1F1F1]">
            {/* FIX: Use the new LogoSVG component */}
            <LogoSVG width="26px" height="26px" /> 
            <span>OpenSchema</span>
          </div>
          <p className="mt-2 text-base text-[#A0A0A0] px-4">
            Chat with me to generate, evaluate and tune synthetic datasets.
          </p>
          
          {/* Logout Button Logic (Your existing code) */}
          {currentUser && (
            <div className="absolute right-4 top-1/2 -translate-y-1/2">
              {!showConfirm ? (
                <button
                  onClick={handleLogoutClick}
                  className="flex items-center justify-center gap-2 px-4 py-3 border border-red-600 text-red-500 hover:bg-red-600 hover:text-white rounded-xl font-medium transition-all shadow-sm hover:shadow-md active:scale-95"
                >
                  <LogoutIcon />
                  <span>Logout</span>
                </button>
              ) : (
                <div className="flex items-center gap-2 px-4 py-3 border border-red-600 bg-red-600 rounded-xl shadow-md">
                  <span className="text-white text-sm font-medium">Confirm?</span>
                  <button
                    onClick={handleConfirmLogout}
                    className="px-3 py-1 bg-white text-red-600 rounded-lg text-sm font-semibold hover:bg-red-50 transition-colors"
                  >
                    Yes
                  </button>
                  <button
                    onClick={handleCancel}
                    className="px-3 py-1 bg-transparent text-white border border-white rounded-lg text-sm font-semibold hover:bg-white/10 transition-colors"
                  >
                    Cancel
                  </button>
                </div>
              )}
            </div>
          )}
        </div>
      </div>
    </header>
  );
};

export default PageHeader;