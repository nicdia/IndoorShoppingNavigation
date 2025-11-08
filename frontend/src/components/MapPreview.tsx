import { RouteNode, RouteSegment, StorePolygon } from "../mockData";

type MapPreviewProps = {
  path: RouteNode[];
  segments: RouteSegment[];
  activeSegmentIndex: number;
  currentNodeId?: string;
  targetNodeId?: string;
  polygons?: StorePolygon[];
};

const CANVAS_SIZE = 520;
const PADDING = 24;

type ProjectedNode = RouteNode & { screenX: number; screenY: number };
type ProjectedPolygon = StorePolygon & { screenPoints: { x: number; y: number }[] };

function collectBounds(nodes: RouteNode[], polygons?: StorePolygon[]) {
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
  const scale = (CANVAS_SIZE - PADDING * 2) / Math.max(width, height);
  return { minX, minY, scale };
}

function projectGeometry(nodes: RouteNode[], polygons?: StorePolygon[]) {
  const bounds = collectBounds(nodes, polygons);
  const projectPoint = (x: number, y: number) => ({
    x: (x - bounds.minX) * bounds.scale + PADDING,
    y: CANVAS_SIZE - ((y - bounds.minY) * bounds.scale + PADDING),
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

  return { projectedNodes, projectedPolygons };
}

export function MapPreview({ path, segments, activeSegmentIndex, currentNodeId, targetNodeId, polygons }: MapPreviewProps) {
  const { projectedNodes, projectedPolygons } = projectGeometry(path, polygons);
  const lookup = new Map(projectedNodes.map((node) => [node.nodeId, node]));
  const currentNode = currentNodeId ? lookup.get(currentNodeId) : undefined;
  const targetNode = targetNodeId ? lookup.get(targetNodeId) : undefined;

  return (
    <section className="map-preview">
      <svg viewBox={`0 0 ${CANVAS_SIZE} ${CANVAS_SIZE}`} role="img" aria-label="Route preview">
        <rect x="0" y="0" width={CANVAS_SIZE} height={CANVAS_SIZE} className="map-background" />
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
            .filter(Boolean);
          if (points.length < 2) {
            return null;
          }
          const pathData = points
            .map((point, idx) => `${idx === 0 ? "M" : "L"}${point!.screenX} ${point!.screenY}`)
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
    </section>
  );
}
