from fastapi import APIRouter, Depends, Form, Request
from sqlalchemy.orm import Session

from app.config import get_settings
from app.db import get_db
from app.models import Utilisateur
from app.security import (
    COOKIE,
    authentifier,
    erreurs_mdp,
    fermer_session,
    fermer_toutes_sessions,
    hacher,
    ouvrir_session,
    session_courante,
    utilisateur_connecte_sans_mdp,
    utilisateur_optionnel,
    verifier_csrf,
    verifier_mdp,
)
from app.services.audit import journaliser
from app.templating import rediriger, rendre

router = APIRouter()


@router.get("/connexion")
def page_connexion(request: Request, u: Utilisateur | None = Depends(utilisateur_optionnel)):
    if u:
        return rediriger("/")
    return rendre(request, "connexion.html")


@router.post("/connexion")
def connexion(
    request: Request,
    identifiant: str = Form(...),
    mot_de_passe: str = Form(...),
    rester_connecte: str | None = Form(None),
    db: Session = Depends(get_db),
):
    u, erreur = authentifier(db, identifiant, mot_de_passe)
    if u is None:
        return rendre(request, "connexion.html", statut=400, erreur=erreur, identifiant=identifiant)
    token, max_age = ouvrir_session(db, u, request.headers.get("user-agent"), longue=bool(rester_connecte))
    r = rediriger("/mot-de-passe" if u.doit_changer_mdp else "/")
    r.set_cookie(COOKIE, token, max_age=max_age, httponly=True, secure=get_settings().cookie_secure,
                 samesite="lax", path="/")
    return r


@router.post("/deconnexion", dependencies=[Depends(verifier_csrf)])
def deconnexion(request: Request, db: Session = Depends(get_db)):
    fermer_session(db, request.cookies.get(COOKIE))
    r = rediriger("/connexion")
    r.delete_cookie(COOKIE, path="/")
    return r


@router.get("/mot-de-passe")
def page_mdp(request: Request, u: Utilisateur = Depends(utilisateur_connecte_sans_mdp)):
    return rendre(request, "mot_de_passe.html", impose=u.doit_changer_mdp)


@router.post("/mot-de-passe", dependencies=[Depends(verifier_csrf)])
def changer_mdp(
    request: Request,
    actuel: str = Form(...),
    nouveau: str = Form(...),
    confirmation: str = Form(...),
    u: Utilisateur = Depends(utilisateur_connecte_sans_mdp),
    db: Session = Depends(get_db),
):
    erreurs = []
    if not verifier_mdp(u.mot_de_passe_hash, actuel):
        erreurs.append("Le mot de passe actuel est incorrect.")
    if nouveau != confirmation:
        erreurs.append("La confirmation ne correspond pas.")
    if nouveau == actuel:
        erreurs.append("Le nouveau mot de passe doit être différent de l'actuel.")
    if (e := erreurs_mdp(nouveau)):
        erreurs.append("Le mot de passe doit contenir " + " et ".join(e) + ".")
    if erreurs:
        return rendre(request, "mot_de_passe.html", statut=400, erreurs=erreurs, impose=u.doit_changer_mdp)
    u = db.merge(u)
    u.mot_de_passe_hash = hacher(nouveau)
    u.doit_changer_mdp = False
    sess = session_courante(request, db)
    fermer_toutes_sessions(db, u.id, sauf=sess.id if sess else None)
    journaliser(db, u, "changement_mdp", "utilisateur", u.id, None, None)
    db.commit()
    return rediriger("/", "Mot de passe modifié.")
