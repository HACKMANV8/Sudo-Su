import React, { useState, useEffect } from 'react';
import { NewChatIcon, EditIcon, DeleteIcon } from './Icons.jsx';
import LoadingDots from './LoadingDots.jsx';
import { useAuth } from '../context/AuthContext.jsx';
import { subscribeToUserChats, createChatForUser, updateChatTitle, removeChatForUser } from '../firebase/rtdb.js';

// This is the navigation panel on the left
const ChatItem = ({ item, currentUser, activeChatId, onSelectChat, onClose }) => {
  const [isEditing, setIsEditing] = useState(false);
  const [editTitle, setEditTitle] = useState(item.title);

  const handleUpdate = async (e) => {
    e.preventDefault();
    if (!currentUser || editTitle.trim() === item.title) {
      setIsEditing(false);
      return;
    }
    const { error } = await updateChatTitle(currentUser.uid, item.id, editTitle.trim());
    if (error) {
      console.error('Failed to update chat title:', error);
    }
    setIsEditing(false);
  };

  return (
    <div
      key={item.id}
      className={`group p-3 rounded-lg text-sm flex items-center justify-between ${item.id === activeChatId
        ? 'bg-[#1A191F] text-[#F1F1F1]'
        : 'text-[#A0A0A0] hover:bg-[#1A191F] hover:text-[#F1F1F1]'
        }`}
    >
      {isEditing ? (
        <form onSubmit={handleUpdate} className="flex-1">
          <input
            type="text"
            value={editTitle}
            onChange={(e) => setEditTitle(e.target.value)}
            onBlur={handleUpdate}
            className="w-full bg-[#111014] text-[#F1F1F1] px-2 py-1 rounded border border-[#2A2931] focus:outline-none focus:border-[#9333ea]"
            autoFocus
          />
        </form>
      ) : (
        <div
          className="flex-1 truncate cursor-pointer"
          onClick={() => {
            if (typeof onSelectChat === 'function') onSelectChat(item.id);
            onClose();
          }}
        >
          {item.title}
        </div>
      )}

      <div className="flex gap-2 ml-2 opacity-0 group-hover:opacity-100 transition-opacity">
        <button
          onClick={(e) => {
            e.stopPropagation();
            setIsEditing(true);
          }}
          className="p-1.5 text-[#A0A0A0] hover:text-[#F1F1F1] transition-colors"
          aria-label="Rename chat"
        >
          <EditIcon />
        </button>
        <button
          onClick={async (e) => {
            e.stopPropagation();
            if (!currentUser || !confirm('Delete this chat?')) return;
            const { error } = await removeChatForUser(currentUser.uid, item.id);
            if (error) {
              console.error('Failed to delete chat:', error);
            }
          }}
          className="p-1.5 text-[#A0A0A0] hover:text-red-500 transition-colors"
          aria-label="Delete chat"
        >
          <DeleteIcon />
        </button>
      </div>
    </div>
  );
};

const Sidebar = ({ isOpen, onClose, activeChatId, onSelectChat }) => {
  const { currentUser } = useAuth();
  const [chats, setChats] = useState([]);
  const [isLoading, setIsLoading] = useState(true);
  // activeChatId is managed by parent (App). onSelectChat(uid) is used to notify parent.

  // Subscribe to user's chats from RTDB
  useEffect(() => {
    if (!currentUser) {
      setChats([]);
      setIsLoading(false);
      return;
    }

    const uid = currentUser.uid;
    setIsLoading(true);

    const unsubscribe = subscribeToUserChats(uid, (userChats) => {
      setChats(userChats || []);
      setIsLoading(false);

      // if parent hasn't selected a chat yet or the selected chat no longer exists
      if (typeof onSelectChat === 'function' && userChats && userChats.length > 0) {
        if (!activeChatId || !userChats.find(c => c.id === activeChatId)) {
          onSelectChat(userChats[0].id);
        }
      }
    });

    return () => {
      unsubscribe && unsubscribe();
      setIsLoading(false);
    };
  }, [currentUser, activeChatId, onSelectChat]);

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
        <div className="flex items-center justify-center mb-6">
          <button
            className="flex items-center justify-center gap-2 px-4 py-3 w-full border border-[#2A2931] rounded-xl text-[#A0A0A0] hover:border-[#9333ea] hover:text-[#F1F1F1] transition-all font-medium"
            aria-label="New session"
            onClick={async () => {
              if (!currentUser) return;
              const { id, error } = await createChatForUser(currentUser.uid, 'New Chat');
              if (error) {
                console.error('Failed to create chat:', error);
              } else if (typeof onSelectChat === 'function') {
                onSelectChat(id);
              }
            }}
          >
            <NewChatIcon />
            <span>New Chat</span>
          </button>
        </div>
        <nav className="flex-grow overflow-y-auto">
          {isLoading ? (
            <div className="text-center py-4 text-[#A0A0A0] flex items-center justify-center gap-2">
              <LoadingDots size="w-1.5 h-1.5" color="bg-[#A0A0A0]" />
              <span>Loading chats...</span>
            </div>
          ) : chats.length === 0 ? (
            <div className="text-center py-4 text-[#A0A0A0]">No chats yet. Create a new chat to begin!</div>
          ) : chats.map(item => (
            <ChatItem
              key={item.id}
              item={item}
              currentUser={currentUser}
              activeChatId={activeChatId}
              onSelectChat={onSelectChat}
              onClose={onClose}
            />
          ))}
        </nav>
      </aside>
    </>
  );
};

export default Sidebar;