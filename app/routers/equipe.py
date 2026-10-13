"""Suivi des badgeages : managers (leur équipe), RH et administrateurs (vue globale)."""
from datetime import date, time

from fastapi import APIRouter, Depends, Form, HTTPException, Request
from fastapi.responses import StreamingResponse
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db import get_db
from app.models import Etablissement, Pointage, Utilisateur
from app.security import AccesRefuse, utilisateur_connecte, verifier_csrf
from app.services import parametres as P
from app.services.export import exporter_excel
from app.services.pointages import (
    ErreurMetier,
    ajout_par_responsable,
    ids_equipe,
    journees_en_liste,
    modifier_pointage,
    peut_corriger,
    peut_valider,
    peut_voir,
    supprimer_pointage,
    syntheses,
    valider_saisie,
)
from app.services.temps import aujourd_hui
from app.templating import PERIODES, mois_entre, periode, rediriger, rendre

router = APIRouter()


def _perimetre(db: Session, u: Utilisateur, etablissement: int | None, manager: int | None,
               q: str | None, inclure_inactifs: bool = False) -> list[Utilisateur]:
    requete = select(Utilisateur).order_by(Utilisateur.nom, Utilisateur.prenom)
    if not u.vue_globale:
        ids = ids_equipe(db, u)
        if not ids:
            raise AccesRefuse()
        requete = requete.where(Utilisateur.id.in_(ids))
    if not inclure_inactifs:
        requete = requete.where(Utilisateur.actif.is_(True))
    if etablissement:
        requete = requete.where(Utilisateur.etablissement_id == etablissement)
    if manager:
        requete = requete.where(Utilisateur.manager_id == manager)
    if q:
        motif = f"%{q.strip()}%"
        requete = requete.where(Utilisateur.nom.ilike(motif) | Utilisateur.prenom.ilike(motif)
                                | Utilisateur.matricule.ilike(motif))
    return list(db.scalars(requete))


def _filtres(request: Request) -> dict:
    qp = request.query_params

    def entier(cle):
        v = qp.get(cle)
        return int(v) if v and v.isdigit() else None

    code, debut, fin = periode(qp.get("periode"), qp.get("debut"), qp.get("fin"))
    return {"periode": code, "debut": debut, "fin": fin, "etablissement": entier("etablissement"),
            "manager": entier("manager"), "q": qp.get("q") or "", "alertes": qp.get("alertes") == "1"}


@router.get("/equipe")
def suivi(request: Request, u: Utilisateur = Depends(utilisateur_connecte), db: Session = Depends(get_db)):
    f = _filtres(request)
    utilisateurs = _perimetre(db, u, f["etablissement"], f["manager"], f["q"])
    lignes = syntheses(db, utilisateurs, f["debut"], f["fin"])
    if f["alertes"]:
        lignes = [s for s in lignes if s.nb_alertes_graves]
    mois = mois_entre(f["debut"], f["fin"])
    managers = db.scalars(
        select(Utilisateur).where(Utilisateur.id.in_(select(Utilisateur.manager_id).where(
            Utilisateur.manager_id.is_not(None)))).order_by(Utilisateur.nom)).all() if u.vue_globale else []
    en_attente = _saisies_en_attente(db, u) if P.lire(db, "validation_manager") else []
    return rendre(request, "equipe/suivi.html", f=f, lignes=lignes, mois=mois if len(mois) > 1 else [],
                  PERIODES=PERIODES, managers=managers, nb_en_attente=len(en_attente),
                  etablissements=db.scalars(select(Etablissement).order_by(Etablissement.nom)).all(),
                  requete=request.url.query)


@router.get("/equipe/export.xlsx")
def export(request: Request, u: Utilisateur = Depends(utilisateur_connecte), db: Session = Depends(get_db)):
    f = _filtres(request)
    lignes = syntheses(db, _perimetre(db, u, f["etablissement"], f["manager"], f["q"]), f["debut"], f["fin"])
    if f["alertes"]:
        lignes = [s for s in lignes if s.nb_alertes_graves]
    flux = exporter_excel(lignes, f["debut"], f["fin"], mois_entre(f["debut"], f["fin"]))
    nom = f"badgeages_{f['debut']:%Y%m%d}_{f['fin']:%Y%m%d}.xlsx"
    return StreamingResponse(flux, media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                             headers={"Content-Disposition": f'attachment; filename="{nom}"'})


def _cible(db: Session, u: Utilisateur, uid: int) -> Utilisateur:
    cible = db.get(Utilisateur, uid)
    if cible is None:
        raise HTTPException(404)
    if not peut_voir(db, u, cible):
        raise AccesRefuse()
    return cible


@router.get("/equipe/{uid}")
def detail(uid: int, request: Request, u: Utilisateur = Depends(utilisateur_connecte),
           db: Session = Depends(get_db)):
    cible = _cible(db, u, uid)
    f = _filtres(request)
    s = syntheses(db, [cible], f["debut"], f["fin"])[0]
    return rendre(request, "equipe/detail.html", cible=cible, s=s, f=f, jours=journees_en_liste(s),
                  PERIODES=PERIODES, corriger=peut_corriger(db, u, cible), valider=peut_valider(db, u, cible),
                  retour=request.url.query, aujourdhui=aujourd_hui().isoformat())


def _pointage(db: Session, u: Utilisateur, pid: int, droit) -> Pointage:
    p = db.get(Pointage, pid)
    if p is None:
        raise HTTPException(404)
    if not droit(db, u, p.utilisateur):
        raise AccesRefuse()
    return p


def _retour(uid: int, retour: str) -> str:
    return f"/equipe/{uid}" + (f"?{retour}" if retour else "")


@router.post("/equipe/{uid}/ajout", dependencies=[Depends(verifier_csrf)])
def ajout(uid: int, type: str = Form(...), jour: date = Form(...), heure: time = Form(...),
          motif: str = Form(""), retour: str = Form(""), u: Utilisateur = Depends(utilisateur_connecte),
          db: Session = Depends(get_db)):
    cible = _cible(db, u, uid)
    if not peut_corriger(db, u, cible):
        raise AccesRefuse()
    try:
        ajout_par_responsable(db, u, cible, type, jour, heure, motif)
    except ErreurMetier as e:
        return rediriger(_retour(uid, retour), str(e), "erreur")
    return rediriger(_retour(uid, retour), "Badgeage ajouté.")


@router.post("/pointages/{pid}/modifier", dependencies=[Depends(verifier_csrf)])
def modifier(pid: int, type: str = Form(...), jour: date = Form(...), heure: time = Form(...),
             motif: str = Form(""), retour: str = Form(""), u: Utilisateur = Depends(utilisateur_connecte),
             db: Session = Depends(get_db)):
    p = _pointage(db, u, pid, peut_corriger)
    try:
        modifier_pointage(db, u, p, type, jour, heure, motif)
    except ErreurMetier as e:
        return rediriger(_retour(p.utilisateur_id, retour), str(e), "erreur")
    return rediriger(_retour(p.utilisateur_id, retour), "Badgeage corrigé.")


@router.post("/pointages/{pid}/supprimer", dependencies=[Depends(verifier_csrf)])
def supprimer(pid: int, motif: str = Form(""), retour: str = Form(""),
              u: Utilisateur = Depends(utilisateur_connecte), db: Session = Depends(get_db)):
    p = _pointage(db, u, pid, peut_corriger)
    uid = p.utilisateur_id
    try:
        supprimer_pointage(db, u, p, motif)
    except ErreurMetier as e:
        return rediriger(_retour(uid, retour), str(e), "erreur")
    return rediriger(_retour(uid, retour), "Badgeage supprimé.")


def _saisies_en_attente(db: Session, u: Utilisateur) -> list[Pointage]:
    requete = select(Pointage).where(Pointage.statut_validation == "en_attente").order_by(Pointage.horodatage)
    if not u.est_admin:
        ids = ids_equipe(db, u)
        if not ids:
            return []
        requete = requete.where(Pointage.utilisateur_id.in_(ids))
    return list(db.scalars(requete))


@router.get("/validations")
def validations(request: Request, u: Utilisateur = Depends(utilisateur_connecte), db: Session = Depends(get_db)):
    return rendre(request, "equipe/validations.html", saisies=_saisies_en_attente(db, u),
                  actif=P.lire(db, "validation_manager"))


@router.post("/pointages/{pid}/valider", dependencies=[Depends(verifier_csrf)])
def valider(pid: int, decision: str = Form(...), commentaire: str = Form(""), retour: str = Form("/validations"),
            u: Utilisateur = Depends(utilisateur_connecte), db: Session = Depends(get_db)):
    p = _pointage(db, u, pid, peut_valider)
    cible = retour if retour.startswith("/") and not retour.startswith("//") else "/validations"
    try:
        valider_saisie(db, u, p, decision == "valider", commentaire)
    except ErreurMetier as e:
        return rediriger(cible, str(e), "erreur")
    return rediriger(cible, "Saisie validée." if decision == "valider" else "Saisie refusée.")
