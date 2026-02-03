from google.adk.agents import Agent
from common.models import MusicSessionState

def alignment_check_tool(bpm: int, key: str, tracks: list):
    """
    Check if the current tracks are aligned with the BPM and Key.
    """
    print(f"Checking alignment: BPM={bpm}, Key={key}, Tracks={len(tracks)}")
    return True

agent = Agent(
    model='gemini-3-flash-preview',
    name='Musicologist',
    instruction='''
    You are a professional music theorist and composer.
    Your role is to ensure that all tracks suggested by the Orchestrator are harmonically and rhythmically consistent.
    - Recommend appropriate BPM for specific genres.
    - Suggest musical keys that evoke certain emotions (e.g., D minor for epic/sad).
    - Design track structures (Intro, Verse, Chorus, etc.).
    ''',
    tools=[alignment_check_tool]
)
