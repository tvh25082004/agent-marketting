import logging, os, subprocess, json, math, time
import numpy as np
from typing import Optional, Dict, Any
from PIL import Image, ImageDraw, ImageFont
from ..config import settings

logger = logging.getLogger(__name__)


class VideoGenerator:
    """Full video generation: image animation + lip-sync + karaoke"""

    def generate_singer_video(
        self,
        image_path: str,
        audio_path: str,
        lyrics: Optional[str] = None,
        output_path: Optional[str] = None,
        duration: Optional[float] = None,
    ) -> Optional[str]:
        """Generate complete singer video from image + audio"""
        if not os.path.exists(image_path):
            logger.error(f"Image not found: {image_path}")
            return None
        if not os.path.exists(audio_path):
            logger.error(f"Audio not found: {audio_path}")
            return None

        if output_path is None:
            output_path = os.path.join(settings.video_output_dir, "singer_video.mp4")
        os.makedirs(os.path.dirname(output_path), exist_ok=True)

        dur = duration or self._get_duration(audio_path)
        dur = min(dur, 262)

        W, H = settings.video_width, settings.video_height
        FPS = 15

        start = time.time()
        mouth_video = self._make_mouth_video(audio_path, dur, FPS)
        karaoke_video = self._make_karaoke_video(lyrics, dur, W, H, FPS) if lyrics else None

        self._composite(
            image_path, audio_path, mouth_video, karaoke_video,
            dur, W, H, FPS, output_path
        )

        elapsed = time.time() - start
        if os.path.exists(output_path):
            mb = os.path.getsize(output_path) / 1_048_576
            logger.info(f"Video done: {output_path} ({dur:.0f}s, {mb:.1f}MB, {elapsed:.0f}s)")
            return output_path
        return None

    def _get_duration(self, path: str) -> float:
        try:
            cmd = ["ffprobe", "-v", "quiet", "-print_format", "json", "-show_format", path]
            r = subprocess.run(cmd, capture_output=True, text=True, timeout=15)
            return float(json.loads(r.stdout)["format"]["duration"])
        except Exception:
            return 60.0

    def _extract_amplitude(self, audio_path: str, fps: int = 15) -> np.ndarray:
        cmd = ["ffmpeg", "-y", "-i", audio_path, "-ac", "1", "-ar", str(fps), "-f", "f32le", "-"]
        r = subprocess.run(cmd, capture_output=True, timeout=120)
        return np.abs(np.frombuffer(r.stdout, dtype=np.float32))

    def _make_mouth_video(self, audio_path: str, duration: float, fps: int) -> str:
        logger.info("Generating mouth animation...")
        out = os.path.join(settings.temp_dir, "mouth.mp4")
        if os.path.exists(out):
            return out

        total = int(duration * fps) + 1
        amp = self._extract_amplitude(audio_path, fps)
        amp = np.convolve(amp, np.ones(5) / 5, mode='same')
        if len(amp) < total:
            amp = np.pad(amp, (0, total - len(amp)), 'edge')
        amp = amp[:total]

        w, h = 300, 120
        raw = os.path.join(settings.temp_dir, "mouth_raw.raw")
        with open(raw, "wb") as f:
            for i in range(total):
                frame = np.zeros((h, w, 3), dtype=np.uint8)
                a = amp[i]
                mh = max(2, int(h * min(1.0, a * 4) * 0.5))
                cx, cy = w // 2, h // 2
                for dy in range(-mh // 2, mh // 2 + 1):
                    ratio = 2 * dy / mh if mh > 0 else 1
                    hw = 0 if abs(ratio) >= 1 else int((w // 2 - 20) * math.sqrt(1 - ratio ** 2))
                    for dx in range(-hw, hw + 1):
                        px, py = cx + dx, cy + dy
                        if 0 <= px < w and 0 <= py < h:
                            t = abs(dy) / (mh / 2) if mh > 0 else 1
                            frame[py, px] = [int(255 * (1 - t * 0.3)), int(50 * (1 - t * 0.5)), int(100 * (1 - t * 0.3))]
                if mh > 8:
                    for dx in range(-w // 4, w // 4 + 1):
                        px = cx + dx
                        if 0 <= px < w:
                            frame[cy, px] = [240, 240, 240]
                            if cy - 1 >= 0 and a > 0.2:
                                frame[cy - 1, px] = [200, 200, 200]
                f.write(frame.tobytes())

        subprocess.run([
            "ffmpeg", "-y", "-f", "rawvideo", "-pixel_format", "rgb24",
            "-video_size", f"{w}x{h}", "-framerate", str(fps), "-i", raw,
            "-c:v", "libx264", "-pix_fmt", "yuv420p", "-preset", "ultrafast", out,
        ], capture_output=True, timeout=120)
        return out

    def _make_karaoke_video(self, lyrics: Optional[str], duration: float, W: int, H: int, fps: int) -> Optional[str]:
        if not lyrics:
            return None
        logger.info("Generating karaoke overlay...")

        out = os.path.join(settings.temp_dir, "karaoke_overlay.mp4")
        if os.path.exists(out):
            return out

        lines = [l.strip() for l in lyrics.split("\n") if l.strip()]
        if not lines:
            return None

        oh = 200
        font = None
        for fp in ["/System/Library/Fonts/Helvetica.ttc", "/System/Library/Fonts/Supplemental/Arial.ttf"]:
            if os.path.exists(fp):
                try:
                    font = ImageFont.truetype(fp, 28)
                    break
                except: pass
        if not font:
            font = ImageFont.load_default()

        total = int(duration * fps)
        line_dur = duration / len(lines)

        # Only render unique text segments
        segments = []
        last_text = None
        for i in range(total):
            idx = min(int(i * fps * line_dur / fps / line_dur), len(lines) - 1)
            t = lines[idx]
            if t != last_text:
                segments.append((i, t))
                last_text = t
        segments.append((total, ""))

        rendered = {}
        raw = os.path.join(settings.temp_dir, "karaoke_raw.raw")
        with open(raw, "wb") as f:
            for seg_idx in range(len(segments) - 1):
                sf, text = segments[seg_idx]
                nf = segments[seg_idx + 1][0] - sf
                if text not in rendered:
                    frame = Image.new("RGBA", (W, oh), (0, 0, 0, 0))
                    draw = ImageDraw.Draw(frame)
                    y = 30
                    for line in text.split("\n")[:3]:
                        bbox = draw.textbbox((0, 0), line, font=font)
                        x = (W - (bbox[2] - bbox[0])) // 2
                        for dx, dy in [(2, 2), (-2, -2), (2, -2), (-2, 2), (0, 0)]:
                            draw.text((x + dx, y + dy), line, font=font,
                                      fill=(0, 0, 0, 180) if (dx, dy) != (0, 0) else (255, 255, 255, 230))
                        y += 50
                    rendered[text] = np.array(frame).tobytes()
                f.write(rendered[text] * nf)

        subprocess.run([
            "ffmpeg", "-y", "-f", "rawvideo", "-pixel_format", "rgba",
            "-video_size", f"{W}x{oh}", "-framerate", str(fps), "-i", raw,
            "-c:v", "libx264", "-pix_fmt", "yuva420p", "-preset", "fast", out,
        ], capture_output=True, timeout=120)
        return out

    def _composite(self, image_path: str, audio_path: str, mouth_video: str,
                   karaoke_video: Optional[str], duration: float,
                   W: int, H: int, FPS: int, output_path: str):
        logger.info("Compositing final video...")

        F = int(duration * FPS)
        img_h = int(W * 1024 / 670)
        yc = (H - img_h) // 2
        mx, my = (W - 300) // 2, yc + int(img_h * 0.4)

        filters = [
            f"[0:v]zoompan=z='if(lte(zoom,1.0),1.08,zoom-0.0003)':"
            f"x='iw/2-(iw/zoom/2)+30*sin(2*PI*on*0.001)':"
            f"y='ih/2-(ih/zoom/2)':"
            f"d={F}:s={W}x{H}:fps={FPS}[img]",
            f"color=c=#1a0b2e:s={W}x{H}:d={duration}:r={FPS}[bg]",
        ]
        inputs = ["-loop", "1", "-i", image_path, "-i", mouth_video, "-i", audio_path]
        chain = f"[bg][img]overlay=0:0[scene];[scene][1:v]overlay={mx}:{my}[face]"
        omap = ["-map", "[face]", "-map", "2:a"]

        if karaoke_video and os.path.exists(karaoke_video):
            inputs += ["-i", karaoke_video]
            chain += f";[face][3:v]overlay=0:{H - 200}[final]"
            omap = ["-map", "[final]", "-map", "2:a"]

        cmd = [
            "ffmpeg", "-y", *inputs,
            "-filter_complex", ";".join(filters + [chain]),
            *omap,
            "-c:v", "libx264", "-c:a", "aac", "-b:a", "192k",
            "-preset", "fast", "-crf", "26",
            "-pix_fmt", "yuv420p", "-shortest", output_path,
        ]
        subprocess.run(cmd, capture_output=True, timeout=900)
