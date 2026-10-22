from datetime import timedelta

from fastapi.testclient import TestClient
from uvicorn.middleware.proxy_headers import ProxyHeadersMiddleware

from app.jobs import purger
from app.models import TentativeConnexion, Utilisateur
from app.security import MESSAGE_BLOCAGE
from app.services.temps import maintenant_utc
from tests.conftest import MDP


def depuis(ip):
    """Client vu depuis l'adresse ip, résolue comme en production (gunicorn --forwarded-allow-ips="*")."""
    from app.main import app
    return TestClient(ProxyHeadersMiddleware(app, trusted_hosts="*"), headers={"X-Forwarded-For": ip})


def connexion(c, identifiant, mdp):
    return c.post("/connexion", data={"identifiant": identifiant, "mot_de_passe": mdp}, follow_redirects=False)


def test_un_tiers_ne_bloque_pas_le_salarie(donnees):
    pirate = depuis("203.0.113.5")
    for _ in range(5):
        assert "incorrect" in connexion(pirate, "SAL01", "faux").text
    # Bloqué depuis son adresse, même avec le bon mot de passe...
    assert MESSAGE_BLOCAGE in connexion(pirate, "SAL01", MDP).text
    # ... mais le salarié se connecte depuis son téléphone.
    assert connexion(depuis("198.51.100.7"), "SAL01", MDP).status_code == 303


def test_adresse_bloquee_tous_identifiants_confondus(donnees):
    pirate = depuis("203.0.113.5")
    for i in range(10):
        connexion(pirate, f"X{i:03d}", "faux")  # identifiants inexistants : comptés aussi
    assert MESSAGE_BLOCAGE in connexion(pirate, "CHEF", MDP).text
    assert connexion(depuis("198.51.100.7"), "CHEF", MDP).status_code == 303


def test_compte_bloque_apres_echecs_de_plusieurs_adresses(client_de, donnees, db):
    for n in range(6):
        c = depuis(f"203.0.113.{n}")
        for _ in range(5):
            connexion(c, "SAL01", "faux")
    assert MESSAGE_BLOCAGE in connexion(depuis("198.51.100.7"), "SAL01", MDP).text

    # La réinitialisation par un administrateur lève le blocage.
    admin = client_de("admin")
    r = admin.post(f"/admin/utilisateurs/{donnees['sal'].id}/reinitialiser", data={"csrf_token": admin.csrf})
    provisoire = r.text.split('class="mdp-provisoire">')[1].split("<")[0]
    db.expire_all()
    assert db.get(Utilisateur, donnees["sal"].id).bloque_jusqu_a is None
    assert connexion(depuis("198.51.100.7"), "SAL01", provisoire).status_code == 303


def test_connexion_reussie_efface_ses_propres_erreurs(donnees):
    salarie = depuis("198.51.100.7")
    for _ in range(4):
        connexion(salarie, "SAL01", "faux")
    assert connexion(salarie, "SAL01", MDP).status_code == 303
    for _ in range(4):
        connexion(salarie, "SAL01", "faux")
    assert connexion(salarie, "SAL01", MDP).status_code == 303


def test_en_tete_x_forwarded_for_ignore_sans_proxy(client, donnees):
    # Sans proxy de confiance (démonstration), l'en-tête envoyé par le client ne change pas l'adresse comptée.
    for i in range(10):
        client.post("/connexion", data={"identifiant": "SAL01", "mot_de_passe": "faux"},
                    headers={"X-Forwarded-For": f"203.0.113.{i}"})
    r = client.post("/connexion", data={"identifiant": "SAL01", "mot_de_passe": MDP}, follow_redirects=False)
    assert MESSAGE_BLOCAGE in r.text


def test_purge_des_tentatives(db, donnees):
    db.add_all([
        TentativeConnexion(horodatage=maintenant_utc() - timedelta(days=2), adresse_ip="203.0.113.5", identifiant="x"),
        TentativeConnexion(horodatage=maintenant_utc(), adresse_ip="203.0.113.5", identifiant="x"),
    ])
    db.commit()
    purger(db)
    assert db.query(TentativeConnexion).count() == 1
