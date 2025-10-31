from flask import Flask, request, jsonify
from flask_cors import CORS # Needed to accept requests from the browser extension

app = Flask(__name__)
# CRITICAL: Allow cross-origin requests from your Chrome Extension
CORS(app) 

@app.route('/api/schema-ingest', methods=['POST'])
def ingest_schema():
    # Get the JSON data sent from the Chrome extension
    data = request.json
    
    # --- LOG THE RECEIVED DATA TO THE TERMINAL ---
    print("\n=============================================")
    print("🚀 OpenSchema Backend received a new payload!")
    print("=============================================")
    print(f"Source URL: {data.get('source_url')}")
    print(f"User Query: {data.get('user_query', 'None specified')}")
    print(f"Schema Type: {data.get('schema_type')}")
    print(f"Detected Wrapper: {data.get('detected_wrapper')}")
    print(f"Fields Detected: {data.get('schema_fields')}")
    
    example_data = data.get('example_data', [])
    print(f"Number of Samples: {len(example_data)}")
    
    if example_data:
        print("\n--- First Sample Data Point ---")
        print(jsonify(example_data[0]).get_data(as_text=True))
        print("-------------------------------")

    # Send a successful response back to the extension
    return jsonify({
        "status": "success",
        "message": "Schema successfully ingested for processing.",
        "task_id": "OS-" + str(hash(data['source_url']) % 10000)
    }), 200

if __name__ == '__main__':
    # Run the server on the port specified in your popup.js (http://localhost:8000/)
    app.run(debug=True, port=8000)