#!/usr/bin/env python3
"""측정 결과 그래프.

results/compare_*.csv 를 읽어 analysis/ 에 그림 3장과 요약표를 만든다.

  fig1_read_pages.png   burst 한 번에 디스크에서 읽힌 페이지 수
  fig2_burst_time.png   burst 읽기에 걸린 시간
  fig3_seq_time.png     긴 순차 읽기에 걸린 시간
  summary.csv           조건·패턴별 중앙값, 최소, 최대

실행: python3 analysis/plot_results.py   (matplotlib 필요)
"""
import csv
import glob
import os
import statistics

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import font_manager
from matplotlib.lines import Line2D
from matplotlib.patches import Patch, PathPatch
from matplotlib.path import Path

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "analysis")

# 색: 파란 계열은 원본 커널이고 read_ahead_kb가 작을수록 옅다. 주황은 패치 커널.
# (이름, 범례 글자, 색, read_ahead_kb)
CONDS = [
    ("B0", "B0 (원본, 128KB)", "#104281", 128),
    ("P1", "P1 (패치, 128KB)", "#eb6834", 128),
    ("Btuned32", "B-tuned (원본, 32KB)", "#2a78d6", 32),
    ("Btuned16", "B-tuned (원본, 16KB)", "#86b6ef", 16),
]
BURSTS = [2, 3, 4, 8, 16]
PAGE = 4096

SURFACE = "#fcfcfb"
INK = "#0b0b0b"
INK2 = "#52514e"
MUTED = "#898781"
GRID = "#e1e0d9"
AXIS = "#c3c2b7"
NEED = "#c3c2b7"  # '필요한 양' 기준 막대

PT = 0.72  # 그림 위 1px(1/100인치)를 포인트로
FOOT = "Linux 5.4.214 · ext4 · 4 KiB pread · 매 실행 전 drop_caches · 조건마다 5회 측정"

# 한글 글꼴: 설치된 것 중 앞에 있는 것을 쓴다 (macOS, Linux, Windows 순)
_installed = {f.name for f in font_manager.fontManager.ttflist}
plt.rcParams["font.family"] = [
    name for name in ("Apple SD Gothic Neo", "NanumGothic", "Noto Sans CJK KR", "Malgun Gothic",
                      "DejaVu Sans")
    if name in _installed
]
plt.rcParams["axes.unicode_minus"] = False


def load():
    """(조건, 패턴, burst 길이) -> 측정 행 목록"""
    data = {}
    for path in sorted(glob.glob(os.path.join(ROOT, "results", "compare_*.csv"))):
        with open(path, newline="") as f:
            for row in csv.DictReader(f):
                key = (row["label"], row["pattern"], int(row["burst_pages"]))
                data.setdefault(key, []).append(row)
    return data


def stats(rows):
    read = statistics.median(int(r["read_bytes"]) for r in rows)
    times = [float(r["elapsed_ms"]) for r in rows]
    bursts = int(rows[0]["bursts"])
    return {
        "runs": len(rows),
        "kernel": rows[0]["kernel"],
        "requested_pages": int(rows[0]["requested_bytes"]) / PAGE / bursts,
        "read_pages": read / PAGE / bursts,
        "t_med": statistics.median(times),
        "t_min": min(times),
        "t_max": max(times),
    }


def figure(w, h, title, subtitle, left, bottom, right, top):
    """w x h 픽셀 그림과 그 안의 그래프 영역을 만든다. 여백도 픽셀 단위."""
    fig = plt.figure(figsize=(w / 100, h / 100), dpi=200, facecolor=SURFACE)
    ax = fig.add_axes(
        [left / w, bottom / h, (w - left - right) / w, (h - bottom - top) / h],
        facecolor=SURFACE,
    )
    ax.plot_px = (w - left - right, h - bottom - top)
    fig.text(16 / w, (h - 30) / h, title, fontsize=13, fontweight="bold", color=INK)
    fig.text(16 / w, (h - 52) / h, subtitle, fontsize=9, color=INK2)
    fig.text(16 / w, 10 / h, FOOT, fontsize=7.5, color=MUTED)
    for side in ("top", "right", "left", "bottom"):
        ax.spines[side].set_visible(False)
    ax.tick_params(length=0, labelsize=8.5, labelcolor=MUTED)
    return fig, ax


def legend(fig, handles, w, h, y):
    fig.legend(
        handles=handles, loc="upper left", bbox_to_anchor=(12 / w, (h - y) / h),
        ncol=len(handles), frameon=False, fontsize=9, labelcolor=INK2,
        handlelength=1.0, handleheight=1.0, handletextpad=0.5, columnspacing=1.6,
        borderaxespad=0,
    )


def units_per_px(ax):
    (x0, x1), (y0, y1) = ax.get_xlim(), ax.get_ylim()
    return (x1 - x0) / ax.plot_px[0], (y1 - y0) / ax.plot_px[1]


def column(ax, x, width_px, height, color, radius_px=4):
    """바닥은 각지고 위쪽 끝만 둥근 세로 막대"""
    ux, uy = units_per_px(ax)
    w = width_px * ux
    rx, ry = radius_px * ux, min(radius_px * uy, height)
    a, b = x - w / 2, x + w / 2
    verts = [(a, 0), (a, height - ry), (a, height), (a + rx, height), (b - rx, height),
             (b, height), (b, height - ry), (b, 0), (a, 0)]
    codes = [Path.MOVETO, Path.LINETO, Path.CURVE3, Path.CURVE3, Path.LINETO,
             Path.CURVE3, Path.CURVE3, Path.LINETO, Path.CLOSEPOLY]
    ax.add_patch(PathPatch(Path(verts, codes), facecolor=color, edgecolor="none"))


def bar(ax, y, thick_px, length, color, radius_px=4):
    """왼쪽은 각지고 오른쪽 끝만 둥근 가로 막대"""
    ux, uy = units_per_px(ax)
    t = thick_px * uy
    rx, ry = min(radius_px * ux, length), radius_px * uy
    a, b = y - t / 2, y + t / 2
    verts = [(0, a), (length - rx, a), (length, a), (length, a + ry), (length, b - ry),
             (length, b), (length - rx, b), (0, b), (0, a)]
    codes = [Path.MOVETO, Path.LINETO, Path.CURVE3, Path.CURVE3, Path.LINETO,
             Path.CURVE3, Path.CURVE3, Path.LINETO, Path.CLOSEPOLY]
    ax.add_patch(PathPatch(Path(verts, codes), facecolor=color, edgecolor="none"))


def burst_axis(ax):
    ax.set_xlim(-0.5, len(BURSTS) - 0.5)
    ax.set_xticks(range(len(BURSTS)))
    ax.set_xticklabels([f"{b}페이지" for b in BURSTS], fontsize=9, color=INK2)
    ax.set_xlabel("한 번에 이어서 읽는 길이 (burst)", fontsize=8.5, color=MUTED, labelpad=6)
    ax.yaxis.grid(True, color=GRID, linewidth=PT)
    ax.set_axisbelow(True)
    ax.axhline(0, color=AXIS, linewidth=PT)


def fig1_read_pages(data):
    w, h = 800, 470
    fig, ax = figure(
        w, h, "짧게 읽고 건너뛸 때 디스크에서 읽힌 양",
        "burst 한 번에 읽힌 페이지 수 (1페이지 = 4 KiB). 괄호 안은 커널과 read_ahead_kb 설정",
        left=52, bottom=80, right=20, top=106,
    )
    burst_axis(ax)
    ax.set_ylim(0, 66)
    ax.set_yticks([0, 20, 40, 60])

    width, gap = 20, 2
    ux, _ = units_per_px(ax)
    series = [("필요한 양", NEED, None)] + [(lab, color, name) for name, lab, color, _ in CONDS]
    for g, burst in enumerate(BURSTS):
        for i, (_, color, name) in enumerate(series):
            x = g + (i - (len(series) - 1) / 2) * (width + gap) * ux
            value = burst if name is None else stats(data[(name, "burst", burst)])["read_pages"]
            column(ax, x, width, value, color)
            if name in ("B0", "P1"):  # 이야기의 중심인 두 조건만 값을 적는다
                ax.annotate(f"{value:.0f}", (x, value), xytext=(0, 3), textcoords="offset points",
                            ha="center", va="bottom", fontsize=8, color=INK)
    legend(fig, [Patch(facecolor=c, edgecolor="none", label=lab) for lab, c, _ in series], w, h, 68)
    fig.savefig(os.path.join(OUT, "fig1_read_pages.png"), facecolor=SURFACE)
    plt.close(fig)


def fig2_burst_time(data):
    w, h = 800, 470
    fig, ax = figure(
        w, h, "짧은 burst 읽기에 걸린 시간",
        "burst 500회에 걸린 시간 (ms). 점은 5회 중앙값, 세로선은 최소~최대",
        left=52, bottom=80, right=20, top=106,
    )
    burst_axis(ax)
    ax.set_ylim(0, 1300)
    ax.set_yticks([0, 250, 500, 750, 1000, 1250])
    ax.set_yticklabels(["0", "250", "500", "750", "1,000", "1,250"])

    step = 18
    ux, _ = units_per_px(ax)
    for g, burst in enumerate(BURSTS):
        for i, (name, _, color, _) in enumerate(CONDS):
            s = stats(data[(name, "burst", burst)])
            x = g + (i - (len(CONDS) - 1) / 2) * step * ux
            ax.plot([x, x], [s["t_min"], s["t_max"]], color=color, linewidth=2 * PT,
                    solid_capstyle="round")
            ax.plot([x], [s["t_med"]], marker="o", markersize=7, color=color,
                    markeredgecolor=SURFACE, markeredgewidth=2 * PT)
    handles = [Line2D([], [], marker="o", linestyle="none", markersize=7, color=color,
                      markeredgecolor=SURFACE, markeredgewidth=2 * PT, label=lab)
               for _, lab, color, _ in CONDS]
    legend(fig, handles, w, h, 68)
    fig.savefig(os.path.join(OUT, "fig2_burst_time.png"), facecolor=SURFACE)
    plt.close(fig)


def fig3_seq_time(data):
    w, h = 800, 320
    fig, ax = figure(
        w, h, "긴 순차 읽기에 걸린 시간",
        "896 MiB 파일을 처음부터 끝까지 읽는 시간 (초). 막대는 5회 중앙값, 선은 최소~최대",
        left=150, bottom=52, right=24, top=84,
    )
    ax.set_xlim(0, 12)
    ax.set_xticks([0, 2, 4, 6, 8, 10])
    ax.set_ylim(-0.5, len(CONDS) - 0.5)
    ax.set_yticks(range(len(CONDS)))
    ax.set_yticklabels([lab for _, lab, _, _ in reversed(CONDS)], fontsize=9, color=INK2)
    ax.tick_params(axis="y", pad=8)
    ax.xaxis.grid(True, color=GRID, linewidth=PT)
    ax.set_axisbelow(True)
    ax.axvline(0, color=AXIS, linewidth=PT)

    base = stats(data[("B0", "seq", 0)])["t_med"]
    for i, (name, _, color, _) in enumerate(CONDS):
        s = stats(data[(name, "seq", 0)])
        y = len(CONDS) - 1 - i
        med, lo, hi = s["t_med"] / 1000, s["t_min"] / 1000, s["t_max"] / 1000
        bar(ax, y, 22, med, color)
        # 최소~최대 선: 막대 안쪽은 바탕색, 바깥쪽은 글자색으로 그려 어느 막대에서도 보이게 한다
        cap = 4 * units_per_px(ax)[1]
        for a, b, c in ((lo, med, SURFACE), (med, hi, INK2)):
            ax.plot([a, b], [y, y], color=c, linewidth=1.5 * PT, solid_capstyle="butt")
        ax.plot([lo, lo], [y - cap, y + cap], color=SURFACE, linewidth=1.5 * PT)
        ax.plot([hi, hi], [y - cap, y + cap], color=INK2, linewidth=1.5 * PT)
        text = f"{med:.2f}초"
        slower = (s["t_med"] / base - 1) * 100
        if name.startswith("Btuned"):
            text += f"  B0보다 {slower:.0f}% 느림"
        ax.annotate(text, (hi, y), xytext=(7, 0), textcoords="offset points",
                    ha="left", va="center", fontsize=9, color=INK)
    fig.savefig(os.path.join(OUT, "fig3_seq_time.png"), facecolor=SURFACE)
    plt.close(fig)


def write_summary(data):
    path = os.path.join(OUT, "summary.csv")
    with open(path, "w", newline="") as f:
        out = csv.writer(f)
        out.writerow(["condition", "kernel", "read_ahead_kb", "pattern", "burst_pages", "runs",
                      "requested_pages", "read_pages", "read_ratio",
                      "time_ms_median", "time_ms_min", "time_ms_max"])
        for name, _, _, ra_kb in CONDS:
            for pattern, burst in [("burst", b) for b in BURSTS] + [("seq", 0)]:
                s = stats(data[(name, pattern, burst)])
                out.writerow([name, s["kernel"], ra_kb, pattern, burst, s["runs"],
                              f"{s['requested_pages']:.0f}", f"{s['read_pages']:.2f}",
                              f"{s['read_pages'] / s['requested_pages']:.2f}",
                              f"{s['t_med']:.1f}", f"{s['t_min']:.1f}", f"{s['t_max']:.1f}"])


def main():
    data = load()
    fig1_read_pages(data)
    fig2_burst_time(data)
    fig3_seq_time(data)
    write_summary(data)
    print("저장:", OUT)


if __name__ == "__main__":
    main()
