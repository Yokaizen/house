from datetime import date, time

from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.db import get_db
from app.models import Utilisateur
from app.security import utilisateur_connecte, verifier_csrf
from app.services import parametres as P
from app.services.pointages import (
    ErreurMetier,
    badger,
    detecter_appareil,
    etat_courant,
    journees_en_liste,
    lieux_autorises,
    saisie_manuelle,
    syntheses,
)
from app.services.temps import aujourd_hui, fin_de_mois, format_heure_fr, ajouter_mois
from app.templating import rediriger, rendre

router = APIRouter()


@router.get("/")
def accueil(request: Request, u: Utilisateur = Depends(utilisateur_connecte), db: Session = Depends(get_db)):
    regles = P.tous(db)
    etat = etat_courant(db, u, regles)
    j = aujourd_hui()
    s = syntheses(db, [u], j, j)[0]
    return rendre(request, "salarie/badger.html", etat=etat, journee=s.journees.get(j),
                  sans_lieu=not lieux_autorises(db, u, regles))


class DemandeBadge(BaseModel):
    type: str = Field(pattern="^(entree|sortie)$")
    latitude: float | None = None
    longitude: float | None = None
    precision: float | None = Field(default=None, ge=0)
    appareil: str | None = None


@router.post("/api/badger", dependencies=[Depends(verifier_csrf)])
def api_badger(
    demande: DemandeBadge,
    request: Request,
    u: Utilisateur = Depends(utilisateur_connecte),
    db: Session = Depends(get_db),
):
    appareil = detecter_appareil(demande.appareil, request.headers.get("user-agent"))
    try:
        p = badger(db, u, demande.type, demande.latitude, demande.longitude, demande.precision, appareil)
    except ErreurMetier as e:
        return JSONResponse({"erreur": str(e)}, status_code=409)
    # La position reçue n'est ni stockée ni renvoyée : seul le résultat l'est.
    return {"type": p.type, "heure": format_heure_fr(p.horodatage), "zone": p.zone_statut}


@router.get("/mes-badgeages")
def mes_badgeages(request: Request, mois: str | None = None, u: Utilisateur = Depends(utilisateur_connecte),
                  db: Session = Depends(get_db)):
    j = aujourd_hui()
    try:
        annee, m = (int(x) for x in (mois or "").split("-"))
        date(annee, m, 1)
    except ValueError:
        annee, m = j.year, j.month
    debut, fin = date(annee, m, 1), fin_de_mois(annee, m)
    s = syntheses(db, [u], debut, fin)[0]
    prec, suiv = ajouter_mois(annee, m, -1), ajouter_mois(annee, m, 1)
    return rendre(request, "salarie/historique.html", s=s, jours=journees_en_liste(s), annee=annee, mois=m,
                  prec=f"{prec[0]}-{prec[1]:02d}",
                  suiv=f"{suiv[0]}-{suiv[1]:02d}" if date(*suiv, 1) <= j else None)


@router.get("/oubli")
def page_oubli(request: Request, u: Utilisateur = Depends(utilisateur_connecte), db: Session = Depends(get_db)):
    return rendre(request, "salarie/oubli.html", jours_max=P.lire(db, "saisie_manuelle_jours_max"),
                  validation=P.lire(db, "validation_manager"), aujourdhui=aujourd_hui().isoformat())


@router.post("/oubli", dependencies=[Depends(verifier_csrf)])
def oubli(
    request: Request,
    type: str = Form(...),
    jour: date = Form(...),
    heure: time = Form(...),
    motif: str = Form(""),
    u: Utilisateur = Depends(utilisateur_connecte),
    db: Session = Depends(get_db),
):
    try:
        p = saisie_manuelle(db, u, type, jour, heure, motif)
    except ErreurMetier as e:
        return rendre(request, "salarie/oubli.html", statut=400, erreur=str(e),
                      jours_max=P.lire(db, "saisie_manuelle_jours_max"), validation=P.lire(db, "validation_manager"),
                      aujourdhui=aujourd_hui().isoformat(), valeurs={"type": type, "jour": jour, "heure": heure,
                                                                     "motif": motif})
    msg = "Saisie enregistrée" + (" : elle sera visible après validation par votre manager."
                                  if p.statut_validation == "en_attente" else ".")
    return rediriger(f"/mes-badgeages?mois={jour:%Y-%m}", msg)


@router.get("/confidentialite")
def confidentialite(request: Request, db: Session = Depends(get_db),
                    u: Utilisateur = Depends(utilisateur_connecte)):
    return rendre(request, "salarie/confidentialite.html", regles=P.tous(db))
