import React, { useState } from 'react';
import PageHeader from './components/PageHeader.jsx';
import Sidebar from './components/Sidebar.jsx';
import ChatArea from './components/ChatArea.jsx';
import LoginModal from './components/loginmodal.jsx';
import { AuthProvider } from './context/AuthContext.jsx';
import { useAuth } from './context/AuthContext.jsx';

// Main App Content Component
function AppContent() {
  const [isSidebarOpen, setIsSidebarOpen] = useState(false);
  const { currentUser } = useAuth();
  const [activeChatId, setActiveChatId] = useState(null);

  return (
    <div className="relative h-screen w-screen">
      <div
        className={`h-full w-full flex flex-col bg-[#171717] ${!currentUser ? 'app-dimmed' : ''}`}
      >
        <PageHeader onMenuClick={() => setIsSidebarOpen(true)} />

        <hr className="border-none h-px bg-[#2A2931] flex-shrink-0" />

        <div className="flex-1 flex overflow-hidden">
          <Sidebar
            isOpen={isSidebarOpen}
            onClose={() => setIsSidebarOpen(false)}
            activeChatId={activeChatId}
            onSelectChat={(id) => setActiveChatId(id)}
          />
          <ChatArea activeChatId={activeChatId} />
        </div>
      </div>

      {!currentUser && <LoginModal />}
    </div>
  );
}

// Main App Component that wraps everything with AuthProvider
function App() {
  return (
    <AuthProvider>
      <AppContent />
    </AuthProvider>
  );
}

export default App;