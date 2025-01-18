from aeneas.executetask import ExecuteTask
from aeneas.task import Task
from io import BytesIO
import langid
from audio_separator.separator import Separator
import os
import ffmpeg
import shutil

def align_lyrics(audio_file_name, text_file_name, vocal_separator_model=None, 
        output_cache='./aligner_cache', input_cache='./inputs_cache/', background_file_name=None,
        aligner_config_string = "task_language=eng|os_task_file_format=srt|is_text_type=plain|os_task_adjust_boundary_nonspeech_min=1.0|os_task_vad_threshold=0.5"):
    
    input_audio_path = os.path.join(input_cache, audio_file_name)
    output_file_path = os.path.join(output_cache, f"{audio_file_name}_aligned.mp4")
    output_vocal_path = os.path.join(output_cache, f"{audio_file_name}_vocal.wav")
      
    input_text_path = os.path.join(input_cache, text_file_name)
    sync_file_path = os.path.join(output_cache, f"{audio_file_name}.srt")
    audio_cache_path = os.path.join(output_cache, 'audios')
    
    if os.path.exists(output_file_path):
        return {
            'video_path': output_file_path,
            'vocal_path': output_vocal_path,
            'subtitles_path': sync_file_path
        }

    if background_file_name:
        background_path = os.path.join(input_cache, background_file_name)
    else:
        background_path = os.path.join(input_cache, 'default.jpg')

    os.makedirs(audio_cache_path, exist_ok=True)

    # Step 1: Vocal Separation
    if vocal_separator_model:
        print('Performing vocal separation...')
        
        if not input_audio_path.endswith('.wav'):
            def convert_mp3_to_wav(input_mp3_path, output_wav_path):
                if os.path.exists(output_wav_path):
                    return output_wav_path
                try:
                    ffmpeg.input(input_mp3_path).output(output_wav_path).run()
                    print(f"Conversion successful: {output_wav_path}")
                except ffmpeg.Error as e:
                    print(f"Error occurred during conversion: {e.stderr.decode('utf8')}")
                return output_wav_path
            input_audio_path = convert_mp3_to_wav(input_audio_path, input_audio_path+'.wav')
        
        vocal_separator = Separator(
            output_dir=audio_cache_path,
            #output_single_stem="vocals",
            model_file_dir=os.path.dirname(vocal_separator_model),
        )
        vocal_separator.load_model(os.path.basename(vocal_separator_model))
        outputs = vocal_separator.separate(input_audio_path)
        vocal_audio_file = outputs[-1]
        vocal_audio_full_path = os.path.join(audio_cache_path, vocal_audio_file)
        print(f"Cleaned audio dave to : {vocal_audio_full_path}")
        shutil.copy2(vocal_audio_full_path, output_vocal_path)
    else:
        vocal_audio_file = input_audio_path

    # Step 2: Lyrics Alignment
        # Detect language
    print("Detecting lyrics language...")
    with open(input_text_path, "r", encoding="utf-8") as f:
        text = f.read()
    language, confidence = langid.classify(text)
    print(f"Detected language {language} with conf: {confidence}")
    if language != 'en':
        new_lang = ""
        if language == "ru":
            new_lang = "rus"
        else:
            raise Exception(f"Unusual language {language}")
        aligner_config_string = aligner_config_string.replace("eng", new_lang)
        print(f"Updated aligner config {aligner_config_string}")
    
    print('Aligning audio with lyrics...')
    task = Task(config_string=aligner_config_string)
    task.audio_file_path_absolute = vocal_audio_full_path
    task.text_file_path_absolute = input_text_path
    task.sync_map_file_path_absolute = sync_file_path
    try:
        ExecuteTask(task).execute()
        task.output_sync_map_file()
    except Exception as e:
        print(f"Error during alignment: {e}")
        return
        
    # Step 3: Video Generation
    print('Building video...')
    def get_audio_duration(audio_path):
        probe = ffmpeg.probe(audio_path)
        return float(probe['format']['duration'])
        print('Building video...')
    def get_audio_duration(audio_path):
        probe = ffmpeg.probe(audio_path)
        return float(probe['format']['duration'])

    def get_video_frame_rate(video_path):
        try:
            probe = ffmpeg.probe(video_path)
            video_stream = next((stream for stream in probe['streams'] if stream['codec_type'] == 'video'), None)
            if video_stream:
                # Try to get frame rate from different possible fields
                if 'avg_frame_rate' in video_stream:
                    num, den = map(int, video_stream['avg_frame_rate'].split('/'))
                    return num/den if den != 0 else 24
                elif 'r_frame_rate' in video_stream:
                    num, den = map(int, video_stream['r_frame_rate'].split('/'))
                    return num/den if den != 0 else 24
            return 24  # default frame rate
        except Exception as e:
            print(f"Warning: Could not determine frame rate, using default. Error: {e}")
            return 24  # default frame rate for images or error cases

    frame_rate = get_video_frame_rate(background_path)
    duration = get_audio_duration(input_audio_path)

    try:
        # Determine if input is image based on extension
        is_image = background_path.lower().endswith(('.png', '.jpg', '.jpeg', '.bmp', '.tiff'))
        
        # Configure input based on whether it's an image or video
        if is_image:
            inv = ffmpeg.input(background_path, loop=1, t=duration, framerate=frame_rate)
        else:
            inv = ffmpeg.input(background_path, stream_loop=-1)  # -1 means infinite loop
        
        ina = ffmpeg.input(input_audio_path)
        out = ffmpeg.output(ina, inv, output_file_path,
                        vf=f"scale=ceil(iw/2)*2:ceil(ih/2)*2,subtitles={sync_file_path}",
                        preset="fast",
                        pix_fmt="yuv420p",
                        acodec="aac",
                        strict="experimental",
                        shortest=None,
                        t=duration
                    )
        out.run()
        print(f"Video created successfully: {output_file_path}")
        return {
            'video_path': output_file_path,
            'vocal_path': output_vocal_path,
            'subtitles_path': sync_file_path
        }
    except ffmpeg.Error as e:
        print(f"FFmpeg error occurred: {e.stderr.decode('utf8')}")
        
def main():
    # Define file paths for demonstration purposes
    import argparse
    parser = argparse.ArgumentParser(description='Generating subtitles for music files and video with text oeverlay')
    parser.add_argument("--audio", help="Path to input audio", default='Nine Thou (Grant Mohrman Superstars Remix).wav', type=str)
    parser.add_argument("--text", help="Path to lyrics", default='Nine Thou (Grant Mohrman Superstars Remix).txt', type=str)
    parser.add_argument("--background", help="Path to background: video or image",
        default='nfsmw.jpg', type=str)
    
    parser.add_argument("--vocal_separator_model", help="Path to vocal separator checkpoint", 
        default="./checkpoints/vocal_separator/Kim_Vocal_2.onnx", type=str)
    parser.add_argument("--inputs_cache", help="Path input cache folder", default='./inputs_cache/', type=str)
    parser.add_argument("--outputs_cache", help="Path output cache folder", default='./aligner_cache/', type=str)
    args = parser.parse_args()

    audio_file_name = args.audio
    text_file_name = args.text
    background_file_name = args.background
    vocal_separator_model = args.vocal_separator_model
    inputs_cache_path = args.inputs_cache
    outputs_cache_path = args.outputs_cache

    align_lyrics(audio_file_name, text_file_name, vocal_separator_model, background_file_name=background_file_name,
        output_cache=outputs_cache_path, input_cache=inputs_cache_path)
    
if __name__ == "__main__":
    main()