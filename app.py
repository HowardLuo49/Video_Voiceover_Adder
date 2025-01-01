import pyttsx3
from flask import Flask, render_template, request, send_from_directory, after_this_request
from moviepy.editor import VideoFileClip, AudioFileClip
from pydub import AudioSegment
import os

app = Flask(__name__)

@app.route("/", methods=["GET", "POST"])
def index():
    if request.method == "POST":
        video_clip = None
        narration_audio_clip = None
        output_path = os.path.join("static", "output_video.mp4")

        # Temporary file paths
        video_path = os.path.join("static", "uploaded_video.mp4")
        narration_audio_path = os.path.join("static", "narration.mp3")

        try:
            # Input data
            video_file = request.files["video"]
            narration_text = request.form["text"]
            start_time = float(request.form.get("start_time", 0)) 
            end_time = request.form.get("end_time")
            selected_voice = request.form["voice"]

            # Process uploaded video
            video_file.save(video_path)
            video_clip = VideoFileClip(video_path)
            video_duration = video_clip.duration

            # Generate narration audio
            engine = pyttsx3.init()
            voices = engine.getProperty("voices")
            # if selected_voice == "male":
            #     engine.setProperty("voice", voices[0].id) # Male
            # elif selected_voice == "female":
            #     engine.setProperty("voice", voices[1].id) # Female
            selected_voice_index = int(request.form["voice"])
            engine.setProperty('voice', voices[selected_voice_index].id)

            engine.save_to_file(narration_text, narration_audio_path)
            engine.runAndWait()

            # Process narration audio
            narration_audio = AudioSegment.from_file(narration_audio_path)
            narration_audio = narration_audio.set_frame_rate(44100).set_channels(1)
            narration_duration = len(narration_audio) / 1000

            if not end_time:
                end_time = min(video_duration, start_time + narration_duration)
            else:
                end_time = float(end_time)

            duration = end_time - start_time
            if narration_duration < duration:
                stretch_factor = duration / narration_duration
                narration_audio = narration_audio._spawn(
                    narration_audio.raw_data,
                    overrides={"frame_rate": int(narration_audio.frame_rate / stretch_factor)}
                ).set_frame_rate(narration_audio.frame_rate)
            elif narration_duration > duration:
                speed_factor = narration_duration / duration
                narration_audio = narration_audio._spawn(
                    narration_audio.raw_data,
                    overrides={"frame_rate": int(narration_audio.frame_rate * speed_factor)}
                ).set_frame_rate(narration_audio.frame_rate)

            narration_audio.export(narration_audio_path, format="mp3")

            # Combine audio and video
            narration_audio_clip = AudioFileClip(narration_audio_path).subclip(0, min(duration, video_duration - start_time))
            video_with_audio = video_clip.set_audio(narration_audio_clip)
            video_with_audio.write_videofile(output_path, codec="libx264", audio_codec="aac")

            @after_this_request
            def remove_file(response):
                for file_path in [video_path, narration_audio_path]: # Facing issues deleting output_path, not too important so leaving it for now
                    if os.path.exists(file_path):
                        try:
                            os.remove(file_path)
                        except Exception as e:
                            app.logger.error(f"Error deleting file {file_path}: {e}")
                return response

            return send_from_directory(directory="static", path="output_video.mp4", as_attachment=True)

        except Exception as e:
            app.logger.error(f"Error during request processing: {e}")
        finally:
            if video_clip:
                video_clip.close()
            if narration_audio_clip:
                narration_audio_clip.close()
    else:
        engine = pyttsx3.init()
        voices = engine.getProperty("voices")
        voice_options = [{"id": idx, "name": voice.name} for idx, voice in enumerate(voices)]
        return render_template("index.html", voice_options=voice_options)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8082, debug=True)
