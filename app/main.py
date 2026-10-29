import logging

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy import text

from app.db import SessionLocal
from app.routers import admin, auth, equipe, salarie
from app.security import AccesRefuse, ChangementMdpRequis, CsrfInvalide, NonConnecte
from app.templating import rendre

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")

app = FastAPI(title="Badgeage Proximy", docs_url=None, redoc_url=None, openapi_url=None)
app.mount("/static", StaticFiles(directory="app/static"), name="static")
app.include_router(auth.router)
app.include_router(salarie.router)
app.include_router(equipe.router)
app.include_router(admin.router)


def _attend_json(request: Request) -> bool:
    return request.url.path.startswith("/api/") or "application/json" in request.headers.get("accept", "")


@app.exception_handler(NonConnecte)
async def _non_connecte(request: Request, exc: NonConnecte):
    if _attend_json(request):
        return JSONResponse({"erreur": "Session expirée, reconnectez-vous."}, status_code=401)
    return RedirectResponse("/connexion", status_code=303)


@app.exception_handler(ChangementMdpRequis)
async def _changement_mdp(request: Request, exc: ChangementMdpRequis):
    if _attend_json(request):
        return JSONResponse({"erreur": "Vous devez changer votre mot de passe."}, status_code=403)
    return RedirectResponse("/mot-de-passe", status_code=303)


@app.exception_handler(AccesRefuse)
async def _acces_refuse(request: Request, exc: AccesRefuse):
    if _attend_json(request):
        return JSONResponse({"erreur": "Accès refusé."}, status_code=403)
    return rendre(request, "erreur.html", statut=403, code=403, titre="Cette page est réservée.",
                  message="Votre compte n'a pas accès à cette page. Si vous pensez que c'est une erreur, contactez votre administrateur.")


@app.exception_handler(CsrfInvalide)
async def _csrf(request: Request, exc: CsrfInvalide):
    if _attend_json(request):
        return JSONResponse({"erreur": "Jeton de sécurité invalide, rechargez la page."}, status_code=403)
    return rendre(request, "erreur.html", statut=403, titre="Le formulaire a expiré.", retour=True,
                  message="Par sécurité, le formulaire n'est plus valable. Revenez en arrière, rechargez la page puis recommencez.")


@app.exception_handler(404)
async def _introuvable(request: Request, exc):
    if _attend_json(request):
        return JSONResponse({"erreur": "Introuvable."}, status_code=404)
    return rendre(request, "erreur.html", statut=404, code=404, titre="Cette page a changé d'adresse.",
                  message="La page demandée n'existe pas ou n'est plus disponible. Repartez de l'accueil.")


@app.middleware("http")
async def entetes_securite(request: Request, call_next):
    reponse = await call_next(request)
    reponse.headers.setdefault("X-Content-Type-Options", "nosniff")
    reponse.headers.setdefault("Referrer-Policy", "same-origin")
    reponse.headers.setdefault("X-Frame-Options", "DENY")
    # La géolocalisation n'est autorisée que pour l'application elle-même.
    reponse.headers.setdefault("Permissions-Policy", "geolocation=(self), camera=(), microphone=()")
    if not request.url.path.startswith("/static/"):
        reponse.headers.setdefault("Cache-Control", "no-store")
    return reponse


@app.get("/sante", include_in_schema=False)
def sante():
    with SessionLocal() as db:
        db.execute(text("SELECT 1"))
    return {"statut": "ok"}
