# Chrome Extension Setup Instructions

## Step 1: Download Firebase SDKs

Chrome Manifest V3 doesn't allow loading external scripts, so we need to download Firebase SDKs locally.

### Option A: Using Node.js (Recommended)

1. Open terminal in the `lakshya-extension` folder
2. Run: `node download-firebase.js`
3. This will create a `lib` folder with the Firebase SDK files

### Option B: Manual Download

1. Create a `lib` folder in `lakshya-extension`
2. Download these files and save them in the `lib` folder:
   - https://www.gstatic.com/firebasejs/10.7.1/firebase-app-compat.js
   - https://www.gstatic.com/firebasejs/10.7.1/firebase-auth-compat.js
   - https://www.gstatic.com/firebasejs/10.7.1/firebase-database-compat.js

3. Save them as:
   - `lib/firebase-app-compat.js`
   - `lib/firebase-auth-compat.js`
   - `lib/firebase-database-compat.js`

## Step 2: Add Extension Icons (Optional but Recommended)

Create or download three icon files:
- `icon16.png` (16x16 pixels)
- `icon48.png` (48x48 pixels)
- `icon128.png` (128x128 pixels)

You can use any image editor or online icon generator. See `ICONS.md` for details.

## Step 3: Load Extension in Chrome

1. Open Chrome and go to `chrome://extensions/`
2. Enable "Developer mode" (toggle in top-right)
3. Click "Load unpacked"
4. Select the `lakshya-extension` folder
5. The extension should now load successfully!

## Troubleshooting

- **Missing Firebase files error**: Make sure you completed Step 1
- **Icon warnings**: The extension will work, but add icons for better appearance
- **CSP errors**: Should be resolved now with local Firebase files

