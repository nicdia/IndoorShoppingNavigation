PRAGMA foreign_keys=OFF;

-- 1️⃣ Alte Tabelle umbenennen (Backup)
ALTER TABLE nodes RENAME TO nodes_old;

-- 2️⃣ Neue Tabelle mit gewünschter Struktur erstellen
CREATE TABLE nodes (
  node_id INTEGER PRIMARY KEY,
  x REAL,
  y REAL
);

-- 3️⃣ Daten übernehmen (nur die relevanten Spalten)
INSERT INTO nodes (node_id, x, y)
SELECT id, x, y FROM nodes_old;

-- 4️⃣ Alte Tabelle löschen
DROP TABLE nodes_old;

PRAGMA foreign_keys=ON;