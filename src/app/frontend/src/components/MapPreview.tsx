import { useEffect, useState } from "react";
import { RouteNode, RouteSegment, StorePolygon } from "../mockData";

type MapPreviewProps = {
  path: RouteNode[];
  segments: RouteSegment[];
  activeSegmentIndex: number;
  currentNodeId?: string;
  targetNodeId?: string;
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
  polygons,
  onDimensionsChange,
}: MapPreviewProps) {
  const { projectedNodes, projectedPolygons, canvasWidth, canvasHeight } = projectGeometry(path, polygons);
  const lookup = new Map(projectedNodes.map((node) => [node.nodeId, node]));
  const currentNode = currentNodeId ? lookup.get(currentNodeId) : undefined;
  const targetNode = targetNodeId ? lookup.get(targetNodeId) : undefined;
  const aspectRatio = canvasWidth / canvasHeight;

  const [viewport, setViewport] = useState(() => ({
    width: typeof window !== "undefined" ? window.innerWidth : 1280,
    height: typeof window !== "undefined" ? window.innerHeight : 720,
  }));

  useEffect(() => {
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
          {segments.map((segment, index) => {
            const points = segment.path
              .map((nodeId) => lookup.get(nodeId))
              .filter((node): node is ProjectedNode => Boolean(node));
            if (points.length < 2) {
              return null;
            }
            const pathData = points
              .map((point, idx) => `${idx === 0 ? "M" : "L"}${point.screenX} ${point.screenY}`)
              .join(" ");
            const isActive = index === activeSegmentIndex;
            return (
              <path
                key={`${segment.from}-${segment.to}`}
                d={pathData}
                className={isActive ? "route-segment active" : "route-segment passive"}
              />
            );
          })}
          {currentNode && (
            <g className="current-node" transform={`translate(${currentNode.screenX}, ${currentNode.screenY})`}>
              <circle className="pulse" r={12} />
              <circle className="core" r={5.5} />
            </g>
          )}
          {targetNode && (
            <g className="target-node" transform={`translate(${targetNode.screenX}, ${targetNode.screenY})`}>
              <circle className="halo" r={8} />
              <circle className="core" r={4} />
            </g>
          )}
        </svg>
      </div>
    </section>
  );
}
