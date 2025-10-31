# OpenSchema Chrome Extension

A Chrome extension that provides full access to OpenSchema chat functionality directly from your browser.

## Features

- 🔐 **Authentication**: Login, Sign Up, and Password Reset
- 💬 **Chat Interface**: Full chat functionality with message history
- 📝 **Chat Management**: Create, rename, and delete chats
- 💾 **Firebase Integration**: Real-time synchronization with Firebase Realtime Database
- 🎨 **Modern UI**: Beautiful, responsive design matching the main app

## Installation

1. **Firebase SDKs are already downloaded** (in the `lib` folder)
   - If missing, see `SETUP.md` for instructions

2. **Load the extension in Chrome**:
   - Open Chrome and navigate to `chrome://extensions/`
   - Enable "Developer mode" (toggle in top-right)
   - Click "Load unpacked"
   - Select the `lakshya-extension` folder

3. **The extension icon should now appear in your Chrome toolbar**

**Note:** If you see icon warnings, the extension will still work. You can add icon files later (see `ICONS.md`)

## Usage

1. Click the OpenSchema extension icon in your Chrome toolbar
2. If not logged in, use the login modal to sign in or create an account
3. Once logged in, you'll see:
   - Sidebar with your chat history
   - Chat area for messaging
   - Input box to send new messages

4. **Create a new chat**: Click "New Chat" button
5. **Select a chat**: Click any chat in the sidebar
6. **Send messages**: Type in the input box and press Enter or click the send button

## File Structure

```
lakshya-extension/
├── manifest.json          # Extension configuration
├── popup.html            # Main UI HTML
├── popup.js              # Main JavaScript logic
├── styles.css            # Styling
├── firebase-config.js    # Firebase configuration
├── content.js            # Content script (optional)
└── README.md            # This file
```

## Firebase Configuration

The extension uses the same Firebase project as the main application:
- Firebase Realtime Database for chat storage
- Firebase Authentication for user management

## Permissions

The extension requires:
- `storage`: For local data persistence
- `host_permissions`: For Firebase API access

## Development

1. Make changes to the files
2. Go to `chrome://extensions/`
3. Click the refresh icon on the OpenSchema extension card
4. Test your changes

## Notes

- The extension popup window is 450x600 pixels
- All data is synced with Firebase in real-time
- Chat history persists across sessions
- Messages are automatically timestamped

## Troubleshooting

- **Extension not loading**: Make sure you're using Chrome (not other Chromium browsers) and have Developer mode enabled
- **Firebase errors**: Check that the Firebase configuration in `firebase-config.js` is correct
- **Messages not appearing**: Check browser console for errors (Right-click extension icon > Inspect popup)

