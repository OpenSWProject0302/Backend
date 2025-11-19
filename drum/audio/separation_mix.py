import logging
import numpy as np
import soundfile as sf
from pathlib import Path
import librosa
import torch
from demucs import pretrained
from demucs.apply import apply_model

def separate_merge_drum(audio_path: Path, drum_audio_path: Path, output_dir=None, audio_format="mp3"):
    logger = logging.getLogger(__name__)
    logger.info("=== 음원 병합 중... ===")
    device = "cuda" if torch.cuda.is_available() else "cpu"

    # Demucs 모델 로드
    model = pretrained.get_model("htdemucs")
    model.eval()
    model.to(device)

    # y_trimmed → Tensor 변환
    y, sr = librosa.load(audio_path, res_type='kaiser_best', sr=None, mono=False)
    y_trimmed, _ = librosa.effects.trim(y, top_db=60)

    if y_trimmed.ndim == 1:
        wav_tensor = torch.from_numpy(y_trimmed).unsqueeze(0)  # (1, samples)
    else:
        wav_tensor = torch.from_numpy(y_trimmed)  # (channels, samples)

    wav_tensor = wav_tensor.to(device)

    # 모델 적용 (드럼 제거)
    with torch.no_grad():
        sources = apply_model(model, wav_tensor[None], device=device, split=True, overlap=0.25)[0]

    # 'drums' 제거 후 나머지 합치기
    source_names = model.sources
    non_drum_tensor = torch.zeros_like(wav_tensor)
    for i, name in enumerate(source_names):
        if name != "drums":
            non_drum_tensor += sources[i]

    mix_audio_path = mix_audio_tracks(non_drum_tensor, drum_audio_path, output_dir, audio_format, sr)
    return mix_audio_path

def mix_audio_tracks(non_drum_tensor: torch.Tensor, audio_path: Path, output_dir=None, audio_format="mp3", sr: int = 44100):
    logger = logging.getLogger(__name__)
    # 1) Tensor → numpy 변환
    non_drum = non_drum_tensor.cpu().numpy()

    # (ch, samples) → stereo 보장
    if non_drum.ndim == 1:
        non_drum = np.stack([non_drum, non_drum], axis=1)  # (samples, 2)
    else:
        non_drum = non_drum.T  # (ch, samples) -> (samples, ch)

    # 2) MIDI 드럼 mp3 로드
    midi_audio, midi_sr = sf.read(str(audio_path))

    if midi_sr != sr:
        midi_audio = librosa.resample(midi_audio.T, orig_sr=midi_sr, target_sr=sr).T

    # 5) 채널 맞추기
    if midi_audio.ndim == 1:
        midi_audio = np.stack([midi_audio, midi_audio], axis=1)
    elif midi_audio.shape[1] == 1 and non_drum.shape[1] == 2:
        midi_audio = np.repeat(midi_audio, 2, axis=1)

    # 6) 길이 맞추기
    max_len = max(len(non_drum), len(midi_audio))
    out_mix = np.zeros((max_len, 2))
    out_mix[:len(non_drum), :] += non_drum
    out_mix[:len(midi_audio), :] += midi_audio

    # 4) Normalize (clip 방지)
    max_amp = np.max(np.abs(out_mix))
    if max_amp > 0:
        out_mix = out_mix / max_amp

    # 5) 최종 mp3 저장
    # 출력 폴더
    if output_dir is None:
        output_dir = audio_path.parent
    output_dir = Path(output_dir)
    output_dir.mkdir(exist_ok=True)

    # 출력 파일 경로 설정
    mix_path = output_dir / f"{audio_path.stem[:-7]}(mix).{audio_format}"
    sf.write(str(mix_path), out_mix, sr)
    logger.info(f"{mix_path.stem}.mp3 파일이 생성되었습니다.")

    return mix_path
