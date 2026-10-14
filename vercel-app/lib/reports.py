"""Portable benchmark CSV and standalone SVG chart exports."""
import csv
import io


def benchmark_csv(data):
    out = io.StringIO()
    writer = csv.writer(out, lineterminator="\n")
    writer.writerow(["N", "brute_force_ms", "divide_conquer_ms", "distances_agree"])
    for row in data["rows"]:
        writer.writerow([row["n"], f'{row["brute_ms"]:.6f}', f'{row["divide_ms"]:.6f}', row["agree"]])
    return out.getvalue()


def benchmark_svg(data):
    rows = data["rows"]
    xmax = max((r["n"] for r in rows), default=1)
    ymax = max((max(r["brute_ms"], r["divide_ms"]) for r in rows), default=1) or 1
    pieces = ['<svg xmlns="http://www.w3.org/2000/svg" width="900" height="520" viewBox="0 0 900 520">',
              '<rect width="900" height="520" fill="white"/>',
              '<g font-family="Arial,sans-serif" fill="#28334b">',
              '<text x="60" y="35" font-size="21">Closest pair · measured running time</text>',
              f'<text x="60" y="60" font-size="12">Median of {data["repeats"]} runs per size; seed {data["seed"]}</text>']
    for i in range(6):
        y = 425 - i * 65
        pieces.append(f'<path d="M80 {y}H840" stroke="#e7ebf2"/><text x="70" y="{y+4}" text-anchor="end" font-size="11">{ymax*i/5:.2f}</text>')
    pieces.append('<path d="M80 95V425H840" fill="none" stroke="#8b95a6"/>')
    for key, color, label, legendx in (("brute_ms", "#df754e", "Brute force", 470), ("divide_ms", "#3974d8", "Divide &amp; conquer", 640)):
        coords = [(80 + r["n"] / xmax * 760, 425 - r[key] / ymax * 325) for r in rows]
        points = " ".join(f"{x:.2f},{y:.2f}" for x, y in coords)
        pieces.append(f'<polyline points="{points}" fill="none" stroke="{color}" stroke-width="3"/>')
        pieces.extend(f'<circle cx="{x:.2f}" cy="{y:.2f}" r="4" fill="{color}"/>' for x, y in coords)
        pieces.append(f'<circle cx="{legendx}" cy="55" r="5" fill="{color}"/><text x="{legendx+12}" y="59" font-size="12">{label}</text>')
    for r in rows:
        x = 80 + r["n"] / xmax * 760
        pieces.append(f'<text x="{x:.2f}" y="446" text-anchor="middle" font-size="11">{r["n"]}</text>')
    pieces.extend(['<text x="455" y="482" text-anchor="middle" font-size="13">Number of points (N)</text>',
                   '<text x="20" y="270" transform="rotate(-90 20 270)" text-anchor="middle" font-size="13">Time (ms)</text>', '</g></svg>'])
    return "".join(pieces)
