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

export type RouteSegment = {
  from: string;
  to: string;
  distance: number;
  path: string[];
};

export type StorePolygon = {
  layer: string;
  points: [number, number][];
};

export type RouteData = {
  order: Array<{
    nodeId: string;
    type: "entry" | "item" | "checkout";
    productId?: number;
    productName?: string;
  }>;
  path: RouteNode[];
  segments: RouteSegment[];
  totalDistance: number;
  metadata: {
    entry: string;
    checkout: string;
    selectedProducts: number[];
    units: string;
  };
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
  order: [
    { nodeId: "21", type: "entry" },
    { nodeId: "41", type: "item", productId: 41, productName: "Kiwi" },
    { nodeId: "61", type: "item", productId: 61, productName: "Apple" },
    { nodeId: "14", type: "checkout" }
  ],
  path: [
    { nodeId: "21", x: 2.0, y: 2.0 },
    { nodeId: "1", x: 2.0, y: 4.0 },
    { nodeId: "41", x: 1.0, y: 6.0 },
    { nodeId: "2", x: 2.0, y: 20.0 },
    { nodeId: "37", x: 7.0, y: 19.0 },
    { nodeId: "61", x: 11.0, y: 20.0 },
    { nodeId: "14", x: 15.0, y: 6.0 }
  ] satisfies RouteNode[],
  segments: [
    { from: "21", to: "41", distance: 4.2, path: ["21", "1", "41"] },
    { from: "41", to: "61", distance: 16.8, path: ["41", "1", "2", "37", "61"] },
    { from: "61", to: "14", distance: 11.4, path: ["61", "12", "13", "14"] }
  ] satisfies RouteSegment[],
  totalDistance: 32.4,
  metadata: {
    entry: "21",
    checkout: "14",
    selectedProducts: [41, 61],
    units: "meters"
  }
};
