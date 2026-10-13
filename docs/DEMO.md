# Tester l'application avant le déploiement

Le kit de démonstration lance l'application sur votre ordinateur, avec des données fictives déjà chargées : les 5 agences, une équipe et six semaines de badgeages. Il ne touche à aucun serveur et ne doit pas servir en production.

## 1. Installer Docker (une seule fois)

- **Docker Desktop** : https://www.docker.com/products/docker-desktop/
  Attention : Docker Desktop est payant pour les entreprises de plus de 250 salariés ou de plus de 10 M$ de chiffre d'affaires.
- **Rancher Desktop**, gratuit, fait la même chose : https://rancherdesktop.io/ . À l'installation, choisissez le moteur « dockerd (moby) ».

Après l'installation, lancez le logiciel et attendez qu'il indique être prêt.

## 2. Récupérer le projet

Sur la page GitHub du dépôt, cliquez sur **Code › Download ZIP**, puis décompressez le fichier, par exemple dans `Documents\badgeage`.

## 3. Lancer la démonstration

Sous Windows, double-cliquez sur **`demo\demarrer.bat`**.

La première fois, la préparation prend quelques minutes. Le navigateur s'ouvre ensuite sur **http://localhost:8080**.

Sur Mac, lancez `demo/demarrer.sh` depuis le Terminal.

## 4. Identifiants

Le mot de passe est le même pour tous les comptes : **`Proximy2026`**

| Identifiant | Rôle | Ce qu'il permet de voir |
|---|---|---|
| `ADMIN` | Administrateur | Tout, y compris l'administration |
| `RH01` | RH | Vue globale en lecture seule |
| `M001` | Manager (Sophie Lefèvre) | Son équipe : Lucas, Inès, Hugo |
| `S001` | Salarié (Lucas Bernard) | Journée, télétravail autorisé, un oubli, des départs hors zone |
| `S002` | Salariée (Inès Moreau) | Postes de nuit badgés depuis un ordinateur |
| `S003` | Salarié (Hugo Garcia) | Temps partiel, un départ oublié, une journée longue |
| `S004` | Salariée (Chloé Roux) | Agence de Créteil, sans manager, une position refusée |

Pour tester plusieurs rôles en même temps, ouvrez une fenêtre de navigation privée pour le second compte.

## 5. Ce qu'il faut essayer

**En tant que salarié** (`S001`)
- [ ] Badger son arrivée, puis son départ. Le navigateur demande l'autorisation de localisation.
- [ ] Refuser la localisation et vérifier que le badgeage est enregistré avec « Position refusée ».
- [ ] « J'ai oublié de badger » : saisir un oubli d'hier, puis le retrouver dans « Mes badgeages ».
- [ ] Essayer de saisir un oubli datant de plus de 7 jours : la saisie est refusée.

**En tant que manager** (`M001`)
- [ ] « Mon équipe » sur le mois en cours, puis sur 3 mois.
- [ ] Cocher « Avec alertes ».
- [ ] Ouvrir Inès : les postes de nuit sont rattachés au jour d'arrivée.
- [ ] Corriger un badgeage de Hugo, avec un motif.
- [ ] Vérifier que Chloé (`S004`) n'apparaît pas dans l'équipe.

**En tant qu'administrateur** (`ADMIN`)
- [ ] « Suivi global » filtré par établissement, puis « Exporter (Excel) ».
- [ ] Administration › Journal d'audit : la correction du manager y figure, avec l'avant et l'après.
- [ ] Administration › Import CSV : télécharger le modèle, ajouter une ligne, l'importer.
- [ ] Administration › Paramètres : activer « Les saisies manuelles doivent être validées par le manager », puis refaire un oubli avec `S001` et le valider avec `M001`.
- [ ] Passer « Nombre maximal d'arrivées par jour » à 2 et badger une pause.

**Contrôle de zone depuis votre bureau**

Les agences de démonstration sont placées au centre de chaque commune, pas à leur adresse réelle. Pour voir « Dans la zone » depuis votre ordinateur :

1. Connectez-vous en `ADMIN`, puis ouvrez Administration › Établissements › **Agence test**.
2. Saisissez l'adresse de votre bureau et cliquez sur « Localiser l'adresse », ou cliquez directement sur la carte. Enregistrez.
3. Connectez-vous avec un salarié et badgez.

Sur un ordinateur, la position est souvent approximative (Wi-Fi ou adresse internet). Un résultat « Indéterminé » est donc normal : c'est précisément ce cas que le seuil de précision « ordinateur » sert à repérer. Sous Windows, la localisation doit être activée dans Paramètres › Confidentialité › Localisation.

## 6. Tester sur un smartphone

Les téléphones n'acceptent de donner leur position qu'à un site en HTTPS. Pour un test rapide, un tunnel Cloudflare fournit une adresse HTTPS temporaire vers votre PC :

1. Installez `cloudflared` : https://developers.cloudflare.com/cloudflare-one/connections/connect-networks/downloads/
2. Démonstration lancée, ouvrez une invite de commandes et tapez :
   ```
   cloudflared tunnel --url http://localhost:8080
   ```
3. Une adresse du type `https://xxxx.trycloudflare.com` s'affiche. Ouvrez-la sur le téléphone et connectez-vous en `S001`.
4. Pour fermer l'accès, faites Ctrl+C dans l'invite de commandes.

Pendant ce test, l'application est joignable depuis Internet par quiconque connaît l'adresse : n'y saisissez que des données fictives.

Pour une répétition générale complète, le mieux est d'installer une copie de test sur le serveur de l'entreprise, avec une adresse du type `badge-test.proximy.net` (voir [DEPLOIEMENT.md](DEPLOIEMENT.md)).

## 7. Arrêter, remettre à zéro, supprimer

| Action | Windows | Mac / Linux |
|---|---|---|
| Arrêter (données conservées) | `demo\arreter.bat` | `docker compose -f docker-compose.demo.yml down` |
| Recharger les données de départ | `demo\reinitialiser.bat` | `docker compose -f docker-compose.demo.yml exec app python -m app.demo --forcer` |
| Tout supprimer | `docker compose -f docker-compose.demo.yml down -v` | idem |

Les badgeages de démonstration couvrent les six semaines précédant le premier lancement. Sur une vue de 3 mois ou plus, les semaines antérieures sont vides : l'écart au contrat y paraît donc très négatif, ce qui est normal. Si vous reprenez le test quelques semaines plus tard, rechargez les données pour qu'elles retombent sur le mois en cours.
