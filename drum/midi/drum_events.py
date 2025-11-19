from mido import MidiTrack, Message
from patterns.constants import DRUM_CHANNEL, VELOCITY, NOTE_LENGTH, DRUM_NOTES

# 악기 재생, 종료 함수
def playOn(track: MidiTrack, note: int, time: int, channel: int):
    track.append(Message('note_on', note=note, velocity=VELOCITY, time=time, channel=channel))

def playOff(track: MidiTrack, note: int, time: int, channel: int):
    track.append(Message('note_off', note=note, velocity=64, time=time, channel=channel))

def play_drum(track: MidiTrack, pattern: dict):
    # 드럼 리듬 패턴을 MIDI 트랙에 기록

    for step in range(16):  # 한 마디 = 16 step (16분음표)
        active_notes = []
        for name, sequence in pattern.items():
            if sequence[step] == 1:
                active_notes.append(DRUM_NOTES[name])

        if active_notes:
            for note in active_notes: # 한 악기만 연주할 경우
                playOn(track, note, time=0, channel=DRUM_CHANNEL)
            for i, note in enumerate(active_notes): # 동시에 연주되는 음 처리
                playOff(track, note, time=NOTE_LENGTH["SIXTEENTH"] if i == 0 else 0, channel=DRUM_CHANNEL)
        else:
            # 쉼표 구간이면 시간만 흐르게 함
            track.append(Message('note_off', note=0, velocity=0, time=NOTE_LENGTH["SIXTEENTH"], channel=DRUM_CHANNEL))