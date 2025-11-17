type ItemEntry = {
  productId: number;
  productName: string;
  nodeId: string;
  level?: number | null;
};

type ChecklistProps = {
  items: ItemEntry[];
  activeIndex: number;
  completed: boolean[];
  onToggleComplete: (index: number) => void;
  onSetActive?: (index: number) => void;
};

const levelLabel = (level?: number | null) => {
  if (level === 1) return "Top shelf";
  if (level === 2) return "Middle shelf";
  if (level === 3) return "Bottom shelf";
  if (level === 99) return " ";
  return "";
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
                  <span className="item-meta">{levelLabel(item.level)}</span>
                </div>
              </label>
            </li>
          );
        })}
      </ol>
    </section>
  );
}
