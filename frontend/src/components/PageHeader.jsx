import React from 'react';
import { LogoIcon, MenuIcon } from './Icons.jsx';
import { useAuth } from '../context/AuthContext.jsx';
import { signOutUser } from '../firebase/auth.js';

const PageHeader = ({ onMenuClick }) => {
  const { currentUser } = useAuth();
  return (
    <header className="py-5 px-4 text-center flex-shrink-0 bg-[#171717]">
      <div className="flex items-center justify-center relative">
        {/* Mobile Menu Button (Hamburger) */}
        <button
          onClick={onMenuClick}
          className="md:hidden absolute left-4 p-1 text-[#A0A0A0] hover:text-[#F1F1F1]"
          aria-label="Open menu"
        >
          <MenuIcon />
        </button>

        {/* Logo and Tagline */}
        <div className="flex flex-col items-center relative w-full">
          <div className="flex items-center justify-center gap-3 text-2xl font-semibold text-[#F1F1F1]">
            <LogoIcon />
            <span>OpenSchema</span>
          </div>
          <p className="mt-2 text-base text-[#A0A0A0] px-4">
            Chat with me to generate, evaluate and tune synthetic datasets.
          </p>
          {currentUser && (
            <button
              onClick={signOutUser}
              className="absolute right-4 top-1/2 -translate-y-1/2 px-5 py-2 text-sm text-white bg-red-600 hover:bg-red-700 rounded-2xl font-semibold transition-all shadow-md hover:shadow-lg active:scale-95"
            >
              Logout
            </button>
          )}
        </div>
      </div>
    </header>
  );
};

export default PageHeader;