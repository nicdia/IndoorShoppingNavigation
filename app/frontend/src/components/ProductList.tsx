import { ChangeEvent } from "react";
import { Product } from "../mockData";

type ProductListProps = {
  products: Product[];
  selectedIds: number[];
  searchTerm: string;
  onToggle: (id: number) => void;
  onSearchChange: (value: string) => void;
  onConfirm?: () => void;
  canConfirm?: boolean;
  confirmLabel?: string;
  isLoading?: boolean;
  errorMessage?: string | null;
};

export function ProductList({
  products,
  selectedIds,
  searchTerm,
  onToggle,
  onSearchChange,
  onConfirm,
  canConfirm = true,
  confirmLabel = "Show route",
  isLoading = false,
  errorMessage = null
}: ProductListProps) {
  const handleSearch = (event: ChangeEvent<HTMLInputElement>) => {
    onSearchChange(event.target.value);
  };

  const normalizedSearch = searchTerm.trim().toLowerCase();

  const filtered = products
    .map((product) => ({
      product,
      normalizedName: product.name.trim(),
    }))
    .filter(({ normalizedName }) => normalizedName.toLowerCase().includes(normalizedSearch))
    .sort((a, b) =>
      a.normalizedName.localeCompare(b.normalizedName, undefined, {
        sensitivity: "base",
      })
    );

  return (
    <section className="product-list">
      <header className="section-header">
        <div>
          <h1>Select Products</h1>
          <p>Pick everything you want to buy, then continue to the route view.</p>
        </div>
      </header>
      <div className="product-search">
        <input
          type="search"
          placeholder="Search products"
          value={searchTerm}
          onChange={handleSearch}
        />
      </div>
      <ul className="product-list-items">
        {filtered.map(({ product, normalizedName }) => {
          const checked = selectedIds.includes(product.id);
          return (
            <li key={product.id}>
              <label className={checked ? "product-row selected" : "product-row"}>
                <input
                  type="checkbox"
                  checked={checked}
                  onChange={() => onToggle(product.id)}
                />
                <span>{normalizedName}</span>
              </label>
            </li>
          );
        })}
        {filtered.length === 0 && <li className="empty-state">No products match your search.</li>}
      </ul>
      {onConfirm && (
        <footer className="section-footer">
          {errorMessage && <span className="form-error">{errorMessage}</span>}
          <button
            type="button"
            className="primary-button"
            onClick={onConfirm}
            disabled={!canConfirm || isLoading}
          >
            {isLoading ? "Calculating…" : confirmLabel}
          </button>
        </footer>
      )}
    </section>
  );
}
