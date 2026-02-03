from pydantic import BaseModel, Field
from typing import List, Optional

class Track(BaseModel):
    instrument: str
    prompt: str
    duration_seconds: float = 30.0
    file_path: Optional[str] = None
    volume: float = 1.0
    pan: float = 0.0  # -1.0 (left) to 1.0 (right)

class MusicSessionState(BaseModel):
    project_name: str
    bpm: int = 120
    key: str = "C Major"
    tracks: List[Track] = Field(default_factory=list)
    master_volume: float = 1.0
    is_completed: bool = False
