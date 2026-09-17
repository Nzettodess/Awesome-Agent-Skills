# Post-Implementation & Replication Blueprint: Google Scotty Resumable Chunked Direct Upload (>50MB Files)

> **Purpose**: This document is a self-contained, granular replication blueprint. Any downstream AI agent or engineer can follow this document to reproduce, maintain, or port the exact same resumable large-file direct upload system with zero ambiguity.

---

## 1. Problem Statement & Root Cause Diagnosis

### A. The 50MB Limits
1. **Frontend DOM Validation**:
   The Gemini Enterprise web application (`vertexaisearch.cloud.google`) runs an Angular/Lit client that enforces client-side file picker validation:
   ```javascript
   if (file.size > 50 * 1024 * 1024) {
       // Renders `.file-container.error` with "File size exceeds 50 MB"
       // Disables the Send button before any network request is sent.
   }
   ```
2. **Playwright CDP WebSocket Buffer Crash**:
   When connecting to a detached background browser daemon via Chrome DevTools Protocol (`connect_over_cdp`), attempting to transfer >50MB binary payloads across the CDP WebSocket channel exceeds Playwright's IPC message limit, crashing the connection with socket resets.

### B. Why Monolithic HTTP Upload Failed
1. **Protocol Handshake**: Google's `UploadServer` (Scotty) does NOT accept raw file POSTs or `application/json` payloads. It requires the Google Resumable Upload protocol (`x-goog-upload-protocol: resumable`).
2. **Scotty Chunk Granularity**: Scotty strictly requires intermediate chunks to be an exact multiple of **256 KiB (`262,144` bytes)**. Slicing with non-standard buffer sizes results in HTTP 400 chunk alignment errors.
3. **MIME Whitelist**: Windows `mimetypes.guess_type` produces `audio/x-wav` or non-standard MIME types, causing Scotty's finalizer to abort with `HTTP 400: Unsupported file type`. Gemini Enterprise explicitly supports MP3 (`audio/mpeg`, up to 200 MB).

### C. Chunking Semantics
* **Transport-Layer Only**: Google's `UploadServer` reassembles all sequential chunks on the server side and commits **ONE single, unified file**.
* The finalize request yields a single `fileId`. Gemini reads the complete file as a single entity—identically to native web UI uploads.

---

## 2. Google Scotty Resumable Upload Protocol Reference

### Architecture Diagram
```
+---------------------+                       +---------------------------+
| Client / Page Fetch |                       | Google UploadServer       |
+---------------------+                       +---------------------------+
           |                                                |
           | 1. POST :uploadFile                            |
           |    x-goog-upload-protocol: resumable           |
           |    x-goog-upload-command: start                |
           |    x-goog-upload-header-content-length: <size> |
           |    x-goog-upload-file-name: <name>             |
           |    x-goog-upload-header-content-type: <mime>   |
           |----------------------------------------------->|
           |                                                |
           | 2. 200 OK                                      |
           |    x-goog-upload-url: <upload_url>             |
           |    x-goog-upload-chunk-granularity: 262144     |
           |<-----------------------------------------------|
           |                                                |
           | 3. POST <upload_url> (intermediate chunks)     |
           |    x-goog-upload-command: upload               |
           |    x-goog-upload-offset: <offset>              |
           |    Body: 8 MiB Uint8Array                      |
           |----------------------------------------------->|
           | 200 OK (x-goog-upload-status: active)          |
           |<-----------------------------------------------|
           |                                                |
           | 4. POST <upload_url> (final chunk)             |
           |    x-goog-upload-command: upload, finalize     |
           |    x-goog-upload-offset: <final_offset>        |
           |    Body: Remaining bytes                       |
           |----------------------------------------------->|
           |                                                |
           | 5. 200 OK                                      |
           |    {"fileId": "7932249799781516592"}           |
           |<-----------------------------------------------|
```

---

## 3. Granular Code Changes (Exact Drop-in Implementation)

### File: `geminion/core/direct_upload.py`

Replace the contents of `geminion/core/direct_upload.py` with the following implementation:

```python
import base64
import logging
import mimetypes
import os

logger = logging.getLogger("Geminion.DirectUpload")

CHUNK_SIZE = 8 * 1024 * 1024  # 8 MiB (exact multiple of 256 KiB / 262,144 bytes)


async def direct_upload_file(
    page, file_path: str, session_url_base: str, auth_headers: dict, worker_id: int = 1
) -> dict:
    """
    Directly uploads a file to Gemini Enterprise via the Google Resumable Upload protocol,
    bypassing the DOM file chooser dialog completely. Supports files of arbitrary size
    (>50MB, up to 200MB+ for audio/media) using 8 MiB chunked streaming.

    Returns:
        dict: {"fileId": str, "name": str, "mimeType": str, "size": int} or raises Exception.
    """
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"File not found for direct upload: {file_path}")

    file_name = os.path.basename(file_path)
    file_size = os.path.getsize(file_path)
    ext = os.path.splitext(file_path)[1].lower()
    
    # MIME Type Normalization for Google Enterprise Whitelist
    MIME_NORMALIZATION = {
        ".mp3": "audio/mpeg",
        ".mp4": "video/mp4",
        ".wav": "audio/wav",
        ".pdf": "application/pdf",
        ".txt": "text/plain",
        ".csv": "text/csv",
        ".json": "application/json",
        ".xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        ".pptx": "application/vnd.openxmlformats-officedocument.presentationml.presentation",
        ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
        ".png": "image/png",
    }
    mime_type = MIME_NORMALIZATION.get(ext)
    if not mime_type:
        mime_type, _ = mimetypes.guess_type(file_path)
    if mime_type == "audio/x-wav":
        mime_type = "audio/wav"
    elif mime_type == "audio/mp3":
        mime_type = "audio/mpeg"
    if not mime_type:
        mime_type = "application/octet-stream"

    auth_token = (
        auth_headers.get("Authorization") or auth_headers.get("authorization") or ""
    )
    if not auth_token:
        raise ValueError(
            "Missing required Authorization Bearer token for direct upload."
        )

    initiate_url = (
        session_url_base
        if session_url_base.endswith(":uploadFile")
        else f"{session_url_base}:uploadFile"
    )
    logger.info(
        f"[Worker {worker_id}] [DIRECT UPLOAD] Initiating upload for '{file_name}' ({file_size} bytes, {mime_type})..."
    )

    # Step 1: Resumable Upload Handshake
    handshake_js = """
    async ([initUrl, token, fileName, fileSizeStr, mimeType]) => {
        try {
            const headers = {
                'authorization': token,
                'content-type': 'application/x-www-form-urlencoded;charset=UTF-8',
                'referer': 'https://vertexaisearch.cloud.google/',
                'x-goog-upload-protocol': 'resumable',
                'x-goog-upload-command': 'start',
                'x-goog-upload-header-content-length': fileSizeStr,
                'x-goog-upload-file-name': fileName
            };
            if (mimeType && mimeType !== 'application/octet-stream') {
                headers['x-goog-upload-header-content-type'] = mimeType;
            }

            const resp = await fetch(initUrl, {
                method: 'POST',
                headers: headers,
                credentials: 'include'
            });

            const uploadUrl = resp.headers.get('x-goog-upload-url');
            if (!uploadUrl) {
                const errText = await resp.text();
                return { success: false, status: resp.status, error: `Handshake failed (${resp.status}): ${errText}` };
            }
            return { success: true, uploadUrl };
        } catch (e) {
            return { success: false, error: e.toString() };
        }
    }
    """

    handshake_res = await page.evaluate(
        handshake_js, [initiate_url, auth_token, file_name, str(file_size), mime_type]
    )

    if not handshake_res.get("success"):
        raise RuntimeError(
            f"Resumable upload handshake failed: {handshake_res.get('error')}"
        )

    upload_url = handshake_res["uploadUrl"]

    # Step 2: Sequential Chunked Upload
    upload_chunk_js = """
    async ([uploadUrl, token, fileName, chunkB64, offsetStr, isFinal]) => {
        try {
            const binStr = atob(chunkB64);
            const len = binStr.length;
            const bytes = new Uint8Array(len);
            for (let i = 0; i < len; i++) {
                bytes[i] = binStr.charCodeAt(i);
            }

            const command = isFinal ? 'upload, finalize' : 'upload';
            const resp = await fetch(uploadUrl, {
                method: 'POST',
                headers: {
                    'authorization': token,
                    'content-type': 'application/x-www-form-urlencoded;charset=utf-8',
                    'referer': 'https://vertexaisearch.cloud.google/',
                    'x-goog-upload-command': command,
                    'x-goog-upload-offset': offsetStr,
                    'x-goog-upload-file-name': fileName
                },
                body: bytes,
                credentials: 'include'
            });

            if (!resp.ok) {
                const errText = await resp.text();
                return { success: false, status: resp.status, error: `Chunk upload failed (${resp.status}): ${errText}` };
            }

            if (isFinal) {
                const data = await resp.json();
                return { success: true, isFinal: true, data };
            }
            return { success: true, isFinal: false };
        } catch (e) {
            return { success: false, error: e.toString() };
        }
    }
    """

    file_id = None
    with open(file_path, "rb") as f:
        offset = 0
        while offset < file_size:
            chunk = f.read(CHUNK_SIZE)
            chunk_len = len(chunk)
            is_final = (offset + chunk_len) >= file_size
            chunk_b64 = base64.b64encode(chunk).decode("ascii")

            logger.info(
                f"[Worker {worker_id}] [DIRECT UPLOAD] Streaming chunk: {offset}-{offset + chunk_len}/{file_size} bytes (final={is_final})..."
            )

            res = await page.evaluate(
                upload_chunk_js,
                [upload_url, auth_token, file_name, chunk_b64, str(offset), is_final],
            )

            if not res.get("success"):
                raise RuntimeError(
                    f"Chunk upload failed at offset {offset}: {res.get('error')}"
                )

            if is_final:
                file_id = res.get("data", {}).get("fileId")
                break

            offset += chunk_len

    if not file_id:
        raise ValueError(
            "Direct upload completed but response did not contain 'fileId'."
        )

    logger.info(
        f"[Worker {worker_id}] [DIRECT UPLOAD] ✅ Successfully uploaded '{file_name}' -> fileId: {file_id}"
    )
    return {
        "fileId": file_id,
        "name": file_name,
        "mimeType": mime_type,
        "size": file_size,
    }


async def direct_upload_multiple_files(
    page,
    file_paths: list,
    session_url_base: str,
    auth_headers: dict,
    worker_id: int = 1,
) -> list:
    """
    Uploads a list of files directly and returns a list of file metadata dictionaries.
    """
    uploaded_files = []
    for fp in file_paths:
        if fp and os.path.exists(fp):
            info = await direct_upload_file(
                page, fp, session_url_base, auth_headers, worker_id
            )
            uploaded_files.append(info)
    return uploaded_files
```

---

## 4. Testing & Verification Suite

### A. Unit Tests (`tests/mocktest/test_direct_api.py`)
Run the mock tests to verify 97%+ statement coverage without making live network calls:
```bash
pytest --cov=geminion.core.direct_upload tests/mocktest/test_direct_api.py
```

#### Mock Test Implementations to Include:
```python
@pytest.mark.asyncio
async def test_direct_upload_large_multichunk_mock():
    """Verify that files > 8 MiB stream across multiple sequential chunks with correct offsets."""
    page = AsyncMock()
    mock_auth = {"authorization": "Bearer test_token"}

    # Create a 17 MiB sparse test file: 2 full 8 MiB chunks + 1 MiB final chunk
    size_17mb = 17 * 1024 * 1024
    with tempfile.NamedTemporaryFile("wb", suffix=".mp3", delete=False) as f:
        f.seek(size_17mb - 1)
        f.write(b"\x00")
        tmp_path = f.name

    try:
        # Handshake, Chunk 0, Chunk 1, Chunk 2 (Final)
        page.evaluate = AsyncMock(
            side_effect=[
                {"success": True, "uploadUrl": "https://upload.url/sessions/multichunk"},
                {"success": True, "isFinal": False},
                {"success": True, "isFinal": False},
                {"success": True, "isFinal": True, "data": {"fileId": "file_multichunk_123"}},
            ]
        )

        res = await direct_upload_file(
            page=page,
            file_path=tmp_path,
            session_url_base="https://upload.test/sessions/mc",
            auth_headers=mock_auth,
            worker_id=1,
        )

        assert res["fileId"] == "file_multichunk_123"
        assert res["size"] == size_17mb
        assert res["mimeType"] == "audio/mpeg"
        assert page.evaluate.call_count == 4  # 1 handshake + 3 chunks
    finally:
        if os.path.exists(tmp_path):
            os.remove(tmp_path)


@pytest.mark.asyncio
async def test_direct_upload_mime_normalization():
    """Verify MIME normalization for .wav, .mp3, .pdf, and fallback extensions."""
    page = AsyncMock()
    mock_auth = {"Authorization": "Bearer tok"}

    for ext, expected_mime in [
        (".wav", "audio/wav"),
        (".mp3", "audio/mpeg"),
        (".pdf", "application/pdf"),
        (".unknownext123", "application/octet-stream"),
    ]:
        with tempfile.NamedTemporaryFile("wb", suffix=ext, delete=False) as f:
            f.write(b"SAMPLE")
            p = f.name

        try:
            page.evaluate = AsyncMock(
                side_effect=[
                    {"success": True, "uploadUrl": "https://upload.url"},
                    {"success": True, "isFinal": True, "data": {"fileId": "fid_mime"}},
                ]
            )
            res = await direct_upload_file(
                page=page,
                file_path=p,
                session_url_base="https://upload.test",
                auth_headers=mock_auth,
            )
            assert res["mimeType"] == expected_mime
        finally:
            if os.path.exists(p):
                os.remove(p)
```

### B. Live Verification Harnesses (No Model Prompting)

#### 1. Instant Synthetic >50MB MP3 Generator & Upload (`tests/realtest/test_large_file_upload.py`)
Tests multi-chunk streaming without needing external internet downloads:
```python
import asyncio
import logging
import os
import sys

from geminion.driver_network import GeminiNetworkDriver
from geminion.core.direct_client import DEFAULT_UPLOAD_BASE
from geminion.core.direct_upload import direct_upload_file
from geminion.core.network import NetworkStateTracker, setup_interception

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("TestLargeFileUpload")


def generate_55mb_test_mp3(file_path: str):
    """Generates valid 55.68MB MPEG-1 Layer 3 MP3 audio file."""
    total_frames = 140000
    frame = b"\xff\xfb\x90\x64" + b"\x00" * 413  # 417 bytes/frame (128kbps stereo)
    batch_size = 10000
    batch = frame * batch_size

    with open(file_path, "wb") as f:
        written = 0
        while written < total_frames:
            count = min(batch_size, total_frames - written)
            f.write(batch if count == batch_size else frame * count)
            written += count


async def run_large_file_upload_verification():
    audio_path = os.path.abspath("test_55mb_speech.mp3")
    try:
        generate_55mb_test_mp3(audio_path)

        driver = GeminiNetworkDriver()
        await driver.start(headless=True)

        try:
            page = driver.idle_pages[0] if getattr(driver, "idle_pages", None) else (await driver.context.new_page())
            tracker = NetworkStateTracker(worker_id=1)
            await setup_interception(page, tracker)

            await page.goto("https://gemini.zebra.com", wait_until="networkidle", timeout=60000)
            await asyncio.sleep(3.0)

            auth_token = tracker.auth_headers.get("Authorization")
            if not auth_token:
                logger.error("Failed to capture active Bearer token.")
                return

            session_id = "4004441143272302691"
            session_resource = f"collections/default_collection/engines/gemini-enterprise-producti_1760472513812/sessions/{session_id}"
            session_url_base = f"{DEFAULT_UPLOAD_BASE}/projects/342265864253/locations/global/{session_resource}"

            # STRICT REQUIREMENT: Only test file upload protocol. Do NOT prompt model.
            result = await direct_upload_file(
                page=page,
                file_path=audio_path,
                session_url_base=session_url_base,
                auth_headers={"Authorization": auth_token},
                worker_id=1,
            )

            logger.info(f"✅ UPLOAD SUCCESSFUL! Assigned fileId: {result.get('fileId')}")

        finally:
            await driver.close()

    finally:
        if os.path.exists(audio_path):
            os.remove(audio_path)


if __name__ == "__main__":
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())
    asyncio.run(run_large_file_upload_verification())
```

#### 2. Real Downloaded Human Speech MP3 (59.61 MB)
* **File**: `adventureholmes_01_doyle.mp3` (from LibriVox / Archive.org, `https://archive.org/download/adventures_holmes/adventureholmes_01_doyle.mp3`).
* **Test script**: [`tests/realtest/test_real_downloaded_mp3_upload.py`](file:///e:/Git%20Repo/GE-Web-API/tests/realtest/test_real_downloaded_mp3_upload.py)

---

## 5. Proven Live Verification Results

Both test cases were verified live against Google's Scotty UploadServer:

1. **Synthetic 55.68 MB MP3 Audio**:
   - Transferred: `58,380,000` bytes across 7 sequential chunks (0 to 58,380,000 bytes).
   - HTTP Status: **200 OK**
   - Assigned fileId: `7932249799781516592`
   - Prompt sent: **None (Zero prompts)**

2. **Real Downloaded 59.61 MB Spoken Voice MP3**:
   - Transferred: `62,507,949` bytes across 8 sequential chunks (0 to 62,507,949 bytes).
   - HTTP Status: **200 OK**
   - Assigned fileId: `10139517412840021647`
   - Prompt sent: **None (Zero prompts)**

