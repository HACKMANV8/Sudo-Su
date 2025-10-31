// popup.js
document.getElementById('captureButton').addEventListener('click', () => {
  document.getElementById('result').textContent = 'Scanning...';

  // 1. Get the current active tab
  chrome.tabs.query({ active: true, currentWindow: true }, (tabs) => {
    const activeTab = tabs[0];

    // 2. Send a message to the content.js script running on that tab
    chrome.tabs.sendMessage(activeTab.id, { action: "captureData" }, (response) => {
      if (response && response.data) {
        // 3. Display the result from the content script
        const data = response.data;
        document.getElementById('result').innerHTML = `✅ **Schema Captured!**<br>Type: **${data.schema_type}**<br>Items: **${data.example_values.length}**`;

        // IMPORTANT: In a real scenario, this is where you send 'data' to your backend API.
        console.log("Captured Data:", data);

      } else {
        document.getElementById('result').textContent = '❌ No usable schema found on this page.';
      }
    });
  });
});