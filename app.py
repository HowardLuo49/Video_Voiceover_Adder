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
            # Get form data
            video_file = request.files["video"]
            narration_text = request.form["text"]
            start_time = float(request.form.get("start_time", 0))  # Default start at 0
            end_time = request.form.get("end_time")  # May be None
            selected_voice = request.form["voice"]  # Get selected voice

            # Save the uploaded video
            video_file.save(video_path)

            # Load video and get its duration
            video_clip = VideoFileClip(video_path)
            video_duration = video_clip.duration

            # Generate narration audio with the selected voice
            engine = pyttsx3.init()
            voices = engine.getProperty("voices")
            if selected_voice == "male":
                engine.setProperty("voice", voices[0].id)  # Male voice
            elif selected_voice == "female":
                engine.setProperty("voice", voices[1].id)  # Female voice

            # Save the narration audio to a file
            engine.save_to_file(narration_text, narration_audio_path)
            engine.runAndWait()

            # Load and process narration audio
            narration_audio = AudioSegment.from_file(narration_audio_path)
            narration_audio = narration_audio.set_frame_rate(44100).set_channels(1)
            narration_duration = len(narration_audio) / 1000  # Convert from ms to seconds

            # If no end time is provided
            if not end_time:
                end_time = min(video_duration, start_time + narration_duration)
            else:
                end_time = float(end_time)

            duration = end_time - start_time

            if narration_duration > duration:
                speed_factor = narration_duration / duration
                narration_audio = narration_audio._spawn(
                    narration_audio.raw_data, overrides={"frame_rate": int(44100 * speed_factor)}
                ).set_frame_rate(44100)

            # Export adjusted narration
            narration_audio.export(narration_audio_path, format="mp3")

            # Set audio on the video
            narration_audio_clip = AudioFileClip(narration_audio_path).subclip(0, min(duration, video_duration - start_time))
            video_with_audio = video_clip.set_audio(narration_audio_clip)
            video_with_audio.write_videofile(output_path, codec="libx264", audio_codec="aac")

            # Close clips to release resources
            video_with_audio.close()
            del video_with_audio

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

    return render_template("index.html")

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8082, debug=True)
