from google.adk.agents import Agent
from common.models import MusicSessionState, Track
from musicologist.agent import agent as musicologist
from percussion_expert.agent import agent as percussion_expert
from string_expert.agent import agent as string_expert
from audio_engineer.agent import agent as audio_engineer

def music_theory_alignment_tool(project_state: MusicSessionState):
    """
    Delegate music theory verification to the Musicologist Agent.
    """
    print(f"Orchestrator consulting Musicologist...")
    return True

root_agent = Agent(
    model='gemini-3-flash-preview',
    name='Music_Orchestrator',
    instruction='''
    You are the "Maestro" of a professional music studio.
    Receive user requests and decompose them into specific instrument tracks.
    Maintain global music characteristics (BPM, Key) in the session state.
    
    WORKFLOW:
    1. Consult Musicologist for BPM and Key.
    2. Delegate Percussion and String generation. 
    3. IMPORTANT: When sub-agents return a track, SOCIALIZE the "prompt_used" they report so the user can see it.
    4. COLLECT all generated filenames.
    5. Once ALL requested tracks are ready, pass the ENTIRE list of filenames to the Audio Engineer's "mix_tracks_tool".
    
    CRITICAL: Sub-agents MUST use their "generate_audio_tool". You must wait for their confirmation before mixing.
    
    You have access to the following sub-agents:
    - Musicologist: For theory and structural review.
    - Percussion_Expert: for rhythm (Must use generate_audio_tool).
    - String_Expert: for melody (Must use generate_audio_tool).
    - Audio_Engineer: for mixing ALL generated tracks together.
    ''',
    tools=[music_theory_alignment_tool],
    sub_agents=[musicologist, percussion_expert, string_expert, audio_engineer]
)
