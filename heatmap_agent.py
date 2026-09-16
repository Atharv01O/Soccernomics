from __future__ import annotations

import os
from typing import Any

import streamlit as st

try:
    from google import genai
    from google.genai import types
except ImportError:  # pragma: no cover
    genai = None
    types = None


IMAGE_MODEL = "gemini-3.1-flash-image"


class HeatmapGenerationError(RuntimeError):
    pass


def _api_key() -> str | None:
    try:
        value = st.secrets.get("GEMINI_API_KEY")
        if value:
            return str(value).strip()
    except Exception:
        pass

    value = os.getenv("GEMINI_API_KEY", "").strip()
    return value or None


def _grounding_sources(response) -> list[dict[str, str]]:
    sources: list[dict[str, str]] = []
    seen: set[str] = set()

    for candidate in getattr(response, "candidates", None) or []:
        metadata = getattr(candidate, "grounding_metadata", None)
        if metadata is None:
            metadata = getattr(candidate, "groundingMetadata", None)

        if metadata is None:
            continue

        chunks = getattr(metadata, "grounding_chunks", None)
        if chunks is None:
            chunks = getattr(metadata, "groundingChunks", None)

        for chunk in chunks or []:
            web = getattr(chunk, "web", None)
            if web is None and isinstance(chunk, dict):
                web = chunk.get("web")

            if web is None:
                continue

            if isinstance(web, dict):
                url = web.get("uri") or web.get("url")
                title = web.get("title") or url
            else:
                url = getattr(web, "uri", None) or getattr(web, "url", None)
                title = getattr(web, "title", None) or url

            if url and str(url) not in seen:
                seen.add(str(url))
                sources.append({
                    "title": str(title or url),
                    "url": str(url),
                })

    return sources


def _extract_image_bytes(response) -> bytes | None:
    """Handle current google-genai inline image response shapes."""
    for candidate in getattr(response, "candidates", None) or []:
        content = getattr(candidate, "content", None)
        parts = getattr(content, "parts", None) if content else None

        for part in parts or []:
            inline = getattr(part, "inline_data", None)
            if inline is None:
                inline = getattr(part, "inlineData", None)

            if inline is None:
                continue

            data = getattr(inline, "data", None)
            if data:
                return data

    return None


@st.cache_data(ttl=1800, show_spinner=False)
def generate_player_heatmap(
    player_name: str,
    season: str,
    competition: str = "Premier League",
) -> dict[str, Any]:
    """Generate a web/image-grounded heatmap illustration.

    This deliberately labels the result as an AI reconstruction rather than
    pretending that generated pixels are raw player tracking coordinates.
    """
    key = _api_key()

    if not key:
        raise HeatmapGenerationError(
            "GEMINI_API_KEY is not configured."
        )

    if genai is None or types is None:
        raise HeatmapGenerationError(
            "google-genai is not installed. Run: "
            "pip install -U google-genai"
        )

    client = genai.Client(api_key=key)

    prompt = f"""
Create a football PLAYER ACTIVITY HEATMAP VISUAL for:

Player: {player_name}
Competition: {competition}
Season: {season}

Use Google Web Search AND Google Image Search grounding to inspect published
football-statistics sources for this exact player and exact season. Prefer
published heatmap/activity-map evidence from sources such as FotMob, FlickStat,
SofaScore, WhoScored, or other reputable football analytics sites.

IMPORTANT:
- The output is an analytical illustration, NOT claimed raw tracking data.
- Base the spatial distribution on the published heatmap/activity evidence
  you find.
- Do NOT invent a random football heatmap.
- Do NOT show the player's face.
- Do NOT add player cards, statistics tables, logos, titles, or unrelated UI.
- Produce ONLY a clean horizontal football pitch with the activity density
  overlaid.
- Use a professional football analytics heatmap appearance: low activity
  should be cool/dim, high activity should be warm/bright.
- Keep pitch markings visible.
- The attacking direction should be left-to-right.
- The visual should look like a genuine scouting-analysis heatmap, not an
  artistic poster.
- If the web evidence is insufficient to determine an exact-season heatmap,
  return a simple pitch with a clearly visible "INSUFFICIENT DATA" label rather
  than inventing player activity.

The final image must contain only the pitch/heatmap visual.
"""

    try:
        response = client.models.generate_content(
            model=IMAGE_MODEL,
            contents=prompt,
            config=types.GenerateContentConfig(
                response_modalities=["IMAGE"],
                tools=[
                    types.Tool(
                        google_search=types.GoogleSearch(
                            search_types=types.SearchTypes(
                                web_search=types.WebSearch(),
                                image_search=types.ImageSearch(),
                            )
                        )
                    )
                ],
            ),
        )
    except Exception as exc:
        raise HeatmapGenerationError(
            f"Gemini heatmap generation failed: {exc}"
        ) from exc

    image_bytes = _extract_image_bytes(response)

    if not image_bytes:
        raise HeatmapGenerationError(
            "Gemini returned no image. Your Gemini API key/model access "
            "may not include image generation."
        )

    return {
        "ok": True,
        "image_bytes": image_bytes,
        "sources": _grounding_sources(response),
        "model": IMAGE_MODEL,
        "player": player_name,
        "season": season,
        "competition": competition,
    }
