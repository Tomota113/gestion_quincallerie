-- Schéma de la base de données du système de gestion
-- Reconstruit à partir des exports Sage 100 Commercial

CREATE TABLE IF NOT EXISTS articles (
    code TEXT PRIMARY KEY,
    designation TEXT NOT NULL,
    famille TEXT,
    prix_achat REAL DEFAULT 0,
    prix_vente REAL DEFAULT 0,
    tva TEXT,
    complet INTEGER DEFAULT 1  -- 1 = vient du catalogue officiel (article.txt), 0 = reconstruit depuis l'historique
);

CREATE TABLE IF NOT EXISTS depots (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    nom TEXT UNIQUE NOT NULL
);

CREATE TABLE IF NOT EXISTS stock (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    article_code TEXT NOT NULL REFERENCES articles(code),
    depot_id INTEGER NOT NULL REFERENCES depots(id),
    quantite REAL DEFAULT 0,
    UNIQUE(article_code, depot_id)
);

CREATE TABLE IF NOT EXISTS clients (
    code TEXT PRIMARY KEY,
    nom TEXT NOT NULL,
    complet INTEGER DEFAULT 1  -- 1 = vient du fichier officiel (client.txt), 0 = reconstruit depuis l'historique
);

CREATE TABLE IF NOT EXISTS factures (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    numero TEXT NOT NULL,
    date TEXT NOT NULL,  -- format ISO YYYY-MM-DD
    client_code TEXT REFERENCES clients(code),
    depot_id INTEGER REFERENCES depots(id),
    UNIQUE(numero, date)
);

CREATE TABLE IF NOT EXISTS lignes_facture (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    facture_id INTEGER NOT NULL REFERENCES factures(id),
    article_code TEXT REFERENCES articles(code),
    designation TEXT,
    prix_unitaire REAL DEFAULT 0,
    quantite REAL DEFAULT 0
);

CREATE INDEX IF NOT EXISTS idx_stock_article ON stock(article_code);
CREATE INDEX IF NOT EXISTS idx_stock_depot ON stock(depot_id);
CREATE INDEX IF NOT EXISTS idx_lignes_facture_facture ON lignes_facture(facture_id);
CREATE INDEX IF NOT EXISTS idx_lignes_facture_article ON lignes_facture(article_code);
CREATE INDEX IF NOT EXISTS idx_factures_client ON factures(client_code);
CREATE INDEX IF NOT EXISTS idx_factures_date ON factures(date);
CREATE INDEX IF NOT EXISTS idx_articles_designation ON articles(designation);
CREATE INDEX IF NOT EXISTS idx_clients_nom ON clients(nom);
