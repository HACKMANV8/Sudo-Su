import React, { useState, useEffect, useRef } from 'react';
// FIX: Removing .jsx extension to let the bundler resolve the correct file
import Message from './Message';
import { UploadIcon, SendIcon } from './Icons';
import { runPrompt, runPromptStream, approveReview, fetchSpec } from '../api';

// This is the main interaction area
const ChatArea = () => {
  const [messages, setMessages] = useState([
    { id: 1, sender: 'assistant', text: 'ON what topic you need the schema? Give the query for it.' },
  ]);
  const [input, setInput] = useState('');
  const [conversationState, setConversationState] = useState({
    step: 'idle',
    lastPrompt: null,
    lastRows: 20,
    hilList: [],
    hilIndex: 0,
    hilCurrent: null,
  });
  const [lastSavedFiles, setLastSavedFiles] = useState([]);
  const placeholderIdRef = useRef(null);
  const messagesEndRef = useRef(null);

  // Helper to append an assistant message
  const appendAssistant = (text) => {
    const id = Date.now() + Math.floor(Math.random() * 1000);
    setMessages((prev) => [...prev, { id, sender: 'assistant', text }]);
    return id;
  };

  // Start live streaming from backend and push to chat
  const startSseStream = ({ prompt, use_csv, rows }) => {
    // Ensure there's a placeholder to replace with first message
    const placeholderId = Date.now() + 1;
    placeholderIdRef.current = placeholderId;
    setMessages((prev) => [
      ...prev,
      { id: placeholderId, sender: 'assistant', text: 'Processing your request...' },
    ]);

    const unsub = runPromptStream(
      { prompt, use_csv, rows },
      {
        onMessage: (text) => {
          // First message replaces placeholder; subsequent ones append
          let replaced = false;
          setMessages((prev) => prev.map((m) => {
            if (m.id === placeholderIdRef.current) {
              replaced = true;
              return { ...m, text };
            }
            return m;
          }));
          if (!replaced) appendAssistant(text);
        },
        onFiles: (files) => {
          if (Array.isArray(files) && files.length) {
            appendAssistant(`Saved files:\n- ${files.slice(0, 10).join('\n- ')}${files.length > 10 ? '\n... (more)' : ''}`);
            setLastSavedFiles(files);
          }
        },
        onDone: () => {
          // Ask for Human-in-the-Loop review
          setConversationState((s) => ({ ...s, step: 'awaiting_hil_decision' }));
          // Match main.py wording
          appendAssistant("Start schema review now? [y/N]");
        },
        onError: (e) => {
          setMessages((prev) => prev.map((m) => (
            m.id === placeholderIdRef.current ? { ...m, text: `Error: ${e?.message || 'Stream error'}` } : m
          )));
          setConversationState({ step: 'idle', lastPrompt: null, lastRows: 20 });
        },
      }
    );
    return unsub;
  };

  // Automatically scroll to the bottom when a new message appears
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  // Parse inline flags like: csv:no rows:10
  const parseFlags = (text) => {
    let use_csv = true;
    let rows = 20;
    let clean = text;
    const csvMatch = text.match(/\bcsv:(yes|no)\b/i);
    if (csvMatch) {
      use_csv = csvMatch[1].toLowerCase() !== 'no';
      clean = clean.replace(csvMatch[0], '').trim();
    }
    const rowsMatch = text.match(/\brows:(\d{1,4})\b/i);
    if (rowsMatch) {
      rows = Math.min(1000, Math.max(1, parseInt(rowsMatch[1], 10)));
      clean = clean.replace(rowsMatch[0], '').trim();
    }
    return { prompt: clean, use_csv, rows };
  };

  // Handles sending a new message (multi-turn conversation)
  const handleSend = async () => {
    const text = input.trim();
    if (!text) return;

    const userMsg = { id: Date.now(), sender: 'user', text };
    setMessages((prev) => [...prev, userMsg]);
    setInput('');

    // Check conversation state
    if (conversationState.step === 'awaiting_csv_decision') {
      // User is answering the CSV question
      const answer = text.toLowerCase();
      const use_csv = ['yes', 'y', ''].includes(answer); // default yes as in main.py
      
      // Start streaming
      startSseStream({ prompt: conversationState.lastPrompt, use_csv, rows: conversationState.lastRows });
      return;
    }

    if (conversationState.step === 'awaiting_hil_decision') {
      const answer = text.toLowerCase();
      const yes = ['y', 'yes'].includes(answer);
      if (!yes) {
        appendAssistant('Okay, skipping review.');
        setConversationState({ step: 'idle', lastPrompt: null, lastRows: 20, hilList: [], hilIndex: 0, hilCurrent: null });
        return;
      }
      // Build list of schema files from lastSavedFiles
      const schemaFiles = (lastSavedFiles || []).filter((f) => /_schema\.json$/i.test(f));
      if (!schemaFiles.length) {
        appendAssistant('No schema files found to review.');
        setConversationState({ step: 'idle', lastPrompt: null, lastRows: 20, hilList: [], hilIndex: 0, hilCurrent: null });
        return;
      }
      // Start review loop with the first file and show schema content
      const nextName = schemaFiles[0];
      setConversationState({ step: 'awaiting_hil_action', lastPrompt: null, lastRows: 20, hilList: schemaFiles, hilIndex: 0, hilCurrent: nextName });
      try {
        const schema = await fetchSpec(nextName);
        appendAssistant(`Schema ${nextName}:\n` + JSON.stringify(schema, null, 2));
      } catch (_) { /* ignore */ }
      appendAssistant(`Review schema ${nextName}: [A]pprove / [E]dit / [S]kip`);
      return;
    }

    if (conversationState.step === 'awaiting_hil_action') {
      const val = text.trim().toLowerCase();
      const name = conversationState.hilCurrent;
      if (!name) {
        setConversationState({ step: 'idle', lastPrompt: null, lastRows: 20, hilList: [], hilIndex: 0, hilCurrent: null });
        return;
      }
      const proceedNext = async () => {
        const idx = conversationState.hilIndex + 1;
        if (idx >= conversationState.hilList.length) {
          appendAssistant('Review complete.');
          setConversationState({ step: 'idle', lastPrompt: null, lastRows: 20, hilList: [], hilIndex: 0, hilCurrent: null });
        } else {
          const nextName = conversationState.hilList[idx];
          setConversationState({ step: 'awaiting_hil_action', lastPrompt: null, lastRows: 20, hilList: conversationState.hilList, hilIndex: idx, hilCurrent: nextName });
          try {
            const schema = await fetchSpec(nextName);
            appendAssistant(`Schema ${nextName}:\n` + JSON.stringify(schema, null, 2));
          } catch (_) { /* ignore */ }
          appendAssistant(`Review schema ${nextName}: [A]pprove / [E]dit / [S]kip`);
        }
      };

      if (val === 'a' || val === 'approve') {
        try {
          const result = await approveReview([name]);
          const approved = Array.isArray(result?.approved) ? result.approved : [];
          if (approved.length) appendAssistant(`✅ Approved: ${approved[0]}`);
        } catch (e) {
          appendAssistant(`Error approving: ${e?.message || e}`);
        }
        await proceedNext();
        return;
      }
      if (val === 's' || val === 'skip') {
        appendAssistant(`Skipped: ${name}`);
        await proceedNext();
        return;
      }
      if (val === 'e' || val === 'edit') {
        try {
          const schema = await fetchSpec(name);
          appendAssistant(`Current schema ${name}:\n` + JSON.stringify(schema, null, 2));
        } catch (_) {
          // ignore
        }
        appendAssistant('Paste edited JSON (or type CANCEL to abort edit):');
        setConversationState({ ...conversationState, step: 'awaiting_schema_edit' });
        return;
      }
      appendAssistant('Please reply with A (approve), E (edit), or S (skip).');
      return;
    }

    if (conversationState.step === 'awaiting_schema_edit') {
      const name = conversationState.hilCurrent;
      const raw = text.trim();
      if (raw.toLowerCase() === 'cancel') {
        appendAssistant('Edit cancelled.');
        setConversationState({ ...conversationState, step: 'awaiting_hil_action' });
        return;
      }
      try {
        const jsonObj = JSON.parse(raw);
        // Submit reviewed schema
        // submitReview is available in api.js but not imported here for brevity; approve path can also accept edits via submit endpoint if needed.
        // To keep changes minimal, use approveReview on the original file AND show edited JSON inline as confirmation.
        // If you prefer to persist edits, we can import submitReview and call it here.
        appendAssistant('✅ Edited schema received (not persisted). If you want persistence, say "SAVE".');
        setConversationState({ ...conversationState, step: 'awaiting_edit_save', editedPayload: jsonObj });
      } catch (e) {
        appendAssistant(`Invalid JSON. Please try again or type CANCEL. Error: ${e?.message || e}`);
      }
      return;
    }

    if (conversationState.step === 'awaiting_edit_save') {
      const val = text.trim().toLowerCase();
      if (val !== 'save') {
        appendAssistant('Not saved. Returning to review menu.');
        setConversationState({ ...conversationState, step: 'awaiting_hil_action', editedPayload: undefined });
        return;
      }
      // Lazy import to avoid circular import on top (keep patch minimal)
      try {
        const { submitReview } = await import('../api');
        const res = await submitReview(conversationState.hilCurrent, conversationState.editedPayload);
        appendAssistant(`💾 Saved reviewed schema to: ${res?.saved || '(unknown)'}`);
      } catch (e) {
        appendAssistant(`Error saving review: ${e?.message || e}`);
      }
      // Continue to next
      const idx = conversationState.hilIndex + 1;
      if (idx >= conversationState.hilList.length) {
        appendAssistant('Review complete.');
        setConversationState({ step: 'idle', lastPrompt: null, lastRows: 20, hilList: [], hilIndex: 0, hilCurrent: null, editedPayload: undefined });
      } else {
        const nextName = conversationState.hilList[idx];
        setConversationState({ step: 'awaiting_hil_action', lastPrompt: null, lastRows: 20, hilList: conversationState.hilList, hilIndex: idx, hilCurrent: nextName, editedPayload: undefined });
        appendAssistant(`Review schema ${nextName}: [A]pprove / [E]dit / [S]kip`);
      }
      return;
    }

    // Initial query - parse flags and check if csv flag is explicit
    const { prompt, use_csv, rows } = parseFlags(text);
  const hasCsvFlag = text.match(/\bcsv:(yes|no)\b/i);

    if (hasCsvFlag) {
      // User provided csv flag inline - run immediately
      startSseStream({ prompt, use_csv, rows });
    } else {
      // No csv flag - ask the user (main.py wording)
      setConversationState({ step: 'awaiting_csv_decision', lastPrompt: prompt, lastRows: rows });
      const askId = Date.now() + 1;
      setMessages((prev) => [
        ...prev,
        { id: askId, sender: 'assistant', text: "Use CSV files in 'data/' to ground the schema/metadata? [Y/n]" },
      ]);
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
              placeholder="ON what topic you need the schema give the query for it"
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


