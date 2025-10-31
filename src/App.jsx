import React, { useState } from 'react';
// FIX: Added .jsx extension to imports for explicit path resolution
import PageHeader from './components/PageHeader.jsx';
import Sidebar from './components/Sidebar.jsx';
import ChatArea from './components/ChatArea.jsx';

// This is the main component that assembles your layout
export default function App() {
  const [isSidebarOpen, setIsSidebarOpen] = useState(false);

  return (
    <div className="h-screen w-screen flex flex-col bg-[#171717]">
      <PageHeader onMenuClick={() => setIsSidebarOpen(true)} />
      
      <hr className="border-none h-px bg-[#2A2931] flex-shrink-0" />
      
      <div className="flex-1 flex overflow-hidden">
        <Sidebar isOpen={isSidebarOpen} onClose={() => setIsSidebarOpen(false)} />
        <ChatArea />
      </div>
    </div>
  );
}