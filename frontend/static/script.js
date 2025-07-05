// static/script.js

let ws; // Global WebSocket instance

async function fetchBackend(endpoint, traceparent) {
    document.getElementById('response-area').innerText = 'Fetching data...';
    try {
        const response = await fetch(endpoint, headers={"traceparent": traceparent});
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        const data = await response.json();
        document.getElementById('response-area').innerText = 
            'Response from HTTP Backend:\n' + JSON.stringify(data, null, 2);
    } catch (error) {
        document.getElementById('response-area').innerText = 'Error fetching backend: ' + error.message;
    }
}
