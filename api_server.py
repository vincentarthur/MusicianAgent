import os
import httpx
import json
import logging
import base64
import re
from fastapi import FastAPI, Request, HTTPException, Response
from fastapi.responses import HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("PremiumBridge")

app = FastAPI(title="MusicianAgent Premium Bridge")

# Enable CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# ADK Configuration
ADK_API_BASE = "http://localhost:8000"
APP_NAME = "orchestrator"
USER_ID = "musician_user"

@app.get("/", response_class=HTMLResponse)
async def get_index():
    logger.info("Serving index.html")
    try:
        with open("index.html", "r") as f:
            return f.read()
    except Exception as e:
        logger.error(f"Failed to read index.html: {e}")
        return HTMLResponse(content="<h1>Error: index.html not found</h1>", status_code=500)

@app.post("/proxy/sessions/{session_id}")
async def create_session_proxy(session_id: str):
    """
    Explicitly create a session on the ADK server.
    """
    logger.info(f"Creating session: {session_id}")
    session_url = f"{ADK_API_BASE}/apps/{APP_NAME}/users/{USER_ID}/sessions/{session_id}"
    async with httpx.AsyncClient() as client:
        try:
            resp = await client.post(session_url, json={"project_name": "Premium Project Early Init"})
            logger.info(f"ADK Session Response: {resp.status_code}")
            if resp.status_code not in [200, 201, 409]:
                logger.error(f"ADK Session Error: {resp.text}")
                raise HTTPException(status_code=resp.status_code, detail=resp.text)
            return {"status": "created", "sessionId": session_id, "userId": USER_ID, "appName": APP_NAME}
        except Exception as e:
            logger.error(f"Connection failed: {e}")
            raise HTTPException(status_code=503, detail=f"ADK Server unreachable: {str(e)}")

@app.post("/proxy/sessions/{session_id}/run")
async def proxy_run(session_id: str, request: Request):
    """
    Proxy the user prompt to the ADK API server using run_sse with streaming=false.
    """
    body = await request.json()
    prompt = body.get("text")
    logger.info(f"Executing prompt for session {session_id}: {prompt}")
    
    # ADK run_sse endpoint (as per User's screenshot recommendation)
    url = f"{ADK_API_BASE}/run_sse"
    
    payload = {
        "appName": APP_NAME,
        "userId": USER_ID,
        "sessionId": session_id,
        "newMessage": {
            "role": "user",
            "parts": [{"text": prompt}]
        },
        "streaming": False
    }
    
    async with httpx.AsyncClient() as client:
        try:
            logger.info(f"Forwarding to ADK run_sse: {url}")
            resp = await client.post(url, json=payload, timeout=120.0)
            logger.info(f"ADK run_sse status: {resp.status_code}")
            
            if resp.status_code != 200:
                logger.error(f"ADK execution failed: {resp.text}")
                raise HTTPException(status_code=resp.status_code, detail=resp.text)
            
            # Parse SSE response
            content = resp.text
            final_data = None
            for line in content.splitlines():
                if line.startswith("data: "):
                    try:
                        final_data = json.loads(line[6:])
                    except:
                        continue
            
            if final_data:
                return final_data
            return {"status": "success", "raw": content}

        except httpx.ReadTimeout:
            logger.error("ADK Synthesis Timed Out")
            raise HTTPException(status_code=504, detail="Generation timed out")
        except Exception as e:
            logger.error(f"Proxy internal error: {e}")
            raise HTTPException(status_code=500, detail=str(e))

@app.get("/proxy/sessions/{session_id}/status")
async def proxy_status(session_id: str):
    """
    Proxy artifacts and session state.
    Normalizes ADK's plain list response to the structured format expected by UI.
    """
    url = f"{ADK_API_BASE}/apps/{APP_NAME}/users/{USER_ID}/sessions/{session_id}/artifacts"
    async with httpx.AsyncClient() as client:
        try:
            resp = await client.get(url)
            if resp.status_code != 200:
                logger.warning(f"Failed to fetch artifacts for {session_id}: {resp.status_code}")
                return {"artifacts": []}
            
            data = resp.json()
            # ADK returns [ "file1.wav", "file2.wav" ]
            # UI expects { "artifacts": [ {"name": "file1.wav"}, ... ] }
            if isinstance(data, list):
                normalized = {"artifacts": [{"name": name} for name in data]}
                return normalized
            return data
        except Exception as e:
            logger.error(f"Error in proxy_status: {e}")
            return {"artifacts": []}

def robust_b64decode(b64_str: str) -> bytes:
    """
    Decodes base64 string while handling non-alphabet chars and padding issues.
    """
    # Remove all non-base64 characters
    clean_str = re.sub(r'[^a-zA-Z0-9+/=]', '', b64_str)
    
    # Base64 length cannot be 1 more than a multiple of 4
    if len(clean_str) % 4 == 1:
        logger.warning(f"Base64 string length {len(clean_str)} is 1 mod 4. Truncating last character.")
        clean_str = clean_str[:-1]
        
    # Add padding if missing
    padding = len(clean_str) % 4
    if padding:
        clean_str += "=" * (4 - padding)
        
    return base64.b64decode(clean_str)

@app.get("/proxy/sessions/{session_id}/artifacts/{filename}")
async def proxy_artifact(session_id: str, filename: str):
    """
    Proxy artifact content with Local and FS Priority.
    """
    # 1. PRIORITY: Check direct ADK filesystem storage (most reliable, avoids b64 encoding errors)
    # Path pattern: agents/.adk/artifacts/users/{USER_ID}/sessions/{session_id}/artifacts/{filename}/versions/0/{filename}
    adk_fs_path = f"agents/.adk/artifacts/users/{USER_ID}/sessions/{session_id}/artifacts/{filename}/versions/0/{filename}"
    
    if os.path.exists(adk_fs_path):
        logger.info(f"Serving {filename} directly from ADK storage: {adk_fs_path}")
        m_type = "image/png" if filename.endswith('.png') else "audio/wav"
        if filename.endswith('.json'): m_type = "application/json"
        
        with open(adk_fs_path, 'rb') as f:
            return Response(content=f.read(), media_type=m_type)

    # 2. Fallback: Try root directory (legacy agent behavior)
    if os.path.exists(filename):
        logger.info(f"Serving {filename} from root storage (Legacy Fallback)")
        with open(filename, 'rb') as f:
            return Response(content=f.read(), media_type="audio/wav")

    # 3. Last Resort: Proxy via ADK API (requires b64 decoding)
    url = f"{ADK_API_BASE}/apps/{APP_NAME}/users/{USER_ID}/sessions/{session_id}/artifacts/{filename}"
    async with httpx.AsyncClient() as client:
        try:
            resp = await client.get(url)
            if resp.status_code == 200:
                data_json = resp.json()
                b64_content = data_json.get("inlineData", {}).get("data")
                m_type = data_json.get("inlineData", {}).get("mimeType", "audio/wav")
                
                if b64_content:
                    try:
                        raw_bytes = robust_b64decode(b64_content)
                        return Response(content=raw_bytes, media_type=m_type)
                    except Exception as de_err:
                        logger.error(f"ADK Decode failed for {filename}: {de_err}")
        except Exception as e:
            logger.error(f"ADK Proxy error for {filename}: {e}")

    logger.error(f"Artifact {filename} NOT FOUND in ADK FS, root, or API.")
    raise HTTPException(status_code=404, detail="Artifact not found")

if __name__ == "__main__":
    logger.info(f"Starting Premium Bridge on :8080. Target ADK on {ADK_API_BASE}")
    uvicorn.run(app, host="0.0.0.0", port=8080)
