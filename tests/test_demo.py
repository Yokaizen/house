from datetime import timedelta

from app import demo
from app.models import Etablissement, Pointage, Utilisateur
from app.services.pointages import syntheses
from app.services.temps import aujourd_hui


def test_refuse_sans_variable_demo(monkeypatch, db):
    monkeypatch.delenv("DEMO", raising=False)
    assert demo.main([]) == 1
    assert db.query(Utilisateur).count() == 0


def test_chargement_idempotent_et_reinitialisation(monkeypatch, db):
    monkeypatch.setenv("DEMO", "1")
    assert demo.main([]) == 0
    n = db.query(Pointage).count()
    assert db.query(Utilisateur).count() == 7 and db.query(Etablissement).count() == 6 and n > 100
    assert demo.main([]) == 0  # deuxième lancement : rien ne change
    assert db.query(Pointage).count() == n
    assert demo.main(["--forcer"]) == 0
    db.expire_all()
    assert db.query(Utilisateur).count() == 7 and db.query(Pointage).count() == n


def test_cas_de_demonstration_presents(monkeypatch, db):
    monkeypatch.setenv("DEMO", "1")
    demo.main([])
    u = {x.matricule: x for x in db.query(Utilisateur)}
    fin = aujourd_hui() - timedelta(days=1)
    s = {x.utilisateur.matricule: x for x in syntheses(db, list(u.values()), fin - timedelta(days=41), fin)}
    assert s["S001"].compte_alertes().get("hors_zone") and s["S001"].compte_alertes().get("manuel")
    assert s["S003"].compte_alertes().get("sortie_manquante") and s["S003"].compte_alertes().get("duree_jour")
    assert s["S004"].compte_alertes().get("indisponible")
    assert s["S002"].compte_alertes().get("indetermine")
    # Aucun badgeage aujourd'hui : chacun peut badger pendant le test.
    assert all(p.horodatage.date() < aujourd_hui() for p in db.query(Pointage) if p.type == "entree")
    assert u["S001"].manager_id == u["M001"].id and u["S004"].manager_id is None
