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
GEMINI_IMAGE_MODEL = "gemini-3.1-flash-image"


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
    """Research a player using Gemini grounded in Google Search."""
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
- For the exact player page, search FotMob first for minutes, shots and shots on target; use StatMuse/FBref/other specialist sources to cross-check when needed.
- If a requested field is missing after the first search, perform a second targeted search for that exact field (for example: "{player_name} Premier League 2026/27 minutes" or "{player_name} Premier League 2026/27 shots on target").
- Do not leave a field null merely because it was absent from the first search result. Search again before concluding it is unavailable.
- Never average conflicting values.
- Never use another competition or another season to fill a missing value.
- If a value still cannot be verified after targeted searches, return null and explain that limitation.
- For passes, use the provider's clearly defined completed/successful-pass
  total when available and state the definition in statistics_notes.
- For minutes and shots on target, return the season total when the source provides it, not a per-90 rate or percentage.
- Keep shots and shots on target as raw totals.

HEATMAP RESEARCH:
- Search explicitly for a published player heatmap/activity map for the exact
  season. Search FlickStat and FotMob first, then other specialist providers.
- If an exact-season player page visibly contains a Heatmap/activity section,
  it is valid evidence even if the visual is embedded in the page.
- Record the page URL, publisher, map type and what the map appears to show.
- If no published heatmap can be verified, return found=false.
- Do not fabricate a heatmap URL.

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
  "heatmap": {{
    "found": false,
    "url": null,
    "source_name": null,
    "heatmap_type": null,
    "description": "",
    "exact_season_verified": false
  }},
  "heatmap_sources": [],
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
            result["statistics_sources"] = existing + [
                s for s in grounded if s["url"] not in existing_urls
            ]
            result["grounding_sources"] = grounded
        else:
            result.setdefault("grounding_sources", [])

        result["ok"] = True
        return result

    except Exception as exc:
        return {"ok": False, "error": f"Gemini request failed: {exc}"}


def generate_ai_heatmap(
    player_name: str,
    season: str,
    research: dict[str, Any],
    competition: str = "Premier League",
) -> dict[str, Any]:
    """Generate a qualitative, web-grounded player activity heatmap.

    This is deliberately labelled as an AI estimate. It is not a replacement
    for event/tracking coordinates and must never be presented as raw data.
    """
    key = get_gemini_api_key()
    if not key:
        return {"ok": False, "error": "GEMINI_API_KEY is not configured."}
    if genai is None or types is None:
        return {"ok": False, "error": "google-genai is not installed. Run: pip install -U google-genai"}

    stats = research.get("statistics") or {}
    heatmap = research.get("heatmap") or {}
    sources = research.get("grounding_sources") or research.get("statistics_sources") or []
    source_text = "\n".join(
        f"- {s.get('title', 'Source')}: {s.get('url', '')}"
        for s in sources[:10]
        if isinstance(s, dict) and s.get("url")
    )

    evidence = json.dumps(
        {
            "player": player_name,
            "season": season,
            "competition": competition,
            "statistics": stats,
            "published_heatmap_evidence": heatmap,
            "scouting_summary": research.get("scouting_summary", ""),
        },
        ensure_ascii=False,
    )

    prompt = f"""
Create a clean football analytics visual: an AI-estimated activity heatmap for
{player_name} in the {competition} {season} season.

IMPORTANT:
This is an ESTIMATE based on public football-statistics evidence. It is NOT raw
tracking data, not a coordinate-derived event map, and must not pretend to show
exact event counts. Use the web-grounded evidence below to infer the player's
qualitative spatial tendencies and role.

Research evidence:
{evidence}

Relevant web sources:
{source_text}

Use Google Search grounding to sanity-check the player's role and the season if
needed. Generate a professional, dark-theme football analytics graphic:
- full horizontal football pitch
- realistic pitch markings
- soft density/heat zones rather than discrete dots
- strongest density where the evidence indicates the player operates most
- weaker secondary zones around supporting areas
- attacking direction toward the right
- no player photograph
- no club badge
- no decorative footballer illustration
- minimal clean title: "{player_name} · {season}"
- subtitle: "AI-estimated activity heatmap"
- include a small legend from low to high activity
- do not print fake numerical percentages, fake coordinates, fake touch counts,
  or fake event totals
- prioritize a useful tactical visualization over artistic decoration

The result should look like a professional football analytics dashboard asset,
not a generic poster.
"""

    try:
        client = genai.Client(api_key=key)
        response = client.models.generate_content(
            model=GEMINI_IMAGE_MODEL,
            contents=prompt,
            config=types.GenerateContentConfig(
                response_modalities=["TEXT", "IMAGE"],
                tools=[types.Tool(google_search=types.GoogleSearch())],
                image_config=types.ImageConfig(aspect_ratio="16:9"),
            ),
        )

        image_bytes = None
        text_parts: list[str] = []
        candidates = getattr(response, "candidates", None) or []
        for candidate in candidates:
            content = getattr(candidate, "content", None)
            parts = getattr(content, "parts", None) if content else None
            for part in parts or []:
                text = getattr(part, "text", None)
                if text:
                    text_parts.append(text)
                inline = getattr(part, "inline_data", None)
                if inline is None:
                    inline = getattr(part, "inlineData", None)
                if inline is not None:
                    data = getattr(inline, "data", None)
                    if data:
                        image_bytes = data
                        break
            if image_bytes:
                break

        if image_bytes is None:
            # Some SDK versions expose generated parts directly.
            for part in getattr(response, "parts", None) or []:
                inline = getattr(part, "inline_data", None) or getattr(part, "inlineData", None)
                if inline is not None and getattr(inline, "data", None):
                    image_bytes = inline.data
                    break

        if not image_bytes:
            return {"ok": False, "error": "Gemini did not return an image for the heatmap request."}

        if not isinstance(image_bytes, bytes):
            image_bytes = bytes(image_bytes)

        return {
            "ok": True,
            "player": player_name,
            "season": season,
            "competition": competition,
            "image_bytes": image_bytes,
            "model": GEMINI_IMAGE_MODEL,
            "note": "AI-estimated from web-grounded public evidence; not raw tracking/event data.",
            "sources": _grounding_sources(response),
            "model_text": " ".join(text_parts).strip(),
        }

    except Exception as exc:
        return {"ok": False, "error": f"AI heatmap generation failed: {exc}"}


def clear_gemini_cache() -> None:
    get_ai_player_research.clear()
