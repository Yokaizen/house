# Déploiement sur le serveur de l'entreprise

## 1. Prérequis

- Serveur Linux avec Docker Engine 24 ou plus récent et le plugin Docker Compose (`docker compose version`).
- Un nom de domaine public (exemple : `badge.proximy.net`) pointant vers le serveur, ports 80 et 443 ouverts depuis Internet.
- Le certificat d'entreprise pour ce domaine (certificat, chaîne intermédiaire et clé privée).
- Accès sortant à `api-adresse.data.gouv.fr` pour localiser les adresses (facultatif : sinon, les positions se placent à la main sur la carte).
- Côté navigateur des administrateurs : accès à `unpkg.com` et `tile.openstreetmap.org` pour afficher la carte.

## 2. Installation

```bash
git clone <dépôt> badgeage && cd badgeage
cp .env.example .env
```

Éditez `.env` :

| Variable | Valeur |
|---|---|
| `POSTGRES_PASSWORD` | mot de passe long et aléatoire (`openssl rand -hex 24`) |
| `BASE_URL` | adresse publique, ex. `https://badge.proximy.net` |
| `SMTP_*` | à remplir quand le serveur d'envoi sera disponible |
| `HTTP_PORT` / `HTTPS_PORT` | à changer seulement si 80/443 sont déjà utilisés |

Certificat (format PEM) :

```bash
cat domaine.crt intermediaire.crt > nginx/certs/certificat.crt
cp domaine.key nginx/certs/certificat.key
chmod 600 nginx/certs/certificat.key
```

Si le certificat est fourni en `.pfx` / `.p12` :

```bash
openssl pkcs12 -in certificat.pfx -clcerts -nokeys -out nginx/certs/certificat.crt
openssl pkcs12 -in certificat.pfx -cacerts -nokeys >> nginx/certs/certificat.crt
openssl pkcs12 -in certificat.pfx -nocerts -nodes -out nginx/certs/certificat.key
```

Démarrage :

```bash
docker compose up -d --build
docker compose ps          # les 4 services doivent être « Up », app « healthy »
```

## 3. Premier paramétrage

1. Créez le premier administrateur. Un mot de passe provisoire s'affiche ; il sera à changer à la première connexion :
   ```bash
   docker compose exec app python -m app.cli creer-admin A0001 Nom Prénom prenom.nom@proximy.net
   ```
2. **Administration › Établissements** : créez les 5 agences (code, nom, adresse), cliquez « Localiser l'adresse », vérifiez le repère sur la carte et ajustez le rayon.
3. **Administration › Paramètres** : vérifiez les règles (rayon, précision, alertes, conservation).
4. **Administration › Import CSV** : téléchargez le modèle, remplissez-le, importez-le. Copiez les mots de passe provisoires affichés pour les transmettre aux salariés.
5. Contrôlez les domiciles marqués « À localiser » dans la liste des utilisateurs.

## 4. Exploitation

| Action | Commande |
|---|---|
| Journaux | `docker compose logs -f app worker` |
| Redémarrer | `docker compose restart` |
| Mettre à jour | `git pull && docker compose up -d --build` (migrations appliquées automatiquement) |
| Arrêter | `docker compose down` (les données restent dans le volume `pgdata`) |
| Réinitialiser l'accès d'un administrateur | `docker compose exec app python -m app.cli creer-admin MATRICULE Nom Prénom` |

### Sauvegardes

À planifier chaque nuit (cron) :

```bash
mkdir -p sauvegardes
docker compose exec -T db pg_dump -U badgeage -Fc badgeage > sauvegardes/badgeage_$(date +%F).dump
find sauvegardes -name '*.dump' -mtime +30 -delete
```

Restauration :

```bash
docker compose exec -T db pg_restore -U badgeage -d badgeage --clean --if-exists < sauvegardes/badgeage_AAAA-MM-JJ.dump
```

Les sauvegardes contiennent des données personnelles : stockez-les dans un emplacement à accès restreint et appliquez-leur la même durée de conservation.

### Renouvellement du certificat

Remplacez les fichiers dans `nginx/certs/`, puis : `docker compose restart nginx`.

## 5. Sécurité en place

- HTTPS obligatoire (HSTS) ; cookies de session `HttpOnly`, `Secure`, `SameSite=Lax`.
- Mots de passe hachés (Argon2), 10 caractères minimum, verrouillage de 15 minutes après 5 échecs.
- Jeton anti-CSRF sur tous les formulaires et appels de badgeage.
- Sessions révoquées à la désactivation du compte ou à la réinitialisation du mot de passe.
- Journal d'audit des corrections, imports, paramètres et comptes.
- Conteneur applicatif exécuté sans droits root ; la base n'est pas exposée hors du réseau Docker.
