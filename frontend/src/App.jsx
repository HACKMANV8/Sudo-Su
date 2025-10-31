import React, { useState } from 'react';
import PageHeader from './components/PageHeader.jsx';
import Sidebar from './components/Sidebar.jsx';
import ChatArea from './components/ChatArea.jsx';
import LoginModal from './components/LoginModal.jsx'; // <-- IMPORT THE NEW COMPONENT

// This is the main component that assembles your layout
export default function App() {
  const [isSidebarOpen, setIsSidebarOpen] = useState(false);
  const [isAuthenticated, setIsAuthenticated] = useState(false); // <-- NEW STATE FOR LOGIN

  // This function will be called by the modal on a successful login
  const handleLogin = () => {
    setIsAuthenticated(true);
  };

  return (
    // This relative container is for the modal overlay
    <div className="relative h-screen w-screen">
      
      {/* --- Main App Container --- */}
      {/* This class dims the app when the modal is open */}
      <div 
        className={`h-full w-full flex flex-col bg-[#171717] ${!isAuthenticated ? 'app-dimmed' : ''}`}
      >
        <PageHeader onMenuClick={() => setIsSidebarOpen(true)} />
        
        <hr className="border-none h-px bg-[#2A2931] flex-shrink-0" />
        
        <div className="flex-1 flex overflow-hidden">
          <Sidebar isOpen={isSidebarOpen} onClose={() => setIsSidebarOpen(false)} />
          <ChatArea />
        </div>
      </div>

      {/* --- Modal Overlay --- */}
      {/* The modal is rendered on top of the app until the user is authenticated */}
      {!isAuthenticated && (
        <LoginModal onLoginSuccess={handleLogin} />
      )}
    </div>
  );
}