import os
import subprocess
import win32com.client

GALLERY_DIR = r"C:\Users\Hassaan\Desktop\Devpost_Project_Gallery"
TEMP_DIR = r"C:\Users\Hassaan\Downloads\mcp-tutor-py\video_build_pitch"
OUTPUT_MP4 = r"C:\Users\Hassaan\Desktop\Omni_Tutor_Pitch_Video_2Min.mp4"

os.makedirs(TEMP_DIR, exist_ok=True)

# 10 High-Energy Founder Pitch Scenes (~125s total = ~2 minutes)
SCENES = [
    {
        "id": "scene_01",
        "image": "13_Omni_Tutor_Multi_Tab_Dashboard.png",
        "narration": "Every AI assistant today treats education like a reading assignment. When students ask about physics or coding, they get hit with five-hundred-word text walls. Even worse, A-I hallucinates and praises broken code, validating bad habits."
    },
    {
        "id": "scene_02",
        "image": "01_Live_Vercel_Production_Server.png",
        "narration": "We built Omni Tutor M-C-P to solve this real-world problem. Instead of walls of text, our system manifests interactive, multi-sensory three-D laboratories directly inside your chat thread using Generative U-I."
    },
    {
        "id": "scene_03",
        "image": "02_3D_Physics_Domino_Momentum_Explained.png",
        "narration": "When a student asks about momentum, we launch a real sixty-hertz rigid-body physics playground. You can pick up a steel cannonball, blast it into dominoes, and watch rotational torque topple the chain in real time."
    },
    {
        "id": "scene_04",
        "image": "03_3D_Physics_Rigid_Body_Photorealistic.png",
        "narration": "Switch gravity from Earth to the Moon, Zero-G, or Jupiter with one click. Students see real mass vectors, friction, and kinetic energy dissipation unfold before their eyes."
    },
    {
        "id": "scene_05",
        "image": "04_Web_Audio_Synthesizer_Oscilloscope.png",
        "narration": "For acoustics and Fourier transforms, we built a browser-native audio synthesizer. Play notes on the eight-key piano, switch between sine and sawtooth waves, and watch harmonics vibrate on a glowing sixty-F-P-S oscilloscope."
    },
    {
        "id": "scene_06",
        "image": "05_3D_Algorithm_Voxel_Sorting_Explained.png",
        "narration": "In computer science, abstract Big-O notation becomes physical. Our three-D voxel visualizer animates sorting step-by-step, color-coding swaps and teaching loop invariants in real space."
    },
    {
        "id": "scene_07",
        "image": "07_3D_Math_Calculus_Surface_Explained.png",
        "narration": "In multivariable calculus, students manipulate three-D topological wave surfaces, exploring closed-form equations, elevation colormaps, and gradient vector fields interactively."
    },
    {
        "id": "scene_08",
        "image": "09_3D_Solar_System_Astrophysics_Explained.png",
        "narration": "Using Google Gemini, the tutor generates structured astrophysical space simulations with Rayleigh atmospheric scattering and in-scene cards explaining Kepler's laws of orbital motion."
    },
    {
        "id": "scene_09",
        "image": "14_Automated_Verification_Report_Card.png",
        "narration": "Most importantly, the A-I never grades its own homework. Real Python subprocesses run unit tests in an isolated sandbox, ensuring one-hundred percent grading honesty with zero hallucinations."
    },
    {
        "id": "scene_10",
        "image": "01_Live_Vercel_Production_Server.png",
        "narration": "Omni Tutor M-C-P is live in production today on Vercel at m-c-p tutor p-y dot vercel dot app. Simply paste the URL into Claude Desktop or any M-C-P client to start learning. Thank you!"
    }
]

print("Step 1: Generating natural founder narration audio with SAPI...")
speaker = win32com.client.Dispatch("SAPI.SpVoice")
speaker.Rate = 0  # Standard human speech rate

def get_audio_duration(wav_path):
    cmd = [
        "ffprobe", "-v", "error", "-show_entries", "format=duration",
        "-of", "default=noprint_wrappers=1:nokey=1", wav_path
    ]
    res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    return float(res.stdout.strip())

scene_clips = []
total_duration = 0.0

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

    duration = get_audio_duration(wav_path) + 0.6  # 0.6s natural pacing buffer
    total_duration += duration
    print(f"  [{idx+1}/{len(SCENES)}] {scene_id}: {duration:.2f}s audio generated.")

    # Render scene MP4 with ffmpeg (1080p, 30fps, cross-fade)
    filter_complex = (
        f"scale=1920:1080:force_original_aspect_ratio=decrease,"
        f"pad=1920:1080:(ow-iw)/2:(oh-ih)/2:color=0x050810,"
        f"fade=t=in:st=0:d=0.35,fade=t=out:st={duration-0.35:.2f}:d=0.35"
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

print(f"\nStep 2: Concatenating all scenes into 2-minute master video (Total: {total_duration:.1f}s)...")
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

# Also save copy to repository
repo_mp4 = r"C:\Users\Hassaan\Downloads\mcp-tutor-py\Omni_Tutor_Pitch_Video_2Min.mp4"
subprocess.run(["ffmpeg", "-y", "-i", OUTPUT_MP4, "-c", "copy", repo_mp4], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

size_mb = os.path.getsize(OUTPUT_MP4) / (1024 * 1024)
print(f"\nSUCCESS! 2-Minute Founder Pitch Video created at: {OUTPUT_MP4} ({size_mb:.2f} MB, {total_duration:.1f}s)")
