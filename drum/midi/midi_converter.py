import os
import subprocess
import platform
from pathlib import Path
import logging
from typing import Union, Optional

from midi2audio import FluidSynth

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
        base_cmd = ["xvfb-run", "-a", musescore_path]
    else:
        base_cmd = [musescore_path]

    # PDF 변환 명령어
    pdf_command = base_cmd + [
        str(midi_path),
        "-o", str(pdf_path),
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

    # ============================================================
    # 🔥🔥 여기서부터: 오디오 변환(MuseScore → FluidSynth로 교체)
    # ============================================================

    logger.info("=== MIDI → 오디오 변환 중... (FluidSynth) ===")

    # 사운드폰트 탐색
    soundfont_candidates = [
        "/usr/share/sounds/sf2/FluidR3_GM.sf2",
        "/usr/share/soundfonts/default.sf2",
    ]

    soundfont = None
    for sf in soundfont_candidates:
        if Path(sf).exists():
            soundfont = sf
            break

    if soundfont is None:
        raise FileNotFoundError(
            "사운드폰트를 찾을 수 없습니다. 'fluid-soundfont-gm' 설치가 필요합니다."
        )

    logger.info(f"사용할 사운드폰트: {soundfont}")

    # FluidSynth 객체 생성
    fs = FluidSynth(soundfont)

    # 변환 수행
    fs.midi_to_audio(str(midi_path), str(audio_path))

    if not audio_path.exists():
        raise FileNotFoundError(f"(guide) 오디오 파일이 생성되지 않았습니다: {audio_path}")

    logger.info(f"오디오 생성 완료: {audio_path}")

    return pdf_path, audio_path
