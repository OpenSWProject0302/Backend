import os
import subprocess
import platform  # OS 확인을 위해 추가
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

    # xvfb-run을 쓸 때는 musescore_path가 실제 파일 경로인지 체크하는 로직이
    # 상황에 따라(심볼릭 링크 등) 실패할 수도 있으니, 단순 존재 여부 체크는 유지하되
    # 리눅스에서는 xvfb-run을 앞에 붙여야 함을 염두에 둡니다.
    if not Path(musescore_path).exists():
        # 혹시나 경로가 틀렸을 수 있으니 로그는 남기지만,
        # 간혹 'musescore3' 명령어 자체로 되어있을 수도 있으므로 주의
        logger.warning(f"MuseScore 실행 파일 경로 경고: {musescore_path} 가 존재하지 않을 수 있습니다.")

    # 1) 출력 폴더 결정
    if output_dir is None:
        output_dir = midi_path.parent
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    pdf_path = output_dir / f"{midi_path.stem}.pdf"
    audio_path = output_dir / f"{midi_path.stem}(guide).{audio_format}"

    # --- [수정된 부분 시작] ---
    # OS가 리눅스인 경우(EC2) 가상 디스플레이(xvfb)를 사용하여 실행
    cmd_prefix = [musescore_path]

    if platform.system() == "Linux":
        # -a: 가상 디스플레이 번호 자동 할당
        cmd_prefix = ["xvfb-run", "-a", musescore_path]

    pdf_command = cmd_prefix + [
        str(midi_path),
        "-o", str(pdf_path),
    ]
    audio_command = cmd_prefix + [
        str(midi_path),
        "-o", str(audio_path),
    ]
    # --- [수정된 부분 끝] ---

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