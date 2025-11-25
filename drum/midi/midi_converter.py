import os
import subprocess
import platform
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

    # 0) MuseScore 실행 파일 경로
    musescore_path = os.getenv("MUSESCORE_PATH")

    if not musescore_path:
        raise RuntimeError("MUSESCORE_PATH 환경변수가 설정되지 않았습니다.")

    # 경로 존재 여부 로그
    if not Path(musescore_path).exists():
        logger.warning(f"[주의] MuseScore 경로가 존재하지 않을 수 있음: {musescore_path}")
        # Ubuntu에서는 symbolic link 형태여도 존재하지 않는 것으로 보일 수 있음

    # 1) 출력 디렉토리 설정
    if output_dir is None:
        output_dir = midi_path.parent

    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    pdf_path = output_dir / f"{midi_path.stem}.pdf"
    audio_path = output_dir / f"{midi_path.stem}(guide).{audio_format}"

    # 2) OS 별 MuseScore 실행 방식 적용
    is_linux = platform.system() == "Linux"

    if is_linux:
        # xvfb-run 사용
        base_cmd = ["xvfb-run", "-a", musescore_path]
    else:
        # Windows 등: MuseScore 실행파일 직접 실행
        base_cmd = [musescore_path]

    # PDF 변환 명령어
    pdf_command = base_cmd + [
        str(midi_path),
        "-o", str(pdf_path),
    ]

    # 오디오 변환 명령어
    audio_command = base_cmd + [
        str(midi_path),
        "-o", str(audio_path),
    ]

    # -------------------------
    # PDF 변환 수행
    # -------------------------
    logger.info("=== MIDI → PDF 변환 중... ===")
    try:
        subprocess.run(pdf_command, check=True, capture_output=True, text=True)
    except subprocess.CalledProcessError as e:
        logger.error(f"PDF 변환 실패: {e.stderr or e}")
        raise RuntimeError(f"PDF 변환 실패: {e.stderr or e}")

    if not pdf_path.exists():
        raise FileNotFoundError(f"PDF 파일이 생성되지 않았습니다: {pdf_path}")

    logger.info(f"PDF 생성 완료: {pdf_path}")

    # -------------------------
    # 오디오 변환 수행
    # -------------------------
    logger.info("=== MIDI → 오디오 변환 중... ===")
    try:
        subprocess.run(audio_command, check=True, capture_output=True, text=True)
    except subprocess.CalledProcessError as e:
        logger.error(f"오디오 변환 실패: {e.stderr or e}")
        raise RuntimeError(f"오디오 변환 실패: {e.stderr or e}")

    if not audio_path.exists():
        raise FileNotFoundError(f"오디오 파일이 생성되지 않았습니다: {audio_path}")

    logger.info(f"오디오 생성 완료: {audio_path}")

    return pdf_path, audio_path
