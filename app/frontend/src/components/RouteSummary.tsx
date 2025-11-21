import { useEffect, useRef } from "react";

type RouteSummaryProps = {
  totalDistance: number;
  directions: string[];
  activeIndex?: number;
  completedCount?: number;
};

export function RouteSummary({ totalDistance, directions, activeIndex, completedCount }: RouteSummaryProps) {
  const itemRefs = useRef<(HTMLLIElement | null)[]>([]);

  useEffect(() => {
    itemRefs.current = itemRefs.current.slice(0, directions.length);
  }, [directions.length]);

  useEffect(() => {
    if (typeof activeIndex !== "number" || activeIndex < 0) {
      return;
    }
    const target = itemRefs.current[activeIndex];
    if (target) {
      target.scrollIntoView({ block: "nearest", behavior: "smooth" });
    }
  }, [activeIndex]);

  return (
    <section className="route-summary">
      <header className="section-header">
        <div>
          <h2>Route Description</h2>
          <p>Plain language instructions to support the visual map.</p>
        </div>
      </header>
      <p className="distance">Total distance: {totalDistance.toFixed(1)} m</p>
      <ol>
        {directions.map((step, index) => {
          const isActive = typeof activeIndex === "number" && activeIndex === index;
          const isCompleted = typeof completedCount === "number" && index < completedCount;
          const classNames = [isCompleted ? "done" : null, isActive ? "active" : null]
            .filter(Boolean)
            .join(" ");
          return (
            <li
              key={`${index}-${step}`}
              className={classNames || undefined}
              ref={(node) => {
                itemRefs.current[index] = node;
              }}
            >
              {step}
            </li>
          );
        })}
      </ol>
    </section>
  );
}
