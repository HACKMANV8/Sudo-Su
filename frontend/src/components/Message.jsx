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
          className={`py-2.5 px-4 text-base leading-relaxed shadow-sm ${isUser
              ? 'bg-[#9333ea] text-white rounded-2xl bubble-user'
              : 'bg-[#1A191F] text-[#F1F1F1] rounded-2xl bubble-assistant'
            }`}
          style={{ 
            maxWidth: '92%',
            display: 'inline-block'
          }}
        >
          <div style={{ 
            whiteSpace: 'pre-wrap',
            wordBreak: 'normal',
            overflowWrap: 'normal',
            wordWrap: 'normal'
          }}>
            {message.text}
          </div>
        </div>
        {message.createdAt && (
          <span className="text-xs text-[#A0A0A0] px-3">
            {formatTime(message.createdAt)}
          </span>
        )}
      </div>
    </div>
  );
};

export default Message;