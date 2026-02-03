from google.adk.agents import Agent
from google.adk.tools.tool_context import ToolContext
from google.genai import types
import base64
import os
import requests
import json
import google.auth
import google.auth.transport.requests

async def generate_audio_tool(prompt: str, instrument: str, tool_context: ToolContext):
    """
    Generate high-fidelity audio using the Google Lyria 2 model (lyria-002) via REST API on Vertex AI.
    """
    project_id = os.getenv("GOOGLE_CLOUD_PROJECT")
    location = os.getenv("LYRIA_LOCATION", "us-central1")
    
    if not project_id:
        return "Error: GOOGLE_CLOUD_PROJECT environment variable not set."

    max_retries = 2
    attempt = 0
    
    while attempt <= max_retries:
        print(f"String Expert requesting Lyria 2 synthesis (Attempt {attempt + 1})...")
        try:
            # Get credentials and refresh token
            credentials, project = google.auth.default()
            auth_req = google.auth.transport.requests.Request()
            credentials.refresh(auth_req)
            access_token = credentials.token

            # Vertex AI Lyria 2 Endpoint
            url = f"https://{location}-aiplatform.googleapis.com/v1/projects/{project_id}/locations/{location}/publishers/google/models/lyria-002:predict"
            
            headers = {
                "Authorization": f"Bearer {access_token}",
                "Content-Type": "application/json"
            }
            
            payload = {
                "instances": [{"prompt": prompt}],
                "parameters": {"sample_count": 1}
            }

            response = requests.post(url, headers=headers, json=payload, timeout=90)
            
            if response.status_code == 200:
                result = response.json()
                print("--- LYRIA 2 RAW RESPONSE (STRING) START ---")
                # print(json.dumps(result, indent=2))
                print("--- LYRIA 2 RAW RESPONSE (STRING) END ---")
                predictions = result.get('predictions', [])
                
                # Support both 'audioContent' and 'bytesBase64Encoded'
                audio_b64 = None
                if predictions:
                    audio_b64 = predictions[0].get('bytesBase64Encoded') or predictions[0].get('audioContent')
                
                if audio_b64:
                    audio_data = base64.b64decode(audio_b64)
                    # Sanitize filename: no commas, no spaces
                    clean_inst = instrument.lower().replace(',', '').replace(' ', '_')
                    filename = f"output_{clean_inst}.wav"
                    
                    await tool_context.save_artifact(
                        filename=filename,
                        artifact=types.Part.from_bytes(data=audio_data, mime_type="audio/wav")
                    )
                    
                    # Save sidecar metadata artifact for UI
                    metadata = {
                        "prompt": prompt,
                        "instrument": instrument,
                        "type": "audio_chunk"
                    }
                    metadata_json = json.dumps(metadata, indent=2).encode('utf-8')
                    await tool_context.save_artifact(
                        filename=f"{filename}.json",
                        artifact=types.Part.from_bytes(data=metadata_json, mime_type="application/json")
                    )
                    
                    with open(filename, 'wb') as f:
                        f.write(audio_data)
                        
                    return f"Successfully generated {instrument} track using prompt: '{prompt}' (File: {filename}). You can play it from the Artifacts tab."
                else:
                    print(f"Warning: Lyria 2 returned empty predictions (possible safety filter block).")
                    return "ERROR: PROMPT_FILTERED: The prompt was blocked by safety filters. Please rewrite it to be more compliant and descriptive, avoiding sensitive terms, and try again."
            
            elif response.status_code in [429, 500, 503]:
                print(f"Lyria 2 API error ({response.status_code}). Retrying internally...")
                if attempt < max_retries:
                    attempt += 1
                    continue
                return f"Error: Lyria 2 API intermittent failure after {max_retries} retries."
            else:
                return f"Lyria 2 API Critical Error (Status {response.status_code}): {response.text}"

        except Exception as e:
            print(f"Exception during Lyria 2 attempt {attempt + 1}: {str(e)}")
            if attempt < max_retries:
                attempt += 1
                continue
            return f"Exception in Lyria 2 synthesis: {str(e)}"
    
    return "Error: Maximum retries reached for Lyria 2 synthesis."

agent = Agent(
    model='gemini-3-flash-preview',
    name='String_Expert',
    instruction='''
    You specialize in orchestral strings, violins, cellos, and cinematic pads.
    Your main tool is generate_audio_tool which calls the Lyria 2 model.
    
    SELF-HEALING WORKFLOW:
    1. Call generate_audio_tool with a descriptive prompt.
    2. If the tool returns "ERROR: PROMPT_FILTERED", do NOT give up.
    3. Analyze the error and your original prompt. Identify words that might be problematic (e.g., specific IPs, copyrighted names, or violent imagery).
    4. Rewrite the prompt using more technical or atmospheric musical terms while keeping the original vibe.
    5. Call generate_audio_tool again with the optimized prompt.
    6. Ensure the process is smooth and report only the successful track to the Orchestrator.
    ''',
    tools=[generate_audio_tool]
)
