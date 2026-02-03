from google.adk.agents import Agent
from google.adk.tools.tool_context import ToolContext
from google.genai import types
import os
import subprocess

import wave
import numpy as np

async def mix_tracks_tool(file_paths: list, tool_context: ToolContext, master_volume: float = 1.0):
    """
    Mix multiple WAV files into a single output file using the wave module.
    """
    print(f"Mixing tracks: {', '.join(file_paths)} into master_mix.wav...")
    filename = "master_mix.wav"
    
    valid_paths = [p for p in file_paths if os.path.exists(p) and p.lower().endswith('.wav')]
    if not valid_paths:
        return "Error: No valid audio tracks found to mix."

    try:
        # Professional Additive Mixing using numpy
        tracks = []
        max_length = 0
        params = None
        
        for p in valid_paths:
            print(f"Loading track: {p}")
            with wave.open(p, 'rb') as w:
                p_params = w.getparams()
                if params is None:
                    params = p_params
                
                # Read all frames and convert to numpy array (assume 16-bit PCM)
                frames = w.readframes(w.getnframes())
                # 16-bit PCM: 'h' for signed short (2 bytes)
                audio_data = np.frombuffer(frames, dtype=np.int16)
                
                # Check for stereo/mono matching (simple approach: take first params)
                tracks.append(audio_data)
                if len(audio_data) > max_length:
                    max_length = len(audio_data)
        
        # Merge tracks (pad zeros for shorter tracks and sum)
        mixed_audio = np.zeros(max_length, dtype=np.float32)
        for t in tracks:
            mixed_audio[:len(t)] += t.astype(np.float32)
            
        # Clipping protection & Normalization
        # Simple limit to 16-bit range
        mixed_audio = np.clip(mixed_audio, -32768, 32767).astype(np.int16)
        
        # Write combined file
        with wave.open(filename, 'wb') as w_out:
            w_out.setparams(params)
            w_out.writeframes(mixed_audio.tobytes())
                
        # Read back for artifact saving
        with open(filename, 'rb') as f:
            master_data = f.read()

        print(f"Saving {filename} as ADK artifact with {len(valid_paths)} tracks...")
        await tool_context.save_artifact(
            filename=filename,
            artifact=types.Part.from_bytes(data=master_data, mime_type="audio/wav")
        )
        return f"Successfully mixed {len(valid_paths)} tracks into {filename}"
        
    except Exception as e:
        print(f"Mixing failed: {e}")
        return f"Error during audio mixing: {e}"

async def play_audio_tool(file_path: str, tool_context: ToolContext):
    """
    Register and display an audio file for manual playback in the ADK Web UI.
    """
    if not os.path.exists(file_path):
        return f"Error: File {file_path} not found."
    
    print(f"File {file_path} is ready for manual playback in the Artifacts tab.")
    return f"The audio file '{file_path}' is ready. Please find it in the Artifacts tab on the right to play or download manually."

agent = Agent(
    model='gemini-3-flash-preview',
    name='Audio_Engineer',
    instruction='''
    You are an expert mixing and mastering engineer.
    Your task is to take the generated audio tracks and combine them into a professional master.
    
    Capabilities:
    1. mix_tracks_tool: Combine multiple WAV files.
    2. play_audio_tool: Display a WAV file in the UI for the user to listen to manually.
    
    Workflow:
    - When tracks are ready, you can offer to show/play them.
    - When the final mix is ready, you MUST use play_audio_tool to show it to the user.
    - Do NOT mention automatic playback, as the user will play it manually in the UI.
    ''',
    tools=[mix_tracks_tool, play_audio_tool]
)
