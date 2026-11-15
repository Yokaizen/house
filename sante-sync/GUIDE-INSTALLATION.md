# Mise en route — 20 minutes, une seule fois

Chaîne : **Apple Watch → Apple Santé (iPhone) → app Health Auto Export → iCloud Drive → PC Windows (collecte à 8 h 30) → dossier `iCloud Drive\Sante` (CSV lisibles par une IA)**.

Aucun mot de passe n'est stocké : Apple Santé ne se lit que sur l'iPhone, c'est l'app qui pousse les fichiers.

---

## 1. Sur l'iPhone (10 min)

1. Installez **Health Auto Export – JSON+CSV** (éditeur HealthyApps) depuis l'App Store.
2. Achetez **Premium** : 7,99 €/an ou 29,99 € à vie. Sans Premium, l'export automatique en arrière-plan ne fonctionne pas.
3. Au premier lancement, **autorisez l'accès à toutes les catégories Santé**.
4. Créez les automatisations (onglet *Automations* → *+*). Pour chacune : **type iCloud Drive**, **format JSON**, **version 2**.

| Nom de l'automatisation | Données | Réglages |
|---|---|---|
| `Sante-Quotidien` | *Health Metrics* : pas, distance marche + course, étages, énergie active, énergie au repos, temps d'exercice, heures debout, fréquence cardiaque, FC au repos, FC moyenne à la marche, variabilité cardiaque, fréquence respiratoire, saturation en oxygène, VO2 max, analyse du sommeil | *Summarize Data* **activé**, regroupement (*Time Grouping*) **Jour**, période (*Date Range*) **Semaine** |
| `Sante-Seances` | *Workouts* (toutes les séances) | période **Semaine** |
| `Sante-Mesures` | *Health Metrics* : poids (et, si vous en avez un jour, masse grasse, masse maigre, IMC) | *Summarize Data* **désactivé** (une ligne par pesée), période **Semaine** |

   Fréquence de synchronisation : **toutes les heures**.
5. Réglages iPhone → Général → **Actualisation en arrière-plan** : activée pour Health Auto Export.
6. Lancez chaque automatisation une fois à la main (bouton *Manual Upload* ou *Run*) : un dossier **iCloud Drive → Auto Export** doit apparaître dans l'app Fichiers.

> Limite d'Apple : l'iPhone n'exporte que **déverrouillé**. Si vous ne touchez pas votre téléphone un matin, l'export partira dès que vous le déverrouillerez, et le PC le rattrapera au passage suivant (il réessaie toutes les heures jusqu'à 22 h).

## 2. Sur le PC Windows (5 min)

1. Installez **iCloud pour Windows** (Microsoft Store), connectez-vous avec votre identifiant Apple, cochez **iCloud Drive**.
2. Dans l'Explorateur : **iCloud Drive → Auto Export** → clic droit → **Toujours conserver sur cet appareil**.
3. Décompressez le dossier `sante-sync` reçu, puis **double-cliquez sur `INSTALLER.cmd`**.
   - Installe Python dans votre profil (sans droits administrateur), copie le programme dans `%LOCALAPPDATA%\SanteSync`, crée `iCloud Drive\Sante`, installe la tâche planifiée, envoie une **notification de test**, puis fait un premier passage.
   - Si Windows affiche « Windows a protégé votre ordinateur » : *Informations complémentaires* → *Exécuter quand même*.
4. À la fin, l'installateur affiche les dernières lignes de vos fichiers. **Copiez-moi ce texte** : je vérifie avec vous que les vraies données sont cohérentes.

## 3. L'historique complet (facultatif, 5 min)

1. iPhone : **Santé → photo de profil → Exporter toutes les données de santé** → enregistrez `export.zip` dans iCloud Drive, puis déplacez-le dans **iCloud Drive → Sante → import_manuel**.
2. PC : double-clic sur `%LOCALAPPDATA%\SanteSync\Historique complet.cmd`. Plusieurs années d'Apple Watch prennent quelques minutes. S'il est interrompu, relancez : il reprend où il s'était arrêté.

## 4. Demain matin : vérifier que la collecte a tourné

- Ouvrez **iCloud Drive → Sante → status.json** : `derniere_execution` doit indiquer demain après 8 h 30, et `resultat` doit valoir `"ok"`.
- Ou bien : *Planificateur de tâches* → *SanteSync - collecte quotidienne* → « Résultat de la dernière exécution » = `(0x0)`.
- En cas de problème, une notification Windows « Santé : … » vous prévient (une seule par jour et par problème).

## 5. Donner les données à une IA

Partagez le dossier `iCloud Drive\Sante` (ou ses fichiers). L'IA doit lire **AGENTS.md** en premier, puis **status.json**.
