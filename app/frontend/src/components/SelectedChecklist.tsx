import { useEffect, useRef } from "react";

// Renders the ordered checklist and keeps the current step in view.

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
  const firstIncomplete = completed.findIndex((value) => !value);
  const itemRefs = useRef<(HTMLLIElement | null)[]>([]);

  useEffect(() => {
    // Trim ref storage when the route length changes.
    itemRefs.current = itemRefs.current.slice(0, items.length);
  }, [items.length]);

  useEffect(() => {
    if (activeIndex < 0) {
      return;
    }
    // Scroll the active entry into view for long shopping lists.
    const target = itemRefs.current[activeIndex];
    if (target) {
      target.scrollIntoView({ block: "nearest", behavior: "smooth" });
    }
  }, [activeIndex]);

  return (
    <section className="checklist">
      <header className="section-header">
        <div>
          <h2>Optimized Route</h2>
        </div>
      </header>
      <ol>
        {items.map((item, index) => {
          const active = index === activeIndex;
          const done = completed[index];
          const isSelectable = !done && firstIncomplete === index;
          return (
            <li
              ref={(node) => {
                itemRefs.current[index] = node;
              }}
              key={item.productId}
              className={`checklist-item${active ? " active" : ""}${done ? " done" : ""}`}
            >
              <label
                onClick={() => {
                  // Only allow focusing the step that is ready to be handled.
                  if (onSetActive && index === firstIncomplete) {
                    onSetActive(index);
                  }
                }}
              >
                <input
                  type="checkbox"
                  checked={done}
                  onChange={() => onToggleComplete(index)}
                  disabled={!isSelectable}
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
