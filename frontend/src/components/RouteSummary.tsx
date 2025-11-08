type RouteSummaryProps = {
  totalDistance: number;
  directions: string[];
};

export function RouteSummary({ totalDistance, directions }: RouteSummaryProps) {
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
        {directions.map((step, index) => (
          <li key={index}>{step}</li>
        ))}
      </ol>
    </section>
  );
}
