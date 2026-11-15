# sante-sync

Collecte quotidienne des données Apple Santé (exportées par l'app iPhone *Health Auto Export* dans iCloud Drive) vers des CSV simples, lisibles par une IA.

- Utilisateur : voir `GUIDE-INSTALLATION.md` (installation Windows : `INSTALLER.cmd`).
- Code : `sante_sync/` (`engine.py` orchestration et sources, `hae.py` lecture Health Auto Export, `apple_xml.py` export complet Apple, `store.py` CSV sans doublon, `docs.py` README/AGENTS du dossier de données).
- Tests : `uv venv .venv && uv pip install -e ".[dev]" && .venv/bin/python -m pytest`.
- Commandes : `python -m sante_sync configurer|collecte|historique|statut|docs|diagnostic|tester-notification`.
