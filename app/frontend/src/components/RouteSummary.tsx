type RouteSummaryProps = {
  totalDistance: number;
  directions: string[];
  activeIndex?: number;
  completedCount?: number;
};

export function RouteSummary({ totalDistance, directions, activeIndex, completedCount }: RouteSummaryProps) {
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
            <li key={`${index}-${step}`} className={classNames || undefined}>
              {step}
            </li>
          );
        })}
      </ol>
    </section>
  );
}
