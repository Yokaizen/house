"""Administration : utilisateurs, import CSV, établissements, paramètres, journal d'audit."""
from datetime import date
from decimal import Decimal, InvalidOperation

from fastapi import APIRouter, Depends, File, Form, HTTPException, Request, UploadFile
from fastapi.responses import Response
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.db import get_db
from app.models import ROLES, Audit, Etablissement, Utilisateur
from app.security import exiger_admin, fermer_toutes_sessions, hacher, mdp_temporaire, verifier_csrf
from app.services import parametres as P
from app.services.audit import instantane, journaliser
from app.services.geocodage import adresse_texte, geocoder
from app.services.import_csv import COLONNES, _cree_un_cycle, importer, modele_csv
from app.templating import rediriger, rendre

router = APIRouter(prefix="/admin")
TAILLE_MAX_CSV = 2 * 1024 * 1024


# ---------------------------------------------------------------------------
# Utilisateurs
# ---------------------------------------------------------------------------

@router.get("/utilisateurs")
def liste_utilisateurs(request: Request, q: str = "", etablissement: str = "", role: str = "", statut: str = "actifs",
                       u: Utilisateur = Depends(exiger_admin), db: Session = Depends(get_db)):
    requete = select(Utilisateur).order_by(Utilisateur.nom, Utilisateur.prenom)
    if q.strip():
        m = f"%{q.strip()}%"
        requete = requete.where(or_(Utilisateur.nom.ilike(m), Utilisateur.prenom.ilike(m),
                                    Utilisateur.matricule.ilike(m), Utilisateur.email.ilike(m)))
    if etablissement.isdigit():
        requete = requete.where(Utilisateur.etablissement_id == int(etablissement))
    if role in ROLES:
        requete = requete.where(Utilisateur.role == role)
    if statut == "actifs":
        requete = requete.where(Utilisateur.actif.is_(True))
    elif statut == "inactifs":
        requete = requete.where(Utilisateur.actif.is_(False))
    utilisateurs = db.scalars(requete).all()
    return rendre(request, "admin/utilisateurs.html", utilisateurs=utilisateurs, ROLES=ROLES,
                  etablissements=db.scalars(select(Etablissement).order_by(Etablissement.nom)).all(),
                  f={"q": q, "etablissement": etablissement, "role": role, "statut": statut})


def _contexte_formulaire(db: Session) -> dict:
    return {
        "ROLES": ROLES,
        "etablissements": db.scalars(select(Etablissement).order_by(Etablissement.nom)).all(),
        "managers": db.scalars(select(Utilisateur).where(Utilisateur.actif.is_(True))
                               .order_by(Utilisateur.nom, Utilisateur.prenom)).all(),
        "rayon_defaut": P.lire(db, "rayon_defaut_m"),
    }


@router.get("/utilisateurs/nouveau")
def nouvel_utilisateur(request: Request, u: Utilisateur = Depends(exiger_admin), db: Session = Depends(get_db)):
    return rendre(request, "admin/utilisateur.html", cible=None, **_contexte_formulaire(db))


@router.get("/utilisateurs/{uid}")
def fiche_utilisateur(uid: int, request: Request, u: Utilisateur = Depends(exiger_admin),
                      db: Session = Depends(get_db)):
    cible = db.get(Utilisateur, uid)
    if cible is None:
        raise HTTPException(404)
    return rendre(request, "admin/utilisateur.html", cible=cible, **_contexte_formulaire(db))


def _texte(form, cle: str) -> str | None:
    v = (form.get(cle) or "").strip()
    return v or None


def _flottant(form, cle: str) -> float | None:
    v = (form.get(cle) or "").strip().replace(",", ".")
    return float(v) if v else None


@router.post("/utilisateurs/enregistrer", dependencies=[Depends(verifier_csrf)])
async def enregistrer_utilisateur(request: Request, u: Utilisateur = Depends(exiger_admin),
                                  db: Session = Depends(get_db)):
    form = await request.form()
    uid = form.get("id")
    cible = db.get(Utilisateur, int(uid)) if uid and str(uid).isdigit() else None
    nouveau = cible is None
    erreurs: list[str] = []

    matricule, nom, prenom = _texte(form, "matricule"), _texte(form, "nom"), _texte(form, "prenom")
    if not (matricule and nom and prenom):
        erreurs.append("Matricule, nom et prénom sont obligatoires.")
    email = (_texte(form, "email") or "").lower() or None
    role = form.get("role") if form.get("role") in ROLES else "salarie"
    if matricule:
        q = select(Utilisateur).where(Utilisateur.matricule == matricule)
        if cible:
            q = q.where(Utilisateur.id != cible.id)
        if db.scalar(q):
            erreurs.append(f"Le matricule {matricule} est déjà utilisé.")
    if email:
        q = select(Utilisateur).where(func.lower(Utilisateur.email) == email)
        if cible:
            q = q.where(Utilisateur.id != cible.id)
        if db.scalar(q):
            erreurs.append(f"L'e-mail {email} est déjà utilisé.")
    try:
        heures = Decimal((form.get("heures_hebdo") or "35").replace(",", "."))
        if not 0 < heures <= 60:
            raise InvalidOperation
    except InvalidOperation:
        erreurs.append("Le contrat hebdomadaire doit être un nombre d'heures entre 0 et 60.")
        heures = Decimal("35")
    try:
        lat, lon = _flottant(form, "domicile_lat"), _flottant(form, "domicile_lon")
        rayon = int(form.get("domicile_rayon_m")) if (form.get("domicile_rayon_m") or "").strip() else None
    except ValueError:
        erreurs.append("Coordonnées ou rayon du domicile invalides.")
        lat = lon = rayon = None
    try:
        date_sortie = date.fromisoformat(form["date_sortie"]) if form.get("date_sortie") else None
    except ValueError:
        erreurs.append("Date de sortie invalide.")
        date_sortie = None
    manager_id = int(form["manager_id"]) if (form.get("manager_id") or "").isdigit() else None
    if manager_id and cible and (manager_id == cible.id or _cree_un_cycle(db, cible.id, db.get(Utilisateur, manager_id))):
        erreurs.append("Ce lien hiérarchique créerait une boucle.")
    if cible and cible.id == u.id and (role != "admin" or form.get("actif") != "on"):
        erreurs.append("Vous ne pouvez pas retirer vos propres droits d'administrateur ni désactiver votre compte.")

    if erreurs:
        return rendre(request, "admin/utilisateur.html", statut=400, cible=cible, erreurs=erreurs,
                      valeurs=dict(form), **_contexte_formulaire(db))

    avant = None if nouveau else instantane(cible)
    mdp = None
    if nouveau:
        mdp = mdp_temporaire()
        cible = Utilisateur(mot_de_passe_hash=hacher(mdp), doit_changer_mdp=True)
        db.add(cible)
    cible.matricule, cible.nom, cible.prenom, cible.email, cible.role = matricule, nom, prenom, email, role
    cible.etablissement_id = int(form["etablissement_id"]) if (form.get("etablissement_id") or "").isdigit() else None
    cible.manager_id = manager_id
    cible.heures_hebdo = heures
    cible.teletravail_autorise = form.get("teletravail_autorise") == "on"
    for c in ("adresse_numero", "adresse_voie", "adresse_complement", "code_postal", "ville"):
        setattr(cible, c, _texte(form, c))
    cible.domicile_lat, cible.domicile_lon, cible.domicile_rayon_m = lat, lon, rayon
    cible.date_sortie = date_sortie
    etait_actif = cible.actif if not nouveau else True
    cible.actif = form.get("actif") == "on"
    message = "Utilisateur enregistré."
    if cible.adresse_voie and cible.ville and not cible.domicile_localise:
        r = geocoder(adresse_texte(cible.adresse_numero, cible.adresse_voie, cible.code_postal, cible.ville),
                     cible.code_postal)
        if r:
            cible.domicile_lat, cible.domicile_lon = r.latitude, r.longitude
        else:
            message += " Adresse non localisée : placez le domicile sur la carte."
    db.flush()
    if etait_actif and not cible.actif:
        fermer_toutes_sessions(db, cible.id)
    journaliser(db, u, "creation_utilisateur" if nouveau else "modification_utilisateur", "utilisateur",
                cible.id, avant, instantane(cible))
    db.commit()
    if mdp:
        return rendre(request, "admin/mot_de_passe_provisoire.html", cible=cible, mdp=mdp)
    return rediriger(f"/admin/utilisateurs/{cible.id}", message)


@router.post("/utilisateurs/{uid}/reinitialiser", dependencies=[Depends(verifier_csrf)])
def reinitialiser_mdp(uid: int, request: Request, u: Utilisateur = Depends(exiger_admin),
                      db: Session = Depends(get_db)):
    cible = db.get(Utilisateur, uid)
    if cible is None:
        raise HTTPException(404)
    mdp = mdp_temporaire()
    cible.mot_de_passe_hash = hacher(mdp)
    cible.doit_changer_mdp = True
    cible.echecs_connexion, cible.bloque_jusqu_a = 0, None
    fermer_toutes_sessions(db, cible.id)
    journaliser(db, u, "reinitialisation_mdp", "utilisateur", cible.id, None, None)
    db.commit()
    return rendre(request, "admin/mot_de_passe_provisoire.html", cible=cible, mdp=mdp)


@router.post("/utilisateurs/{uid}/supprimer", dependencies=[Depends(verifier_csrf)])
def supprimer_utilisateur(uid: int, confirmation: str = Form(""), u: Utilisateur = Depends(exiger_admin),
                          db: Session = Depends(get_db)):
    cible = db.get(Utilisateur, uid)
    if cible is None:
        raise HTTPException(404)
    if cible.id == u.id:
        return rediriger(f"/admin/utilisateurs/{uid}", "Vous ne pouvez pas supprimer votre propre compte.", "erreur")
    if confirmation.strip() != cible.matricule:
        return rediriger(f"/admin/utilisateurs/{uid}", "Recopiez le matricule pour confirmer la suppression.",
                         "erreur")
    journaliser(db, u, "suppression_utilisateur", "utilisateur", cible.id,
                {"matricule": cible.matricule, "nom": cible.nom_complet}, None)
    db.query(Utilisateur).filter(Utilisateur.manager_id == cible.id).update({"manager_id": None})
    db.delete(cible)
    db.commit()
    return rediriger("/admin/utilisateurs", "Utilisateur et badgeages supprimés définitivement.")


@router.get("/api/geocoder")
def api_geocoder(adresse: str, code_postal: str = "", u: Utilisateur = Depends(exiger_admin)):
    r = geocoder(adresse, code_postal or None)
    if r is None:
        return {"trouve": False}
    return {"trouve": True, "latitude": r.latitude, "longitude": r.longitude, "libelle": r.libelle,
            "score": r.score}


# ---------------------------------------------------------------------------
# Import CSV
# ---------------------------------------------------------------------------

@router.get("/import")
def page_import(request: Request, u: Utilisateur = Depends(exiger_admin)):
    return rendre(request, "admin/import.html", colonnes=COLONNES)


@router.get("/import/modele.csv")
def telecharger_modele(u: Utilisateur = Depends(exiger_admin)):
    return Response("﻿" + modele_csv(), media_type="text/csv; charset=utf-8",
                    headers={"Content-Disposition": 'attachment; filename="modele_import_utilisateurs.csv"'})


@router.post("/import", dependencies=[Depends(verifier_csrf)])
async def importer_csv(request: Request, fichier: UploadFile = File(...), geocoder_adresses: str | None = Form(None),
                       u: Utilisateur = Depends(exiger_admin), db: Session = Depends(get_db)):
    contenu = await fichier.read(TAILLE_MAX_CSV + 1)
    if len(contenu) > TAILLE_MAX_CSV:
        return rendre(request, "admin/import.html", statut=400, colonnes=COLONNES,
                      erreur="Fichier trop volumineux (2 Mo maximum).")
    rapport = importer(db, contenu, u, geocoder_adresses=bool(geocoder_adresses))
    return rendre(request, "admin/import.html", colonnes=COLONNES, rapport=rapport)


# ---------------------------------------------------------------------------
# Établissements
# ---------------------------------------------------------------------------

@router.get("/etablissements")
def liste_etablissements(request: Request, u: Utilisateur = Depends(exiger_admin), db: Session = Depends(get_db)):
    etabs = db.scalars(select(Etablissement).order_by(Etablissement.nom)).all()
    effectifs = dict(db.execute(select(Utilisateur.etablissement_id, func.count()).where(
        Utilisateur.actif.is_(True)).group_by(Utilisateur.etablissement_id)).all())
    return rendre(request, "admin/etablissements.html", etablissements=etabs, effectifs=effectifs)


@router.get("/etablissements/{eid}")
def fiche_etablissement(eid: str, request: Request, u: Utilisateur = Depends(exiger_admin),
                        db: Session = Depends(get_db)):
    etab = None
    if eid != "nouveau":
        etab = db.get(Etablissement, int(eid)) if eid.isdigit() else None
        if etab is None:
            raise HTTPException(404)
    return rendre(request, "admin/etablissement.html", etab=etab, rayon_defaut=P.lire(db, "rayon_defaut_m"))


@router.post("/etablissements/enregistrer", dependencies=[Depends(verifier_csrf)])
async def enregistrer_etablissement(request: Request, u: Utilisateur = Depends(exiger_admin),
                                    db: Session = Depends(get_db)):
    form = await request.form()
    eid = form.get("id")
    etab = db.get(Etablissement, int(eid)) if eid and str(eid).isdigit() else None
    erreurs = []
    code, nom = (_texte(form, "code") or "").upper(), _texte(form, "nom")
    if not code or not nom:
        erreurs.append("Le code et le nom sont obligatoires.")
    q = select(Etablissement).where(Etablissement.code == code)
    if etab:
        q = q.where(Etablissement.id != etab.id)
    if code and db.scalar(q):
        erreurs.append(f"Le code {code} est déjà utilisé.")
    try:
        lat, lon = _flottant(form, "latitude"), _flottant(form, "longitude")
        rayon = int(form.get("rayon_m") or P.lire(db, "rayon_defaut_m"))
        if not 20 <= rayon <= 5000:
            erreurs.append("Le rayon doit être compris entre 20 et 5 000 m.")
    except ValueError:
        erreurs.append("Coordonnées ou rayon invalides.")
        lat = lon = None
        rayon = 100
    if erreurs:
        return rendre(request, "admin/etablissement.html", statut=400, etab=etab, erreurs=erreurs,
                      valeurs=dict(form), rayon_defaut=P.lire(db, "rayon_defaut_m"))
    nouveau = etab is None
    avant = None if nouveau else instantane(etab)
    if nouveau:
        etab = Etablissement()
        db.add(etab)
    etab.code, etab.nom = code, nom
    for c in ("adresse_numero", "adresse_voie", "adresse_complement", "code_postal", "ville"):
        setattr(etab, c, _texte(form, c))
    etab.latitude, etab.longitude, etab.rayon_m = lat, lon, rayon
    etab.actif = form.get("actif") == "on"
    message = "Établissement enregistré."
    if not etab.localise and etab.adresse_voie and etab.ville:
        r = geocoder(adresse_texte(etab.adresse_numero, etab.adresse_voie, etab.code_postal, etab.ville),
                     etab.code_postal)
        if r:
            etab.latitude, etab.longitude = r.latitude, r.longitude
        else:
            message += " Adresse non localisée : placez l'établissement sur la carte."
    db.flush()
    journaliser(db, u, "creation_etablissement" if nouveau else "modification_etablissement", "etablissement",
                etab.id, avant, instantane(etab))
    db.commit()
    return rediriger(f"/admin/etablissements/{etab.id}", message)


# ---------------------------------------------------------------------------
# Paramètres et audit
# ---------------------------------------------------------------------------

@router.get("/parametres")
def page_parametres(request: Request, u: Utilisateur = Depends(exiger_admin), db: Session = Depends(get_db)):
    return rendre(request, "admin/parametres.html", groupes=P.groupes(), valeurs=P.tous(db))


@router.post("/parametres", dependencies=[Depends(verifier_csrf)])
async def enregistrer_parametres(request: Request, u: Utilisateur = Depends(exiger_admin),
                                 db: Session = Depends(get_db)):
    form = await request.form()
    avant = P.tous(db)
    nouvelles, erreurs = {}, []
    for d in P.DEFINITIONS:
        try:
            nouvelles[d.cle] = P.convertir(d.cle, form.get(d.cle))
        except ValueError as e:
            erreurs.append(str(e) if d.libelle in str(e) else f"{d.libelle} : valeur invalide")
    if erreurs:
        return rendre(request, "admin/parametres.html", statut=400, groupes=P.groupes(),
                      valeurs={**avant, **{k: form.get(k) for k in avant if k not in nouvelles}}, erreurs=erreurs)
    for cle, v in nouvelles.items():
        P.ecrire(db, cle, v)
    modifies = {k: v for k, v in nouvelles.items() if avant.get(k) != v}
    if modifies:
        journaliser(db, u, "modification_parametres", "parametres", None,
                    {k: avant[k] for k in modifies}, modifies)
    db.commit()
    return rediriger("/admin/parametres", "Paramètres enregistrés.")


@router.get("/audit")
def journal_audit(request: Request, page: int = 1, action: str = "", u: Utilisateur = Depends(exiger_admin),
                  db: Session = Depends(get_db)):
    par_page = 50
    requete = select(Audit).order_by(Audit.horodatage.desc())
    if action:
        requete = requete.where(Audit.action == action)
    entrees = db.scalars(requete.offset((max(page, 1) - 1) * par_page).limit(par_page + 1)).all()
    actions = db.scalars(select(Audit.action).distinct().order_by(Audit.action)).all()
    noms = {x.id: x for x in db.scalars(select(Utilisateur).where(
        Utilisateur.id.in_({e.cible_id for e in entrees if e.cible_type == "utilisateur" and e.cible_id})))}
    return rendre(request, "admin/audit.html", entrees=entrees[:par_page], page=max(page, 1),
                  suivante=len(entrees) > par_page, actions=actions, action=action, noms=noms)
