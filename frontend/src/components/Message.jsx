import React from 'react';

// Renders a single message bubble
const Message = ({ message }) => {
  const isUser = message.sender === 'user';

  const formatTime = (timestamp) => {
    if (!timestamp) return '';
    const date = new Date(timestamp);
    return date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
  };

  return (
    <div className={`flex flex-col gap-2 animate-fadeIn ${isUser ? 'items-end' : 'items-start'}`}>
      <div className="flex flex-col gap-1">
        <div
          className={`max-w-[90%] py-3 px-5 rounded-2xl text-base leading-relaxed ${isUser
              ? 'bg-[#9333ea] text-white rounded-br-lg'
              : 'bg-[#1A191F] text-[#F1F1F1] rounded-bl-lg'
            }`}
        >
          {message.text}
        </div>
        {message.createdAt && (
          <span className="text-xs text-[#A0A0A0] px-2">
            {formatTime(message.createdAt)}
          </span>
        )}
      </div>
    </div>
  );
};

export default Message;