"""Publica o Story do dia via Instagram Graph API (Instagram Login).

Fluxo de Content Publishing (2 passos + poll):
  1. POST /{ig-user-id}/media       -> cria o container (media_type=STORIES)
  2. GET  /{container-id}?fields=status_code -> espera FINISHED
  3. POST /{ig-user-id}/media_publish -> publica

A Meta baixa a imagem da URL informada, então ela precisa ser pública — por isso
o endpoint /api/v1/story/{dia}.jpg é servido pelo próprio site.
"""

from __future__ import annotations

import time

import httpx

from .settings import settings

GRAPH_HOST = "https://graph.instagram.com"


class InstagramError(RuntimeError):
    pass


def _base() -> str:
    return f"{GRAPH_HOST}/{settings.IG_API_VERSION}"


def _friendly(resp: httpx.Response) -> str:
    try:
        data = resp.json()
    except Exception:  # noqa: BLE001
        return resp.text
    err = data.get("error") if isinstance(data, dict) else None
    if isinstance(err, dict):
        return err.get("message") or str(err)
    return str(data)


def publish_story(image_url: str, timeout: float = 30.0) -> dict:
    """Cria o container, espera ficar pronto e publica o Story. Devolve o id publicado."""
    token = settings.IG_ACCESS_TOKEN
    user = settings.IG_USER_ID
    if not token or not user:
        raise InstagramError("IG_USER_ID/IG_ACCESS_TOKEN não configurados")

    with httpx.Client(timeout=timeout) as client:
        created = client.post(
            f"{_base()}/{user}/media",
            data={
                "image_url": image_url,
                "media_type": "STORIES",
                "access_token": token,
            },
        )
        if created.status_code >= 400:
            raise InstagramError(f"criar container: {created.status_code} {_friendly(created)}")
        container_id = created.json().get("id")
        if not container_id:
            raise InstagramError(f"resposta sem container id: {created.text}")

        # O container fica EXPIRED/ERROR se algo falhar; poller até FINISHED.
        for _ in range(30):
            status = client.get(
                f"{_base()}/{container_id}",
                params={"fields": "status_code", "access_token": token},
            )
            code = status.json().get("status_code") if status.status_code < 400 else None
            if code == "FINISHED":
                break
            if code in ("ERROR", "EXPIRED"):
                raise InstagramError(f"container {code}: {status.text}")
            time.sleep(3)
        else:
            raise InstagramError("container não ficou pronto a tempo")

        published = client.post(
            f"{_base()}/{user}/media_publish",
            data={"creation_id": container_id, "access_token": token},
        )
        if published.status_code >= 400:
            raise InstagramError(f"publicar: {published.status_code} {_friendly(published)}")
        return published.json()
