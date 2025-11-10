type ItemEntry = {
  productId: number;
  productName: string;
  nodeId: string;
};

type ChecklistProps = {
  items: ItemEntry[];
  activeIndex: number;
  completed: boolean[];
  onToggleComplete: (index: number) => void;
  onSetActive?: (index: number) => void;
};

export function SelectedChecklist({ items, activeIndex, completed, onToggleComplete, onSetActive }: ChecklistProps) {
  return (
    <section className="checklist">
      <header className="section-header">
        <div>
          <h2>Optimized Route</h2>
          <p>Follow the ordered list to walk the shortest path.</p>
        </div>
      </header>
      <ol>
        {items.map((item, index) => {
          const active = index === activeIndex;
          const done = completed[index];
          return (
            <li
              key={item.productId}
              className={`checklist-item${active ? " active" : ""}${done ? " done" : ""}`}
            >
              <label
                onClick={() => {
                  if (onSetActive) {
                    onSetActive(index);
                  }
                }}
              >
                <input
                  type="checkbox"
                  checked={done}
                  onChange={() => onToggleComplete(index)}
                />
                <div>
                  <span className="item-name">{item.productName}</span>
                  <span className="item-meta">Node {item.nodeId}</span>
                </div>
              </label>
            </li>
          );
        })}
      </ol>
    </section>
  );
}
