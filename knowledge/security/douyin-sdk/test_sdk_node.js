// Test: Run webmssdk in Node.js with polyfills
global.window = global;
global.document = { 
    cookie: "",
    currentScript: null,
    createElement: () => ({}),
    addEventListener: () => {},
    querySelectorAll: () => [],
    referrer: "https://www.douyin.com/",
};
global.navigator = { 
    userAgent: "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
    platform: "Win32",
    language: "zh-CN",
    hardwareConcurrency: 8,
    deviceMemory: 8,
};
global.location = { 
    href: "https://www.douyin.com/",
    hostname: "www.douyin.com",
    protocol: "https:",
    pathname: "/",
};
global.localStorage = {
    _data: {},
    getItem(k) { return this._data[k] || null; },
    setItem(k, v) { this._data[k] = v; },
};
global.XMLHttpRequest = function() {};
global.fetch = undefined;
global.Reflect = Reflect;
global.Proxy = Proxy;

// Load the SDK
try {
    require("./webmssdk.es5.js");
    console.log("=== SDK Loaded ===");
    
    // Check what was exported
    const sdkName = Object.keys(global).find(k => k.includes("_$webrt") || k.includes("webmssdk") || k.includes("1668687510"));
    console.log("SDK key:", sdkName);
    
    if (sdkName && global[sdkName]) {
        const sdk = global[sdkName];
        console.log("SDK type:", typeof sdk);
        console.log("SDK keys:", Object.keys(sdk).slice(0, 20));
        
        if (typeof sdk === "function") {
            // Try to call it
            try {
                const instance = sdk();
                console.log("Instance type:", typeof instance);
                console.log("Instance keys:", Object.keys(instance || {}).slice(0, 20));
            } catch(e) {
                console.log("SDK call error:", e.message.slice(0, 200));
            }
        }
    }
    
    // Check for other globals
    const securityGlobals = Object.keys(global).filter(k => 
        k.includes("web") || k.includes("ms") || k.includes("byted") || 
        k.includes("sec") || k.includes("sign") || k.includes("_$")
    );
    console.log("\nSecurity globals:", securityGlobals);
    
} catch(e) {
    console.log("Error:", e.message.slice(0, 300));
    console.log("Stack:", (e.stack || "").slice(0, 800));
}
