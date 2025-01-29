import os
import logging
import whisperx
from config import Config

class LyricsAlignerWithWhisper:
    def __init__(self, config):
        self.config = config
        self.device = "cuda" if config.gpu_on else "cpu"
        self.model = whisperx.load_model("large-v2", device=self.device)
        
    def format_time(self, time_in_seconds):
        # Convert seconds to hours, minutes, seconds, and milliseconds
        hours = int(time_in_seconds // 3600)
        minutes = int((time_in_seconds % 3600) // 60)
        seconds = int(time_in_seconds % 60)
        milliseconds = int((time_in_seconds % 1) * 1000)

        # Format the time in SRT format (HH:MM:SS,mmm)
        return f"{hours:02}:{minutes:02}:{seconds:02},{milliseconds:03}"
        
    def save_lyrics(self, lyrics, path, key='word'):
         # Write the transcription result to an SRT file
        with open(path, 'w') as srt_file:
            for i, segment in enumerate(lyrics):
                start_time = segment['start']
                end_time = segment['end']
                text = segment[key]

                # Format the time in SRT format (HH:MM:SS,mmm)
                start_time_str = self.format_time(start_time)
                end_time_str = self.format_time(end_time)

                # Write the SRT segment
                srt_file.write(f"{i + 1}\n")
                srt_file.write(f"{start_time_str} --> {end_time_str}\n")
                srt_file.write(f"{text}\n\n")

    def align_lyrics(self, vocal_audio_full_path):
        sync_file_path = os.path.join(self.config.output_cache, f"{self.config.audio_file_name}.srt")

        logging.info('Transcribing audio with WhisperX...')
        result = self.model.transcribe(vocal_audio_full_path, chunk_size=30)
        # 2. Align whisper output
        model_a, metadata = whisperx.load_align_model(language_code=result["language"], device=self.device)
        result = whisperx.align(result["segments"], model_a, metadata, 
            vocal_audio_full_path, self.device, return_char_alignments=False)
        
        self.save_lyrics(result['word_segments'], sync_file_path)
        print(f"Transcription saved to {sync_file_path}")
        return sync_file_path

# Example usage
if __name__ == "__main__":
    config = Config(input_cache = "/app/synclyr/data/inputs_cache", output_cache = "/app/synclyr/data/aligner_cache")
    config.from_user_data(
        {
            "text_file_name": "lyrics.txt",
            "audio_file_name": "09f7803f-baad-485e-afe9-186ca2024256.mp4"
        }
    )
    aligner = LyricsAlignerWithWhisper(config)
    vocal_audio_full_path = "/app/synclyr/data/inputs_cache/audio_cache/09f7803f-baad-485e-afe9-186ca2024256.mp4_(Vocals)_Kim_Vocal_2.wav"
    sync_file_path = aligner.align_lyrics(vocal_audio_full_path)
    if sync_file_path:
        print(f"Sync file created at: {sync_file_path}")
    else:
        print("Failed to create sync file.")