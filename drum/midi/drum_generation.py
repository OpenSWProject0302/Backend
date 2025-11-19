from pathlib import Path
from mido import MidiTrack, MetaMessage, bpm2tempo
from audio.analysis import detect_phrase_transitions
from midi.drum_writer import write_drum_patterns_normal, write_drum_patterns_easy
import logging

def generate_drum_midi_from_audio(audio_path: Path, genre: str, tempo: int, level:str) -> MidiTrack:
    # 오디오 파일을 분석해서 프레이즈별로 드럼 리듬을 MIDI 트랙에 기록

    # 1. 오디오 분석
    result = detect_phrase_transitions(audio_path, tempo)
    tempo = result["tempo"]
    num_bars = result["num_bars"]
    transition_bars = result["transition_bars"]
    phrase_strengths = result["phrase_strengths"]

    track = MidiTrack()
    track.append(MetaMessage('time_signature', numerator=4, denominator=4))
    track.append(MetaMessage('set_tempo', tempo=bpm2tempo(tempo)))

    # 2. 프레이즈 구간 생성
    phrase_starts = [0] + transition_bars
    phrase_ends = transition_bars + [num_bars]
    phrases = list(zip(phrase_starts, phrase_ends))

    # 로그 debug 출력
    logger = logging.getLogger(__name__)
    logger.info(f"Detected tempo: {tempo:.2f} BPM")
    logger.info("=== phrases ===")
    for i, (s, e) in enumerate(phrases):
        logger.info(f"{i}: bars {s} → {e}  (len={e-s}) | strength={phrase_strengths[i]:.4f}")

    # 3. 각 프레이즈에 드럼 리듬을 패턴대로 추가
    if level == "Easy":
        track = write_drum_patterns_easy(track, genre, phrases)
    elif level == "Normal":
        track = write_drum_patterns_normal(track, genre, phrases, phrase_strengths)

    return track