import os
import platform
import shutil
import subprocess
from pathlib import Path
import logging
from typing import Union, Optional

from midi2audio import FluidSynth

logger = logging.getLogger(__name__)


def _get_musescore_path() -> str:
    """
    PDF 출력용 MuseScore 실행파일 경로 찾기.
    - 환경변수 MUSESCORE_PATH 우선
    - 없으면 OS별 기본값/which 로 탐색
    """
    env_path = os.getenv("MUSESCORE_PATH")
    if env_path:
        return env_path

    system = platform.system()
    if system == "Windows":
        # 로컬 개발용 (필요하면 수정)
        return "MuseScore4.exe"
    elif system == "Darwin":  # macOS
        return "/Applications/MuseScore 4.app/Contents/MacOS/mscore"

    # Linux (EC2)
    for name in ("musescore4", "musescore3", "mscore", "mscore3"):
        path = shutil.which(name)
        if path:
            return path

    raise RuntimeError(
        "MuseScore 실행파일을 찾을 수 없습니다. "
        "환경변수 MUSESCORE_PATH를 설정하거나, musescore4/mscore 등을 설치해주세요."
    )


def _get_soundfont_path() -> Path:
    """
    FluidSynth에서 사용할 사운드폰트 경로 찾기.
    - 환경변수 SOUNDFONT_PATH 우선
    - 없으면 몇 가지 기본 위치를 탐색
    """
    env_sf = os.getenv("SOUNDFONT_PATH")
    if env_sf:
        p = Path(env_sf)
        if p.exists():
            return p
        raise FileNotFoundError(f"SOUNDFONT_PATH에 지정된 사운드폰트를 찾을 수 없습니다: {p}")

    # Ubuntu 기본 GM 사운드폰트 후보
    candidates = [
        "/usr/share/sounds/sf2/FluidR3_GM.sf2",
        "/usr/share/soundfonts/default.sf2",
    ]
    for c in candidates:
        p = Path(c)
        if p.exists():
            return p

    raise FileNotFoundError(
        "GM 사운드폰트(.sf2)를 찾을 수 없습니다. "
        "fluid-soundfont-gm 패키지가 설치되어 있는지 확인하거나, "
        "SOUNDFONT_PATH 환경변수로 사운드폰트 경로를 지정해주세요."
    )


def convert_midi(
    midi_path: Union[str, Path],
    output_dir: Optional[Union[str, Path]] = None,
    audio_format: str = "wav",
):
    """
    MIDI 파일을 받아서
    - MuseScore로 PDF 악보 생성
    - FluidSynth(사운드폰트)로 가이드 오디오 생성
    을 수행하고 (pdf_path, audio_path)를 반환한다.
    """
    midi_path = Path(midi_path).resolve()

    if output_dir is None:
        output_dir = midi_path.parent
    else:
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)

    # 출력 경로들
    pdf_path = output_dir / f"{midi_path.stem}.pdf"
    audio_path = output_dir / f"{midi_path.stem}(guide).{audio_format}"

    logger.info("=== MIDI → PDF / 오디오 변환 시작 ===")
    logger.info(f"MIDI 경로: {midi_path}")
    logger.info(f"출력 디렉토리: {output_dir}")

    # -------------------------
    # 1) MuseScore로 PDF 생성
    # -------------------------
    musescore_path = _get_musescore_path()
    pdf_command = [
        musescore_path,
        str(midi_path),
        "-o",
        str(pdf_path),
    ]

    logger.info("=== MIDI → PDF (MuseScore) 변환 중... ===")
    logger.info(f"명령어: {' '.join(pdf_command)}")

    try:
        subprocess.run(pdf_command, check=True, capture_output=True, text=True)
    except subprocess.CalledProcessError as e:
        logger.error(f"PDF 변환 실패: {e.stderr or e}")
        raise RuntimeError(f"PDF 변환 실패: {e.stderr or e}")

    if not pdf_path.exists():
        raise FileNotFoundError(f"PDF 파일이 생성되지 않았습니다: {pdf_path}")

    logger.info(f"PDF 생성 완료: {pdf_path}")

    # -------------------------
    # 2) FluidSynth로 오디오 생성
    # -------------------------
    sf_path = _get_soundfont_path()
    logger.info(f"사운드폰트 사용: {sf_path}")

    fs = FluidSynth(str(sf_path))

    logger.info("=== MIDI → 오디오 (FluidSynth) 변환 중... ===")
    logger.info(f"오디오 출력: {audio_path}")

    fs.midi_to_audio(str(midi_path), str(audio_path))

    if not audio_path.exists():
        raise FileNotFoundError(f"오디오 파일이 생성되지 않았습니다: {audio_path}")

    logger.info(f"오디오 생성 완료: {audio_path}")
    logger.info("=== MIDI 변환 전체 완료 ===")

    return pdf_path, audio_path
