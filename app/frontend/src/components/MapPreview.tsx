import { useEffect, useMemo, useState } from "react";
import { RouteNode, RouteSegment, StorePolygon } from "../types/route";

// Draws the store layout along with the shopper path and markers.

type MapPreviewProps = {
  path: RouteNode[];
  segments: RouteSegment[];
  activeSegmentIndex: number;
  currentNodeId?: string;
  targetNodeId?: string;
  targetLabel?: string;
  polygons?: StorePolygon[];
  onDimensionsChange?: (dimensions: { width: number; height: number }) => void;
};

const CANVAS_LONG_SIDE = 520;
const PADDING = 24;

type ProjectedNode = RouteNode & { screenX: number; screenY: number };
type ProjectedPolygon = StorePolygon & { screenPoints: { x: number; y: number }[] };

type Bounds = {
  minX: number;
  minY: number;
  scale: number;
  canvasWidth: number;
  canvasHeight: number;
};

function collectBounds(nodes: RouteNode[], polygons?: StorePolygon[]): Bounds {
  // Compute the visible canvas window so the geometry fits the viewport.
  const xs = [...nodes.map((node) => node.x)];
  const ys = [...nodes.map((node) => node.y)];
  if (polygons) {
    for (const poly of polygons) {
      for (const [x, y] of poly.points) {
        xs.push(x);
        ys.push(y);
      }
    }
  }
  const minX = Math.min(...xs);
  const maxX = Math.max(...xs);
  const minY = Math.min(...ys);
  const maxY = Math.max(...ys);
  const width = maxX - minX || 1;
  const height = maxY - minY || 1;
  const longestSide = Math.max(width, height);
  const scale = (CANVAS_LONG_SIDE - PADDING * 2) / longestSide;
  const canvasWidth = Math.max(width * scale + PADDING * 2, 160);
  const canvasHeight = Math.max(height * scale + PADDING * 2, 160);
  return { minX, minY, scale, canvasWidth, canvasHeight };
}

function projectGeometry(nodes: RouteNode[], polygons?: StorePolygon[]) {
  // Project map coordinates into canvas space while keeping proportions.
  const bounds = collectBounds(nodes, polygons);
  const projectPoint = (x: number, y: number) => ({
    x: (x - bounds.minX) * bounds.scale + PADDING,
    y: bounds.canvasHeight - ((y - bounds.minY) * bounds.scale + PADDING),
  });

  const projectedNodes: ProjectedNode[] = nodes.map((node) => {
    const screen = projectPoint(node.x, node.y);
    return {
      ...node,
      screenX: screen.x,
      screenY: screen.y,
    };
  });

  const projectedPolygons: ProjectedPolygon[] | undefined = polygons?.map((poly) => ({
    ...poly,
    screenPoints: poly.points.map(([x, y]) => projectPoint(x, y)),
  }));

  return { projectedNodes, projectedPolygons, canvasWidth: bounds.canvasWidth, canvasHeight: bounds.canvasHeight };
}

export function MapPreview({
  path,
  segments,
  activeSegmentIndex,
  currentNodeId,
  targetNodeId,
  targetLabel,
  polygons,
  onDimensionsChange,
}: MapPreviewProps) {
  const augmentedPath = useMemo(() => {
    // Include every segment waypoint so the map stays continuous.
    const map = new Map<string, RouteNode>();
    for (const node of path) {
      map.set(node.nodeId, node);
    }
    for (const segment of segments) {
      segment.path_coordinates?.forEach((coord) => {
        const nodeId = String(coord.node_id);
        if (!map.has(nodeId)) {
          map.set(nodeId, { nodeId, x: coord.x, y: coord.y });
        }
      });
    }
    return Array.from(map.values());
  }, [path, segments]);

  const { projectedNodes, projectedPolygons, canvasWidth, canvasHeight } = projectGeometry(augmentedPath, polygons);
  const lookup = new Map(projectedNodes.map((node) => [node.nodeId, node]));
  const currentNode = currentNodeId ? lookup.get(currentNodeId) : undefined;
  const targetNode = targetNodeId ? lookup.get(targetNodeId) : undefined;
  const targetCallout = useMemo(() => {
    // Position the target label so it avoids overlapping the marker.
    if (!targetNode) {
      return undefined;
    }
    const diagonalLength = 18;
    const horizontalLength = 28;
    const rightSpace = canvasWidth - targetNode.screenX;
    const leftSpace = targetNode.screenX;
    const direction: 1 | -1 = rightSpace >= leftSpace ? 1 : -1;
    const angleDegrees = direction === 1 ? -45 : -135;
    const angle = (angleDegrees * Math.PI) / 180;
    const start = { x: targetNode.screenX, y: targetNode.screenY };
    const kink = {
      x: start.x + Math.cos(angle) * diagonalLength,
      y: start.y + Math.sin(angle) * diagonalLength,
    };
    const end = {
      x: kink.x + direction * horizontalLength,
      y: kink.y,
    };
    const label = {
      x: end.x + direction * 6,
      y: end.y,
    };
    const textAnchor: "start" | "end" = direction === 1 ? "start" : "end";
    return { start, kink, end, label, textAnchor };
  }, [targetNode, canvasWidth]);
  const segmentPaths = segments
    .map((segment, index) => {
      const points = segment.path
        .map((nodeId) => lookup.get(nodeId))
        .filter((node): node is ProjectedNode => Boolean(node));
      if (points.length < 2) {
        return null;
      }
      const pathData = points
        .map((point, idx) => `${idx === 0 ? "M" : "L"}${point.screenX} ${point.screenY}`)
        .join(" ");
      return {
        key: `${segment.from}-${segment.to}-${index}`,
        pathData,
        isActive: index === activeSegmentIndex,
      };
    })
    .filter((entry): entry is { key: string; pathData: string; isActive: boolean } => Boolean(entry));
  const aspectRatio = canvasWidth / canvasHeight;

  const [viewport, setViewport] = useState(() => ({
    width: typeof window !== "undefined" ? window.innerWidth : 1280,
    height: typeof window !== "undefined" ? window.innerHeight : 720,
  }));

  useEffect(() => {
    // Track viewport updates so the canvas can respond to resizing.
    const update = () => {
      setViewport({ width: window.innerWidth, height: window.innerHeight });
    };
    update();
    window.addEventListener("resize", update);
    return () => window.removeEventListener("resize", update);
  }, []);

  const maxViewportHeight = Math.max(320, viewport.height - 220);
  const constrainedHeight = Math.min(660, maxViewportHeight);
  const displayHeight = Math.round(Math.max(320, Math.min(canvasHeight, constrainedHeight)));
  const desiredWidth = displayHeight * aspectRatio;
  const cappedCanvasWidth = Math.min(canvasWidth, 660);
  const minWidth = 280;
  const displayWidth = Math.round(Math.max(minWidth, Math.min(cappedCanvasWidth, desiredWidth)));
  const isNarrowLayout = viewport.width <= 960;
  const containerStyle = isNarrowLayout
    ? { width: "100%", maxWidth: "100%", height: `${displayHeight}px` }
    : { width: `${displayWidth}px`, height: `${displayHeight}px` };

  useEffect(() => {
    // Share the final render size with the parent layout.
    onDimensionsChange?.({ width: displayWidth, height: displayHeight });
  }, [displayWidth, displayHeight, onDimensionsChange]);

  return (
    <section
      className="map-preview"
      style={{ ...containerStyle, maxHeight: `${displayHeight}px`, aspectRatio: `${canvasWidth} / ${canvasHeight}` }}
    >
      <div className="map-frame">
        <svg
          viewBox={`0 0 ${canvasWidth} ${canvasHeight}`}
          role="img"
          aria-label="Route preview"
          preserveAspectRatio="xMidYMid meet"
          style={{ aspectRatio: `${aspectRatio}` }}
        >
          <rect x="0" y="0" width={canvasWidth} height={canvasHeight} className="map-background" />
          {projectedPolygons?.map((polygon, index) => (
            <polygon
              key={`${polygon.layer}-${index}`}
              points={polygon.screenPoints.map((point) => `${point.x},${point.y}`).join(" ")}
              className="map-polygon"
            />
          ))}
          {segmentPaths
            .filter((segment) => !segment.isActive)
            .map((segment) => (
              <path key={segment.key} d={segment.pathData} className="route-segment passive" />
            ))}
          {segmentPaths
            .filter((segment) => segment.isActive)
            .map((segment) => (
              <path key={`${segment.key}-active`} d={segment.pathData} className="route-segment active" />
            ))}
          {/* Node ID overlay removed because it was only used for debugging */}
          {currentNode && (
            <g className="current-node" transform={`translate(${currentNode.screenX}, ${currentNode.screenY})`}>
              <circle className="pulse" r={12} />
              <circle className="core" r={5.5} />
            </g>
          )}
          {targetCallout && (
            <g className="target-callout">
              <circle className="target-anchor" cx={targetCallout.start.x} cy={targetCallout.start.y} r={4.5} />
              <polyline
                className="target-callout-line"
                points={`${targetCallout.start.x},${targetCallout.start.y} ${targetCallout.kink.x},${targetCallout.kink.y} ${targetCallout.end.x},${targetCallout.end.y}`}
              />
              {targetLabel && (
                <text
                  className="target-callout-label"
                  x={targetCallout.label.x}
                  y={targetCallout.label.y}
                  dominantBaseline="middle"
                  textAnchor={targetCallout.textAnchor}
                >
                  {targetLabel}
                </text>
              )}
            </g>
          )}
        </svg>
      </div>
    </section>
  );
}
