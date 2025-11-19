import numpy as np
from mido import MidiTrack
from patterns.drum_patterns import DRUM_PATTERNS
from midi.drum_events import play_drum

def write_drum_patterns_easy(track:MidiTrack, genre: str, phrases: list) -> MidiTrack:
    # 장르에 맞는 드럼 패턴을 MIDI 트랙에 기록 (쉬움 난이도: 가장 쉬운 패턴(1)만 프레이즈에 맞춰 배치)
    pattern = DRUM_PATTERNS[genre][1]

    for i, (start, end) in enumerate(phrases):
        seq = expend_structure(pattern["structure"], end-start)
        for token in seq:
            part = {
                "S": "start",
                "M": "middle",
                "E": "end"
            }[token]

            play_drum(track, pattern[part])

    return track

def write_drum_patterns_normal(track:MidiTrack, genre: str, phrases: list, strengths: list) -> MidiTrack:
    # 장르에 맞는 드럼 패턴을 MIDI 트랙에 기록 (기본 난이도: strengths에 따라 배치)
    patterns = DRUM_PATTERNS[genre]
    pattern_keys = sorted(patterns.keys())
    num_patterns = len(patterns)

    strengths = np.array(strengths)
    n = len(strengths)

    decay = 0.6   # 감소 계수 (변경 가능)
    raw = np.array([decay**i for i in range(num_patterns)])
    ratios = raw / raw.sum()

    sorted_idx = np.argsort(strengths)
    selected_patterns_sorted = np.zeros(n, dtype=int)

    start = 0
    for p_index, r in enumerate(ratios):
        count = int(r * n)
        if p_index == num_patterns - 1:
            end = n
        else:
            end = min(start + count, n)
        pid = pattern_keys[p_index]
        selected_patterns_sorted[start:end] = pid
        start = end
        if start >= n:
            break

    selected_patterns = np.zeros(n, dtype=int)
    selected_patterns[sorted_idx] = selected_patterns_sorted

    for i, (start, end) in enumerate(phrases):
        pattern_id = patterns[selected_patterns[i]]
        seq = expend_structure(pattern_id["structure"], end-start)
        for token in seq:
            part = {
                "S": "start",
                "M": "middle",
                "E": "end"
            }[token]

            play_drum(track, pattern_id[part])

    return track

def expend_structure(structure: str, phrase_bars: int) -> list[str]:
    base = structure.split("-")

    if len(base) > phrase_bars:
        freq = {}
        for ch in base:
            freq[ch] = freq.get(ch, 0) + 1
        return [max(freq, key=freq.get)] * phrase_bars
    elif len(base) == phrase_bars:
        return base

    if structure == "S-M-M-E":
        return ["S"] + ["M"] * (phrase_bars - 2) + ["E"]
    elif structure == "S-M-S-E":
        if phrase_bars % 2 == 0:
            return ["S", "M"] * (phrase_bars // 2 - 1) + ["S", "E"]
        else:
            return ["S", "M"] * (phrase_bars // 2) + ["E"]
    elif structure == "S-E-M-E":
        if phrase_bars % 2 == 0:
            return ["S", "E"] + ["M", "E"] * (phrase_bars // 2 - 1)
        else:
            return ["S"] + ["M", "E"] * (phrase_bars // 2)
    elif structure == "S-S-S-S":
        return ["S"] * phrase_bars
    elif structure == "S-S-S-E":
        return ["S"] * (phrase_bars - 1) + ["E"]
    elif structure == "S-E-E-E":
        return ["S"] + ["E"] * (phrase_bars - 1)
    elif structure == "S-E-S-E":
        if phrase_bars % 2 == 0:
            return ["S", "E"] * (phrase_bars // 2)
        else:
            return ["S", "E"] * (phrase_bars // 2 - 1) + ["S"]
    else:
        return base * (phrase_bars // len(base)) + base[:phrase_bars % len(base)]