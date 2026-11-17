#!/usr/bin/env python3
"""
Import des exports Sage 100 Commercial vers une vraie base SQLite.

Sources utilisées et pourquoi :
  - article.txt  -> catalogue officiel (code, désignation, famille, prix, TVA)
                    ATTENTION : incomplet, ne couvre que A -> AM environ (62 lignes)
  - client.txt   -> fichier clients officiel
                    ATTENTION : incomplet aussi, ne couvre que 411 + A -> BA (62 lignes)
  - pp.txt       -> stock par dépôt, version complète (stock.txt est une copie tronquée
                    du même fichier, donc on ne s'en sert pas)
  - mp.txt       -> historique des ventes, 30/01/2021 -> 22/07/2022 (le plus complet)
  - p4.txt       -> vérifié : sous-ensemble exact de mp.txt -> pas importé (doublon)
  - p5.txt       -> ventes 02/01/2026 -> 17/08/2026 (données courantes)
  - p10.txt      -> vérifié : mêmes ventes que p5.txt, juste une colonne vide en moins
                    -> pas importé (doublon)
  - p7.txt       -> 222 lignes, toutes datées du 03/01/2026, structure différente
                    (ressemble à un inventaire physique de début d'année)
                    -> pas encore importé, à regarder séparément si besoin

Les articles/clients qui apparaissent dans les ventes ou le stock mais pas dans
article.txt/client.txt sont créés quand même, avec complet=0, pour ne perdre
aucune ligne d'historique. Il manquera juste leur prix / leurs coordonnées
tant qu'un export complet de Sage n'aura pas été fait.
"""
import os
import sqlite3

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data")
DB_PATH = os.path.join(BASE_DIR, "gestion.db")
SCHEMA_PATH = os.path.join(BASE_DIR, "schema.sql")


def to_float(s):
    if not s:
        return 0.0
    s = s.strip().replace(" ", "").replace(",", ".")
    try:
        return float(s)
    except ValueError:
        return 0.0


def to_iso_date(ddmmyy):
    ddmmyy = (ddmmyy or "").strip()
    if len(ddmmyy) != 6 or not ddmmyy.isdigit():
        return None
    dd, mm, yy = ddmmyy[0:2], ddmmyy[2:4], ddmmyy[4:6]
    if not (1 <= int(mm) <= 12 and 1 <= int(dd) <= 31):
        return None
    return f"20{yy}-{mm}-{dd}"


def read_records(path, delim):
    """Lit un export Sage : enregistrements séparés par ';' ou par saut de ligne,
    champs séparés par des tabulations. Gère l'encodage windows-1252 des exports."""
    with open(path, encoding="cp1252", errors="replace") as f:
        content = f.read()
    raw = content.split(";") if delim == ";" else content.splitlines()
    records = []
    for r in raw:
        r = r.strip("\r\n\t ")
        if not r:
            continue
        records.append(r.split("\t"))
    return records


def field(fields, idx, default=""):
    return fields[idx].strip() if idx < len(fields) and fields[idx] is not None else default


def main():
    if os.path.exists(DB_PATH):
        os.remove(DB_PATH)
    conn = sqlite3.connect(DB_PATH)
    with open(SCHEMA_PATH, encoding="utf-8") as f:
        conn.executescript(f.read())
    cur = conn.cursor()
    stats = {}

    # --- 1. Catalogue officiel des articles ---
    n = 0
    for f_ in read_records(os.path.join(DATA_DIR, "article.txt"), ";"):
        code = field(f_, 0)
        if not code:
            continue
        cur.execute(
            """INSERT OR REPLACE INTO articles (code, designation, famille, prix_achat, prix_vente, tva, complet)
               VALUES (?, ?, ?, ?, ?, ?, 1)""",
            (code, field(f_, 1) or code, field(f_, 2), to_float(field(f_, 3)),
             to_float(field(f_, 6)), field(f_, 13)),
        )
        n += 1
    stats["Articles (catalogue officiel, article.txt)"] = n

    # --- 2. Fichier officiel des clients ---
    n = 0
    for f_ in read_records(os.path.join(DATA_DIR, "client.txt"), ";"):
        code = field(f_, 0)
        if not code:
            continue
        cur.execute(
            "INSERT OR REPLACE INTO clients (code, nom, complet) VALUES (?, ?, 1)",
            (code, field(f_, 1) or code),
        )
        n += 1
    stats["Clients (fichier officiel, client.txt)"] = n

    # --- 3. Dépôts + stock (pp.txt, version complète) ---
    depot_ids = {}

    def get_depot_id(nom):
        nom = " ".join(nom.split())
        if nom not in depot_ids:
            cur.execute("INSERT OR IGNORE INTO depots (nom) VALUES (?)", (nom,))
            cur.execute("SELECT id FROM depots WHERE nom = ?", (nom,))
            depot_ids[nom] = cur.fetchone()[0]
        return depot_ids[nom]

    n = 0
    for f_ in read_records(os.path.join(DATA_DIR, "pp.txt"), "\n"):
        code = field(f_, 0)
        depot_nom = field(f_, 1)
        if not code or not depot_nom:
            continue
        cur.execute("INSERT OR IGNORE INTO articles (code, designation, complet) VALUES (?, ?, 0)", (code, code))
        cur.execute(
            "INSERT OR REPLACE INTO stock (article_code, depot_id, quantite) VALUES (?, ?, ?)",
            (code, get_depot_id(depot_nom), to_float(field(f_, 2))),
        )
        n += 1
    stats["Lignes de stock (pp.txt)"] = n
    stats["Dépôts distincts"] = len(depot_ids)

    # --- 4. Mouvements de vente ---
    def import_mouvements(path, delim, label):
        facture_ids = {}
        n_lignes = 0
        for f_ in read_records(path, delim):
            numero = field(f_, 2)
            date_iso = to_iso_date(field(f_, 3))
            client_code = field(f_, 4)
            article_code = field(f_, 5)
            designation = field(f_, 6)
            prix = to_float(field(f_, 12))
            qte = to_float(field(f_, 13))
            depot_nom = field(f_, 24)
            if not numero or not date_iso or not article_code:
                continue
            if client_code:
                cur.execute(
                    "INSERT OR IGNORE INTO clients (code, nom, complet) VALUES (?, ?, 0)",
                    (client_code, client_code),
                )
            cur.execute(
                "INSERT OR IGNORE INTO articles (code, designation, complet) VALUES (?, ?, 0)",
                (article_code, designation or article_code),
            )
            depot_id = get_depot_id(depot_nom) if depot_nom else None
            key = (numero, date_iso)
            if key not in facture_ids:
                cur.execute(
                    "INSERT OR IGNORE INTO factures (numero, date, client_code, depot_id) VALUES (?, ?, ?, ?)",
                    (numero, date_iso, client_code or None, depot_id),
                )
                cur.execute("SELECT id FROM factures WHERE numero=? AND date=?", (numero, date_iso))
                row = cur.fetchone()
                facture_ids[key] = row[0] if row else None
            facture_id = facture_ids[key]
            if facture_id is None:
                continue
            cur.execute(
                """INSERT INTO lignes_facture (facture_id, article_code, designation, prix_unitaire, quantite)
                   VALUES (?, ?, ?, ?, ?)""",
                (facture_id, article_code, designation, prix, qte),
            )
            n_lignes += 1
        stats[f"Factures ({label})"] = len(facture_ids)
        stats[f"Lignes de vente ({label})"] = n_lignes

    import_mouvements(os.path.join(DATA_DIR, "mp.txt"), ";", "historique 2021-2022, mp.txt")
    import_mouvements(os.path.join(DATA_DIR, "p5.txt"), "\n", "2026, p5.txt")

    conn.commit()

    cur.execute("SELECT COUNT(*) FROM articles WHERE complet=1")
    stats["  dont articles avec prix connus"] = cur.fetchone()[0]
    cur.execute("SELECT COUNT(*) FROM articles WHERE complet=0")
    stats["  dont articles reconstruits (code seul)"] = cur.fetchone()[0]
    cur.execute("SELECT COUNT(*) FROM clients WHERE complet=1")
    stats["  dont clients avec coordonnées connues"] = cur.fetchone()[0]
    cur.execute("SELECT COUNT(*) FROM clients WHERE complet=0")
    stats["  dont clients reconstruits (code seul)"] = cur.fetchone()[0]

    conn.close()

    print("=== Import terminé ===")
    for k, v in stats.items():
        print(f"  {k}: {v}")


if __name__ == "__main__":
    main()
