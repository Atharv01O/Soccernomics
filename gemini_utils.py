from __future__ import annotations

import json
import os
import re
from typing import Any

import streamlit as st

try:
    from google import genai
    from google.genai import types
except ImportError:  # pragma: no cover
    genai = None
    types = None

GEMINI_MODEL = "gemini-2.5-flash"


def get_gemini_api_key() -> str | None:
    """Read Gemini API key from Streamlit secrets or environment variables."""
    try:
        key = st.secrets.get("GEMINI_API_KEY")
        if key:
            return str(key).strip()
    except Exception:
        pass

    key = os.getenv("GEMINI_API_KEY", "").strip()
    return key or None


def gemini_is_configured() -> bool:
    return bool(get_gemini_api_key()) and genai is not None


def _extract_json(text: str) -> dict[str, Any]:
    """Parse JSON even when a model wraps it in a markdown code fence."""
    cleaned = (text or "").strip()
    cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"\s*```$", "", cleaned)

    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        start = cleaned.find("{")
        end = cleaned.rfind("}")
        if start >= 0 and end > start:
            return json.loads(cleaned[start:end + 1])
        raise


def _grounding_sources(response) -> list[dict[str, str]]:
    """Extract web sources from Gemini grounding metadata when available."""
    sources: list[dict[str, str]] = []
    seen: set[str] = set()

    candidates = getattr(response, "candidates", None) or []
    for candidate in candidates:
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

            if url and url not in seen:
                seen.add(url)
                sources.append({"title": str(title or url), "url": str(url)})

    return sources


@st.cache_data(ttl=3600, show_spinner=False)
def get_ai_player_research(
    player_name: str,
    season: str,
    competition: str = "Premier League",
) -> dict[str, Any]:
    """Research a player using Gemini grounded in Google Search.

    This is a FALLBACK, not the primary stats source — the page should
    prefer local, real, deterministic data (playerstats.csv) wherever it
    covers a field, and only call this for fields/players it doesn't."""
    key = get_gemini_api_key()
    if not key:
        return {"ok": False, "error": "GEMINI_API_KEY is not configured."}
    if genai is None or types is None:
        return {"ok": False, "error": "google-genai is not installed. Run: pip install -U google-genai"}

    client = genai.Client(api_key=key)

    prompt = f"""
You are the research layer for a Premier League football analytics dashboard.

Player: {player_name}
Competition: {competition}
Season: {season}

Use Google Search grounding heavily. Search the exact player, competition and
season. Prefer specialist football-statistics sources and current season pages.

SOURCE PRIORITY:
- FotMob, FBref, StatMuse, Understat and xGStat for structured statistics.
- FlickStat and FotMob for touches, passes, key passes and player activity maps.
- Search multiple sources when a field is missing, but do not combine values
  from incompatible snapshots without explaining the discrepancy.

CURRENT-SEASON RULES:
- The season may be live and different sites may update at different times.
- Prefer one coherent, recently updated source for related statistics.
- Never average conflicting values.
- Never use another competition or another season to fill a missing value.
- If a value cannot be verified, return null.
- For passes, use the provider's clearly defined completed/successful-pass
  total when available and state the definition in statistics_notes.

Return JSON only:
{{
  "player": "{player_name}",
  "competition": "{competition}",
  "season": "{season}",
  "data_as_of": null,
  "primary_stats_source": null,
  "statistics": {{
    "appearances": null,
    "starts": null,
    "minutes": null,
    "goals": null,
    "assists": null,
    "shots": null,
    "shots_on_target": null,
    "key_passes": null,
    "touches": null,
    "passes": null,
    "xg": null,
    "xa": null
  }},
  "statistics_notes": "",
  "statistics_sources": [],
  "scouting_summary": "",
  "limitations": ""
}}
"""

    try:
        response = client.models.generate_content(
            model=GEMINI_MODEL,
            contents=prompt,
            config=types.GenerateContentConfig(
                tools=[types.Tool(google_search=types.GoogleSearch())],
                temperature=0.1,
            ),
        )

        if not getattr(response, "text", None):
            return {"ok": False, "error": "Gemini returned an empty response."}

        result = _extract_json(response.text)
        if not isinstance(result, dict):
            return {"ok": False, "error": "Gemini returned an unexpected JSON structure."}

        grounded = _grounding_sources(response)
        if grounded:
            existing = result.get("statistics_sources") or []
            existing_urls = {x.get("url") for x in existing if isinstance(x, dict)}
            result["statistics_sources"] = existing + [s for s in grounded if s["url"] not in existing_urls]
            result["grounding_sources"] = grounded
        else:
            result.setdefault("grounding_sources", [])

        result["ok"] = True
        return result

    except Exception as exc:
        return {"ok": False, "error": f"Gemini request failed: {exc}"}


def clear_gemini_cache() -> None:
    get_ai_player_research.clear()