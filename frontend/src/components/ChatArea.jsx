import React, { useState, useEffect, useRef } from 'react';
import { useAuth } from '../context/AuthContext.jsx';
import Message from './Message.jsx';
import LoadingDots from './LoadingDots.jsx';
import { UploadIcon, SendIcon } from './Icons.jsx';
import { sendMessageToChat, subscribeToChatMessages } from '../firebase/rtdb.js';

// This is the main interaction area
const ChatArea = ({ activeChatId }) => {
  const { currentUser } = useAuth();

  // messages are either loaded from RTDB (when logged in and chat selected) or local mocks when not
  const [messages, setMessages] = useState([
    { id: 1, sender: 'user', text: 'Generate 1000 rows from ecommerce.yaml', createdAt: Date.now() },
    { id: 2, sender: 'assistant', text: 'Okay, I am generating 1000 rows based on the provided `ecommerce.yaml` schema...', createdAt: Date.now() + 1000 },
  ]);
  const [input, setInput] = useState('');
  const [isSending, setIsSending] = useState(false);
  const messagesEndRef = useRef(null);

  // Automatically scroll to the bottom when a new message appears
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  // Subscribe to RTDB messages for the selected chat when a user is logged in
  useEffect(() => {
    if (!currentUser || !activeChatId) return;

    const uid = currentUser.uid;
    const unsubscribe = subscribeToChatMessages(uid, activeChatId, (msgs) => {
      const normalized = msgs.map(m => ({ id: m.id, sender: m.sender, text: m.text, createdAt: m.createdAt }));
      setMessages(normalized);
    });

    return () => unsubscribe && unsubscribe();
  }, [currentUser, activeChatId]);

  // Handles sending a new message
  const handleSend = async () => {
    if (!input.trim() || isSending) return;

    const text = input.trim();
    setInput('');
    setIsSending(true);

    const timestamp = Date.now();

    // Optimistic add to UI
    const userMessage = { id: `temp-${timestamp}`, sender: 'user', text, createdAt: timestamp };
    setMessages(prev => [...prev, userMessage]);

    // Persist user message to RTDB when logged in and a chat is selected
    if (currentUser && activeChatId) {
      const { error } = await sendMessageToChat(currentUser.uid, activeChatId, { sender: 'user', text });
      if (error) {
        console.error('Failed to save user message:', error);
      }
    }

    // Mock assistant reply and persist it as well
    setTimeout(async () => {
      const assistantText = 'Processing your request...';
      const assistantTimestamp = Date.now();
      const assistantMessage = { id: `temp-${assistantTimestamp}`, sender: 'assistant', text: assistantText, createdAt: assistantTimestamp };
      setMessages(prev => [...prev, assistantMessage]);

      if (currentUser && activeChatId) {
        const { error } = await sendMessageToChat(currentUser.uid, activeChatId, { sender: 'assistant', text: assistantText });
        if (error) {
          console.error('Failed to save assistant message:', error);
        }
      }
      
      setIsSending(false);
    }, 1000);
  };

  return (
    <main className="flex-1 flex flex-col relative bg-[#111014] overflow-hidden">
      {/* Background Aura Effect: The key visual element */}
      <div
        className="absolute inset-0 -z-10 chat-area-aura"
      ></div>

      {/* Messages Container */}
      <div className="flex-1 overflow-y-auto p-4 md:p-8">
        <div className="max-w-3xl mx-auto flex flex-col gap-6">
          {messages.map(msg => <Message key={msg.id} message={msg} />)}
          <div ref={messagesEndRef} />
        </div>
      </div>

      {/* Input Area */}
      <div className="w-full p-4 pb-8 md:p-8 md:pb-12 bg-gradient-to-t from-[#111014] via-[#111014]/90 to-transparent">
        <div className="max-w-3xl mx-auto">
          <div className="flex items-center bg-[#1A191F] border border-[#2A2931] rounded-xl shadow-xl focus-within:border-[#9333ea] focus-within:ring-2 focus-within:ring-[#9333ea]/30">
            <button className="p-4 text-[#A0A0A0] hover:text-[#F1F1F1]" aria-label="Upload file">
              <UploadIcon />
            </button>
            <input
              type="text"
              className="flex-1 bg-transparent border-none outline-none p-4 text-base text-[#F1F1F1] placeholder:text-[#A0A0A0]"
              placeholder="Evaluate data quality for the last run..."
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={(e) => e.key === 'Enter' && handleSend()}
            />
            <button
              className="p-4 text-[#9333ea] disabled:text-[#585858] flex items-center justify-center"
              onClick={handleSend}
              disabled={!input.trim() || isSending}
              aria-label="Send message"
            >
              {isSending ? (
                <LoadingDots size="w-2 h-2" color="bg-[#9333ea]" />
              ) : (
                <SendIcon />
              )}
            </button>
          </div>
        </div>
      </div>
    </main>
  );
};

export default ChatArea;


