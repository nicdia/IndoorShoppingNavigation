import { useCallback, useEffect, useMemo, useState, type CSSProperties } from "react";
import { ProductList } from "./components/ProductList";
import { MapPreview } from "./components/MapPreview";
import { SelectedChecklist } from "./components/SelectedChecklist";
import { RouteSummary } from "./components/RouteSummary";
import { Product, RouteData, StorePolygon, mockProducts, mockRoute } from "./mockData";

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

  const enrichedPath = useMemo(() => {
    return activeRoute.path.map((node) => {
      const matching = activeRoute.order.find((step) => step.nodeId === node.nodeId);
      return {
        ...node,
        type: matching?.type,
        productId: matching?.productId,
      };
    });
  }, [activeRoute]);

  const routeItems = useMemo(() => {
    const itemsFromRoute = activeRoute.order
      .filter((step) => step.type === "item")
      .map((step, index) => {
        let productId = step.productId;
        if (productId === undefined || Number.isNaN(productId)) {
          const numericNode = Number(step.nodeId);
          productId = Number.isFinite(numericNode) ? numericNode : selectedProducts[index] ?? index;
        }
        const matchingProduct = products.find((item) => item.id === productId);
        const productName = step.productName ?? matchingProduct?.name ?? "Unknown item";
        return {
          productId,
          productName,
          nodeId: step.nodeId,
        };
      });

    if (itemsFromRoute.length > 0) {
      return itemsFromRoute;
    }

    return selectedProducts.map((id) => {
      const product = products.find((item) => item.id === id);
      return {
        productId: id,
        productName: product?.name ?? "Unknown item",
        nodeId: "?",
      };
    });
  }, [activeRoute, products, selectedProducts]);

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
    return activeRoute.segments.map((segment) => {
      const origin = activeRoute.order.find((step) => step.nodeId === segment.from);
      const destination = activeRoute.order.find((step) => step.nodeId === segment.to);
      const originLabel = origin?.type === "entry" ? "Entry" : origin?.productName ?? origin?.nodeId;
      const destinationLabel =
        destination?.type === "checkout"
          ? "Checkout"
          : destination?.productName ?? destination?.nodeId;
      return `Walk ${segment.distance.toFixed(1)} meters from ${originLabel} to ${destinationLabel}.`;
    });
  }, [activeRoute]);

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
      if (Array.isArray(payload?.metadata?.selectedProducts)) {
        setSelectedProducts(payload.metadata.selectedProducts.map((value: any) => Number(value)));
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

  const activeSegments = activeRoute.segments;
  const unclampedSegmentIndex = activeIndex >= routeItems.length ? activeSegments.length - 1 : activeIndex;
  const activeSegmentIndex =
    activeSegments.length === 0 ? -1 : Math.max(0, Math.min(unclampedSegmentIndex, activeSegments.length - 1));

  const currentNodeId = (() => {
    if (activeIndex <= 0) {
      return activeRoute.metadata.entry;
    }
    if (activeIndex > routeItems.length) {
      return activeRoute.metadata.checkout;
    }
    const previous = routeItems[activeIndex - 1];
    return typeof previous?.nodeId === "string" ? previous.nodeId : activeRoute.metadata.entry;
  })();

  const targetNodeId = activeIndex < routeItems.length ? routeItems[activeIndex]?.nodeId : activeRoute.metadata.checkout;

  const effectiveActiveIndex = routeItems.length > 0 ? Math.min(activeIndex, routeItems.length - 1) : -1;

  return (
    <div className="app-shell">
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
        <>
          <div className="route-header">
            <button type="button" className="secondary-button" onClick={handleEditSelection}>
              Edit selection
            </button>
          </div>
          <div className="content-grid" style={contentGridStyle}>
            <MapPreview
              path={enrichedPath}
              segments={activeSegments}
              activeSegmentIndex={activeSegmentIndex}
              currentNodeId={currentNodeId}
              targetNodeId={targetNodeId}
              polygons={layoutPolygons ?? undefined}
              onDimensionsChange={handleMapDimensionsChange}
            />
            <RouteSummary totalDistance={activeRoute.totalDistance} directions={directions} />
            <SelectedChecklist
              items={routeItems}
              activeIndex={effectiveActiveIndex}
              completed={completed}
              onToggleComplete={handleToggleComplete}
              onSetActive={handleSetActive}
            />
          </div>
        </>
      )}

      {view === "route" && !routeData && (
        <p style={{ color: "#dc2626" }}>No route data available. Please return to the selection and try again.</p>
      )}
    </div>
  );
}

export default App;
