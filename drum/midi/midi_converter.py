import os
import subprocess
from pathlib import Path
import logging
from typing import Union, Optional

logger = logging.getLogger(__name__)

def convert_midi(
    midi_path: Union[str, Path],
    output_dir: Optional[Union[str, Path]] = None,
    audio_format: str = "wav",
):
    midi_path = Path(midi_path)

    # 0) MuseScore 실행 파일 경로 확인
    musescore_path = os.getenv("MUSESCORE_PATH")
    if not musescore_path:
        raise RuntimeError("MUSESCORE_PATH 환경변수가 설정되지 않았습니다.")
    if not Path(musescore_path).exists():
        raise RuntimeError(f"MuseScore 실행 파일을 찾을 수 없습니다: {musescore_path}")

    # 1) 출력 폴더 결정
    if output_dir is None:
        output_dir = midi_path.parent
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    pdf_path = output_dir / f"{midi_path.stem}.pdf"
    audio_path = output_dir / f"{midi_path.stem}(guide).{audio_format}"

    pdf_command = [
        musescore_path,
        str(midi_path),
        "-o", str(pdf_path),
    ]
    audio_command = [
        musescore_path,
        str(midi_path),
        "-o", str(audio_path),
    ]

    logger.info("=== MIDI → PDF 변환 중... ===")
    try:
        subprocess.run(
            pdf_command,
            check=True,
            capture_output=True,
            text=True,
        )
    except subprocess.CalledProcessError as e:
        logger.error(f"PDF 변환 실패: {e.stderr or e}")
        raise RuntimeError(f"PDF 변환 실패: {e.stderr or e}")

    if not pdf_path.exists():
        raise FileNotFoundError(f"PDF 파일이 생성되지 않았습니다: {pdf_path}")

    logger.info(f"PDF 생성 완료: {pdf_path}")

    logger.info("=== MIDI → 오디오 변환 중... ===")
    try:
        subprocess.run(
            audio_command,
            check=True,
            capture_output=True,
            text=True,
        )
    except subprocess.CalledProcessError as e:
        logger.error(f"오디오 변환 실패: {e.stderr or e}")
        raise RuntimeError(f"오디오 변환 실패: {e.stderr or e}")

    if not audio_path.exists():
        raise FileNotFoundError(f"오디오 파일이 생성되지 않았습니다: {audio_path}")

    logger.info(f"오디오 생성 완료: {audio_path}")

    return pdf_path, audio_path
