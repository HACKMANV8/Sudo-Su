import React from 'react';
import { LogoIcon, MenuIcon } from './Icons.jsx';

// This is the top banner with the title and tagline
const PageHeader = ({ onMenuClick }) => {
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
        <div className="flex flex-col items-center">
          <div className="flex items-center justify-center gap-3 text-2xl font-semibold text-[#F1F1F1]">
            <LogoIcon />
            <span>OpenSchema</span>
          </div>
          <p className="mt-2 text-base text-[#A0A0A0] px-4">
            Chat with me to generate, evaluate and tune synthetic datasets.
          </p>
        </div>
      </div>
    </header>
  );
};

export default PageHeader;