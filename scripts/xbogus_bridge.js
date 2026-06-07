#!/usr/bin/env node
/**
 * X-Bogus signing bridge for ChinaCrawl Douyin adapter.
 * Usage: node xbogus_bridge.js <query_string> [user_agent]
 *
 * Generates X-Bogus signature for douyin web API requests.
 * Outputs the signature string to stdout (exit 0) or nothing (exit 1).
 */

const xbogus = require("xbogus");

const DEFAULT_UA =
  "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36";

const args = process.argv.slice(2);

if (args.length < 1) {
  console.error("Usage: node xbogus_bridge.js <query_string> [user_agent]");
  process.exit(1);
}

const queryString = args[0];
const userAgent = args[1] || DEFAULT_UA;

try {
  const signature = xbogus(queryString, userAgent);
  if (!signature) {
    process.exit(1);
  }
  process.stdout.write(signature);
} catch (err) {
  console.error("X-Bogus signing error:", err.message);
  process.exit(1);
}
