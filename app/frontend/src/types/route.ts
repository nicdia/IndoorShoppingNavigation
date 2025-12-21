// Shared data contracts between the client and the backend service.

export type Product = {
  id: number;
  name: string;
  category?: string;
  level?: number | null;
  nodeId?: number | null;
};

export type RouteNode = {
  nodeId: string;
  x: number;
  y: number;
  type?: "entry" | "item" | "checkout";
  productId?: number;
};

export type NodeCoordinate = {
  x: number;
  y: number;
};

export type WaypointCoordinate = {
  node_id: string;
  x: number;
  y: number;
};

export type RouteSegment = {
  from: string;
  to: string;
  path: string[];
  cost: number;
  disconnected?: boolean;
  path_coordinates?: WaypointCoordinate[];
  path_edges?: RoutePathEdge[];
};

export type RoutePathEdge = {
  from: string;
  to: string;
  length?: number | null;
  left_shelf?: string | null;
  right_shelf?: string | null;
};

export type StorePolygon = {
  layer: string;
  points: [number, number][];
};

export type RouteData = {
  order: string[];
  products: Array<{
    product_id: number;
    name: string;
    node_id: string;
    node_x?: number;
    node_y?: number;
  }>;
  segments: RouteSegment[];
  total_cost: number;
  way_nodes: string[];
  node_coordinates?: Record<string, NodeCoordinate>;
  waypoint_coordinates?: WaypointCoordinate[];
};
