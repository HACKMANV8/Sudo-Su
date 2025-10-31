// Initialize Firebase
let auth, database;
let currentUser = null;
let currentChatId = null;
let chatsUnsubscribe = null;
let messagesUnsubscribe = null;

// Initialize Firebase when page loads
window.addEventListener('DOMContentLoaded', () => {
    // Setup event listeners first (they work independently of Firebase)
    setupEventListeners();
    
    // Initialize Firebase
    initializeFirebase();
    
    // Check auth state after Firebase is ready
    setTimeout(() => {
        checkAuthState();
    }, 100);
});

function initializeFirebase() {
    try {
        if (typeof firebase !== 'undefined' && firebaseConfig) {
            firebase.initializeApp(firebaseConfig);
            auth = firebase.auth();
            database = firebase.database();
        } else {
            console.error('Firebase or config not loaded');
            setTimeout(() => {
                if (typeof firebase !== 'undefined' && firebaseConfig) {
                    firebase.initializeApp(firebaseConfig);
                    auth = firebase.auth();
                    database = firebase.database();
                    checkAuthState();
                }
            }, 500);
        }
    } catch (error) {
        console.error('Firebase initialization error:', error);
        showError('Failed to initialize Firebase');
    }
}

function setupEventListeners() {
    // Auth form - ensure elements exist before attaching listeners
    const authForm = document.getElementById('authForm');
    if (authForm) {
        authForm.addEventListener('submit', handleAuthSubmit);
    }
    
    const toggleBtn = document.getElementById('toggleAuthBtn');
    if (toggleBtn) {
        toggleBtn.addEventListener('click', toggleAuthMode);
    }
    
    const forgotBtn = document.getElementById('forgotPasswordBtn');
    if (forgotBtn) {
        forgotBtn.addEventListener('click', showForgotPassword);
    }
    
    const logoutBtn = document.getElementById('logoutBtn');
    if (logoutBtn) {
        logoutBtn.addEventListener('click', handleLogout);
    }

    // Chat interface
    const newChatBtn = document.getElementById('newChatBtn');
    if (newChatBtn) {
        newChatBtn.addEventListener('click', createNewChat);
    }
    
    const sendBtn = document.getElementById('sendBtn');
    if (sendBtn) {
        sendBtn.addEventListener('click', sendMessage);
    }
    
    const messageInput = document.getElementById('messageInput');
    if (messageInput) {
        messageInput.addEventListener('keypress', (e) => {
            if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                sendMessage();
            }
        });
    }
    
    // URL checkbox - get current tab URL
    loadCurrentTabUrl();
}

function checkAuthState() {
    auth.onAuthStateChanged((user) => {
        currentUser = user;
        if (user) {
            showChatInterface();
            loadUserChats();
        } else {
            showLoginModal();
        }
    });
}

// ============ Authentication ============

let isLoginMode = true;
let isResetMode = false;

function toggleAuthMode() {
    isLoginMode = !isLoginMode;
    isResetMode = false;
    updateAuthUI();
}

function showForgotPassword() {
    isResetMode = true;
    updateAuthUI();
}

function updateAuthUI() {
    const modalTitle = document.getElementById('modalTitle');
    const submitText = document.getElementById('submitText');
    const passwordGroup = document.getElementById('passwordGroup');
    const confirmPasswordGroup = document.getElementById('confirmPasswordGroup');
    const toggleBtn = document.getElementById('toggleAuthBtn');
    const forgotBtn = document.getElementById('forgotPasswordBtn');
    const confirmPasswordInput = document.getElementById('confirmPassword');

    hideMessages();

    if (isResetMode) {
        modalTitle.textContent = 'Reset Password';
        submitText.textContent = 'Send Reset Email';
        passwordGroup.style.display = 'none';
        confirmPasswordGroup.style.display = 'none';
        if (toggleBtn) toggleBtn.innerHTML = 'Need to login? <span>Back to Login</span>';
        if (forgotBtn) forgotBtn.style.display = 'none';
        if (confirmPasswordInput) confirmPasswordInput.removeAttribute('required');
    } else if (isLoginMode) {
        modalTitle.textContent = 'Welcome Back';
        submitText.textContent = 'Login';
        passwordGroup.style.display = 'block';
        confirmPasswordGroup.style.display = 'none';
        if (toggleBtn) toggleBtn.innerHTML = 'Don\'t have an account? <span>Sign Up</span>';
        if (forgotBtn) forgotBtn.style.display = 'block';
        if (confirmPasswordInput) confirmPasswordInput.removeAttribute('required');
    } else {
        modalTitle.textContent = 'Create Account';
        submitText.textContent = 'Sign Up';
        passwordGroup.style.display = 'block';
        confirmPasswordGroup.style.display = 'block';
        if (toggleBtn) toggleBtn.innerHTML = 'Already have an account? <span>Login</span>';
        if (forgotBtn) forgotBtn.style.display = 'none';
        if (confirmPasswordInput) confirmPasswordInput.setAttribute('required', 'required');
    }
}

async function handleAuthSubmit(e) {
    e.preventDefault();
    const submitBtn = document.getElementById('submitBtn');
    const submitLoader = document.getElementById('submitLoader');
    const submitText = document.getElementById('submitText');
    const email = document.getElementById('email').value;
    const password = document.getElementById('password').value;
    const confirmPasswordInput = document.getElementById('confirmPassword');
    const confirmPassword = !isLoginMode && !isResetMode && confirmPasswordInput
        ? confirmPasswordInput.value 
        : '';

    submitBtn.disabled = true;
    submitLoader.style.display = 'block';
    submitText.style.display = 'none';
    hideMessages();

    try {
        if (isResetMode) {
            await auth.sendPasswordResetEmail(email);
            showSuccess('If an account exists for that email, a reset link has been sent.');
        } else if (isLoginMode) {
            await auth.signInWithEmailAndPassword(email, password);
        } else {
            // Signup mode - validate confirm password
            if (!confirmPassword) {
                throw new Error('Please confirm your password');
            }
            if (password !== confirmPassword) {
                throw new Error('Passwords do not match');
            }
            await auth.createUserWithEmailAndPassword(email, password);
        }
    } catch (error) {
        showError(error.message);
    } finally {
        submitBtn.disabled = false;
        submitLoader.style.display = 'none';
        submitText.style.display = 'block';
    }
}

async function handleLogout() {
    try {
        hideMessages(); // Clear any existing messages
        await auth.signOut();
        currentChatId = null;
        if (chatsUnsubscribe) {
            chatsUnsubscribe();
            chatsUnsubscribe = null;
        }
        if (messagesUnsubscribe) {
            messagesUnsubscribe();
            messagesUnsubscribe = null;
        }
        // Don't show error if logout is successful - auth state change will handle UI
    } catch (error) {
        console.error('Logout error:', error);
        // Only show error if logout actually failed
        if (currentUser) {
            showError('Failed to logout: ' + error.message);
        }
    }
}

// ============ UI Helpers ============

function showLoginModal() {
    document.getElementById('loginModal').style.display = 'flex';
    document.getElementById('chatInterface').style.display = 'none';
    document.getElementById('logoutBtn').style.display = 'none';
}

function showChatInterface() {
    document.getElementById('loginModal').style.display = 'none';
    document.getElementById('chatInterface').style.display = 'flex';
    document.getElementById('logoutBtn').style.display = 'block';
    // Load URL when chat interface is shown
    loadCurrentTabUrl();
}

function showError(message) {
    const errorMsg = document.getElementById('errorMsg');
    errorMsg.textContent = message;
    errorMsg.style.display = 'block';
    document.getElementById('successMsg').style.display = 'none';
}

function showSuccess(message) {
    const successMsg = document.getElementById('successMsg');
    successMsg.textContent = message;
    successMsg.style.display = 'block';
    document.getElementById('errorMsg').style.display = 'none';
}

function hideMessages() {
    document.getElementById('errorMsg').style.display = 'none';
    document.getElementById('successMsg').style.display = 'none';
}

// ============ Chat Management ============

async function loadUserChats() {
    if (!currentUser) return;

    const chatsList = document.getElementById('chatsList');
    chatsList.innerHTML = '<div class="loading-text">Loading chats...</div>';

    const chatsRef = database.ref(`users/${currentUser.uid}/chats`);

    chatsUnsubscribe = chatsRef.on('value', (snapshot) => {
        const chatsData = snapshot.val() || {};
        const chats = Object.keys(chatsData).map(id => ({
            id,
            ...chatsData[id]
        }));

        chats.sort((a, b) => (b.createdAt || 0) - (a.createdAt || 0));

        if (chats.length === 0) {
            chatsList.innerHTML = '<div class="loading-text">No chats yet. Create a new chat to begin!</div>';
            return;
        }

        chatsList.innerHTML = chats.map(chat => `
            <div class="chat-item ${chat.id === currentChatId ? 'active' : ''}" data-chat-id="${chat.id}">
                ${chat.title || 'New Chat'}
            </div>
        `).join('');

        // Add click listeners
        chatsList.querySelectorAll('.chat-item').forEach(item => {
            item.addEventListener('click', () => {
                const chatId = item.getAttribute('data-chat-id');
                selectChat(chatId);
            });
        });

        // Auto-select first chat if none selected
        if (!currentChatId && chats.length > 0) {
            selectChat(chats[0].id);
        }
    }, (error) => {
        console.error('Error loading chats:', error);
        chatsList.innerHTML = '<div class="loading-text">Error loading chats</div>';
    });
}

async function createNewChat() {
    if (!currentUser) return;

    try {
        const chatsRef = database.ref(`users/${currentUser.uid}/chats`);
        const newChatRef = chatsRef.push();
        await newChatRef.set({
            title: 'New Chat',
            createdAt: Date.now()
        });
        selectChat(newChatRef.key);
    } catch (error) {
        console.error('Error creating chat:', error);
        showError('Failed to create chat');
    }
}

async function selectChat(chatId) {
    if (!currentUser || chatId === currentChatId) return;

    currentChatId = chatId;

    // Update UI
    document.querySelectorAll('.chat-item').forEach(item => {
        item.classList.remove('active');
        if (item.getAttribute('data-chat-id') === chatId) {
            item.classList.add('active');
        }
    });

    // Load messages
    loadChatMessages(chatId);
}

function loadChatMessages(chatId) {
    if (!currentUser || !chatId) return;

    const messagesContainer = document.getElementById('messagesContainer');
    messagesContainer.innerHTML = '<div class="loading-text">Loading messages...</div>';

    const messagesRef = database.ref(`users/${currentUser.uid}/chats/${chatId}/messages`);

    messagesUnsubscribe = messagesRef.on('value', (snapshot) => {
        const messagesData = snapshot.val() || {};
        const messages = Object.keys(messagesData).map(id => ({
            id,
            ...messagesData[id]
        }));

        messages.sort((a, b) => (a.createdAt || 0) - (b.createdAt || 0));

        if (messages.length === 0) {
            messagesContainer.innerHTML = '<div class="empty-state">No messages yet. Start a conversation!</div>';
            return;
        }

        messagesContainer.innerHTML = messages.map(msg => {
            const time = msg.createdAt ? new Date(msg.createdAt).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }) : '';
            return `
                <div class="message ${msg.sender}">
                    <div class="message-bubble">${escapeHtml(msg.text)}</div>
                    ${time ? `<div class="message-time">${time}</div>` : ''}
                </div>
            `;
        }).join('');

        // Scroll to bottom
        messagesContainer.scrollTop = messagesContainer.scrollHeight;
    }, (error) => {
        console.error('Error loading messages:', error);
        messagesContainer.innerHTML = '<div class="empty-state">Error loading messages</div>';
    });
}

async function sendMessage() {
    const input = document.getElementById('messageInput');
    const messageText = input.value.trim();
    const sendBtn = document.getElementById('sendBtn');
    const includeUrlCheckbox = document.getElementById('includeUrlCheckbox');

    if (!messageText || !currentUser || sendBtn.disabled) return;

    sendBtn.disabled = true;

    // Create chat if none selected
    if (!currentChatId) {
        await createNewChat();
        // Wait a moment for chat to be created
        await new Promise(resolve => setTimeout(resolve, 200));
    }

    try {
        let text = messageText;
        
        // Add URL if checkbox is checked
        if (includeUrlCheckbox && includeUrlCheckbox.checked) {
            const currentUrl = await getCurrentTabUrl();
            if (currentUrl) {
                text = `${messageText}\n\n[Reference URL: ${currentUrl}]`;
            }
        }
        
        input.value = '';

        // Add user message to UI immediately
        const messagesContainer = document.getElementById('messagesContainer');
        if (messagesContainer.querySelector('.empty-state')) {
            messagesContainer.innerHTML = '';
        }
        messagesContainer.innerHTML += `
            <div class="message user">
                <div class="message-bubble">${escapeHtml(text)}</div>
                <div class="message-time">${new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}</div>
            </div>
        `;
        messagesContainer.scrollTop = messagesContainer.scrollHeight;

        // Save to Firebase
        const messagesRef = database.ref(`users/${currentUser.uid}/chats/${currentChatId}/messages`);
        const newMsgRef = messagesRef.push();
        await newMsgRef.set({
            sender: 'user',
            text: text,
            createdAt: Date.now()
        });

        // Update chat title if it's "New Chat"
        const chatRef = database.ref(`users/${currentUser.uid}/chats/${currentChatId}`);
        const chatSnapshot = await chatRef.once('value');
        const chat = chatSnapshot.val();
        if (chat && chat.title === 'New Chat') {
            const title = messageText.slice(0, 30) + (messageText.length > 30 ? '...' : '');
            await chatRef.update({ title, updatedAt: Date.now() });
        }

        // Mock assistant response
        setTimeout(async () => {
            const assistantText = 'Processing your request...';
            messagesContainer.innerHTML += `
                <div class="message assistant">
                    <div class="message-bubble">${escapeHtml(assistantText)}</div>
                    <div class="message-time">${new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}</div>
                </div>
            `;
            messagesContainer.scrollTop = messagesContainer.scrollHeight;

            // Save assistant message
            const assistantMsgRef = messagesRef.push();
            await assistantMsgRef.set({
                sender: 'assistant',
                text: assistantText,
                createdAt: Date.now()
            });
        }, 1000);

    } catch (error) {
        console.error('Error sending message:', error);
        showError('Failed to send message');
    } finally {
        sendBtn.disabled = false;
        input.focus();
    }
}

// Get current tab URL
async function getCurrentTabUrl() {
    try {
        const tabs = await chrome.tabs.query({ active: true, currentWindow: true });
        if (tabs && tabs[0] && tabs[0].url) {
            return tabs[0].url;
        }
    } catch (error) {
        console.error('Error getting current tab URL:', error);
    }
    return null;
}

// Load and display current tab URL
async function loadCurrentTabUrl() {
    const urlText = document.getElementById('urlText');
    const includeUrlCheckbox = document.getElementById('includeUrlCheckbox');
    
    if (!urlText || !includeUrlCheckbox) return;
    
    try {
        const url = await getCurrentTabUrl();
        if (url) {
            // Show shortened URL
            const urlObj = new URL(url);
            const shortUrl = urlObj.hostname + urlObj.pathname;
            urlText.textContent = `Include URL: ${shortUrl.length > 40 ? shortUrl.substring(0, 40) + '...' : shortUrl}`;
            includeUrlCheckbox.checked = true;
        } else {
            urlText.textContent = 'Include current page URL';
            includeUrlCheckbox.checked = false;
            includeUrlCheckbox.disabled = true;
        }
    } catch (error) {
        console.error('Error loading URL:', error);
        urlText.textContent = 'Include current page URL';
        includeUrlCheckbox.checked = false;
        includeUrlCheckbox.disabled = true;
    }
}

function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}
