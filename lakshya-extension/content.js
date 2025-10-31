// content.js

// Listen for a message from the popup script
chrome.runtime.onMessage.addListener((request, sender, sendResponse) => {
  if (request.action === "captureData") {

    // --- HACKATHON FOCUS: Find an obvious data structure ---
    // Priority 1: Find tables (the most structured data)
    const firstTable = document.querySelector('table');

    let schemaData = null;

    if (firstTable) {
        // Simple structure based on table headers (if they exist)
        const headers = Array.from(firstTable.querySelectorAll('th')).map(th => th.innerText.trim());

        schemaData = {
            schema_type: "HTML_Table_Structure",
            source_url: window.location.href,
            example_fields: headers.length > 0 ? headers : ["Column_1", "Column_2", "..."],
            example_values: Array.from(firstTable.querySelectorAll('tr')).slice(1, 4).map(tr => 
                Array.from(tr.querySelectorAll('td')).map(td => td.innerText.trim())
            )
        };

    } else {
        // Priority 2: Find lists
        const firstList = document.querySelector('ul');

        if (firstList) {
            const items = Array.from(firstList.querySelectorAll('li')).slice(0, 5).map(li => li.innerText.trim());

            schemaData = {
                schema_type: "List_Structure",
                source_url: window.location.href,
                example_data_types: "Text",
                example_values: items
            };
        }
    }

    // Send the captured data back to the popup.js
    sendResponse({ data: schemaData });
  }
});