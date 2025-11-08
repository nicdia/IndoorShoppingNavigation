"""Extract shelf and wall polygons from the DXF and export them as JSON for the frontend."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Iterable, List, Tuple

import ezdxf

DXF_PATH = Path(__file__).with_name("drawing_supermarket.dxf")
OUTPUT_PATH = Path(__file__).parents[2] / "frontend" / "public" / "layout.json"
TARGET_LAYERS = {"0"}


def sanitize_loop(points: Iterable[Tuple[float, float]]) -> List[Tuple[float, float]]:
    cleaned: List[Tuple[float, float]] = []
    for x, y in points:
        cleaned.append((float(x), float(y)))
    if cleaned and cleaned[0] != cleaned[-1]:
        cleaned.append(cleaned[0])
    return cleaned


def main() -> None:
    doc = ezdxf.readfile(str(DXF_PATH))
    msp = doc.modelspace()

    polygons: List[dict] = []

    for entity in msp:
        dxftype = entity.dxftype()
        layer = entity.dxf.layer if entity.dxf.hasattr("layer") else ""
        if layer.lower() not in TARGET_LAYERS:
            continue

        if dxftype == "LWPOLYLINE":
            points = sanitize_loop(entity.get_points(format="xy"))
            if len(points) >= 4:
                polygons.append({"type": "polygon", "layer": layer, "points": points})
        elif dxftype == "POLYLINE":
            points = sanitize_loop(p[:2] for p in entity.points())
            if len(points) >= 4:
                polygons.append({"type": "polygon", "layer": layer, "points": points})
        elif dxftype == "HATCH":
            if not hasattr(entity, "paths"):
                continue
            for path in entity.paths:
                boundary = sanitize_loop(path.vertices)
                if len(boundary) >= 4:
                    polygons.append({"type": "polygon", "layer": layer, "points": boundary})

    bounds = doc.header.get("$EXTMIN"), doc.header.get("$EXTMAX")

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    content = {
        "source": DXF_PATH.name,
        "layers": sorted({poly["layer"] for poly in polygons}),
        "polygons": polygons,
        "extents": {
            "min": bounds[0],
            "max": bounds[1],
        },
    }
    OUTPUT_PATH.write_text(json.dumps(content, indent=2))
    print(f"Exported {len(polygons)} polygons to {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
