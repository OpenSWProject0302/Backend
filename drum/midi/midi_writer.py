from pathlib import Path
import uuid
from mido import MidiFile

def create_midi_path(audio_path: Path, output_dir=None):
    name = audio_path.stem
    suffix = uuid.uuid4().hex[:6]
    filename = f"{name}_{suffix}.mid"

    if output_dir is None:
        output_dir = audio_path.parent
    output_dir = Path(output_dir)
    output_dir.mkdir(exist_ok=True)

    midi_path = output_dir / filename
    
    return midi_path

def write_midi(drum_track, midi_path):
    mid = MidiFile(ticks_per_beat=480)
    mid.tracks.append(drum_track)
    mid.save(midi_path)
