import React, { useState } from 'react';
import { NewChatIcon } from './Icons.jsx';

// This is the navigation panel on the left
const Sidebar = ({ isOpen, onClose }) => {
  const historyItems = [
    { id: 1, title: 'Ecommerce Data Generation' },
    { id: 2, title: 'Medical Dataset Evaluation' },
    { id: 3, title: 'Time-Series Anomaly Schema' },
  ];
  
  const [activeId, setActiveId] = useState(1);

  return (
    <>
      {/* Mobile Overlay: Dims the background when sidebar is open */}
      <div 
        className={`fixed inset-0 bg-black/50 z-10 md:hidden ${isOpen ? 'block' : 'hidden'}`}
        onClick={onClose}
      ></div>

      {/* Sidebar Content */}
      <aside 
        className={`fixed md:static top-0 left-0 w-64 h-full bg-[#171717] flex-shrink-0 p-4 flex flex-col border-r border-[#2A2931] z-20
                   transition-transform transform ${isOpen ? 'translate-x-0' : '-translate-x-full'} md:translate-x-0`}
      >
        <div className="flex items-center justify-end mb-6 h-9">
          <button 
            className="flex items-center justify-center p-2 border border-[#2A2931] rounded-lg text-[#A0A0A0] hover:border-[#F1F1F1] hover:text-[#F1F1F1]"
            aria-label="New session"
          >
            <NewChatIcon />
          </button>
        </div>
        <nav className="flex-grow overflow-y-auto">
          {historyItems.map(item => (
            <div
              key={item.id}
              className={`p-3 rounded-lg text-sm truncate cursor-pointer ${
                item.id === activeId 
                  ? 'bg-[#1A191F] text-[#F1F1F1]' 
                  : 'text-[#A0A0A0] hover:bg-[#1A191F] hover:text-[#F1F1F1]'
              }`}
              onClick={() => {
                setActiveId(item.id);
                onClose(); // Close sidebar on mobile after selection
              }}
            >
              {item.title}
            </div>
          ))}
        </nav>
      </aside>
    </>
  );
};

export default Sidebar;