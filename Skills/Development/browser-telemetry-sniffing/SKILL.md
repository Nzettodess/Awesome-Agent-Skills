---
name: browser-telemetry-sniffing
description: Practical workflows, probing methodology, and troubleshooting decision tree for reverse-engineering undocumented Single-Page Application (SPA) HTTP/SSE endpoints, passive network sniffing via Chrome DevTools Protocol (CDP), and implementing resilient resumable HTTP uploads without mutating server-side state.
---

# Browser Telemetry Sniffing & API Reverse Engineering

This skill provides a systematic, deterministic workflow for discovering, inspecting, probing, and replicating private REST/RPC endpoints used by modern enterprise Single-Page Applications (SPAs)—such as Google Cloud Vertex AI Search, Gemini Enterprise, and internal cloud portals—without sending unauthorized prompts or mutating server-side state.

---

## 1. Core Philosophy: Why Sniff Instead of Guessing?

Modern cloud enterprise SPAs enforce complex security mechanisms:
* **Dynamic WAA / Workforce Identity JWTs**: Ephemeral Bearer tokens bound to specific sessions (`csesidx`).
* **Origin & Cross-Domain Security (XD3)**: Strict validation of `Origin`, `Referer`, and `Sec-Fetch-*` metadata.
* **Custom Transport Protocols**: Protocols like Google's Scotty Resumable Upload that require multi-step handshakes, 256 KiB chunk boundary alignments, and specific header commands (`start`, `upload`, `finalize`).

**Attempting to guess endpoint URLs, headers, or payloads wastes hours in trial and error.** Passive telemetry sniffing captures the **verbatim ground truth** directly from active browser execution.

---

## 2. The 5-Step Sniffing & Probing Methodology

When reverse-engineering an undocumented endpoint, execute this strict sequence:

```
+-------------------------------------------------------------------------------+
| Step 1: Passive Traffic Sniffer (Capture real browser interactions)          |
+-------------------------------------------------------------------------------+
                                      │
                                      ▼
+-------------------------------------------------------------------------------+
| Step 2: Minimal Non-Destructive UI Trigger (e.g. upload 10-byte test file)    |
+-------------------------------------------------------------------------------+
                                      │
                                      ▼
+-------------------------------------------------------------------------------+
| Step 3: In-Page Diagnostic Fetch Probe (Verify call works in page origin)    |
+-------------------------------------------------------------------------------+
                                      │
                                      ▼
+-------------------------------------------------------------------------------+
| Step 4: Protocol Dissection & Header Isolation (Identify required headers)   |
+-------------------------------------------------------------------------------+
                                      │
                                      ▼
+-------------------------------------------------------------------------------+
| Step 5: Chunked Transport & IPC Buffer Hardening (Scale to >50MB files)       |
+-------------------------------------------------------------------------------+
```

### Step 1: Passive Traffic Sniffer
* **Why**: Intercepts exact requests without altering browser behavior or alerting anti-bot systems.
* **How**: Attach listeners to Playwright's `page.on("request")` and `page.on("response")` before any action.
* **Filtering**: Strip out static noise (`.svg`, `.png`, `.woff`, `.css`) to isolate target API endpoints.

```python
async def setup_sniffing(page, target_keywords: list):
    sniffed_events = []

    async def on_request(req):
        url = req.url
        if any(ext in url for ext in [".woff", ".ttf", ".svg", ".png", ".css", ".ico"]):
            return
        if any(kw in url.lower() for kw in target_keywords):
            sniffed_events.append({
                "type": "REQUEST",
                "method": req.method,
                "url": url,
                "headers": dict(req.headers),
                "post_data": req.post_data,
            })

    async def on_response(res):
        url = res.url
        if any(kw in url.lower() for kw in target_keywords):
            try:
                body = await res.text()
            except Exception:
                body = "<binary/unreadable>"
            sniffed_events.append({
                "type": "RESPONSE",
                "status": res.status,
                "url": url,
                "headers": dict(res.headers),
                "body": body,
            })

    page.on("request", on_request)
    page.on("response", on_response)
    return sniffed_events
```

### Step 2: Minimal Non-Destructive UI Trigger
* **Why**: To see what the frontend sends without triggering heavy server processing or consuming quotas.
* **How**: 
  - For file uploads: stage a tiny 10-byte `.txt` file (`b"HELLO_SNIFF_TEST"`).
  - For query endpoints: trigger harmless state changes (e.g. click "New Chat" or inspect existing session lists).
  - **NEVER** submit actual prompt queries (`widgetStreamAssist`) during discovery.

### Step 3: In-Page Diagnostic Fetch Probe
* **Why**: Proves whether an HTTP request works from **inside the authenticated browser session**.
* **How**: Use `page.evaluate()` to dispatch `fetch()` with the exact sniffed headers.
* **Decision**:
  - If in-page `fetch()` **succeeds (HTTP 200)**: Authentication, session ID, and payload schema are 100% correct. Any failure from an external Python script (`httpx`/`requests`) is due to missing browser headers (`Cookie`, `Origin`, `Referer`, `Sec-Fetch-*`).
  - If in-page `fetch()` **fails (HTTP 4xx/5xx)**: The payload, endpoint URL, or header structure is fundamentally invalid.

### Step 4: Protocol Dissection (Scotty Resumable Upload)
When inspecting upload endpoints, examine the response headers:
1. `x-goog-upload-url`: Dedicated upload session URL (contains `upload_id=...`).
2. `x-goog-upload-chunk-granularity`: Required chunk boundary alignment (e.g., `262144` = 256 KiB).
3. `x-goog-upload-status`: `active` indicates the session is ready for chunk streaming.

### Step 5: Chunked Transport & IPC Buffer Hardening
* **Why**: Playwright CDP WebSocket channels fail on payloads >50MB. Angular/Lit client-side validators reject files >50MB in `<input type="file">`.
* **How**: Read files from disk in exact 8 MiB (`8,388,608` bytes = 32 × 256 KiB) slices, encode each slice to Base64, convert to `Uint8Array` in-browser, and stream sequentially.

---

## 3. HTTP Sniffing & Upload Troubleshooting Decision Tree

Follow this deterministic logic tree whenever diagnosing API/HTTP failures:

```
[HTTP Response Received]
  │
  ├─► Status == 200 OK
  │     ├─► Check response headers for `x-goog-upload-url` (Handshake complete)
  │     ├─► Check `x-goog-upload-status: active` (Chunk received successfully)
  │     └─► Check body for `{"fileId": "..."}` (Finalize complete -> Return fileId)
  │
  ├─► Status == 401 Unauthorized
  │     ├─► IF token expired:
  │     │     Reload page or navigate to app root to capture fresh Bearer token.
  │     └─► IF token missing prefix:
  │           Ensure `Authorization: Bearer <jwt>` format.
  │
  ├─► Status == 403 Forbidden
  │     ├─► IF executing from external client (Python httpx/requests):
  │     │     Endpoint requires browser context. Move execution inside `page.evaluate(fetch)`.
  │     ├─► IF `credentials: 'include'` missing:
  │     │     Add session cookie credentials to in-page fetch.
  │     └─► IF session ID mismatch:
  │           Verify `session_id` belongs to the active authenticated user profile.
  │
  ├─► Status == 400 Bad Request
  │     ├─► IF body contains "Unsupported file type":
  │     │     Server MIME whitelist rejection!
  │     │     -> Map `.wav` to `audio/wav` (never `audio/x-wav`).
  │     │     -> For audio >50MB, use `.mp3` (`audio/mpeg`, up to 200MB limit).
  │     │     -> Pass `x-goog-upload-header-content-type: <mime>` in handshake.
  │     │
  │     ├─► IF body contains "Granularity" or "Chunk alignment":
  │     │     Chunk size is NOT a multiple of 262,144 bytes.
  │     │     -> Set `CHUNK_SIZE = 8 * 1024 * 1024` (8 MiB = 32 * 256 KiB).
  │     │
  │     ├─► IF body contains "Invalid content length":
  │     │     Length header was calculated from Base64 string length instead of raw bytes!
  │     │     -> Use exact `os.path.getsize(file_path)`.
  │     │
  │     └─► IF body contains "Offset mismatch":
  │           Verify `x-goog-upload-offset` strictly equals previous `offset + chunk_length`.
  │
  └─► Browser CDP Disconnect / WebSocket Crash (No HTTP Status)
        ├─► IF file size > 50MB:
        │     Playwright CDP IPC frame buffer exhausted by monolithic payload!
        │     -> DO NOT use `page.set_input_files()` for files > 50MB.
        │     -> DO NOT send monolithic Base64 string over CDP.
        │     -> Stream sequentially in 8 MiB slices via `direct_upload_file()`.
        │
        └─► IF browser DOM displays "File size exceeds 50 MB":
              Angular/Lit client-side DOM validation blocked file staging.
              -> Completely bypass DOM by posting directly to Google Scotty endpoint.
```

---

## 4. Google Scotty Resumable Upload Specification

### Sequence Diagram
```
Client (Page Fetch)                         Google Scotty UploadServer
       │                                                │
       │ 1. Handshake POST :uploadFile                  │
       │    content-type: application/x-www-form-urlencoded;charset=UTF-8
       │    x-goog-upload-protocol: resumable           │
       │    x-goog-upload-command: start                │
       │    x-goog-upload-header-content-length: <size> │
       │    x-goog-upload-file-name: <filename>         │
       │    x-goog-upload-header-content-type: <mime>   │
       │───────────────────────────────────────────────>│
       │                                                │
       │ 2. 200 OK                                      │
       │    x-goog-upload-url: <upload_url>             │
       │    x-goog-upload-chunk-granularity: 262144     │
       │<───────────────────────────────────────────────│
       │                                                │
       │ 3. Chunk POST <upload_url>                     │
       │    x-goog-upload-command: upload               │
       │    x-goog-upload-offset: 0                     │
       │    Body: 8 MiB binary slice (Uint8Array)       │
       │───────────────────────────────────────────────>│
       │ 200 OK (x-goog-upload-status: active)          │
       │<───────────────────────────────────────────────│
       │                                                │
       │ 4. Final Chunk POST <upload_url>               │
       │    x-goog-upload-command: upload, finalize     │
       │    x-goog-upload-offset: <final_offset>        │
       │    Body: Remaining binary bytes                │
       │───────────────────────────────────────────────>│
       │                                                │
       │ 5. 200 OK                                      │
       │    {"fileId": "10139517412840021647"}          │
       │<───────────────────────────────────────────────│
```

---

## 5. Standard MIME Type Normalization Table

Windows registry frequently maps audio extensions to obsolete MIME strings (`audio/x-wav`). Always normalize against this whitelist before dispatching the handshake:

| Extension | Normalized MIME Type | Max Size Limit (Google Enterprise) |
|---|---|---|
| `.mp3` | `audio/mpeg` | **200 MB** |
| `.mp4` | `video/mp4` | **200 MB** |
| `.pdf` | `application/pdf` | **100 MB** |
| `.pptx` | `application/vnd.openxmlformats-officedocument.presentationml.presentation` | **100 MB** |
| `.xlsx` | `application/vnd.openxmlformats-officedocument.spreadsheetml.sheet` | **50 MB** |
| `.docx` | `application/vnd.openxmlformats-officedocument.wordprocessingml.document` | **3 MB** |
| `.txt`, `.csv` | `text/plain`, `text/csv` | **7 MB** |
| `.wav` | `audio/wav` *(normalize from `audio/x-wav`)* | Varies |
