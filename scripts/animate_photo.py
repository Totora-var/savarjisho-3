#!/usr/bin/env python3
"""Cinemagraph-style animation: Ken Burns + cigarette smoke + golden-hour shimmer."""

from __future__ import annotations

import argparse
import math
import random
from pathlib import Path

import imageio.v2 as imageio
import numpy as np
from PIL import Image, ImageDraw, ImageEnhance, ImageFilter


def lerp(a: float, b: float, t: float) -> float:
    return a + (b - a) * t


def ease_in_out(t: float) -> float:
    return 0.5 - 0.5 * math.cos(math.pi * t)


class SmokeParticle:
    def __init__(self, origin: tuple[float, float], rng: random.Random) -> None:
        self.rng = rng
        self.reset(origin, initial=True)

    def reset(self, origin: tuple[float, float], initial: bool = False) -> None:
        ox, oy = origin
        self.x = ox + self.rng.uniform(-6, 6)
        self.y = oy + self.rng.uniform(-4, 4)
        self.vx = self.rng.uniform(-0.18, 0.28)
        self.vy = self.rng.uniform(-1.35, -0.55)
        self.life = self.rng.uniform(0.0, 1.0) if initial else 0.0
        self.max_life = self.rng.uniform(1.8, 3.6)
        self.size = self.rng.uniform(10, 28)
        self.wobble = self.rng.uniform(0.4, 1.4)
        self.phase = self.rng.uniform(0, math.tau)

    def update(self, origin: tuple[float, float], dt: float) -> None:
        self.life += dt
        if self.life >= self.max_life:
            self.reset(origin)
            return
        self.phase += dt * self.wobble
        self.x += self.vx + math.sin(self.phase) * 0.35
        self.y += self.vy
        self.size *= 1.01
        self.vx += self.rng.uniform(-0.02, 0.03)


def crop_ken_burns(img: Image.Image, frame: int, total: int, zoom_from: float, zoom_to: float) -> Image.Image:
    w, h = img.size
    t = ease_in_out(frame / max(total - 1, 1))
    zoom = lerp(zoom_from, zoom_to, t)
    cw, ch = int(w / zoom), int(h / zoom)
    # Slow drift upward-left toward the face / cigarette area
    max_x = w - cw
    max_y = h - ch
    x = int(lerp(max_x * 0.35, max_x * 0.18, t))
    y = int(lerp(max_y * 0.42, max_y * 0.22, t))
    return img.crop((x, y, x + cw, y + ch)).resize((w, h), Image.Resampling.LANCZOS)


def apply_shimmer(img: Image.Image, frame: int, fps: int) -> Image.Image:
    pulse = 0.5 + 0.5 * math.sin(frame / fps * math.tau * 0.35)
    brightness = 1.0 + 0.035 * pulse
    contrast = 1.0 + 0.02 * pulse
    out = ImageEnhance.Brightness(img).enhance(brightness)
    out = ImageEnhance.Contrast(out).enhance(contrast)
    # Warm tint breathe
    arr = np.asarray(out).astype(np.float32)
    warm = 1.0 + 0.018 * pulse
    arr[..., 0] = np.clip(arr[..., 0] * warm, 0, 255)
    arr[..., 1] = np.clip(arr[..., 1] * (1.0 + 0.008 * pulse), 0, 255)
    return Image.fromarray(arr.astype(np.uint8))


def draw_smoke(
    size: tuple[int, int],
    particles: list[SmokeParticle],
    origin: tuple[float, float],
    dt: float,
) -> Image.Image:
    layer = Image.new("RGBA", size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(layer)
    for p in particles:
        p.update(origin, dt)
        progress = p.life / p.max_life
        alpha = int(150 * (1.0 - progress) ** 1.15)
        if alpha <= 2:
            continue
        r = max(2, int(p.size * (0.45 + 0.85 * progress)))
        # Soft grey-white smoke with slight blue coolness
        color = (236, 238, 242, alpha)
        x0, y0 = int(p.x - r), int(p.y - r)
        draw.ellipse((x0, y0, x0 + 2 * r, y0 + 2 * r), fill=color)
    # Keep some structure after blur so wisps stay visible on bright shirts
    soft = layer.filter(ImageFilter.GaussianBlur(radius=5))
    return Image.alpha_composite(soft, layer.filter(ImageFilter.GaussianBlur(radius=1)))


def estimate_cigarette_tip(img: Image.Image) -> tuple[float, float]:
    """Find a small orange ember near the hand — avoid warm face skin."""
    w, h = img.size
    arr = np.asarray(img).astype(np.float32)
    # Hands/cigarette usually sit mid-frame, slightly right; skip forehead/cheeks.
    y0, y1 = int(h * 0.40), int(h * 0.68)
    x0, x1 = int(w * 0.42), int(w * 0.82)
    region = arr[y0:y1, x0:x1]
    r, g, b = region[..., 0], region[..., 1], region[..., 2]
    # Ember: hot orange/yellow speck, not broad skin.
    ember = (
        (r > 170)
        & (g > 70)
        & (g < 190)
        & (b < 120)
        & (r > g + 25)
        & (r > b + 50)
        & ((r - g) > (g - b) * 0.5)
    )
    if not np.any(ember):
        return w * 0.62, h * 0.48

    # Prefer compact bright clusters via local density of ember pixels.
    yy, xx = np.where(ember)
    scores = []
    for y, x in zip(yy, xx):
        y1b, y2b = max(0, y - 2), min(region.shape[0], y + 3)
        x1b, x2b = max(0, x - 2), min(region.shape[1], x + 3)
        density = float(ember[y1b:y2b, x1b:x2b].sum())
        heat = float(r[y, x] - 0.4 * g[y, x] - 0.8 * b[y, x])
        # Slight preference for lower (hand) vs upper (face edge)
        bias = (y / region.shape[0]) * 8.0
        scores.append((heat + density * 6.0 + bias, x, y))
    scores.sort(reverse=True)
    _, xx_best, yy_best = scores[0]
    return float(x0 + xx_best), float(y0 + yy_best)


def render(
    src: Path,
    out_mp4: Path,
    out_gif: Path | None,
    duration: float,
    fps: int,
    smoke_count: int,
    origin: tuple[float, float] | None = None,
) -> None:
    base = Image.open(src).convert("RGB")
    w, h = base.size
    # Work at a manageable render size then upscale if needed
    target_w = min(w, 720)
    scale = target_w / w
    target_h = int(h * scale)
    base = base.resize((target_w, target_h), Image.Resampling.LANCZOS)
    w, h = base.size

    if origin is None:
        origin = estimate_cigarette_tip(base)
        # Nudge slightly upward from ember so smoke rises from tip
        origin = (origin[0], origin[1] - 4)
    else:
        origin = (origin[0] * scale, origin[1] * scale)

    rng = random.Random(42)
    particles = [SmokeParticle(origin, rng) for _ in range(smoke_count)]

    total = int(duration * fps)
    frames: list[np.ndarray] = []
    dt = 1.0 / fps

    for i in range(total):
        frame = crop_ken_burns(base, i, total, zoom_from=1.0, zoom_to=1.12)
        frame = apply_shimmer(frame, i, fps)
        smoke = draw_smoke((w, h), particles, origin, dt)
        # Scale smoke origin with ken burns approx by keeping absolute for simplicity
        composed = Image.alpha_composite(frame.convert("RGBA"), smoke).convert("RGB")
        frames.append(np.asarray(composed))

    out_mp4.parent.mkdir(parents=True, exist_ok=True)
    imageio.mimsave(
        out_mp4,
        frames,
        fps=fps,
        codec="libx264",
        quality=8,
        pixelformat="yuv420p",
        macro_block_size=None,
    )

    if out_gif:
        # Shorter/lighter GIF for previews
        step = max(1, fps // 10)
        gif_frames = [Image.fromarray(frames[i]).resize((360, int(360 * h / w)), Image.Resampling.LANCZOS) for i in range(0, total, step)]
        gif_frames[0].save(
            out_gif,
            save_all=True,
            append_images=gif_frames[1:],
            duration=int(1000 / (fps / step)),
            loop=0,
            optimize=True,
        )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--src", type=Path, required=True)
    parser.add_argument("--out-mp4", type=Path, required=True)
    parser.add_argument("--out-gif", type=Path, default=None)
    parser.add_argument("--duration", type=float, default=6.0)
    parser.add_argument("--fps", type=int, default=24)
    parser.add_argument("--smoke", type=int, default=72)
    parser.add_argument(
        "--origin",
        type=str,
        default=None,
        help="Optional smoke origin as 'x,y' in pixels of the source image",
    )
    args = parser.parse_args()

    origin_override = None
    if args.origin:
        ox, oy = args.origin.split(",")
        origin_override = (float(ox), float(oy))

    render(
        args.src,
        args.out_mp4,
        args.out_gif,
        args.duration,
        args.fps,
        args.smoke,
        origin=origin_override,
    )
    print(f"Wrote {args.out_mp4}")
    if args.out_gif:
        print(f"Wrote {args.out_gif}")


if __name__ == "__main__":
    main()
