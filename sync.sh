python -m aeneas.tools.execute_task \
    "./audio_cache/Nine Thou (Grant Mohrman Superstars Remix)_(Vocals)_Kim_Vocal_2-16k.wav" \
    "./temp_corpus/txt/Nine Thou (Grant Mohrman Superstars Remix).txt" \
    "task_language=eng|os_task_file_format=srt|is_text_type=plain|os_task_adjust_boundary_nonspeech_min=1.0|os_task_vad_threshold=0.5" \
    output.srt \
    --log-level=DEBUG

ffmpeg -loop 1 -framerate 2 -i nfsmw.jpg -i "Nine Thou (Grant Mohrman Superstars Remix).wav" -vf "subtitles=output.srt" -c:v libx264 -preset fast -pix_fmt yuv420p -c:a aac -strict experimental -shortest -y ninethou.mp4
