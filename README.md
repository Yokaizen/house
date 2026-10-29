# Badgeage Proximy

Application web de badgeage des arrivées et départs des salariés, avec contrôle de périmètre GPS **sans enregistrement de la position**.

## Fonctionnalités

**Salarié** (smartphone ou ordinateur)
- Bouton unique « Badger mon arrivée » / « Badger mon départ », heure enregistrée côté serveur.
- Contrôle de zone : le serveur vérifie si la position est dans le rayon d'un lieu autorisé (tous les établissements et le domicile déclaré). Seul le résultat est stocké : *Dans la zone*, *Hors zone*, *Indéterminé* (position trop imprécise) ou *Position refusée*. Le badgeage n'est jamais bloqué.
- Le type d'appareil (smartphone ou PC) et la précision annoncée sont conservés : un badgeage depuis un PC est repérable (mention « · PC ») et soumis à un seuil de précision distinct.
- « J'ai oublié de badger » : saisie manuelle avec motif obligatoire, limitée à N jours en arrière, marquée visiblement (pastille « Saisie manuelle », heure soulignée en pointillé).
- Historique mensuel : totaux par jour et par semaine, comparaison au contrat, alertes.
- Session longue (90 jours par défaut, option « Rester connecté »), application installable sur l'écran d'accueil.

**Manager**
- Vue de son équipe (N-1, ou N-2 en option) sur la période en cours, un mois, 3, 6 ou 12 mois, ou une période libre, avec ventilation par mois.
- Durée badgée, durée théorique, écart, points de vigilance : départ ou arrivée non badgés, durée journalière, amplitude, repos quotidien, durée hebdomadaire, hors zone.
- Correction, ajout et suppression de badgeages avec motif obligatoire, tracés dans le journal d'audit.
- Validation des saisies manuelles : prête, désactivée par défaut (paramètre).

**RH (lecture seule) et administrateur**
- Vue globale filtrable par établissement, manager et nom, avec export Excel (synthèse, détail, légende).
- Administration : utilisateurs (création, rattachement à un manager, réinitialisation du mot de passe, désactivation, suppression), **import CSV**, établissements avec carte et rayon, paramètres métier, journal d'audit.

**Tâches automatiques** (conteneur `worker`)
- Désactivation des comptes à la date de sortie, purge des comptes sortis et des badgeages anciens (durées paramétrables).
- Relance par e-mail en cas de départ non badgé ; rappel quotidien des saisies à valider (si activé). Sans serveur SMTP, les e-mails sont seulement journalisés.

## Architecture

| Conteneur | Rôle |
|---|---|
| `nginx` | HTTPS avec le certificat d'entreprise, redirection HTTP vers HTTPS, en-têtes de sécurité |
| `app` | Application Python (FastAPI) servie par Gunicorn ; applique les migrations au démarrage |
| `worker` | Tâches planifiées (toutes les 15 minutes) |
| `db` | PostgreSQL 16 (volume `pgdata`) |

Code : `app/services` (logique métier), `app/routers` (pages), `app/templates` (écrans), `migrations` (schéma de base Alembic), `tests`.

## Tester avant le déploiement

Un kit de démonstration lance l'application sur un PC avec des données fictives : double-cliquez sur `demo\demarrer.bat` (Windows) puis ouvrez http://localhost:8080. Voir [docs/DEMO.md](docs/DEMO.md).

## Déploiement

Voir [docs/DEPLOIEMENT.md](docs/DEPLOIEMENT.md). En résumé :

```bash
cp .env.example .env          # renseigner POSTGRES_PASSWORD, BASE_URL…
cp mon-certificat.crt nginx/certs/certificat.crt
cp ma-cle.key        nginx/certs/certificat.key
docker compose up -d --build
docker compose exec app python -m app.cli creer-admin MATRICULE Nom Prénom email@proximy.net
```

## Développement

```bash
python -m venv .venv && . .venv/bin/activate
pip install -r requirements-dev.txt
pytest
```

Les tests utilisent SQLite ; la production utilise PostgreSQL.

L'interface suit la charte web Proximy : [docs/CHARTE-WEB.md](docs/CHARTE-WEB.md).

## Points à valider avant la mise en service

- **Durées de conservation** : par défaut 12 mois pour les badgeages et 2 mois pour les comptes après la date de sortie (paramétrables). Le Code du travail impose de pouvoir présenter les décomptes de durée du travail pendant un an : à valider avec le DPO.
- **Information des salariés et consultation du CSE** : la page « Vos données » de l'application décrit le traitement ; son texte est à relire avec le DPO.
- **Fiabilité** : la position est fournie par le navigateur. Un salarié techniquement averti peut la falsifier ; le contrôle sert d'indicateur, pas de preuve.
- La durée théorique ne tient pas compte des absences (congés, maladie) ni des plannings : elle vaut contrat ÷ 5 par jour ouvré, hors jours fériés nationaux.
