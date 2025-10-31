import { collection, addDoc, query, orderBy, onSnapshot, serverTimestamp } from 'firebase/firestore';
import { db } from './config';

// Add a message to a user's message collection
export const sendMessageForUser = async (uid, message) => {
    try {
        const colRef = collection(db, 'users', uid, 'messages');
        const docRef = await addDoc(colRef, {
            sender: message.sender,
            text: message.text,
            createdAt: serverTimestamp(),
            meta: message.meta || null,
        });
        return { id: docRef.id, error: null };
    } catch (error) {
        return { id: null, error: error.message };
    }
};

// Subscribe to a user's messages (realtime) and call callback(messages)
export const subscribeToUserMessages = (uid, callback) => {
    if (!uid) return () => { };
    const colRef = collection(db, 'users', uid, 'messages');
    const q = query(colRef, orderBy('createdAt', 'asc'));
    const unsubscribe = onSnapshot(q, (snapshot) => {
        const messages = snapshot.docs.map((doc) => ({ id: doc.id, ...doc.data() }));
        callback(messages);
    }, (err) => {
        console.error('Messages subscription error', err);
    });
    return unsubscribe;
};
