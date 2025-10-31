// This script helps download Firebase SDKs for local use
// Run this in Node.js: node download-firebase.js

const https = require('https');
const fs = require('fs');
const path = require('path');

const libDir = path.join(__dirname, 'lib');
if (!fs.existsSync(libDir)) {
    fs.mkdirSync(libDir);
}

const files = [
    { url: 'https://www.gstatic.com/firebasejs/10.7.1/firebase-app-compat.js', name: 'firebase-app-compat.js' },
    { url: 'https://www.gstatic.com/firebasejs/10.7.1/firebase-auth-compat.js', name: 'firebase-auth-compat.js' },
    { url: 'https://www.gstatic.com/firebasejs/10.7.1/firebase-database-compat.js', name: 'firebase-database-compat.js' }
];

function downloadFile(url, filepath) {
    return new Promise((resolve, reject) => {
        const file = fs.createWriteStream(filepath);
        https.get(url, (response) => {
            response.pipe(file);
            file.on('finish', () => {
                file.close();
                console.log(`Downloaded: ${filepath}`);
                resolve();
            });
        }).on('error', (err) => {
            fs.unlink(filepath, () => {});
            reject(err);
        });
    });
}

async function downloadAll() {
    console.log('Downloading Firebase SDKs...');
    for (const file of files) {
        const filepath = path.join(libDir, file.name);
        try {
            await downloadFile(file.url, filepath);
        } catch (error) {
            console.error(`Error downloading ${file.name}:`, error);
        }
    }
    console.log('Done!');
}

downloadAll();

