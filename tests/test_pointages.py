from datetime import date, datetime, time, timedelta, timezone

import pytest

from app.models import Pointage
from app.services import parametres as P
from app.services.pointages import (
    ErreurMetier,
    apparier,
    construire_journees,
    etat_courant,
    ids_equipe,
    saisie_manuelle,
    syntheses,
)
from app.services.temps import aujourd_hui, local_vers_utc

DUREE_MAX = timedelta(hours=16)


def pt(type_, jour, h, m=0, **kw):
    return Pointage(type=type_, horodatage=local_vers_utc(jour, time(h, m)), source=kw.pop("source", "badge"),
                    zone_statut=kw.pop("zone", "dans_zone"), statut_validation=kw.pop("statut", "valide"), **kw)


def test_poste_de_nuit_rattache_au_jour_d_arrivee():
    j = date(2026, 3, 2)
    postes = apparier([pt("entree", j, 22), pt("sortie", j + timedelta(days=1), 6)], DUREE_MAX)
    assert len(postes) == 1
    assert postes[0].jour == j
    assert postes[0].duree == timedelta(hours=8)


def test_depart_manquant_et_arrivee_manquante():
    j = date(2026, 3, 2)
    postes = apparier([pt("entree", j, 8), pt("entree", j + timedelta(days=1), 8),
                       pt("sortie", j + timedelta(days=1), 17), pt("sortie", j + timedelta(days=2), 17)],
                      DUREE_MAX, maintenant=datetime(2026, 3, 10, tzinfo=timezone.utc))
    assert [(bool(p.entree), bool(p.sortie)) for p in postes] == [(True, False), (True, True), (False, True)]


def test_saisie_refusee_ignoree():
    j = date(2026, 3, 2)
    postes = apparier([pt("entree", j, 8), pt("sortie", j, 12, statut="refuse"), pt("sortie", j, 17)], DUREE_MAX)
    assert postes[0].duree == timedelta(hours=9)


def test_alertes_repos_et_duree():
    regles = {k.cle: k.defaut for k in P.DEFINITIONS}
    j = date(2026, 3, 2)
    postes = apparier([pt("entree", j, 6), pt("sortie", j, 18),
                       pt("entree", j + timedelta(days=1), 2), pt("sortie", j + timedelta(days=1), 10, zone="hors_zone")],
                      DUREE_MAX)
    journees = construire_journees(postes, regles)
    assert "duree_jour" in journees[j].alertes
    lendemain = journees[j + timedelta(days=1)]
    assert "repos" in lendemain.alertes and "hors_zone" in lendemain.alertes
    assert lendemain.repos_avant == timedelta(hours=8)


def test_perimetre_manager(db, donnees):
    chef, sal, sous = donnees["chef"], donnees["sal"], donnees["sous"]
    assert ids_equipe(db, chef) == {sal.id}
    assert ids_equipe(db, chef, niveaux=2) == {sal.id, sous.id}


def test_etat_et_limite_d_une_paire(db, donnees):
    sal = donnees["sal"]
    assert etat_courant(db, sal).prochain == "entree"
    maintenant = datetime.now(timezone.utc)
    db.add_all([Pointage(utilisateur_id=sal.id, type="entree", horodatage=maintenant - timedelta(minutes=2)),
                Pointage(utilisateur_id=sal.id, type="sortie", horodatage=maintenant - timedelta(minutes=1))])
    db.commit()
    if (maintenant - timedelta(minutes=2)).astimezone().date() == aujourd_hui():
        assert etat_courant(db, sal).prochain is None
        P.ecrire(db, "paires_max_par_jour", 2)
        db.commit()
        assert etat_courant(db, sal).prochain == "entree"


def test_saisie_manuelle_controles(db, donnees):
    sal = donnees["sal"]
    with pytest.raises(ErreurMetier):
        saisie_manuelle(db, sal, "entree", aujourd_hui() - timedelta(days=30), time(8), "oubli")
    with pytest.raises(ErreurMetier):
        saisie_manuelle(db, sal, "entree", aujourd_hui() - timedelta(days=1), time(8), "")
    p = saisie_manuelle(db, sal, "entree", aujourd_hui() - timedelta(days=1), time(8), "Téléphone déchargé")
    assert p.source == "manuel" and p.statut_validation == "valide" and p.zone_statut == "non_applicable"
    P.ecrire(db, "validation_manager", True)
    db.commit()
    p2 = saisie_manuelle(db, sal, "sortie", aujourd_hui() - timedelta(days=1), time(17), "Oubli")
    assert p2.statut_validation == "en_attente"


def test_synthese_contrat(db, donnees):
    sal = donnees["sal"]
    lundi = date(2026, 3, 2)
    for i in range(5):
        j = lundi + timedelta(days=i)
        db.add_all([Pointage(utilisateur_id=sal.id, type="entree", horodatage=local_vers_utc(j, time(9))),
                    Pointage(utilisateur_id=sal.id, type="sortie", horodatage=local_vers_utc(j, time(17)))])
    db.commit()
    s = syntheses(db, [sal], lundi, lundi + timedelta(days=6))[0]
    assert s.duree == timedelta(hours=40)
    assert s.duree_attendue == timedelta(hours=35)
    assert s.ecart == timedelta(hours=5)
    assert s.jours_travailles == 5
