"""Accès au trousseau du système (Credential Manager sous Windows, Keychain
sous macOS, Secret Service sous Linux) via la bibliothèque « keyring ».

La source Apple Santé n'a besoin d'aucun secret : elle lit des fichiers. Ce
module sert aux sources qui en demandent (Google Sheet facultatif, futur
Garmin/Withings). Règle : aucun mot de passe, jeton ou clé dans un fichier.
"""
from __future__ import annotations

SERVICE = "sante-sync"


def get(name: str) -> str | None:
    import keyring
    return keyring.get_password(SERVICE, name)


def put(name: str, value: str) -> None:
    import keyring
    keyring.set_password(SERVICE, name, value)


def delete(name: str) -> None:
    import keyring
    try:
        keyring.delete_password(SERVICE, name)
    except keyring.errors.PasswordDeleteError:
        pass


def backend_name() -> str:
    try:
        import keyring
        return type(keyring.get_keyring()).__name__
    except Exception as exc:
        return f"indisponible ({exc})"
