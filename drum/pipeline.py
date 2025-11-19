from typing import Union, Optional
from pathlib import Path
import logging

from midi.midi_writer import create_midi_path, write_midi
from midi.drum_generation import generate_drum_midi_from_audio
from midi.midi_converter import convert_midi
from audio.separation_mix import separate_merge_drum

logger = logging.getLogger(__name__)


def run_drum_pipeline(
        audio_path: Union[str, Path],
        genre: str,
        tempo: int,
        level: str,
        output_dir: Optional[Union[str, Path]] = None,
):
    """
    S3에서 다운로드된 audio 파일을 받아
    드럼 MIDI, PDF, 믹스 오디오를 생성하는 파이프라인.

    반환값: dict 형태로 결과 파일들의 로컬 경로를 제공.
    """
    audio_path = Path(audio_path)

    if output_dir:
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)
    else:
        output_dir = audio_path.parent  # 기본은 같은 폴더

    # 1. MIDI 파일 경로 생성
    midi_path = create_midi_path(audio_path, output_dir)

    # 2. 드럼 MIDI 생성
    drum_track = generate_drum_midi_from_audio(audio_path, genre, tempo, level)

    # 3. MIDI 저장
    write_midi(drum_track, midi_path)
    logger.info(f"[DRUM PIPELINE] MIDI 생성: {midi_path}")

    # 4. PDF / 드럼 오디오 변환
    pdf_path, drum_audio_path = convert_midi(midi_path)
    logger.info(f"[DRUM PIPELINE] PDF 생성: {pdf_path}")
    logger.info(f"[DRUM PIPELINE] 드럼 오디오 생성: {drum_audio_path}")

    # 5. 원곡 + 드럼 오디오 병합
    mix_audio_path = separate_merge_drum(audio_path, drum_audio_path)
    logger.info(f"[DRUM PIPELINE] 믹스 오디오 생성: {mix_audio_path}")

    # Django 서버에서는 dict로 반환하는 게 가장 편함
    return {
        "midi": str(midi_path),
        "pdf": str(pdf_path),
        "drum_audio": str(drum_audio_path),
        "mix_audio": str(mix_audio_path),
    }
