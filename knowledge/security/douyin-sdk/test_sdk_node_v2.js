/**
 * Deep trace: Hook frontierSign to capture exact I/O.
 * Also capture the bytecode passed to the SDK.
 */
const fs = require("fs");
const path = require("path");

// Minimal browser polyfills for Node.js
global.window = global;
global.document = {
    cookie: "s_v_web_id=verify_test; device_web_cpu_core=8; device_web_memory_size=8",
    currentScript: null,
    createElement: () => ({}),
    addEventListener: () => {},
    removeEventListener: () => {},
    querySelectorAll: () => [],
    querySelector: () => null,
    referrer: "https://www.douyin.com/",
    hidden: false,
    visibilityState: "visible",
    createEvent: () => ({ initEvent: () => {} }),
    dispatchEvent: () => {},
    documentElement: { style: {} },
    head: { appendChild: () => {} },
    body: { appendChild: () => {} },
};
global.navigator = {
    userAgent: "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
    platform: "Win32",
    language: "zh-CN",
    languages: ["zh-CN", "zh"],
    hardwareConcurrency: 8,
    deviceMemory: 8,
    maxTouchPoints: 0,
    webdriver: false,
    cookieEnabled: true,
    doNotTrack: null,
    plugins: [],
    mimeTypes: [],
    vendor: "Google Inc.",
    productSub: "20030107",
    appVersion: "5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
    appName: "Netscape",
    appCodeName: "Mozilla",
};
global.location = {
    href: "https://www.douyin.com/",
    hostname: "www.douyin.com",
    host: "www.douyin.com",
    protocol: "https:",
    pathname: "/",
    search: "",
    hash: "",
    origin: "https://www.douyin.com",
    port: "",
    ancestorOrigins: [],
};
global.localStorage = {
    _data: {},
    getItem(k) { return this._data[k] || null; },
    setItem(k, v) { this._data[k] = String(v); },
    removeItem(k) { delete this._data[k]; },
    get length() { return Object.keys(this._data).length; },
    key(i) { return Object.keys(this._data)[i] || null; },
};
global.sessionStorage = { ...global.localStorage._data ? global.localStorage : { _data: {}, getItem(k) { return this._data[k] || null; }, setItem(k, v) { this._data[k] = v; } } };
global.performance = {
    now: () => Date.now(),
    timing: { navigationStart: Date.now() - 1000 },
    getEntriesByType: () => [],
    mark: () => {},
    measure: () => {},
};
global.XMLHttpRequest = class {
    open() {}
    send() {}
    setRequestHeader() {}
};
global.fetch = undefined;
global.Reflect = Reflect;
global.Proxy = Proxy;
global.setTimeout = setTimeout;
global.setInterval = setInterval;
global.clearTimeout = clearTimeout;
global.clearInterval = clearInterval;
global.console = console;
global.Symbol = Symbol;
global.Math = Math;
global.Date = Date;
global.JSON = JSON;
global.Object = Object;
global.Array = Array;
global.String = String;
global.Number = Number;
global.Boolean = Boolean;
global.RegExp = RegExp;
global.Error = Error;
global.Function = Function;
global.parseInt = parseInt;
global.parseFloat = parseFloat;
global.encodeURIComponent = encodeURIComponent;
global.decodeURIComponent = decodeURIComponent;
global.atob = (s) => Buffer.from(s, "base64").toString("binary");
global.btoa = (s) => Buffer.from(s, "binary").toString("base64");
global.Image = class {};
global.HTMLScriptElement = class {};
global.HTMLLinkElement = class {};
global.CSSStyleDeclaration = class { setProperty() {} };
global.getComputedStyle = () => ({});
global.matchMedia = () => ({ matches: false, addListener: () => {} });
global.screen = { width: 1920, height: 1080, colorDepth: 24, pixelDepth: 24 };
global.innerWidth = 1920;
global.innerHeight = 1080;
global.pageXOffset = 0;
global.pageYOffset = 0;

// Load the SDK
console.log("=== Loading webmssdk ===");
try {
    require("./webmssdk.es5.js");
    
    const sdkName = "_$webrt_1668687510";
    console.log(`SDK ${sdkName}: ${typeof global[sdkName]}`);
    
    if (typeof global[sdkName] === "function") {
        // The SDK is a factory function that takes 3 params
        // Let's try calling it with empty params
        console.log("\n=== Trying SDK(undefined, undefined, undefined) ===");
        try {
            const result = global[sdkName](undefined, undefined, undefined);
            console.log("Result:", typeof result, result);
        } catch(e) {
            console.log("Error:", e.message.slice(0, 200));
        }
        
        // Try with empty objects
        console.log("\n=== Trying SDK({}, {}, {}) ===");
        try {
            const result = global[sdkName]({}, {}, {});
            console.log("Result:", typeof result, result);
        } catch(e) {
            console.log("Error:", e.message.slice(0, 200));
        }
        
        // Try with string arrays
        console.log("\n=== Trying SDK([], {}, {}) ===");
        try {
            const result = global[sdkName]([], {}, {});
            console.log("Result:", typeof result, result);
        } catch(e) {
            console.log("Error:", e.message.slice(0, 200));
        }
    }
    
    // Check for any exports
    const exports = Object.keys(global).filter(k => 
        k.startsWith("_$") || k.includes("webrt") || k.includes("webmssdk") || 
        k.includes("frontierSign") || k.includes("byted")
    );
    console.log("\nExported globals:", exports);
    
} catch(e) {
    console.log("FATAL:", e.message.slice(0, 300));
    console.log("Stack:", (e.stack || "").slice(0, 500));
}
