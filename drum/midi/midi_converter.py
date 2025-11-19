import os
import subprocess
from pathlib import Path
import logging

def convert_midi(midi_path, output_dir=None, audio_format="mp3"):
    musescore_path = os.getenv("MUSESCORE_PATH")
    midi_path = Path(midi_path)

    # 출력 폴더 기본값: MIDI 파일 있는 곳
    if output_dir is None:
        output_dir = midi_path.parent
    output_dir = Path(output_dir)
    output_dir.mkdir(exist_ok=True)

    # 출력 파일 경로 설정
    pdf_path = output_dir / f"{midi_path.stem}.pdf"
    audio_path = output_dir / f"{midi_path.stem}(guide).{audio_format}"

    # PDF 변환 명령
    pdf_command = [
        musescore_path,
        str(midi_path),
        "-o", str(pdf_path)
    ]

    # 오디오 변환 명령
    audio_command = [
        musescore_path,
        str(midi_path),
        "-o", str(audio_path)
    ]

    logger = logging.getLogger(__name__)
    logger.info("=== MIDI → PDF 변환 중... ===")
    try:
        subprocess.run(pdf_command, check=True)
        logger.info(f"PDF 생성 완료: {pdf_path.stem}.pdf")
    except Exception as e:
        logger.info(f"PDF 변환 실패: {e}")

    logger.info("=== MIDI → 오디오 변환 중... ===")
    try:
        subprocess.run(audio_command, check=True)
        logger.info(f"오디오 생성 완료: {audio_path.stem}.{audio_format}")
    except Exception as e:
        logger.info(f"오디오 변환 실패: {e}")

    return pdf_path, audio_path