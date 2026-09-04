import os
import subprocess
import win32com.client

GALLERY_DIR = r"C:\Users\Hassaan\Desktop\Devpost_Project_Gallery"
TEMP_DIR = r"C:\Users\Hassaan\Downloads\mcp-tutor-py\video_build"
OUTPUT_MP4 = r"C:\Users\Hassaan\Desktop\Omni_Tutor_Demo_Video.mp4"

os.makedirs(TEMP_DIR, exist_ok=True)

# 10 High-Impact Scenes for The WebMCP Challenge Demo Video
SCENES = [
    {
        "id": "scene_01",
        "image": "01_Live_Vercel_Production_Server.png",
        "narration": "Welcome to Omni Tutor MCP, the interactive 3D STEM and coding studio built for the Web MCP Challenge, live in production on Vercel."
    },
    {
        "id": "scene_02",
        "image": "13_Omni_Tutor_Multi_Tab_Dashboard.png",
        "narration": "Traditional AI assistants trap students in long, passive text walls and frequently hallucinate grading. Omni Tutor replaces text with live Generative UI inside your chat."
    },
    {
        "id": "scene_03",
        "image": "02_3D_Physics_Domino_Momentum_Explained.png",
        "narration": "Here is our 60 Hertz rigid-body physics playground powered by Cannon-es and Three.js. Students fire steel cannonballs, trigger domino cascades, and explore momentum and torque equations in real time."
    },
    {
        "id": "scene_04",
        "image": "03_3D_Physics_Rigid_Body_Photorealistic.png",
        "narration": "With one click, toggle gravity from Earth to the Moon, Zero-G, or Jupiter, experimenting with mass vectors, friction, and inelastic collision dissipation."
    },
    {
        "id": "scene_05",
        "image": "04_Web_Audio_Synthesizer_Oscilloscope.png",
        "narration": "Next is our interactive Web Audio synthesizer. Students play notes on an 8-key piano keyboard, toggle waveforms, and watch sound harmonics vibrate on a glowing 60 FPS oscilloscope."
    },
    {
        "id": "scene_06",
        "image": "05_3D_Algorithm_Voxel_Sorting_Explained.png",
        "narration": "To master computer science, our 3D voxel visualizer animates sorting step-by-step, color-coding swaps and teaching loop invariants directly in 3D space."
    },
    {
        "id": "scene_07",
        "image": "07_3D_Math_Calculus_Surface_Explained.png",
        "narration": "In multivariable calculus, students explore 3D wave topology surfaces with closed-form equations, elevation colormaps, and gradient vector fields."
    },
    {
        "id": "scene_08",
        "image": "09_3D_Solar_System_Astrophysics_Explained.png",
        "narration": "Using Google Gemini, Omni Tutor generates structured 3D astrophysics simulations with Rayleigh atmospheric scattering and in-scene cards explaining Kepler's laws of orbital motion."
    },
    {
        "id": "scene_09",
        "image": "14_Automated_Verification_Report_Card.png",
        "narration": "Most importantly, the AI never grades its own homework. Real Python subprocesses verify code deterministically, with 100% test coverage across all 13 tools and 6 widgets."
    },
    {
        "id": "scene_10",
        "image": "01_Live_Vercel_Production_Server.png",
        "narration": "Omni Tutor MCP is live in production today on Vercel and completely open source on GitHub. Thank you for watching!"
    }
]

print("Step 1: Generating voiceover narration audio with SAPI...")
speaker = win32com.client.Dispatch("SAPI.SpVoice")
speaker.Rate = 0  # Natural speed

# Get audio duration using ffprobe
def get_audio_duration(wav_path):
    cmd = [
        "ffprobe", "-v", "error", "-show_entries", "format=duration",
        "-of", "default=noprint_wrappers=1:nokey=1", wav_path
    ]
    res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    return float(res.stdout.strip())

scene_clips = []

for idx, sc in enumerate(SCENES):
    scene_id = sc["id"]
    wav_path = os.path.join(TEMP_DIR, f"{scene_id}.wav")
    img_path = os.path.join(GALLERY_DIR, sc["image"])
    clip_mp4 = os.path.join(TEMP_DIR, f"{scene_id}.mp4")

    # Generate WAV
    filestream = win32com.client.Dispatch("SAPI.SpFileStream")
    filestream.Open(wav_path, 3, False)
    speaker.AudioOutputStream = filestream
    speaker.Speak(sc["narration"])
    filestream.Close()

    duration = get_audio_duration(wav_path) + 0.8  # Add 0.8s padding for natural pacing
    print(f"  [{idx+1}/{len(SCENES)}] {scene_id}: {duration:.2f}s audio generated.")

    # Render scene MP4 with ffmpeg (1080p, 30fps, fade in/out)
    filter_complex = (
        f"scale=1920:1080:force_original_aspect_ratio=decrease,"
        f"pad=1920:1080:(ow-iw)/2:(oh-ih)/2:color=0x050810,"
        f"fade=t=in:st=0:d=0.4,fade=t=out:st={duration-0.4:.2f}:d=0.4"
    )

    cmd_clip = [
        "ffmpeg", "-y",
        "-loop", "1", "-t", str(duration), "-i", img_path,
        "-i", wav_path,
        "-vf", filter_complex,
        "-c:v", "libx264", "-tune", "stillimage", "-pix_fmt", "yuv420p",
        "-c:a", "aac", "-b:a", "192k",
        "-shortest",
        clip_mp4
    ]
    subprocess.run(cmd_clip, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)
    scene_clips.append(clip_mp4)

print("\nStep 2: Concatenating all scenes into final video...")
concat_txt = os.path.join(TEMP_DIR, "concat_list.txt")
with open(concat_txt, "w", encoding="utf-8") as f:
    for clip in scene_clips:
        f.write(f"file '{clip.replace(os.sep, '/')}'\n")

cmd_concat = [
    "ffmpeg", "-y",
    "-f", "concat", "-safe", "0",
    "-i", concat_txt,
    "-c", "copy",
    OUTPUT_MP4
]
subprocess.run(cmd_concat, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)

# Also copy to repo
repo_mp4 = r"C:\Users\Hassaan\Downloads\mcp-tutor-py\Omni_Tutor_Demo_Video.mp4"
subprocess.run(["ffmpeg", "-y", "-i", OUTPUT_MP4, "-c", "copy", repo_mp4], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

size_mb = os.path.getsize(OUTPUT_MP4) / (1024 * 1024)
print(f"\nSUCCESS! Demo video created at: {OUTPUT_MP4} ({size_mb:.2f} MB)")
