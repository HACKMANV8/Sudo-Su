import React from 'react';

// Renders a single message bubble
const Message = ({ message }) => {
  const isUser = message.sender === 'user';
  const text = String(message.text ?? '');
  const jsonLike = !isUser && (text.trim().startsWith('{') || text.includes('\n{') || text.trim().startsWith('Schema ') || text.includes('Saved files:'));
  return (
    <div className={`flex flex-col gap-2 animate-fadeIn ${isUser ? 'items-end' : 'items-start'}`}>
      <div
        className={`max-w-[90%] py-3 px-5 rounded-2xl text-base leading-relaxed ${
          isUser
            ? 'bg-[#9333ea] text-white rounded-br-lg'
            : 'bg-[#1A191F] text-[#F1F1F1] rounded-bl-lg'
        }`}
        style={{ whiteSpace: 'pre-wrap', fontFamily: jsonLike ? 'ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, "Liberation Mono", "Courier New", monospace' : undefined }}
      >
        {text}
      </div>
    </div>
  );
};

export default Message;