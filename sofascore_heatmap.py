from __future__ import annotations

import re
from typing import Any

import pandas as pd
import plotly.graph_objects as go
import requests
import streamlit as st


BASE_URL = "https://www.sofascore.com/api/v1"
PL_TOURNAMENT_ID = 17

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/142.0 Safari/537.36"
    ),
    "Accept": "application/json,text/plain,*/*",
    "Referer": "https://www.sofascore.com/",
}


class SofaScoreHeatmapError(RuntimeError):
    pass


def _request_json(path: str) -> dict[str, Any]:
    url = f"{BASE_URL}{path}"

    try:
        response = requests.get(
            url,
            headers=HEADERS,
            timeout=15,
        )
    except requests.RequestException as exc:
        raise SofaScoreHeatmapError(
            f"Could not reach SofaScore: {exc}"
        ) from exc

    if response.status_code == 403:
        raise SofaScoreHeatmapError(
            "SofaScore denied the request (HTTP 403). "
            "The public endpoint may be temporarily protected."
        )

    if response.status_code == 429:
        raise SofaScoreHeatmapError(
            "SofaScore rate-limited the request (HTTP 429). "
            "Try again shortly."
        )

    if response.status_code >= 400:
        raise SofaScoreHeatmapError(
            f"SofaScore returned HTTP {response.status_code} for {path}."
        )

    try:
        data = response.json()
    except ValueError as exc:
        raise SofaScoreHeatmapError(
            "SofaScore returned a non-JSON response."
        ) from exc

    if not isinstance(data, dict):
        raise SofaScoreHeatmapError(
            "SofaScore returned an unexpected response."
        )

    return data


def _normalise(value: str) -> str:
    return re.sub(
        r"[^a-z0-9]+",
        "",
        str(value).lower(),
    )


@st.cache_data(ttl=86400, show_spinner=False)
def find_player(player_name: str) -> dict[str, Any]:
    """Find the closest SofaScore player match by name."""
    query = requests.utils.quote(str(player_name))
    data = _request_json(f"/search/all?q={query}")

    results = data.get("results") or []
    target = _normalise(player_name)

    candidates = []

    for item in results:
        entity = item.get("entity") or {}

        item_type = item.get("type")
        entity_type = entity.get("type")

        if item_type != "player" and entity_type != "player":
            continue

        name = entity.get("name") or item.get("name")
        if not name:
            continue

        norm = _normalise(name)
        score = 0

        if norm == target:
            score += 100

        if target in norm or norm in target:
            score += 50

        candidates.append((score, entity))

    if not candidates:
        raise SofaScoreHeatmapError(
            f"SofaScore could not find player '{player_name}'."
        )

    candidates.sort(key=lambda item: item[0], reverse=True)
    entity = candidates[0][1]

    return {
        "id": entity.get("id"),
        "name": entity.get("name") or player_name,
        "slug": entity.get("slug"),
        "team": (entity.get("team") or {}).get("name"),
    }


@st.cache_data(ttl=86400, show_spinner=False)
def get_pl_seasons() -> list[dict[str, Any]]:
    """Return Premier League seasons known to SofaScore."""
    data = _request_json(
        f"/unique-tournament/{PL_TOURNAMENT_ID}/seasons"
    )

    seasons = data.get("seasons") or []

    return [
        {
            "id": season.get("id"),
            "name": season.get("name"),
            "slug": season.get("slug"),
        }
        for season in seasons
        if season.get("id") and season.get("name")
    ]


def find_season_id(season: str) -> int:
    """Resolve e.g. '2026/27' to SofaScore's season ID."""
    wanted = _normalise(season)
    seasons = get_pl_seasons()

    for item in seasons:
        if _normalise(item["name"]) == wanted:
            return int(item["id"])

    # Tolerate 2026-27 / other formatting.
    match = re.search(r"(20\d{2})", str(season))
    if match:
        start_year = match.group(1)

        for item in seasons:
            if str(item["name"]).startswith(start_year):
                return int(item["id"])

    raise SofaScoreHeatmapError(
        f"SofaScore does not list Premier League season '{season}'."
    )


@st.cache_data(ttl=3600, show_spinner=False)
def get_season_heatmap(
    player_name: str,
    season: str,
) -> dict[str, Any]:
    """Fetch actual SofaScore season-level player heatmap coordinates."""
    player = find_player(player_name)

    player_id = player.get("id")
    if not player_id:
        raise SofaScoreHeatmapError(
            "SofaScore player ID was not returned."
        )

    season_id = find_season_id(season)

    path = (
        f"/player/{player_id}"
        f"/unique-tournament/{PL_TOURNAMENT_ID}"
        f"/season/{season_id}"
        f"/heatmap/overall"
    )

    data = _request_json(path)
    points = data.get("points") or []

    clean_points: list[dict[str, float]] = []

    for point in points:
        try:
            x = float(point["x"])
            y = float(point["y"])
            count = float(point.get("count", 1))
        except (KeyError, TypeError, ValueError):
            continue

        if (
            0 <= x <= 100
            and 0 <= y <= 100
            and count >= 0
        ):
            clean_points.append(
                {
                    "x": x,
                    "y": y,
                    "count": count,
                }
            )

    if not clean_points:
        raise SofaScoreHeatmapError(
            f"No season-level heatmap points were returned for "
            f"{player_name} in {season}."
        )

    return {
        "player_id": int(player_id),
        "player_name": player.get("name") or player_name,
        "team": player.get("team"),
        "season": season,
        "season_id": season_id,
        "points": clean_points,
        "source": "SofaScore",
        "player_url": (
            "https://www.sofascore.com/player/"
            f"{player.get('slug') or _normalise(player_name)}"
            f"/{player_id}"
        ),
    }


def _pitch_shapes() -> list[dict[str, Any]]:
    """Pitch markings in the same 0–100 coordinate system as the heatmap."""
    line_color = "#EAF2ED"

    return [
        dict(
            type="rect",
            x0=0,
            y0=0,
            x1=100,
            y1=100,
            line=dict(color=line_color, width=1.5),
        ),
        dict(
            type="line",
            x0=50,
            y0=0,
            x1=50,
            y1=100,
            line=dict(color=line_color, width=1),
        ),
        dict(
            type="circle",
            x0=38,
            y0=38,
            x1=62,
            y1=62,
            line=dict(color=line_color, width=1),
        ),
        dict(
            type="rect",
            x0=0,
            y0=30,
            x1=16,
            y1=70,
            line=dict(color=line_color, width=1),
        ),
        dict(
            type="rect",
            x0=84,
            y0=30,
            x1=100,
            y1=70,
            line=dict(color=line_color, width=1),
        ),
        dict(
            type="rect",
            x0=0,
            y0=42,
            x1=6,
            y1=58,
            line=dict(color=line_color, width=1),
        ),
        dict(
            type="rect",
            x0=94,
            y0=42,
            x1=100,
            y1=58,
            line=dict(color=line_color, width=1),
        ),
    ]


def make_heatmap_figure(
    heatmap: dict[str, Any],
    height: int = 500,
) -> go.Figure:
    """Render the retrieved SofaScore activity coordinates on a pitch."""
    points = pd.DataFrame(heatmap["points"])

    if points.empty:
        raise SofaScoreHeatmapError(
            "Cannot render an empty heatmap."
        )

    fig = go.Figure()

    # The input is actual source activity coordinates with a count per point.
    # Histogram2d is only the visualization layer; it does not invent player
    # positions or use the shot-event CSV.
    fig.add_trace(
        go.Histogram2d(
            x=points["x"],
            y=points["y"],
            z=points["count"],
            histfunc="sum",
            nbinsx=24,
            nbinsy=16,
            colorscale=[
                [0.00, "rgba(0,0,0,0)"],
                [0.18, "rgba(20,65,45,0.28)"],
                [0.45, "rgba(47,191,113,0.55)"],
                [0.72, "rgba(232,183,93,0.78)"],
                [1.00, "rgba(215,91,72,0.92)"],
            ],
            colorbar=dict(
                title="Activity",
                thickness=10,
            ),
            hovertemplate=(
                "Activity: %{z:.0f}"
                "<extra></extra>"
            ),
            showscale=True,
        )
    )

    for shape in _pitch_shapes():
        fig.add_shape(**shape)

    fig.update_layout(
        height=height,
        margin=dict(l=5, r=5, t=5, b=5),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        xaxis=dict(
            visible=False,
            range=[0, 100],
            constrain="domain",
        ),
        yaxis=dict(
            visible=False,
            range=[0, 100],
            scaleanchor="x",
            scaleratio=1,
        ),
        coloraxis_colorbar=dict(
            tickfont=dict(color="#EAF2ED"),
        ),
        font_color="#EAF2ED",
    )

    return fig
