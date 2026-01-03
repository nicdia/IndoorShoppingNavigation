import { useMemo, useState, ChangeEvent } from "react";

// Single-selection list for choosing the starting aisle/node.

type StartOption = {
  value: string;
  label: string;
};

type StartLocationSelectorProps = {
  options: StartOption[];
  selectedValue: string | null;
  onSelect: (value: string) => void;
  onConfirm?: () => void;
  confirmLabel?: string;
  isConfirmDisabled?: boolean;
  errorMessage?: string | null;
};

export function StartLocationSelector({
  options,
  selectedValue,
  onSelect,
  onConfirm,
  confirmLabel = "Continue",
  isConfirmDisabled = false,
  errorMessage = null,
}: StartLocationSelectorProps) {
  const [searchTerm, setSearchTerm] = useState("");

  const filtered = useMemo(() => {
    const normalized = searchTerm.trim().toLowerCase();
    if (!normalized) {
      return options;
    }
    return options.filter((option) => option.label.toLowerCase().includes(normalized));
  }, [options, searchTerm]);

  const handleChange = (event: ChangeEvent<HTMLInputElement>) => {
    setSearchTerm(event.target.value);
  };

  return (
    <section className="product-list">
      <header className="section-header">
        <div>
          <h1>Where are you?</h1>
          <p>Select your current position inside the store.</p>
        </div>
      </header>
      <div className="product-search">
        <input
          type="search"
          placeholder="Search locations"
          value={searchTerm}
          onChange={handleChange}
        />
      </div>
      <ul className="product-list-items">
        {filtered.map((option) => (
          <li key={option.value}>
            <label className={selectedValue === option.value ? "product-row selected" : "product-row"}>
              <input
                type="radio"
                name="start-location"
                checked={selectedValue === option.value}
                onChange={() => onSelect(option.value)}
              />
              <span>{option.label}</span>
            </label>
          </li>
        ))}
        {filtered.length === 0 && <li className="empty-state">No matching locations found.</li>}
      </ul>
      {onConfirm && (
        <footer className="section-footer">
          {errorMessage && <span className="form-error">{errorMessage}</span>}
          <button
            type="button"
            className="primary-button"
            onClick={onConfirm}
            disabled={isConfirmDisabled}
          >
            {confirmLabel}
          </button>
        </footer>
      )}
    </section>
  );
}
