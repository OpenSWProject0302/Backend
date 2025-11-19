import numpy as np
from pathlib import Path
import librosa

def detect_phrase_transitions(audio_path: Path, tempo: int, hop_length=512, bar_beats: int = 4) -> dict:
    # 오디오를 불러와 박자, 프레이즈 전환을 감지
    y, sr = librosa.load(audio_path, res_type='kaiser_best', sr=None, mono=True)
    y_trimmed, (start, end) = librosa.effects.trim(y, top_db=60)
    y = y_trimmed

    onset_env = librosa.onset.onset_strength(y=y, sr=sr, hop_length=hop_length, aggregate=np.median)

    seconds_per_beat = 60.0 / tempo
    seconds_per_bar = seconds_per_beat * bar_beats
    audio_duration = librosa.get_duration(y=y, sr=sr)
    num_bars = int(np.floor(audio_duration / seconds_per_bar))

    times = librosa.frames_to_time(np.arange(len(onset_env)), sr=sr, hop_length=hop_length)

    bar_strengths = []
    for i in range(num_bars):
        # 해당 마디의 시작/끝을 나타내는 시간(초)
        start_t = i * seconds_per_bar
        end_t = start_t + seconds_per_bar
        # 해당 마디 인덱스
        idx = np.where((times >= start_t) & (times < end_t))[0]
        if idx.size > 0:
            bar_strengths.append(np.mean(onset_env[idx])) # 마디별 평균 강도를 bar_strengths에 추가함
        else:
            bar_strengths.append(0.0)

    bar_strengths = np.array(bar_strengths)
    
    delta = np.abs(np.diff(bar_strengths))
    threshold = np.mean(delta) + np.std(delta)
    transition_bars = np.where(delta > threshold)[0] + 1 # +1 하면 다음 마디 인덱스

    phrase_starts = [0] + transition_bars.tolist()
    phrase_ends = transition_bars.tolist() + [num_bars]

    phrase_strengths = []
    for start, end in zip(phrase_starts, phrase_ends):
        phrase_strengths.append(float(np.mean(bar_strengths[start:end])))

    return {
        "tempo": tempo,
        "num_bars": num_bars,
        "transition_bars": transition_bars.tolist(),
        "phrase_strengths": phrase_strengths
    }