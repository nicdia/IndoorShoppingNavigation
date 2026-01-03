import { useCallback, useEffect, useMemo, useState, type CSSProperties } from "react";
import { ProductList } from "./components/ProductList";
import { StartLocationSelector } from "./components/StartLocationSelector";
import { MapPreview } from "./components/MapPreview";
import { SelectedChecklist } from "./components/SelectedChecklist";
import { RouteSummary } from "./components/RouteSummary";
import { Product, RouteData, RouteNode, StorePolygon } from "./types/route";
import { NODE_COORDINATES } from "./data/nodeCoordinates";
import { buildNavigationInstructions, EdgeAnnotationLookup, makeEdgeKey } from "./utils/navigationText";

// Central application component driving product selection and route execution.

const DEFAULT_API_BASE = "http://127.0.0.1:8000";
const API_BASE_URL = (import.meta.env.VITE_API_BASE_URL as string | undefined)?.replace(/\/$/, "") ?? DEFAULT_API_BASE;

const NODE_LABEL_OVERRIDES: Record<string, string> = {
  "21": "Entrance",
  "14": "Checkout",
  "15": "Checkout",
};

const DEFAULT_ENTRY_NODE_ID = "21";

const getNodeLabelOverride = (nodeId: string | number | null | undefined) => {
  if (nodeId === null || nodeId === undefined) {
    return undefined;
  }
  const normalized = String(nodeId).trim();
  if (!normalized) {
    return undefined;
  }
  const numericCandidate = Number(normalized);
  const candidateKeys = [normalized];
  if (Number.isFinite(numericCandidate)) {
    candidateKeys.push(String(numericCandidate));
    candidateKeys.push(String(Math.trunc(numericCandidate)));
  }
  for (const key of candidateKeys) {
    const override = NODE_LABEL_OVERRIDES[key];
    if (override) {
      return override;
    }
  }
  return undefined;
};

function App() {
  const [searchTerm, setSearchTerm] = useState("");
  const [products, setProducts] = useState<Product[]>([]);
  const [productsLoading, setProductsLoading] = useState(false);
  const [productsError, setProductsError] = useState<string | null>(null);

  const [selectedProducts, setSelectedProducts] = useState<number[]>([]);
  const [startNodeId, setStartNodeId] = useState<string>(DEFAULT_ENTRY_NODE_ID);
  const [routeData, setRouteData] = useState<RouteData | null>(null);
  const [isLoadingRoute, setIsLoadingRoute] = useState(false);
  const [routeError, setRouteError] = useState<string | null>(null);

  const [activeIndex, setActiveIndex] = useState(0);
  const [completed, setCompleted] = useState<boolean[]>([]);
    const [view, setView] = useState<"start" | "select" | "route">("start");
  const [layoutPolygons, setLayoutPolygons] = useState<StorePolygon[] | null>(null);
  const [mapPanelSize, setMapPanelSize] = useState<{ width: number; height: number } | null>(null);

  useEffect(() => {
    // Fetch products from the backend on first render.
    setProductsLoading(true);
    fetch(`${API_BASE_URL}/products`)
      .then(async (response) => {
        const payload = await response.json().catch(() => ({}));
        if (!response.ok) {
          const detail = typeof payload.detail === "string" ? payload.detail : "Failed to load products from API.";
          throw new Error(detail);
        }
        return payload;
      })
      .then((data) => {
        if (Array.isArray(data?.items)) {
          const parsed = data.items
            .map((item: any): Product | null => {
              const id = Number(item.id ?? item.code);
              if (!Number.isFinite(id)) {
                return null;
              }
              return {
                id,
                name: String(item.name ?? ""),
                level: item.level ?? null,
                nodeId: item.nodeId ?? null,
              };
            })
            .filter((item: Product | null): item is Product => item !== null);
          if (parsed.length > 0) {
            setProductsError(null);
            setProducts(parsed);
          } else {
            setProductsError("Product list from API was empty.");
            setProducts([]);
          }
        }
      })
      .catch((error) => {
        setProductsError(error instanceof Error ? error.message : "Could not load products from API.");
        setProducts([]);
      })
      .finally(() => setProductsLoading(false));
  }, []);

  useEffect(() => {
    // Load static layout polygons once for the map overlay.
    fetch("/layout.json")
      .then((response) => {
        if (!response.ok) {
          throw new Error("Failed to load layout.json");
        }
        return response.json();
      })
      .then((data) => {
        if (Array.isArray(data.polygons)) {
          setLayoutPolygons(
            data.polygons.map((polygon: { layer: string; points: [number, number][] }) => ({
              layer: polygon.layer,
              points: polygon.points,
            }))
          );
        }
      })
      .catch(() => {
        setLayoutPolygons(null);
      });
  }, []);

  const combinedErrorMessage = useMemo(() => {
    // Merge product and route errors so the UI can show a single message.
    const messages = [productsError, routeError].filter((value): value is string => Boolean(value));
    return messages.length > 0 ? messages.join(". ") : null;
  }, [productsError, routeError]);

  const startOptions = useMemo(() => {
    const entranceLabel = getNodeLabelOverride(DEFAULT_ENTRY_NODE_ID) ?? "Entrance";

    const nodeLabelMap = new Map<string, string>();
    products.forEach((product) => {
      if (product.nodeId === null || product.nodeId === undefined) {
        return;
      }
      const nodeValue = String(product.nodeId).trim();
      if (!nodeValue || nodeLabelMap.has(nodeValue)) {
        return;
      }
      const label = product.name?.trim() || `Product ${nodeValue}`;
      nodeLabelMap.set(nodeValue, label);
    });

    const productOptions = Array.from(nodeLabelMap.entries())
      .map(([value, label]) => ({ value, label }))
      .sort((a, b) => a.label.localeCompare(b.label, undefined, { sensitivity: "base" }));

    return [{ value: DEFAULT_ENTRY_NODE_ID, label: entranceLabel }, ...productOptions];
  }, [products]);

  const coordinateLookup = useMemo(() => {
    // Build a lookup table for node coordinates with service data taking priority.
    const map = new Map<string, { x: number; y: number }>();

    if (routeData?.node_coordinates) {
      Object.entries(routeData.node_coordinates).forEach(([nodeId, coords]) => {
        if (coords && typeof coords.x === "number" && typeof coords.y === "number") {
          map.set(String(nodeId), { x: coords.x, y: coords.y });
        }
      });
    }

    if (Array.isArray(routeData?.waypoint_coordinates)) {
      routeData.waypoint_coordinates.forEach((waypoint) => {
        if (waypoint && typeof waypoint.node_id === "string") {
          const { node_id, x, y } = waypoint;
          if (typeof x === "number" && typeof y === "number") {
            map.set(node_id, { x, y });
          }
        }
      });
    }

    if (map.size === 0) {
      Object.entries(NODE_COORDINATES).forEach(([nodeId, coords]) => {
        map.set(nodeId, { x: coords.x, y: coords.y });
      });
    }

    return map;
  }, [routeData]);

  const pathNodeIds = useMemo(() => {
    // Derive an ordered list of node ids that make up the full path.
    const unique: string[] = [];
    const appendUnique = (value: string | number | null | undefined) => {
      if (value === null || value === undefined) {
        return;
      }
      const stringValue = String(value).trim();
      if (!stringValue) {
        return;
      }
      if (unique.length === 0 || unique[unique.length - 1] !== stringValue) {
        unique.push(stringValue);
      }
    };

    const wayNodes = routeData?.way_nodes ?? [];
    if (wayNodes.length > 0) {
      wayNodes.forEach((nodeId) => appendUnique(nodeId));
    } else if (Array.isArray(routeData?.segments)) {
      for (const segment of routeData.segments) {
        if (Array.isArray(segment.path)) {
          segment.path.forEach((nodeId) => appendUnique(nodeId));
        }
      }
    }

    if (unique.length === 0 && Array.isArray(routeData?.order)) {
      routeData.order.forEach((nodeId) => appendUnique(nodeId));
    }

    return unique;
  }, [routeData]);

  const pathNodes = useMemo<RouteNode[]>(() => {
    // Resolve node ids to coordinates for drawing the overview path.
    if (pathNodeIds.length === 0) {
      return [];
    }
    return pathNodeIds.map((nodeId) => {
      const coords = coordinateLookup.get(nodeId) ?? NODE_COORDINATES[nodeId];
      if (!coords) {
        console.warn(`Missing coordinates for node ${nodeId}. Falling back to origin.`);
        return { nodeId, x: 0, y: 0 };
      }
      return { nodeId, x: coords.x, y: coords.y };
    });
  }, [coordinateLookup, pathNodeIds]);

  const edgeAnnotations = useMemo<EdgeAnnotationLookup>(() => {
    const map: EdgeAnnotationLookup = new Map();
    const segments = Array.isArray(routeData?.segments) ? routeData.segments : [];

    const normalizeNodeId = (value: unknown): string => {
      if (value === null || value === undefined) {
        return "";
      }
      return String(value).trim();
    };

    const normalizeShelfId = (value: unknown): string | null => {
      if (value === null || value === undefined) {
        return null;
      }
      const text = String(value).trim();
      return text ? text : null;
    };

    for (const segment of segments) {
      if (!segment || !Array.isArray(segment.path_edges)) {
        continue;
      }
      for (const edge of segment.path_edges) {
        if (!edge) {
          continue;
        }
        const from = normalizeNodeId(edge.from);
        const to = normalizeNodeId(edge.to);
        if (!from || !to) {
          continue;
        }

        const lengthRaw = edge.length;
        const numericCandidate =
          typeof lengthRaw === "number" && Number.isFinite(lengthRaw) ? lengthRaw : Number(lengthRaw);
        const length = Number.isFinite(numericCandidate) && numericCandidate > 0 ? numericCandidate : 0;

        const leftShelf = normalizeShelfId(edge.left_shelf);
        const rightShelf = normalizeShelfId(edge.right_shelf);
        const key = makeEdgeKey(from, to);
        map.set(key, { from, to, length, leftShelf, rightShelf });
      }
    }

    return map;
  }, [routeData]);

  const nodeProductMap = useMemo(() => {
    // Group products by node so we can label map markers and list entries.
    const map = new Map<
      string,
      { productId: number | null; productName: string; position?: { x: number; y: number } }[]
    >();
    if (Array.isArray(routeData?.products)) {
      for (const product of routeData.products) {
        const nodeId = String(product.node_id ?? "").trim();
        if (!nodeId) {
          continue;
        }
        const list = map.get(nodeId) ?? [];
        const numericId = Number(product.product_id);
        const productCoords =
          (typeof product.node_x === "number" && typeof product.node_y === "number"
            ? { x: product.node_x, y: product.node_y }
            : undefined) ??
          coordinateLookup.get(nodeId);
        const overrideLabel = getNodeLabelOverride(nodeId);
        list.push({
          productId: Number.isFinite(numericId) ? numericId : null,
          productName: overrideLabel ?? product.name ?? `Product ${nodeId}`,
          position: productCoords,
        });
        map.set(nodeId, list);
      }
    }
    return map;
  }, [routeData, coordinateLookup]);

  const productLevelMap = useMemo(() => {
    // Cache product shelf levels for quick lookup when rendering the checklist.
    const map = new Map<number, number | null>();
    for (const product of products) {
      if (typeof product.id === "number") {
        map.set(product.id, product.level ?? null);
      }
    }
    return map;
  }, [products]);

  const routeItems = useMemo(() => {
    // Flatten the ordered node list into checklist entries with readable labels.
    const items: {
      productId: number;
      productName: string;
      nodeId: string;
      level?: number | null;
      segmentIndex: number;
    }[] = [];

    const orderedNodeIds =
      Array.isArray(routeData?.order) && routeData.order.length > 0
        ? routeData.order.map((nodeId) => String(nodeId).trim())
        : Array.from(nodeProductMap.keys());

    const segmentCount = Array.isArray(routeData?.segments) ? routeData.segments.length : 0;

    orderedNodeIds.forEach((nodeId, routeIndex) => {
      const productsAtNode = nodeProductMap.get(nodeId);
      if (!productsAtNode || productsAtNode.length === 0) {
        return;
      }

      const previousSegment = segmentCount > 0 ? Math.max(0, Math.min(routeIndex - 1, segmentCount - 1)) : 0;
      const nextSegment = segmentCount > 0 ? Math.max(0, Math.min(routeIndex, segmentCount - 1)) : previousSegment;

      productsAtNode.forEach((product, productIndex) => {
        const fallbackId = Number(nodeId);
        const numericId = product.productId ?? (Number.isFinite(fallbackId) ? fallbackId : items.length);
        const resolvedId = Number.isFinite(numericId) ? Number(numericId) : items.length;
        const overrideLabel = getNodeLabelOverride(nodeId);
        const isLastAtNode = productIndex === productsAtNode.length - 1;
        const segmentIndex = productsAtNode.length > 1 && isLastAtNode ? nextSegment : previousSegment;

        items.push({
          productId: resolvedId,
          productName: overrideLabel ?? product.productName,
          nodeId,
          level: productLevelMap.get(resolvedId) ?? null,
          segmentIndex,
        });
      });
    });

    if (items.length > 0) {
      return items;
    }

    return selectedProducts.map((id) => {
      const product = products.find((entry) => entry.id === id);
      const nodeId = pathNodeIds[0] ?? "";
      const overrideLabel = getNodeLabelOverride(nodeId);
      return {
        productId: id,
        productName: overrideLabel ?? product?.name ?? "Unknown item",
        nodeId,
        level: product?.level ?? null,
        segmentIndex: 0,
      };
    });
  }, [routeData, nodeProductMap, pathNodeIds, productLevelMap, products, selectedProducts]);

  const routeSignature = useMemo(
    // Signature is used to reset local state when the route changes.
    () => routeItems.map((item) => `${item.productId}-${item.nodeId}`).join("|"),
    [routeItems]
  );

  useEffect(() => {
    // Reset focus to the first item when the user opens the route view.
    if (view === "route") {
      setActiveIndex(0);
    }
  }, [view, routeSignature]);

  useEffect(() => {
    // Clear completion state whenever a new route arrives.
    setCompleted(new Array(routeItems.length).fill(false));
    setActiveIndex(0);
  }, [routeItems.length, routeSignature, view]);

  useEffect(() => {
    // Reset map panel size when leaving the route view.
    if (view !== "route") {
      setMapPanelSize(null);
    }
  }, [view]);

  const directions = useMemo(() => {
    if (pathNodes.length === 0) {
      return [];
    }
    return buildNavigationInstructions({
      path: pathNodes,
      routeItems,
      nodeProductMap,
      resolveNodeName: (nodeId) => getNodeLabelOverride(nodeId) ?? nodeId,
      edgeAnnotations,
    });
  }, [pathNodes, routeItems, nodeProductMap, edgeAnnotations]);

  const contentGridStyle = useMemo<CSSProperties | undefined>(() => {
    // Tie the map height to the measured canvas size for consistent layout.
    if (!mapPanelSize) {
      return undefined;
    }
    return { "--map-panel-height": `${mapPanelSize.height}px` } as CSSProperties;
  }, [mapPanelSize]);

  const toggleProduct = (id: number) => {
    // Allow users to add or remove products from their shopping list.
    setSelectedProducts((previous) => {
      if (previous.includes(id)) {
        return previous.filter((entry) => entry !== id);
      }
      return [...previous, id];
    });
  };

  const handleToggleComplete = useCallback((index: number) => {
    // Guard completion so only the first incomplete item can be checked.
    setCompleted((prev) => {
      const next = [...prev];
      const firstIncomplete = next.findIndex((value) => !value);
      if (firstIncomplete === -1) {
        return prev;
      }
      if (index !== firstIncomplete) {
        return prev;
      }
      next[index] = true;
      return next;
    });
  }, []);

  useEffect(() => {
    // Advance the active index to the next incomplete item.
    const firstIncomplete = completed.findIndex((value) => !value);
    if (firstIncomplete === -1) {
      setActiveIndex(routeItems.length);
    } else {
      setActiveIndex(firstIncomplete);
    }
  }, [completed, routeItems.length]);

  const handleSetActive = (index: number) => {
    // Allow keyboard focus to follow programmatic scroll in the checklist.
    setActiveIndex(index);
  };

  const handleMapDimensionsChange = useCallback((size: { width: number; height: number }) => {
    // Cache canvas dimensions so the layout grid can adjust once rendering finishes.
    setMapPanelSize((previous) => {
      if (previous && previous.width === size.width && previous.height === size.height) {
        return previous;
      }
      return size;
    });
  }, []);

  const handleShowRoute = async () => {
    // Request a new route from the backend for the selected products.
    if (selectedProducts.length === 0 || isLoadingRoute) {
      return;
    }
    setRouteError(null);
    setIsLoadingRoute(true);
    try {
      const requestPayload: Record<string, unknown> = {
        productCodes: selectedProducts,
      };
      if (startNodeId) {
        requestPayload.startNodeId = startNodeId;
      }
      const response = await fetch(`${API_BASE_URL}/route`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(requestPayload),
      });
      const payload = await response.json().catch(() => ({}));
      if (!response.ok) {
        const detail = typeof payload.detail === "string" ? payload.detail : "Route calculation failed.";
        throw new Error(detail);
      }
      setRouteData(payload as RouteData);
      if (Array.isArray(payload?.products)) {
        const nextSelected = payload.products
          .map((item: any) => Number(item.product_id ?? item.id ?? item.code))
          .filter((value: number) => Number.isFinite(value));
        if (nextSelected.length > 0) {
          setSelectedProducts(nextSelected);
        }
      }
      setView("route");
      setActiveIndex(0);
    } catch (error) {
      console.error("Route request failed", error);
      setRouteError(error instanceof Error ? error.message : "Route calculation failed.");
    } finally {
      setIsLoadingRoute(false);
    }
  };

  const handleEditSelection = () => {
    // Return to the selection view so the user can adjust the basket.
    setView("select");
  };

  const activeSegments = Array.isArray(routeData?.segments) ? routeData.segments : [];
  const productSegmentIndices = useMemo(() => {
    if (routeItems.length === 0) {
      return [];
    }
    const maxSegmentIndex = Math.max(0, activeSegments.length - 1);
    return routeItems.map((item, idx) => {
      if (activeSegments.length === 0) {
        return -1;
      }
      const candidate = typeof item.segmentIndex === "number" ? item.segmentIndex : idx;
      return Math.max(0, Math.min(candidate, maxSegmentIndex));
    });
  }, [routeItems, activeSegments.length]);
  const productSegmentIndex =
    routeItems.length === 0
      ? activeSegments.length - 1
      : activeIndex >= routeItems.length
      ? activeSegments.length - 1
      : productSegmentIndices[activeIndex] ?? 0;

  const activeSegmentIndex =
    activeSegments.length === 0 || productSegmentIndex < 0
      ? -1
      : Math.max(0, Math.min(productSegmentIndex, activeSegments.length - 1));

  const entryNodeId = pathNodeIds[0] ?? routeItems[0]?.nodeId ?? null;
  const checkoutNodeId = pathNodeIds[pathNodeIds.length - 1] ?? routeItems[routeItems.length - 1]?.nodeId ?? entryNodeId;

  const currentNodeId = (() => {
    if (!entryNodeId) {
      return undefined;
    }
    if (routeItems.length === 0) {
      return entryNodeId;
    }
    if (activeIndex <= 0) {
      return entryNodeId;
    }
    if (activeIndex > routeItems.length) {
      return checkoutNodeId ?? entryNodeId;
    }
    return routeItems[activeIndex - 1]?.nodeId ?? entryNodeId;
  })();

  const targetNodeId = (() => {
    if (routeItems.length === 0) {
      return checkoutNodeId ?? entryNodeId ?? undefined;
    }
    if (activeIndex < routeItems.length) {
      return routeItems[activeIndex]?.nodeId ?? checkoutNodeId ?? entryNodeId ?? undefined;
    }
    return checkoutNodeId ?? entryNodeId ?? undefined;
  })();

  const targetLabel = (() => {
    if (routeItems.length === 0) {
      return "Checkout";
    }
    if (activeIndex < routeItems.length) {
      return routeItems[activeIndex]?.productName ?? "Produkt";
    }
    return "Checkout";
  })();

  const previewPath: RouteNode[] = pathNodes.length > 0 ? pathNodes : [{ nodeId: "origin", x: 0, y: 0 }];

  // Build an ordered, edge-following path from the route's segments. Each segment may contain
  // `path_coordinates` (preferred) or a `path` (node ids) which we resolve via coordinateLookup.
  const enrichedPath = useMemo<RouteNode[]>(() => {
    const out: RouteNode[] = [];
    const segments = Array.isArray(routeData?.segments) ? routeData.segments : [];
    if (segments.length === 0) {
      return pathNodes.length > 0 ? pathNodes : out;
    }

    const pushIfNotDuplicate = (node: RouteNode) => {
      const last = out[out.length - 1];
      if (!last || last.nodeId !== node.nodeId) {
        out.push(node);
      }
    };

    for (const seg of segments) {
      // prefer coordinates directly provided on the segment
      if (Array.isArray((seg as any).path_coordinates) && (seg as any).path_coordinates.length > 0) {
        for (const coord of (seg as any).path_coordinates) {
          const nodeId = String(coord.node_id ?? coord.nodeId ?? coord.nodeId ?? "");
          if (!nodeId) continue;
          pushIfNotDuplicate({ nodeId, x: Number(coord.x), y: Number(coord.y) });
        }
        continue;
      }

      // fallback: resolve `seg.path` node ids via coordinateLookup or static table
      if (Array.isArray((seg as any).path) && (seg as any).path.length > 0) {
        for (const nodeIdRaw of (seg as any).path) {
          const nodeId = String(nodeIdRaw);
          const coords = coordinateLookup.get(nodeId) ?? NODE_COORDINATES[nodeId];
          if (coords) {
            pushIfNotDuplicate({ nodeId, x: coords.x, y: coords.y });
          } else {
            // no coords: still include placeholder to preserve node order
            pushIfNotDuplicate({ nodeId, x: 0, y: 0 });
          }
        }
      }
    }

    // If we ended up empty (no segments with coords), fallback to pathNodes
    if (out.length === 0 && pathNodes.length > 0) return pathNodes;
    return out;
  }, [routeData, coordinateLookup, pathNodes]);

  const effectiveActiveIndex = routeItems.length > 0 ? Math.min(activeIndex, routeItems.length - 1) : -1;
  const completedStepsCount = useMemo(() => completed.filter(Boolean).length, [completed]);

  return (
    <div className="app-shell">
      <header className="app-page-header">
        <h1>Grocery Store Navigation</h1>
        {view === "select" && (
          <button
            type="button"
            className="secondary-button"
            onClick={() => setView("start")}
            disabled={isLoadingRoute || productsLoading}
          >
            Change start
          </button>
        )}
        {view === "route" && (
          <button type="button" className="secondary-button" onClick={handleEditSelection}>
            Edit selection
          </button>
        )}
      </header>
      <main className="app-main">
        {view === "start" && (
          <StartLocationSelector
            options={startOptions}
            selectedValue={startNodeId}
            onSelect={setStartNodeId}
            onConfirm={() => setView("select")}
            confirmLabel="Select products"
            isConfirmDisabled={productsLoading}
            errorMessage={productsError}
          />
        )}

        {view === "select" && (
          <ProductList
            products={products}
            selectedIds={selectedProducts}
            searchTerm={searchTerm}
            onToggle={toggleProduct}
            onSearchChange={setSearchTerm}
            onConfirm={handleShowRoute}
            canConfirm={selectedProducts.length > 0}
            confirmLabel="Show route"
            isLoading={isLoadingRoute || productsLoading}
            errorMessage={combinedErrorMessage}
          />
        )}

        {view === "route" && routeData && (
          <div className="content-grid" style={contentGridStyle}>
            <MapPreview
              path={enrichedPath}
              segments={activeSegments}
              activeSegmentIndex={activeSegmentIndex}
              currentNodeId={currentNodeId}
              targetNodeId={targetNodeId}
              targetLabel={targetLabel}
              polygons={layoutPolygons ?? undefined}
              onDimensionsChange={handleMapDimensionsChange}
            />
            <RouteSummary
              totalDistance={routeData?.total_cost ?? 0}
              directions={directions}
              activeIndex={activeSegmentIndex}
              completedCount={completedStepsCount}
            />
            <SelectedChecklist
              items={routeItems}
              activeIndex={effectiveActiveIndex}
              completed={completed}
              onToggleComplete={handleToggleComplete}
              onSetActive={handleSetActive}
            />
          </div>
        )}

        {view === "route" && !routeData && (
          <p style={{ color: "#dc2626" }}>No route data available. Please return to the selection and try again.</p>
        )}
      </main>

      <footer className="app-footer">
        <span className="footer-context">Location Based Services WiSe 25/26</span>
        <span className="footer-authors">Nicolas Diaczyszyn | David Engler | Kes Lo | Niklas Menz</span>
      </footer>
    </div>
  );
}

export default App;
