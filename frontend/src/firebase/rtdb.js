import { ref, push, onValue, set, get, update, serverTimestamp, remove } from 'firebase/database';
import { rtdb } from './config';

// Create a new chat under users/{uid}/chats and return the new chat id
export const createChatForUser = async (uid, title = 'New Chat') => {
    try {
        const chatsRef = ref(rtdb, `users/${uid}/chats`);
        // push returns a ref with a unique key
        const newChatRef = push(chatsRef);
        await set(newChatRef, {
            title,
            createdAt: Date.now(),
        });
        return { id: newChatRef.key, error: null };
    } catch (error) {
        return { id: null, error: error.message };
    }
};

// Subscribe to a user's chats and call callback with an array of { id, title, createdAt }
export const subscribeToUserChats = (uid, callback) => {
    if (!uid) return () => { };
    const chatsRef = ref(rtdb, `users/${uid}/chats`);
    const unsubscribe = onValue(chatsRef, (snapshot) => {
        const val = snapshot.val() || {};
        const chats = Object.keys(val).map((k) => ({ id: k, ...val[k] }));
        // sort by createdAt descending (newest first)
        chats.sort((a, b) => (b.createdAt || 0) - (a.createdAt || 0));
        callback(chats);
    }, (err) => {
        console.error('subscribeToUserChats error', err);
    });
    // return an unsubscribe function
    return () => unsubscribe();
};

// Send a message into users/{uid}/chats/{chatId}/messages
export const sendMessageToChat = async (uid, chatId, message) => {
    try {
        const msgsRef = ref(rtdb, `users/${uid}/chats/${chatId}/messages`);
        const newMsgRef = push(msgsRef);
        const timestamp = Date.now();

        await set(newMsgRef, {
            sender: message.sender,
            text: message.text,
            createdAt: timestamp,
            meta: message.meta || null,
        });

        // Try to update chat title if this is the first user message
        if (message.sender === 'user') {
            await tryUpdateChatTitleFromMessage(uid, chatId, message);
        }

        return { id: newMsgRef.key, error: null };
    } catch (error) {
        return { id: null, error: error.message };
    }
};

// Subscribe to messages for a chat and call callback(messages array)
export const subscribeToChatMessages = (uid, chatId, callback) => {
    if (!uid || !chatId) return () => { };
    const msgsRef = ref(rtdb, `users/${uid}/chats/${chatId}/messages`);
    const unsubscribe = onValue(msgsRef, (snapshot) => {
        const val = snapshot.val() || {};
        const msgs = Object.keys(val).map((k) => ({ id: k, ...val[k] }));
        // sort by createdAt asc
        msgs.sort((a, b) => (a.createdAt || 0) - (b.createdAt || 0));
        callback(msgs);
    }, (err) => {
        console.error('subscribeToChatMessages error', err);
    });
    return () => unsubscribe();
};

// Update chat title
export const updateChatTitle = async (uid, chatId, newTitle) => {
    try {
        const chatRef = ref(rtdb, `users/${uid}/chats/${chatId}`);
        const snapshot = await get(chatRef);
        const existingChat = snapshot.val();
        if (!existingChat) {
            throw new Error('Chat not found');
        }

        await update(chatRef, {
            title: newTitle,
            updatedAt: Date.now(),
        });
        return { error: null };
    } catch (error) {
        return { error: error.message };
    }
};

// Remove a chat and all its messages
export const removeChatForUser = async (uid, chatId) => {
    try {
        const chatRef = ref(rtdb, `users/${uid}/chats/${chatId}`);
        await remove(chatRef);
        return { error: null };
    } catch (error) {
        return { error: error.message };
    }
};

// Auto-update chat title from first message if title is "New Chat"
const tryUpdateChatTitleFromMessage = async (uid, chatId, message) => {
    try {
        const chatRef = ref(rtdb, `users/${uid}/chats/${chatId}`);
        const snapshot = await get(chatRef);
        const chat = snapshot.val();

        if (chat && chat.title === 'New Chat' && message.sender === 'user') {
            const title = message.text.slice(0, 30) + (message.text.length > 30 ? '...' : '');
            await update(chatRef, {
                title,
                updatedAt: Date.now()
            });
        }
    } catch (error) {
        console.error('Failed to update chat title:', error);
    }
};
