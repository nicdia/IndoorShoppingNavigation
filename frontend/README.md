# Frontend Vision

The frontend will provide an interactive shopping assistant for the indoor navigation route.

## Core Screens

- **Product selection**: searchable list of all products with checkboxes, allowing shoppers to mark the items they plan to buy before generating a route.
- **Store map**: renders the supermarket layout (graph nodes, shelves, and entry/checkout points) as a 2D SVG/Canvas map. The calculated path is highlighted with distinct colors for current vs. upcoming segments.
- **Checklist view**: shows the selected products in optimal order. Each item has a checkbox; checking an item fades its segment and highlights the next destination.

## Additional Ideas

- Place the textual turn-by-turn instructions or distance summaries below the map so users can follow the route without relying solely on visuals.
- Make the layout responsive: a single-column flow on mobile, split map and checklist side-by-side on larger screens.
- Consider persisting selections locally so users can recover their list if they reload the page.
