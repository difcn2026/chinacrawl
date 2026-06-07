// xbogus_bridge.js — Node.js bridge for X-Bogus signing
// Usage: node xbogus_bridge.js "<query_string>" "<user_agent>"
// Outputs: X-Bogus value to stdout

const xbogus = require('xbogus');

const queryString = process.argv[2];
const userAgent = process.argv[3] || 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36';

if (!queryString) {
    console.error('Usage: node xbogus_bridge.js "<query_string>" "[user_agent]"');
    process.exit(1);
}

try {
    const result = xbogus(queryString, userAgent);
    console.log(result);
} catch (e) {
    console.error('Error:', e.message);
    process.exit(1);
}
