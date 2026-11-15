"""README.md, AGENTS.md et LISEZMOI de l'import manuel, écrits dans le dossier de données."""
from __future__ import annotations

import sys
from pathlib import Path

from .config import Config, app_dir

PROFILE = {
    "owner": "Yann Kerlidou",
    "age": "35-44 ans",
    "goals": [
        "Poids et composition corporelle",
        "Mieux dormir (durée et régularité)",
        "Forme et endurance (activité, VO2max, pas)",
        "Récupération et stress (FC au repos, variabilité cardiaque)",
    ],
    "weight": ("Pesées : balance connectée Xiaomi Mi (app Zepp, ex-Mi Fit) qui écrit dans Apple Santé "
               "(sources « Zepp », « Zepp Life ») ; quelques pesées saisies à la main (iPhone, GymBook). Masse grasse et "
               "masse maigre présentes seulement quand la balance a pu mesurer l'impédance (pieds nus) ; sinon "
               "poids et IMC seuls. Plusieurs pesées à quelques secondes d'écart = remontées sur la balance : "
               "prendre la dernière ou la moyenne."),
    "context": ("Rien de particulier signalé (pas de traitement agissant sur le cœur, pas de blessure). "
                "La montre n'est en général **pas portée la nuit** : colonnes de sommeil vides la plupart du temps "
                "(c'est normal, pas une panne), et FC au repos / VFC calculées sur les mesures de la journée. "
                "Il envisage de la porter la nuit : les nuits mesurées apparaîtront alors d'elles-mêmes."),
    "devices": "Apple Watch + iPhone (Apple Santé) ; balance Xiaomi Mi via l'app Zepp.",
}


def _code_dir() -> str:
    return str(app_dir())


def readme(cfg: Config) -> str:
    code = _code_dir()
    py = r"%LOCALAPPDATA%\SanteSync\venv\Scripts\python.exe" if sys.platform == "win32" or "AppData" in code \
        else f"{code}/venv/bin/python"
    return f"""# Données santé — maintenance

- **Code** : `{code}` (hors du dossier synchronisé ; environnement Python dans `venv`, réglages dans `config.json`).
- **Journal** : `{code}\\journaux\\sante-sync.log` ; état interne (fichiers déjà lus, verrou) dans `{code}\\etat`.
- **Données** : ce dossier ({cfg.data_dir}). Ne rien y mettre d'autre que ce que le script produit, sauf dans `import_manuel/`.
- **Lancement automatique** : tâche planifiée Windows « SanteSync - collecte quotidienne », chaque jour à {cfg.run_after}, plus à l'ouverture de session et au déverrouillage ; relance toutes les heures jusqu'à 22 h tant que le passage n'a pas réussi.
- **Un seul passage réussi par jour** : les déclenchements suivants s'arrêtent tout de suite ; pas de collecte automatique avant {cfg.run_after}.
- **Relancer à la main** : double-clic sur `{code}\\Collecter maintenant.cmd` (ou `{py} -m sante_sync collecte --force`).
- **Récupérer tout l'historique** : exporter depuis l'iPhone (Santé → photo de profil → Exporter toutes les données), déposer `export.zip` dans `import_manuel/`, puis double-clic sur `{code}\\Historique complet.cmd`. Reprend où il s'est arrêté s'il est interrompu.
- **Vérifier que ça a tourné** : ouvrir `status.json` (champ `derniere_execution`), ou Planificateur de tâches → SanteSync → « Résultat de la dernière exécution » = 0x0.
- **Source des données** : app iPhone *Health Auto Export* (Premium) → iCloud Drive → `Auto Export/<automatisation>` → ce script → CSV.
- **Se « reconnecter » à Apple Santé** : rien à faire côté ordinateur (aucun mot de passe). Sur l'iPhone : ouvrir Health Auto Export une fois déverrouillé ; vérifier Réglages → Santé → Accès aux données → Health Auto Export.
- **Si status.json dit « dernier export reçu il y a NN h »** : l'iPhone n'a pas exporté (verrouillé, mode économie d'énergie, actualisation en arrière-plan coupée) ; ouvrir l'app et lancer l'automatisation à la main.
- **Si iCloud ne descend pas les fichiers** : ouvrir iCloud pour Windows ; clic droit sur le dossier `Auto Export` → « Toujours conserver sur cet appareil ».
- **Mots de passe / jetons** : aucun pour Apple Santé ; si une source en demande un jour, il ira dans le Gestionnaire d'identification Windows (service « sante-sync »), jamais dans un fichier.
- **Import manuel** : déposer dans `import_manuel/` un export Apple (`export.zip`) ou un fichier Health Auto Export (`.json`/`.csv`) ; intégré au passage suivant puis rangé dans `import_manuel/integres/`.
- **Choix : Health Auto Export** : seule voie fiable, automatique et sans Mac pour sortir Apple Santé de l'iPhone ; export JSON quotidien vers iCloud Drive.
- **Choix : JSON plutôt que CSV côté app** : structure stable et documentée par l'éditeur ; le CSV de l'app est lu au mieux.
- **Choix : sources multiples** (montre + iPhone qui comptent tous les deux les pas) : on ne les additionne jamais ; on garde la source la plus complète du jour.
- **Choix : sommeil** : attribué au jour du réveil (une nuit qui finit avant 18 h compte pour ce jour-là).
- **Choix : heures** : heure locale du lieu de la mesure, sans décalage horaire.
- **Choix : case vide** : la donnée n'existe pas à la source ; jamais remplacée par zéro.
- **Choix : priorité** : les valeurs de Health Auto Export priment sur celles recalculées depuis l'export complet Apple (colonne `origine`).
- **Choix : rechargement** : chaque passage relit les fichiers des 3 derniers jours (montre synchronisée en retard) et des pesées depuis la dernière moins 7 jours ; les jours manqués se rattrapent seuls.
- **Erreurs** : 3 essais espacés (30 s, 2 min), puis erreur écrite dans `status.json` et notification Windows (une seule par jour et par problème) ; une source en panne ne bloque pas les autres.
- **Désinstaller** : `powershell -ExecutionPolicy Bypass -File "{code}\\app\\windows\\desinstaller.ps1"` (les données restent).
- **Garmin / Withings / autres** : non installés (non utilisés). Le code est prévu pour ajouter une source (`engine.py`, classe `Source`).
"""


def agents(cfg: Config) -> str:
    p = PROFILE
    goals = "\n".join(f"  - {g}" for g in p["goals"])
    return f"""# AGENTS.md — à lire par toute IA qui ouvre ce dossier

## À qui sont ces données
- Données de santé personnelles de **{p['owner']}** ({p['age']}). **Confidentielles** : ne pas les copier ailleurs, ne pas les envoyer à un service tiers, ne pas les citer hors de la conversation avec leur propriétaire.
- Appareils : {p['devices']}
- {p['weight']}
- Contexte : {p['context']}
- Objectifs, par ordre d'importance égal :
{goals}

## Par où commencer
1. Lire `status.json` : `derniere_execution`, `resultat` (ok / partiel / erreur), état par source, `fichiers.*.derniere_date`.
2. Données fraîches = `resultat` ok et `apple_quotidien.csv` a une ligne pour aujourd'hui ou hier. Sinon, le dire avant toute analyse.
3. Puis lire les CSV (UTF-8, séparateur virgule, point décimal, une ligne d'en-tête).

## Les fichiers
| Fichier | Contenu | Clé | Origine |
|---|---|---|---|
| `status.json` | Fraîcheur et santé de la collecte | — | script de collecte |
| `apple_quotidien.csv` | Une ligne par jour : activité, cœur, sommeil, résumé des séances | `date` (AAAA-MM-JJ) | Apple Watch/iPhone → Apple Santé → Health Auto Export |
| `apple_activites.csv` | Une ligne par séance (course, marche, vélo…) | `id` = heure de début | idem |
| `apple_pesees.csv` | Une ligne par pesée (deux pesées rapprochées = deux mesures réelles) | `id` = horodatage de la mesure | balance Xiaomi via Zepp → Apple Santé ; anciennes saisies manuelles |
| `import_manuel/` | Dépôt d'exports téléchargés à la main ; vidé à chaque passage | — | propriétaire |

### Colonnes de `apple_quotidien.csv`
- `pas`, `distance_km` (marche + course), `etages`, `calories_actives_kcal`, `calories_repos_kcal` (métabolisme de base estimé), `minutes_exercice` (anneau vert), `heures_debout` (anneau bleu).
- `fc_repos_bpm` (FC au repos calculée par la montre), `fc_moyenne_bpm`, `fc_min_bpm`, `fc_max_bpm`, `fc_marche_bpm`.
- `vfc_sdnn_ms` : variabilité cardiaque **SDNN** (Apple), moyenne des mesures ponctuelles du jour. Pas comparable au RMSSD d'autres marques.
- `frequence_respiratoire` (nuit), `spo2_pct`, `vo2max` (estimation Apple, ml/kg/min).
- Sommeil de la **nuit qui se termine ce jour-là** : `sommeil_total_h`, `sommeil_leger_h` (« Core »), `sommeil_profond_h`, `sommeil_paradoxal_h` (REM), `eveil_nuit_h`, `au_lit_h`, `coucher`, `lever` (heure locale).
- `nb_activites`, `minutes_activites`, `activites` (résumé des séances du jour).
- Fichiers CSV en UTF-8 avec BOM (pour Excel) : lire avec l'encodage `utf-8-sig`.
- `lumiere_jour_min` (temps passé à la lumière du jour, utile pour le sommeil), `minutes_debout`, `vitesse_marche_kmh`, `longueur_pas_cm`, `asymetrie_marche_pct`, `double_appui_pct` (marqueurs de mobilité mesurés par l'iPhone en poche), `effort_physique_met` (intensité moyenne, MET), `bruit_ambiant_db`, `bruit_casque_db`.
- `origine` : `hae` (export quotidien de l'app, référence, à partir de mi-novembre 2026) ou `export_apple` (recalculé depuis l'export complet, historique ancien).
- **Attention à la rupture de série** : sur les jours `export_apple`, pas et distance sont **sous-estimés de 2 à 10 %** (comparaison des jours présents dans les deux : 7 325 contre 7 674 pas, 8 105 contre 8 988). Ne pas interpréter le passage de `export_apple` à `hae` comme une hausse d'activité ; comparer des périodes de même origine. Les mesures cardiaques et les pesées sont identiques dans les deux.

## Ne jamais modifier
`apple_quotidien.csv`, `apple_activites.csv`, `apple_pesees.csv`, `status.json` sont **réécrits chaque jour** : toute modification serait perdue. Pour une analyse, travailler sur une copie. `README.md` et `AGENTS.md` sont mis à jour par le programme ; le propriétaire peut les enrichir en supprimant d'abord la ligne de commentaire finale.

## Comment interpréter
- **Case vide = donnée absente à la source** (montre non portée, pas de mesure). Ne jamais la traiter comme zéro ; l'exclure des moyennes.
- Raisonner sur la **moyenne glissante sur 7 jours** et sa tendance sur 4 à 8 semaines, pas sur un jour isolé. Un jour seul (mauvaise nuit, FC au repos +5) n'est pas un signal.
- Récupération : une **FC au repos qui monte** et une **VFC qui baisse** plusieurs jours de suite, par rapport à la moyenne des 30 jours, signalent fatigue, stress, maladie ou alcool.
- Le jour courant est **incomplet** (pas, calories) tant que la journée n'est pas finie.
- Poids : pesées à des heures variables (balance Xiaomi, parfois saisies à la main) ; comparer des moyennes hebdomadaires, idéalement les pesées du matin. Une variation de ±1 kg sur quelques jours est surtout de l'eau.
- Composition corporelle : la balance Xiaomi est à impédance ; sa masse grasse (`masse_grasse_pct`, `masse_maigre_kg`) est **fiable en tendance, pas en valeur absolue** (dépend de l'hydratation, de l'heure, des repas).
- Sommeil : peu de nuits mesurées (montre rarement portée la nuit). Ne jamais conclure à un manque de sommeil à partir d'une case vide ; pour l'objectif « mieux dormir », s'appuyer sur les nuits mesurées et le signaler quand il y en a trop peu.
- Sommeil : les phases (léger/profond/paradoxal) de l'Apple Watch sont des estimations ; la durée totale et la régularité de l'heure de coucher sont plus fiables.
- Calories : estimations de l'appareil, à ±10-20 % ; utiles pour comparer des jours entre eux.
- Ces données ne remplacent pas un avis médical : signaler sans alarmer, et suggérer un médecin si une tendance inquiétante persiste.
"""


IMPORT_README = """Déposez ici un fichier téléchargé à la main, il sera intégré au prochain passage :
- export.zip d'Apple Santé (iPhone : Santé → photo de profil → Exporter toutes les données de santé) ;
- un fichier .json ou .csv exporté depuis Health Auto Export.
Une fois intégré, le fichier est rangé dans integres/. En cas d'échec, il reste ici et status.json explique pourquoi.
"""


MARKER = "<!-- Fichier généré : supprimez cette ligne pour que vos modifications ne soient plus remplacées. -->"


def ensure_docs(cfg: Config, overwrite: bool = False) -> list[Path]:
    d = cfg.data_path
    d.mkdir(parents=True, exist_ok=True)
    (d / "import_manuel").mkdir(exist_ok=True)
    written = []
    for name, content in (("README.md", readme(cfg) + "\n" + MARKER + "\n"),
                          ("AGENTS.md", agents(cfg) + "\n" + MARKER + "\n"),
                          ("import_manuel/LISEZMOI.txt", IMPORT_README)):
        p = d / name
        old = p.read_text(encoding="utf-8") if p.exists() else None
        # Mis à jour tant que le propriétaire ne l'a pas personnalisé (marqueur présent, ou
        # première version sans marqueur jamais modifiée à la main).
        auto = old is None or MARKER in old or (name.endswith(".md") and "## " in old and "Fichier généré" not in old
                                                 and old.startswith(content.split("\n", 1)[0]))
        if (overwrite or auto) and old != content:
            p.write_text(content, encoding="utf-8")
            written.append(p)
    return written
