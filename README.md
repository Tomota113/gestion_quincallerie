# Gestion Quincaillerie — v0

Première brique du système de gestion : les données de Sage 100 Commercial
reconstruites dans une vraie base, consultables depuis un navigateur.

## Installer et lancer

Il ne faut qu'une seule dépendance externe (Flask), tout le reste est du
Python standard.

```bash
cd gestion
pip install -r requirements.txt --break-system-packages   # ou dans un venv si tu préfères

python3 import_data.py     # (re)construit gestion.db depuis les fichiers dans data/
python3 app.py              # lance le serveur
```

Puis ouvrir `http://localhost:5000` dans un navigateur — sur le PC de la
boutique ou sur un autre appareil du même réseau wifi (remplacer `localhost`
par l'adresse IP du PC, ex. `http://192.168.1.X:5000`).

## Ce qui a été fait

- **Articles / Clients** : importés depuis `article.txt` et `client.txt`.
- **Stock** : importé depuis `pp.txt` (version complète — `stock.txt` est
  une copie tronquée du même fichier, pas utilisée).
- **Ventes** : importées depuis `mp.txt` (historique 30/01/2021 → 22/07/2022)
  et `p5.txt` (02/01/2026 → 17/08/2026, le plus récent).
  `p4.txt` et `p10.txt` ont été vérifiés programmatiquement : ce sont des
  doublons exacts de `mp.txt` et `p5.txt`, donc pas réimportés.
- **`p7.txt`** n'est pas encore importé : ses 222 lignes sont toutes datées
  du 03/01/2026 et la structure est différente (ça ressemble à un
  inventaire physique de début d'année plutôt qu'à des ventes). À regarder
  si c'est utile.

## Ce qui manque encore

`article.txt` et `client.txt` ne couvraient qu'une petite partie de
l'alphabet (voir le message de discussion). Le script a donc créé des
fiches "à compléter" pour tous les articles/clients rencontrés dans le
stock et l'historique des ventes mais absents de ces deux fichiers —
1863 articles et 231 clients dans ce cas. Ils apparaissent avec un badge
**"à compléter"** dans l'interface : on connaît leur code (et leur
désignation pour les articles), mais pas leur prix d'achat/vente, leur TVA,
ou les coordonnées du client. Un ré-export complet depuis Sage réglera ça
d'un coup — en attendant, la fiche est éditable à la main article par
article si besoin.

## Structure du projet

```
gestion/
  app.py              → application Flask (routes + logique)
  import_data.py       → script qui lit les fichiers Sage et remplit la base
  schema.sql            → définition des tables
  gestion.db            → la base SQLite (déjà construite, relancer
                           import_data.py pour la reconstruire à zéro)
  data/                  → les 9 fichiers Sage d'origine
  templates/              → les pages HTML
  static/style.css        → la mise en forme
```

## Pour la suite

C'était la base commune (catalogue, stock, clients, historique des
ventes) — l'étape suivante logique est de pouvoir **créer une vente
directement depuis l'interface** (ça enlève vraiment le papier), avec mise
à jour automatique du stock. Ensuite : achats/réapprovisionnement,
export des factures en PDF, et une vraie authentification si plusieurs
personnes doivent s'en servir.
