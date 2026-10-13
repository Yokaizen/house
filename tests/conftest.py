import os
import tempfile

_base = os.path.join(tempfile.mkdtemp(), "test.db")
os.environ["DATABASE_URL"] = f"sqlite:///{_base}"
os.environ["COOKIE_SECURE"] = "false"
os.environ["GEOCODAGE_ACTIF"] = "false"

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402
from sqlalchemy import event  # noqa: E402

from app.db import Base, SessionLocal, engine  # noqa: E402
from app.models import Etablissement, Utilisateur  # noqa: E402
from app.security import hacher  # noqa: E402


@event.listens_for(engine, "connect")
def _cles_etrangeres(conn, _):
    conn.execute("PRAGMA foreign_keys=ON")


MDP = "MotDePasse2026"
# Agence de référence (coordonnées fictives en Île-de-France).
SITE = (48.9500, 2.3800)


@pytest.fixture(autouse=True)
def base():
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    yield


@pytest.fixture
def db():
    with SessionLocal() as s:
        yield s


@pytest.fixture
def donnees(db):
    etab = Etablissement(code="STAINS", nom="Stains", latitude=SITE[0], longitude=SITE[1], rayon_m=100)
    db.add(etab)
    db.flush()

    def creer(matricule, role="salarie", manager=None, **kw):
        u = Utilisateur(matricule=matricule, nom=matricule.title(), prenom="Test", role=role,
                        etablissement_id=etab.id, manager_id=manager.id if manager else None,
                        mot_de_passe_hash=hacher(MDP), doit_changer_mdp=False, **kw)
        db.add(u)
        db.flush()
        return u

    admin = creer("ADMIN", "admin")
    rh = creer("RH01", "rh")
    chef = creer("CHEF", "manager")
    sal = creer("SAL01", manager=chef, domicile_lat=48.80, domicile_lon=2.20)
    sous = creer("SAL02", manager=sal)
    autre = creer("AUTRE")
    db.commit()
    return {"etab": etab, "admin": admin, "rh": rh, "chef": chef, "sal": sal, "sous": sous, "autre": autre}


class Client(TestClient):
    csrf: str = ""

    def connecter(self, matricule):
        r = self.post("/connexion", data={"identifiant": matricule, "mot_de_passe": MDP, "rester_connecte": "on"},
                      follow_redirects=False)
        assert r.status_code == 303, r.text
        page = self.get("/mes-badgeages").text
        self.csrf = page.split('name="csrf_token" value="')[1].split('"')[0]
        return self


@pytest.fixture
def client():
    from app.main import app
    return Client(app)


@pytest.fixture
def client_de(donnees):
    from app.main import app

    def fabrique(cle):
        return Client(app).connecter(donnees[cle].matricule)
    return fabrique
