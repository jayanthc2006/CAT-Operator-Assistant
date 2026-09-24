"""Build the offline micro-lesson training_videos/terrain.mp4 ("Safe operation on sloped terrain").

Build-time only: uses matplotlib for frames and the ffmpeg binary bundled with the `imageio-ffmpeg` package
(`pip install imageio-ffmpeg`). The app itself only plays the resulting MP4, with no extra dependency.
Run: .venv\\Scripts\\python.exe tools\\make_offline_lesson.py
"""
from pathlib import Path

import imageio_ffmpeg
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.patches import Circle, FancyBboxPatch, Polygon, Rectangle, Wedge

OUT = Path(__file__).resolve().parents[1] / "training_videos" / "terrain.mp4"
W, H, FPS = 1280, 720, 12
YEL, BLK, RED, GRN, GRY = "#FFCD11", "#1A1A1A", "#D32F2F", "#2E7D32", "#9E9E9E"


def canvas():
    fig = plt.figure(figsize=(W / 100, H / 100), dpi=100)
    ax = fig.add_axes([0, 0, 1, 1])
    ax.set_xlim(0, 16)
    ax.set_ylim(0, 9)
    ax.axis("off")
    ax.add_patch(Rectangle((0, 8.1), 16, 0.9, color=BLK))
    ax.text(0.4, 8.55, "CAT", color=BLK, fontsize=20, fontweight="bold", va="center",
            bbox=dict(boxstyle="square,pad=0.2", fc=YEL, ec=YEL))
    ax.text(1.6, 8.55, "Operator Assistant · Micro-lesson: Safe operation on sloped terrain", color="white",
            fontsize=16, va="center")
    return fig, ax


def machine(ax, x, y, angle_deg, bucket_low=True, colour=YEL):
    """Very simple side view of an excavator/dozer body rotated to the ground angle."""
    a = np.radians(angle_deg)
    rot = np.array([[np.cos(a), -np.sin(a)], [np.sin(a), np.cos(a)]])

    def P(pts):
        return (np.array(pts) @ rot.T) + [x, y]

    ax.add_patch(Polygon(P([(-1.2, 0), (1.2, 0), (1.2, .35), (-1.2, .35)]), color=BLK))        # tracks
    ax.add_patch(Polygon(P([(-1.0, .35), (0.9, .35), (0.9, 1.2), (-1.0, 1.2)]), color=colour))  # body
    ax.add_patch(Polygon(P([(-0.2, 1.2), (0.6, 1.2), (0.6, 1.8), (-0.2, 1.8)]), color=colour, ec=BLK))  # cab
    by = 0.15 if bucket_low else 1.6
    ax.add_patch(Polygon(P([(0.9, .9), (1.9, by + .5), (2.0, by + .3)]), color=BLK))              # arm
    ax.add_patch(Polygon(P([(1.9, by), (2.4, by), (2.3, by + .5), (1.9, by + .5)]), color=GRY))  # bucket


def tilt_gauge(ax, x, y, value, limit=15):
    ax.add_patch(Wedge((x, y), 1.4, 0, 180, width=0.35, color="#e6e6e6"))
    ax.add_patch(Wedge((x, y), 1.4, 180 - limit / 30 * 180, 180, width=0.35, color="#c8e6c9"))
    ax.add_patch(Wedge((x, y), 1.4, 0, 180 - limit / 30 * 180, width=0.35, color="#ffcdd2"))
    ang = np.radians(180 - min(value, 30) / 30 * 180)
    ax.plot([x, x + 1.2 * np.cos(ang)], [y, y + 1.2 * np.sin(ang)], color=BLK, lw=4)
    ax.add_patch(Circle((x, y), .12, color=BLK))
    ax.text(x, y - .5, f"Tilt {value:.0f}°", ha="center", fontsize=18, fontweight="bold",
            color=RED if value > limit else BLK)


def caption(ax, text, colour=BLK):
    ax.add_patch(FancyBboxPatch((0.5, 0.3), 15, 1.1, boxstyle="round,pad=0.1", fc="white", ec=colour, lw=3))
    ax.text(8, .85, text, ha="center", va="center", fontsize=22, color=colour, fontweight="bold")


def scene_title(t):
    fig, ax = canvas()
    ax.text(8, 5.2, "Safe operation on\nsloped terrain", ha="center", va="center", fontsize=54, fontweight="bold")
    ax.text(8, 2.8, "2-minute micro-lesson · plays offline in the cab", ha="center", fontsize=22, color=GRY)
    return fig


def scene_across(t):  # 0..1
    fig, ax = canvas()
    ax.add_patch(Polygon([(0, 1.6), (16, 1.6), (16, 5.2), (0, 2.2)], color="#d7c9a7"))  # side slope seen from behind
    tilt = 4 + 16 * t
    xm = 3 + 9 * t
    ground = np.degrees(np.arctan(3 / 16))  # the drawn side-slope
    machine(ax, xm, 2.2 + 3 * xm / 16, ground + 6 * t, bucket_low=False, colour=YEL)
    tilt_gauge(ax, 13.5, 6.0, tilt)
    if t > 0.55:
        ax.text(8, 6.6, "✗", fontsize=90, color=RED, ha="center", va="center")
    caption(ax, "Never travel ACROSS a slope: the machine tilts sideways and can roll", RED)
    return fig


def scene_straight(t):
    fig, ax = canvas()
    ax.add_patch(Polygon([(0, 1.6), (16, 1.6), (16, 6.0), (0, 1.6)], color="#d7c9a7"))
    ang = np.degrees(np.arctan(4.4 / 16))
    xm = 2 + 10 * t
    machine(ax, xm, 1.6 + xm * 4.4 / 16 + .02, ang, bucket_low=True, colour=YEL)
    tilt_gauge(ax, 13.5, 6.4, 3)
    if t > 0.5:
        ax.text(3.5, 6.4, "✓", fontsize=90, color=GRN, ha="center", va="center")
    caption(ax, "Travel straight UP or DOWN the slope with the bucket LOW", GRN)
    return fig


def scene_speed(t):
    fig, ax = canvas()
    v = 40 + 50 * np.sin(np.pi * t) ** 2 * 0.95
    ax.add_patch(Rectangle((3, 3.2), 10, 1.0, color="#e6e6e6"))
    ax.add_patch(Rectangle((3, 3.2), 10 * v / 100, 1.0, color=GRN if v <= 95 else RED))
    ax.plot([3 + 9.5, 3 + 9.5], [2.9, 4.5], color=RED, lw=4)
    ax.text(12.5, 4.8, "95% of site limit", ha="center", fontsize=16, color=RED)
    ax.text(8, 5.8, f"Speed on slope: {v:.0f}% of limit", ha="center", fontsize=30, fontweight="bold")
    caption(ax, "Slow down on slopes: stay below 95% of the site speed limit")
    return fig


def scene_warning(t):
    fig, ax = canvas()
    val = 8 + 10 * min(1, t * 1.6)
    tilt_gauge(ax, 5, 4.2, val)
    if val > 15:
        ax.add_patch(FancyBboxPatch((8.6, 3.2), 6.6, 2.6, boxstyle="round,pad=0.2", fc=RED, ec=RED))
        ax.text(11.9, 4.9, "TILT WARNING", ha="center", fontsize=28, color="white", fontweight="bold")
        ax.text(11.9, 3.9, "1. Stop   2. Lower the bucket\n3. Move to level ground", ha="center", fontsize=17, color="white")
    caption(ax, "Tilt warning at 15°: stop, lower the bucket, move to level ground", RED if val > 15 else BLK)
    return fig


def scene_summary(t):
    fig, ax = canvas()
    ax.text(8, 7.2, "Remember", ha="center", fontsize=40, fontweight="bold")
    pts = ["Straight up or down, never across", "Bucket or blade low when travelling",
           "Below 95% of the speed limit on slopes", "At a 15° tilt warning: stop, lower, level"]
    for i, p in enumerate(pts):
        if t > i * 0.18:
            ax.text(3, 5.8 - i * 1.15, f"✓  {p}", fontsize=26, color=GRN if i < 3 else RED)
    caption(ax, "Now take the 3-question knowledge check in the Training Hub")
    return fig


SCENES = [(scene_title, 4), (scene_across, 9), (scene_straight, 8), (scene_speed, 6), (scene_warning, 8), (scene_summary, 7)]


def main():
    OUT.parent.mkdir(exist_ok=True)
    writer = imageio_ffmpeg.write_frames(str(OUT), (W, H), fps=FPS, codec="libx264", pix_fmt_out="yuv420p",
                                         output_params=["-movflags", "+faststart"], macro_block_size=16)
    writer.send(None)
    for scene, seconds in SCENES:
        n = seconds * FPS
        for i in range(n):
            fig = scene(i / max(1, n - 1))
            fig.canvas.draw()
            frame = np.asarray(fig.canvas.buffer_rgba())[:, :, :3].copy()
            plt.close(fig)
            writer.send(frame)
    writer.close()
    print(f"wrote {OUT} ({OUT.stat().st_size / 1e6:.1f} MB, {sum(s for _, s in SCENES)} s)")


if __name__ == "__main__":
    main()
