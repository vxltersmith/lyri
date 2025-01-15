
from audio_separator.separator import Separator
import os
import subprocess


wav_path = 'Nine Thou (Grant Mohrman Superstars Remix).wav'
cache_dir = './audio_cache/'
vocal_separator_model = "./checkpoints/vocal_separator/Kim_Vocal_2.onnx"
vocal_separator_model = "./checkpoints/drum_separator/model_bs_roformer_ep_317_sdr_12.9755.ckpt"
sample_rate: int = 16000
#path='Devil Eyes.mp3'

def resample_audio(input_audio_file: str, output_audio_file: str, sample_rate: int = 16000):
    p = subprocess.Popen(
        [
            "ffmpeg",
            "-y",
            "-v",
            "error",
            "-i",
            input_audio_file,
            "-ar",
            str(sample_rate),
            output_audio_file,
        ]
    )
    ret = p.wait()
    assert ret == 0, f"Resample audio failed! Input: {input_audio_file}, Output: {output_audio_file}"
    return output_audio_file

# Initialize vocal separator if provided
vocal_separator = None
if vocal_separator_model is not None:
    os.makedirs(cache_dir, exist_ok=True)
    vocal_separator = Separator(
        output_dir=cache_dir,
        output_single_stem="vocals",
        model_file_dir=os.path.dirname(vocal_separator_model),
    )
    vocal_separator.load_model(os.path.basename(vocal_separator_model))
    assert vocal_separator.model_instance is not None, "Failed to load audio separation model."

# Perform vocal separation if applicable
if vocal_separator is not None:
    outputs = vocal_separator.separate(wav_path)
    assert len(outputs) > 0, "Audio separation failed."
    vocal_audio_file = outputs[0]
    vocal_audio_name, _ = os.path.splitext(vocal_audio_file)
    vocal_audio_file = os.path.join(vocal_separator.output_dir, vocal_audio_file)
    vocal_audio_file = resample_audio(
        vocal_audio_file,
        os.path.join(vocal_separator.output_dir, f"{vocal_audio_name}-16k.wav"),
        sample_rate,
    )
else:
    vocal_audio_file = wav_path
print('done')
