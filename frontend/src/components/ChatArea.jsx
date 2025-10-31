import React, { useState, useEffect, useRef } from 'react';
// FIX: Removing .jsx extension to let the bundler resolve the correct file
import Message from './Message';
import { UploadIcon, SendIcon } from './Icons';

// This is the main interaction area
const ChatArea = () => {
  // We use mock messages for the frontend-only demo
  const [messages, setMessages] = useState([
    { id: 1, sender: 'user', text: 'Generate 1000 rows from ecommerce.yaml' },
    { id: 2, sender: 'assistant', text: 'Okay, I am generating 1000 rows based on the provided `ecommerce.yaml` schema...' },
  ]);
  const [input, setInput] = useState('');
  const messagesEndRef = useRef(null);

  // Automatically scroll to the bottom when a new message appears
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  // Handles sending a new message
  const handleSend = () => {
    if (input.trim()) {
      setMessages([...messages, { id: Date.now(), sender: 'user', text: input }]);
      setInput('');
      
      // Mock an assistant reply for demo purposes
      setTimeout(() => {
        setMessages(prev => [...prev, { id: Date.now() + 1, sender: 'assistant', text: 'Processing your request...' }]);
      }, 1000);
    }
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
              className="p-4 text-[#9333ea] disabled:text-[#585858]"
              onClick={handleSend}
              disabled={!input.trim()}
              aria-label="Send message"
            >
              <SendIcon />
            </button>
          </div>
        </div>
      </div>
    </main>
  );
};

export default ChatArea;


