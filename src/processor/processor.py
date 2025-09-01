import os
import ipfshttpclient
import speech_recognition as sr
from pydub import AudioSegment

IPFS_CLIENT = ipfshttpclient.connect('/ip4/127.0.0.1/tcp/5001')

def transcribe_audio(audio_file):
    """Convert audio to text using SpeechRecognition"""
    recognizer = sr.Recognizer()
    audio = AudioSegment.from_file(audio_file)
    audio.export("temp.wav", format="wav")
    
    with sr.AudioFile("temp.wav") as source:
        audio_data = recognizer.record(source)
        try:
            text = recognizer.recognize_google(audio_data)
            return text
        except sr.UnknownValueError:
            return None
        except sr.RequestError as e:
            print(f"API error: {e}")
            return None

def process_video(video_path):
    """Process video → extract audio → transcribe → store on IPFS"""
    # Extract audio from video (if not already extracted)
    if not video_path.endswith('.mp3'):
        audio_path = video_path.replace('.mp4', '.mp3').replace('.webm', '.mp3')
        AudioSegment.from_file(video_path).export(audio_path, format='mp3')
    else:
        audio_path = video_path
    
    # Transcribe audio
    transcript = transcribe_audio(audio_path)
    
    if transcript:
        # Store transcript on IPFS
        metadata = {
            'source': video_path,
            'transcript': transcript,
            'type': 'transcription'
        }
        ipfs_hash = IPFS_CLIENT.add_json(metadata)
        print(f"Transcript stored on IPFS: {ipfs_hash}")
        return ipfs_hash
    return None

if __name__ == "__main__":
    # Process all videos in crawler output directory
    video_dir = 'crawler/videos'
    for video_file in os.listdir(video_dir):
        if video_file.endswith(('.mp4', '.webm', '.mp3')):
            video_path = os.path.join(video_dir, video_file)
            print(f"Processing: {video_path}")
            process_video(video_path)
    print("Video processing completed.")