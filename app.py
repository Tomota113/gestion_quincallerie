import os
import sqlite3
from flask import Flask, render_template, request, abort, g

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "gestion.db")

app = Flask(__name__)
PAGE_SIZE = 50


def get_db():
    if "db" not in g:
        g.db = sqlite3.connect(DB_PATH)
        g.db.row_factory = sqlite3.Row
    return g.db


@app.teardown_appcontext
def close_db(exception=None):
    db = g.pop("db", None)
    if db is not None:
        db.close()


def paginate(request):
    try:
        page = max(1, int(request.args.get("page", 1)))
    except ValueError:
        page = 1
    return page, (page - 1) * PAGE_SIZE


@app.route("/")
def dashboard():
    db = get_db()
    stats = {
        "articles": db.execute("SELECT COUNT(*) FROM articles").fetchone()[0],
        "articles_connus": db.execute("SELECT COUNT(*) FROM articles WHERE complet=1").fetchone()[0],
        "clients": db.execute("SELECT COUNT(*) FROM clients").fetchone()[0],
        "clients_connus": db.execute("SELECT COUNT(*) FROM clients WHERE complet=1").fetchone()[0],
        "factures": db.execute("SELECT COUNT(*) FROM factures").fetchone()[0],
        "depots": db.execute("SELECT COUNT(*) FROM depots").fetchone()[0],
    }
    top_articles = db.execute(
        """SELECT l.article_code, COALESCE(a.designation, l.designation) as designation, SUM(l.quantite) as total
           FROM lignes_facture l LEFT JOIN articles a ON a.code = l.article_code
           GROUP BY l.article_code ORDER BY total DESC LIMIT 8"""
    ).fetchall()
    ventes_recentes = db.execute(
        """SELECT f.id, f.numero, f.date, COALESCE(c.nom, f.client_code) as client_nom,
                  (SELECT COUNT(*) FROM lignes_facture WHERE facture_id=f.id) as n_lignes
           FROM factures f LEFT JOIN clients c ON c.code = f.client_code
           ORDER BY f.date DESC, f.id DESC LIMIT 8"""
    ).fetchall()
    alertes_stock = db.execute(
        """SELECT a.code, a.designation, SUM(s.quantite) as total
           FROM stock s JOIN articles a ON a.code = s.article_code
           WHERE a.complet = 1
           GROUP BY a.code HAVING total <= 2
           ORDER BY total ASC LIMIT 8"""
    ).fetchall()
    return render_template(
        "dashboard.html", stats=stats, top_articles=top_articles,
        ventes_recentes=ventes_recentes, alertes_stock=alertes_stock,
    )


@app.route("/articles")
def articles_list():
    db = get_db()
    q = request.args.get("q", "").strip()
    page, offset = paginate(request)
    where, params = "", []
    if q:
        where = "WHERE code LIKE ? OR designation LIKE ?"
        params = [f"%{q}%", f"%{q}%"]
    total = db.execute(f"SELECT COUNT(*) FROM articles {where}", params).fetchone()[0]
    rows = db.execute(
        f"""SELECT code, designation, famille, prix_vente, complet,
                   (SELECT COALESCE(SUM(quantite),0) FROM stock WHERE article_code=articles.code) as stock_total
            FROM articles {where} ORDER BY designation LIMIT ? OFFSET ?""",
        params + [PAGE_SIZE, offset],
    ).fetchall()
    return render_template(
        "articles_list.html", rows=rows, q=q, page=page,
        has_next=offset + PAGE_SIZE < total, total=total,
    )


@app.route("/articles/<code>")
def article_detail(code):
    db = get_db()
    article = db.execute("SELECT * FROM articles WHERE code=?", (code,)).fetchone()
    if article is None:
        abort(404)
    stock = db.execute(
        """SELECT d.nom as depot, s.quantite FROM stock s JOIN depots d ON d.id = s.depot_id
           WHERE s.article_code=? ORDER BY s.quantite DESC""",
        (code,),
    ).fetchall()
    ventes = db.execute(
        """SELECT f.date, f.numero, COALESCE(c.nom, f.client_code) as client_nom, l.prix_unitaire, l.quantite
           FROM lignes_facture l JOIN factures f ON f.id = l.facture_id
           LEFT JOIN clients c ON c.code = f.client_code
           WHERE l.article_code=? ORDER BY f.date DESC LIMIT 30""",
        (code,),
    ).fetchall()
    return render_template("article_detail.html", a=article, stock=stock, ventes=ventes)


@app.route("/stock")
def stock_view():
    db = get_db()
    q = request.args.get("q", "").strip()
    depot_id = request.args.get("depot", "").strip()
    depots = db.execute("SELECT * FROM depots ORDER BY nom").fetchall()
    where = ["1=1"]
    params = []
    if q:
        where.append("(a.code LIKE ? OR a.designation LIKE ?)")
        params += [f"%{q}%", f"%{q}%"]
    if depot_id:
        where.append("d.id = ?")
        params.append(depot_id)
    rows = db.execute(
        f"""SELECT a.code, a.designation, d.nom as depot, s.quantite
            FROM stock s JOIN articles a ON a.code = s.article_code
            JOIN depots d ON d.id = s.depot_id
            WHERE {' AND '.join(where)} AND s.quantite > 0
            ORDER BY a.designation LIMIT 300""",
        params,
    ).fetchall()
    return render_template("stock.html", rows=rows, q=q, depots=depots, depot_id=depot_id)


@app.route("/clients")
def clients_list():
    db = get_db()
    q = request.args.get("q", "").strip()
    page, offset = paginate(request)
    where, params = "", []
    if q:
        where = "WHERE code LIKE ? OR nom LIKE ?"
        params = [f"%{q}%", f"%{q}%"]
    total = db.execute(f"SELECT COUNT(*) FROM clients {where}", params).fetchone()[0]
    rows = db.execute(
        f"""SELECT code, nom, complet,
                   (SELECT COUNT(*) FROM factures WHERE client_code=clients.code) as n_factures
            FROM clients {where} ORDER BY nom LIMIT ? OFFSET ?""",
        params + [PAGE_SIZE, offset],
    ).fetchall()
    return render_template(
        "clients_list.html", rows=rows, q=q, page=page,
        has_next=offset + PAGE_SIZE < total, total=total,
    )


@app.route("/clients/<code>")
def client_detail(code):
    db = get_db()
    client = db.execute("SELECT * FROM clients WHERE code=?", (code,)).fetchone()
    if client is None:
        abort(404)
    factures = db.execute(
        """SELECT id, numero, date,
                  (SELECT COALESCE(SUM(prix_unitaire*quantite),0) FROM lignes_facture WHERE facture_id=factures.id) as total
           FROM factures WHERE client_code=? ORDER BY date DESC LIMIT 50""",
        (code,),
    ).fetchall()
    return render_template("client_detail.html", c=client, factures=factures)


@app.route("/factures")
def factures_list():
    db = get_db()
    q = request.args.get("q", "").strip()
    page, offset = paginate(request)
    where, params = "1=1", []
    if q:
        where = "(f.numero LIKE ? OR c.nom LIKE ? OR f.client_code LIKE ?)"
        params = [f"%{q}%", f"%{q}%", f"%{q}%"]
    total = db.execute(
        f"SELECT COUNT(*) FROM factures f LEFT JOIN clients c ON c.code=f.client_code WHERE {where}", params
    ).fetchone()[0]
    rows = db.execute(
        f"""SELECT f.id, f.numero, f.date, COALESCE(c.nom, f.client_code) as client_nom,
                   (SELECT COALESCE(SUM(prix_unitaire*quantite),0) FROM lignes_facture WHERE facture_id=f.id) as total
            FROM factures f LEFT JOIN clients c ON c.code=f.client_code
            WHERE {where} ORDER BY f.date DESC, f.id DESC LIMIT ? OFFSET ?""",
        params + [PAGE_SIZE, offset],
    ).fetchall()
    return render_template(
        "factures_list.html", rows=rows, q=q, page=page,
        has_next=offset + PAGE_SIZE < total, total=total,
    )


@app.route("/factures/<int:facture_id>")
def facture_detail(facture_id):
    db = get_db()
    f = db.execute(
        """SELECT f.*, COALESCE(c.nom, f.client_code) as client_nom, d.nom as depot_nom
           FROM factures f LEFT JOIN clients c ON c.code=f.client_code
           LEFT JOIN depots d ON d.id=f.depot_id WHERE f.id=?""",
        (facture_id,),
    ).fetchone()
    if f is None:
        abort(404)
    lignes = db.execute("SELECT * FROM lignes_facture WHERE facture_id=?", (facture_id,)).fetchall()
    total = sum(l["prix_unitaire"] * l["quantite"] for l in lignes)
    return render_template("facture_detail.html", f=f, lignes=lignes, total=total)


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
