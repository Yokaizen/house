"""Configuration d'infrastructure, lue depuis les variables d'environnement.

Les règles métier modifiables (rayons, seuils, alertes, conservation...) sont
stockées en base et éditables depuis l'interface d'administration : voir
app/services/parametres.py.
"""
from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = "postgresql+psycopg://badgeage:badgeage@db:5432/badgeage"
    base_url: str = "https://badge.proximy.net"
    timezone: str = "Europe/Paris"

    # Cookie de session : Secure obligatoire en production (HTTPS).
    cookie_secure: bool = True
    session_duree_jours: int = 90

    # Géocodage des adresses (API Adresse de l'État, gratuite, sans clé).
    geocodage_url: str = "https://api-adresse.data.gouv.fr/search/"
    geocodage_actif: bool = True

    # SMTP : laisser smtp_host vide tant que le serveur n'est pas fourni,
    # les e-mails sont alors seulement journalisés.
    smtp_host: str = ""
    smtp_port: int = 587
    smtp_user: str = ""
    smtp_password: str = ""
    smtp_starttls: bool = True
    smtp_from: str = "badgeage@proximy.net"

    # Intervalle de la boucle de tâches planifiées (worker).
    jobs_intervalle_minutes: int = 15


@lru_cache
def get_settings() -> Settings:
    return Settings()
