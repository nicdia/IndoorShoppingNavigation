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

export const mockProducts: Product[] = [
  { id: 41, name: "Kiwi", category: "Fruit", level: 99, nodeId: 41 },
  { id: 61, name: "Apple", category: "Fruit", level: 99, nodeId: 61 },
  { id: 126, name: "Sausage", category: "Meat", level: 1, nodeId: 126 },
  { id: 139, name: "Peanut", category: "Snacks", level: 1, nodeId: 139 },
  { id: 145, name: "Toast", category: "Bakery", level: 2, nodeId: 145 },
  { id: 55, name: "Lettuce", category: "Vegetable", level: 99, nodeId: 55 }
];

export const mockRoute: RouteData = {
  order: ["41", "61", "59"],
  products: [
    { product_id: 2, name: "Kiwi", node_id: "41", node_x: 1.0, node_y: 6.0 },
    { product_id: 3, name: "Apple", node_id: "61", node_x: 1.0, node_y: 9.0 },
    { product_id: 4, name: "Banana", node_id: "59", node_x: 1.0, node_y: 13.0 }
  ],
  segments: [
    {
      from: "41",
      to: "61",
      cost: 3.0,
      path: ["41", "61"],
      disconnected: true,
      path_coordinates: [
        { node_id: "41", x: 1.0, y: 6.0 },
        { node_id: "61", x: 1.0, y: 9.0 }
      ]
    },
    {
      from: "61",
      to: "59",
      cost: 4.0,
      path: ["61", "59"],
      disconnected: true,
      path_coordinates: [
        { node_id: "61", x: 1.0, y: 9.0 },
        { node_id: "59", x: 1.0, y: 13.0 }
      ]
    }
  ],
  total_cost: 7.0,
  way_nodes: ["41", "61", "59"],
  node_coordinates: {
    "41": { x: 1.0, y: 6.0 },
    "61": { x: 1.0, y: 9.0 },
    "59": { x: 1.0, y: 13.0 }
  },
  waypoint_coordinates: [
    { node_id: "41", x: 1.0, y: 6.0 },
    { node_id: "61", x: 1.0, y: 9.0 },
    { node_id: "59", x: 1.0, y: 13.0 }
  ]
};
