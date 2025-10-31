import React from 'react';

// Modern loading dots component with bounce animation
const LoadingDots = ({ size = 'w-2 h-2', color = 'bg-[#9333ea]', className = '' }) => {
  return (
    <div className={`flex items-center justify-center gap-1.5 ${className}`}>
      <div className={`animate-bounce-dot ${size} ${color} rounded-full`}></div>
      <div className={`animate-bounce-dot ${size} ${color} rounded-full`}></div>
      <div className={`animate-bounce-dot ${size} ${color} rounded-full`}></div>
    </div>
  );
};

export default LoadingDots;

