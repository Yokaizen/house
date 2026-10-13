from datetime import date, timedelta
from urllib.parse import quote, unquote

from fastapi import Request
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy import select

from app.config import get_settings
from app.db import SessionLocal
from app.models import ROLE_LIBELLES, ZONE_LIBELLES, Utilisateur
from app.services.pointages import ALERTES, ALERTES_GRAVES
from app.services.temps import (
    MOIS,
    MOIS_COURTS,
    aujourd_hui,
    format_date,
    format_duree,
    format_heure,
    libelle_mois,
    vers_local,
)

templates = Jinja2Templates(directory="app/templates")
env = templates.env
env.filters["duree"] = format_duree
env.filters["heure"] = format_heure
env.filters["date_fr"] = format_date
env.filters["date_iso"] = lambda dt: vers_local(dt).date().isoformat() if dt else ""
env.globals.update(
    ROLE_LIBELLES=ROLE_LIBELLES, ZONE_LIBELLES=ZONE_LIBELLES, ALERTES=ALERTES, ALERTES_GRAVES=ALERTES_GRAVES,
    libelle_mois=libelle_mois, MOIS=MOIS, MOIS_COURTS=MOIS_COURTS, aujourd_hui=aujourd_hui, fuseau=get_settings().timezone,
)

FLASH = "flash"


def a_une_equipe(u: Utilisateur) -> bool:
    with SessionLocal() as db:
        return db.scalar(select(Utilisateur.id).where(Utilisateur.manager_id == u.id).limit(1)) is not None


def rendre(request: Request, nom: str, statut: int = 200, **ctx):
    sess = getattr(request.state, "session_auth", None)
    u = sess.utilisateur if sess else None
    flash = request.cookies.get(FLASH)
    ctx.update(
        request=request, moi=u, csrf=sess.csrf_token if sess else "",
        flash=unquote(flash).split("|", 1) if flash else None,
        menu_equipe=bool(u and (u.vue_globale or a_une_equipe(u))),
    )
    reponse = templates.TemplateResponse(request, nom, ctx, status_code=statut)
    if flash:
        reponse.delete_cookie(FLASH)
    return reponse


def rediriger(url: str, message: str | None = None, niveau: str = "ok") -> RedirectResponse:
    r = RedirectResponse(url, status_code=303)
    if message:
        r.set_cookie(FLASH, quote(f"{niveau}|{message}"), max_age=60, httponly=True, samesite="lax")
    return r


PERIODES = {
    "semaine": "Semaine en cours",
    "mois": "Mois en cours",
    "mois_prec": "Mois précédent",
    "3mois": "3 derniers mois",
    "6mois": "6 derniers mois",
    "12mois": "12 derniers mois",
    "perso": "Personnalisée",
}


def periode(code: str | None, debut: str | None = None, fin: str | None = None) -> tuple[str, date, date]:
    """Renvoie (code, date de début, date de fin) d'une période de consultation."""
    j = aujourd_hui()
    code = code if code in PERIODES else "mois"
    if code == "semaine":
        d = j - timedelta(days=j.weekday())
        return code, d, d + timedelta(days=6)
    if code == "mois_prec":
        f = j.replace(day=1) - timedelta(days=1)
        return code, f.replace(day=1), f
    if code in ("3mois", "6mois", "12mois"):
        n = int(code.removesuffix("mois"))
        total = j.year * 12 + j.month - 1 - (n - 1)
        return code, date(total // 12, total % 12 + 1, 1), j
    if code == "perso":
        try:
            d, f = date.fromisoformat(debut or ""), date.fromisoformat(fin or "")
            if d > f:
                d, f = f, d
            if (f - d).days > 400:
                d = f - timedelta(days=400)
            return code, d, f
        except ValueError:
            code = "mois"
    d = j.replace(day=1)
    return "mois", d, j


def mois_entre(debut: date, fin: date) -> list[tuple[int, int]]:
    res, a, m = [], debut.year, debut.month
    while (a, m) <= (fin.year, fin.month):
        res.append((a, m))
        a, m = (a + 1, 1) if m == 12 else (a, m + 1)
    return res
