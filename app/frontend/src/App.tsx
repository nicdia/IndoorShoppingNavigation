import { useCallback, useEffect, useMemo, useState, type CSSProperties } from "react";
import { ProductList } from "./components/ProductList";
import { MapPreview } from "./components/MapPreview";
import { SelectedChecklist } from "./components/SelectedChecklist";
import { RouteSummary } from "./components/RouteSummary";
import {
  Product,
  RouteData,
  RouteNode,
  StorePolygon,
  mockProducts,
  mockRoute,
} from "./mockData";
import { NODE_COORDINATES } from "./data/nodeCoordinates";

const DEFAULT_API_BASE = "http://127.0.0.1:8000";
const API_BASE_URL = (import.meta.env.VITE_API_BASE_URL as string | undefined)?.replace(/\/$/, "") ?? DEFAULT_API_BASE;

function App() {
  const [searchTerm, setSearchTerm] = useState("");
  const [products, setProducts] = useState<Product[]>(mockProducts);
  const [productsLoading, setProductsLoading] = useState(false);
  const [productsError, setProductsError] = useState<string | null>(null);

  const [selectedProducts, setSelectedProducts] = useState<number[]>([]);
  const [routeData, setRouteData] = useState<RouteData | null>(null);
  const [isLoadingRoute, setIsLoadingRoute] = useState(false);
  const [routeError, setRouteError] = useState<string | null>(null);

  const [activeIndex, setActiveIndex] = useState(0);
  const [completed, setCompleted] = useState<boolean[]>([]);
  const [view, setView] = useState<"select" | "route">("select");
  const [layoutPolygons, setLayoutPolygons] = useState<StorePolygon[] | null>(null);
  const [mapPanelSize, setMapPanelSize] = useState<{ width: number; height: number } | null>(null);

  useEffect(() => {
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
            setProductsError("Product list from API was empty. Showing fallback data.");
            setProducts(mockProducts);
          }
        }
      })
      .catch((error) => {
        console.warn("Falling back to mock products", error);
        setProductsError(error instanceof Error ? error.message : "Could not load products from API.");
        setProducts(mockProducts);
      })
      .finally(() => setProductsLoading(false));
  }, []);

  useEffect(() => {
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

  const activeRoute: RouteData = routeData ?? mockRoute;
  const combinedErrorMessage = useMemo(() => {
    const messages = [productsError, routeError].filter((value): value is string => Boolean(value));
    return messages.length > 0 ? messages.join(". ") : null;
  }, [productsError, routeError]);

  const coordinateLookup = useMemo(() => {
    const map = new Map<string, { x: number; y: number }>();

    if (activeRoute?.node_coordinates) {
      Object.entries(activeRoute.node_coordinates).forEach(([nodeId, coords]) => {
        if (coords && typeof coords.x === "number" && typeof coords.y === "number") {
          map.set(String(nodeId), { x: coords.x, y: coords.y });
        }
      });
    }

    if (Array.isArray(activeRoute?.waypoint_coordinates)) {
      activeRoute.waypoint_coordinates.forEach((waypoint) => {
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
  }, [activeRoute]);

  const pathNodeIds = useMemo(() => {
    const unique: string[] = [];
    const appendUnique = (value: string | number | null | undefined) => {
      if (value === null || value === undefined) {
        return;
      }
      const stringValue = String(value);
      if (!stringValue) {
        return;
      }
      if (unique.length === 0 || unique[unique.length - 1] !== stringValue) {
        unique.push(stringValue);
      }
    };

    if (Array.isArray(activeRoute.way_nodes) && activeRoute.way_nodes.length > 0) {
      activeRoute.way_nodes.forEach((nodeId) => appendUnique(nodeId));
    } else if (Array.isArray(activeRoute.segments)) {
      for (const segment of activeRoute.segments) {
        segment.path.forEach((nodeId) => appendUnique(nodeId));
      }
    }

    if (unique.length === 0 && Array.isArray(activeRoute.order)) {
      activeRoute.order.forEach((nodeId) => appendUnique(nodeId));
    }

    return unique;
  }, [activeRoute]);

  const pathNodes = useMemo<RouteNode[]>(() => {
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

  const nodeProductMap = useMemo(() => {
    const map = new Map<
      string,
      { productId: number | null; productName: string; position?: { x: number; y: number } }[]
    >();
    if (Array.isArray(activeRoute.products)) {
      for (const product of activeRoute.products) {
        const nodeId = String(product.node_id ?? "");
        if (!nodeId) {
          continue;
        }
        const list = map.get(nodeId) ?? [];
        const numericId = Number(product.product_id);
        const productCoords =
          coordinateLookup.get(nodeId) ??
          (typeof product.node_x === "number" && typeof product.node_y === "number"
            ? { x: product.node_x, y: product.node_y }
            : undefined);
        list.push({
          productId: Number.isFinite(numericId) ? numericId : null,
          productName: product.name ?? `Product ${nodeId}`,
          position: productCoords,
        });
        map.set(nodeId, list);
      }
    }
    return map;
  }, [activeRoute, coordinateLookup]);

  const productLevelMap = useMemo(() => {
    const map = new Map<number, number | null>();
    for (const product of products) {
      if (typeof product.id === "number") {
        map.set(product.id, product.level ?? null);
      }
    }
    return map;
  }, [products]);

  const routeItems = useMemo(() => {
    const items: { productId: number; productName: string; nodeId: string; level?: number | null }[] = [];
    const orderedNodeIds =
      Array.isArray(activeRoute.order) && activeRoute.order.length > 0
        ? activeRoute.order.map((nodeId) => String(nodeId))
        : Array.from(nodeProductMap.keys());

    for (const nodeId of orderedNodeIds) {
      const productsAtNode = nodeProductMap.get(nodeId);
      if (!productsAtNode) {
        continue;
      }
      for (const product of productsAtNode) {
        const fallbackId = Number(nodeId);
        const numericId = product.productId ?? (Number.isFinite(fallbackId) ? fallbackId : items.length);
        const resolvedId = Number.isFinite(numericId) ? Number(numericId) : items.length;
        items.push({
          productId: resolvedId,
          productName: product.productName,
          nodeId,
          level: productLevelMap.get(resolvedId) ?? null,
        });
      }
    }

    if (items.length > 0) {
      return items;
    }

    return selectedProducts.map((id) => {
      const product = products.find((entry) => entry.id === id);
      return {
        productId: id,
        productName: product?.name ?? "Unknown item",
        nodeId: pathNodeIds[0] ?? "",
        level: product?.level ?? null,
      };
    });
  }, [activeRoute, nodeProductMap, pathNodeIds, productLevelMap, products, selectedProducts]);

  const routeSignature = useMemo(
    () => routeItems.map((item) => `${item.productId}-${item.nodeId}`).join("|"),
    [routeItems]
  );

  useEffect(() => {
    if (view === "route") {
      setActiveIndex(0);
    }
  }, [view, routeSignature]);

  useEffect(() => {
    setCompleted(new Array(routeItems.length).fill(false));
    setActiveIndex(0);
  }, [routeItems.length, routeSignature, view]);

  useEffect(() => {
    if (view !== "route") {
      setMapPanelSize(null);
    }
  }, [view]);

  const directions = useMemo(() => {
    if (!Array.isArray(activeRoute.segments)) {
      return [];
    }
    const labelFor = (nodeId: string) => {
      const productsAtNode = nodeProductMap.get(nodeId);
      if (productsAtNode && productsAtNode.length > 0) {
        return productsAtNode[0].productName;
      }
      return nodeId;
    };
    return activeRoute.segments.map((segment) => {
      const distance = typeof segment.cost === "number" ? segment.cost : 0;
      const originLabel = labelFor(segment.from);
      const destinationLabel = labelFor(segment.to);
      return `Walk ${distance.toFixed(1)} meters from ${originLabel} to ${destinationLabel}.`;
    });
  }, [activeRoute, nodeProductMap]);

  const contentGridStyle = useMemo<CSSProperties | undefined>(() => {
    if (!mapPanelSize) {
      return undefined;
    }
    return { "--map-panel-height": `${mapPanelSize.height}px` } as CSSProperties;
  }, [mapPanelSize]);

  const toggleProduct = (id: number) => {
    setSelectedProducts((previous) => {
      if (previous.includes(id)) {
        return previous.filter((entry) => entry !== id);
      }
      return [...previous, id];
    });
  };

  const handleToggleComplete = useCallback((index: number) => {
    setCompleted((prev) => {
      const next = [...prev];
      next[index] = !next[index];
      return next;
    });
  }, []);

  useEffect(() => {
    const firstIncomplete = completed.findIndex((value) => !value);
    if (firstIncomplete === -1) {
      setActiveIndex(routeItems.length);
    } else {
      setActiveIndex(firstIncomplete);
    }
  }, [completed, routeItems.length]);

  const handleSetActive = (index: number) => {
    setActiveIndex(index);
  };

  const handleMapDimensionsChange = useCallback((size: { width: number; height: number }) => {
    setMapPanelSize((previous) => {
      if (previous && previous.width === size.width && previous.height === size.height) {
        return previous;
      }
      return size;
    });
  }, []);

  const handleShowRoute = async () => {
    if (selectedProducts.length === 0 || isLoadingRoute) {
      return;
    }
    setRouteError(null);
    setIsLoadingRoute(true);
    try {
      const response = await fetch(`${API_BASE_URL}/route`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ productCodes: selectedProducts }),
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
    setView("select");
  };

  const activeSegments = Array.isArray(activeRoute.segments) ? activeRoute.segments : [];
  const unclampedSegmentIndex =
    routeItems.length === 0
      ? activeSegments.length - 1
      : activeIndex >= routeItems.length
      ? activeSegments.length - 1
      : activeIndex;
  const activeSegmentIndex =
    activeSegments.length === 0 ? -1 : Math.max(0, Math.min(unclampedSegmentIndex, activeSegments.length - 1));

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
    if (!Array.isArray(activeRoute.segments) || activeRoute.segments.length === 0) {
      return pathNodes.length > 0 ? pathNodes : out;
    }

    const pushIfNotDuplicate = (node: RouteNode) => {
      const last = out[out.length - 1];
      if (!last || last.nodeId !== node.nodeId) {
        out.push(node);
      }
    };

    for (const seg of activeRoute.segments) {
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
  }, [activeRoute.segments, coordinateLookup, pathNodes]);

  const effectiveActiveIndex = routeItems.length > 0 ? Math.min(activeIndex, routeItems.length - 1) : -1;
  const completedStepsCount = useMemo(() => completed.filter(Boolean).length, [completed]);

  return (
    <div className="app-shell">
      <header className="app-page-header">
        <h1>Grocery Store Navigation</h1>
        {view === "route" && (
          <button type="button" className="secondary-button" onClick={handleEditSelection}>
            Edit selection
          </button>
        )}
      </header>
      <main className="app-main">
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
              totalDistance={activeRoute.total_cost ?? 0}
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
