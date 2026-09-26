// CONFIG-01: Backend API URL — dynamically resolved at runtime.
//
// ─── HOW TO SET YOUR BACKEND URL ───────────────────────────────────────────
//
// OPTION A (Recommended for Netlify) — Set the override below:
//   Replace null with your Render/Railway/backend URL string, e.g.:
//   var PRODUCTION_BACKEND_URL = "https://forensix-backend.onrender.com";
//
// OPTION B — Set a Netlify environment variable FORENSIX_API_BASE_OVERRIDE
//   via netlify.toml [[headers]] or the Netlify dashboard.
//
// Local development (localhost / 127.0.0.1):
//   Automatically resolves to http://<hostname>:8000 — no changes needed.
//
// ─────────────────────────────────────────────────────────────────────────────

(function () {
  "use strict";

  // ⬇️  CHANGE THIS to your deployed backend URL when hosting on Netlify/Render.
  // Leave as null to use automatic detection.
  var PRODUCTION_BACKEND_URL = "https://forensix-kypq.onrender.com";
  // Example: var PRODUCTION_BACKEND_URL = "https://forensix-backend.onrender.com";

  var hostname = window.location.hostname;
  var isLocal = (hostname === "localhost" || hostname === "127.0.0.1");

  // Priority 1: Hardcoded production URL (set above)
  if (PRODUCTION_BACKEND_URL) {
    window.FORENSIX_API_BASE = PRODUCTION_BACKEND_URL;
    return;
  }

  // Priority 2: Server-injected override (nginx / CDN header trick)
  if (typeof window.FORENSIX_API_BASE_OVERRIDE !== "undefined") {
    window.FORENSIX_API_BASE = window.FORENSIX_API_BASE_OVERRIDE;
    return;
  }

  // Priority 3: Local development — auto-detect port 8000
  if (isLocal) {
    window.FORENSIX_API_BASE = window.location.protocol + "//" + hostname + ":8000";
    return;
  }

  // Priority 4: Deployed but no override set — warn developer
  window.FORENSIX_API_BASE = window.location.protocol + "//" + hostname + ":8000";
  console.warn(
    "[ForensiX] Production deployment detected but PRODUCTION_BACKEND_URL is not set in config.js. " +
    "Edit frontend/js/config.js and set PRODUCTION_BACKEND_URL to your backend URL " +
    "(e.g. https://forensix-backend.onrender.com)."
  );
}());
