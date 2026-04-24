"""GPS Tracker Map - Custom Integration for Home Assistant.

Polls ALL device_tracker entities every minute and stores GPS positions
in a local SQLite database, enabling full historical track visualization.
"""
from __future__ import annotations

import logging
import math
import os
import sqlite3
from datetime import datetime, timedelta

from homeassistant.components.frontend import async_register_built_in_panel, async_remove_panel
from homeassistant.components.http import HomeAssistantView, StaticPathConfig
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.event import async_track_time_interval

from .const import DOMAIN, PANEL_TITLE, PANEL_ICON, PANEL_URL_PATH

_LOGGER = logging.getLogger(__name__)

PANEL_DIR = os.path.join(os.path.dirname(__file__), "panel")
STATIC_URL = "/gps_tracker_map_static"
DB_FILENAME = "gps_tracker_map.db"
POLL_INTERVAL = timedelta(minutes=1)
RETENTION_DAYS = 90
MIN_DISTANCE_METERS = 30  # skip point if phone moved less than this


# ── Database helpers (sync, run in executor) ───────────────────────────────

def _haversine_m(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Return distance in metres between two GPS coordinates."""
    R = 6_371_000.0
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp = math.radians(lat2 - lat1)
    dl = math.radians(lon2 - lon1)
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))


def _init_db(db_path: str) -> None:
    """Create the database schema if it doesn't already exist."""
    with sqlite3.connect(db_path) as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS gps_positions (
                id        INTEGER PRIMARY KEY AUTOINCREMENT,
                entity_id TEXT    NOT NULL,
                latitude  REAL    NOT NULL,
                longitude REAL    NOT NULL,
                accuracy  REAL    DEFAULT 0,
                altitude  REAL    DEFAULT 0,
                timestamp TEXT    NOT NULL
            )
        """)
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_entity_ts "
            "ON gps_positions (entity_id, timestamp)"
        )
        conn.commit()


def _store_position(
    db_path: str,
    entity_id: str,
    lat: float,
    lng: float,
    accuracy: float,
    altitude: float,
) -> None:
    """Store a position, skipping duplicates closer than MIN_DISTANCE_METERS."""
    with sqlite3.connect(db_path) as conn:
        row = conn.execute(
            "SELECT latitude, longitude FROM gps_positions "
            "WHERE entity_id=? ORDER BY timestamp DESC LIMIT 1",
            (entity_id,),
        ).fetchone()

        if row:
            if lat == row[0] and lng == row[1]:
                return  # Exact overlap — skip
            if _haversine_m(row[0], row[1], lat, lng) < MIN_DISTANCE_METERS:
                return  # Phone hasn't moved enough — skip

        conn.execute(
            "INSERT INTO gps_positions "
            "(entity_id, latitude, longitude, accuracy, altitude, timestamp) "
            "VALUES (?,?,?,?,?,?)",
            (entity_id, lat, lng, accuracy, altitude,
             datetime.utcnow().isoformat()),
        )
        conn.commit()


def _cleanup_old(db_path: str) -> None:
    """Delete records older than RETENTION_DAYS."""
    cutoff = (datetime.utcnow() - timedelta(days=RETENTION_DAYS)).isoformat()
    with sqlite3.connect(db_path) as conn:
        conn.execute("DELETE FROM gps_positions WHERE timestamp < ?", (cutoff,))
        conn.commit()


def _get_history(db_path: str, entity_id: str, days: int) -> list[dict]:
    """Return GPS history for a given entity and day range."""
    cutoff = (datetime.utcnow() - timedelta(days=days)).isoformat()
    with sqlite3.connect(db_path) as conn:
        conn.row_factory = sqlite3.Row
        rows = conn.execute(
            "SELECT latitude, longitude, accuracy, altitude, timestamp "
            "FROM gps_positions "
            "WHERE entity_id=? AND timestamp>=? "
            "ORDER BY timestamp ASC",
            (entity_id, cutoff),
        ).fetchall()
    return [dict(r) for r in rows]


def _list_tracked_entities(db_path: str) -> list[str]:
    """Return all entity_ids that have at least one recorded position."""
    with sqlite3.connect(db_path) as conn:
        rows = conn.execute(
            "SELECT DISTINCT entity_id FROM gps_positions ORDER BY entity_id"
        ).fetchall()
    return [r[0] for r in rows]


# ── HTTP Views ─────────────────────────────────────────────────────────────

class GpsTrackerHistoryView(HomeAssistantView):
    """GET /api/gps_tracker_map/history?entity_id=X&days=Y"""

    url = "/api/gps_tracker_map/history"
    name = "api:gps_tracker_map:history"
    requires_auth = True

    def __init__(self, db_path: str) -> None:
        self._db = db_path

    async def get(self, request):
        entity_id = request.query.get("entity_id", "")
        days = min(int(request.query.get("days", 3)), 365)
        hass = request.app["hass"]
        rows = await hass.async_add_executor_job(_get_history, self._db, entity_id, days)
        return self.json(rows)


class GpsTrackerEntitiesView(HomeAssistantView):
    """GET /api/gps_tracker_map/entities — list entities with recorded data"""

    url = "/api/gps_tracker_map/entities"
    name = "api:gps_tracker_map:entities"
    requires_auth = True

    def __init__(self, db_path: str) -> None:
        self._db = db_path

    async def get(self, request):
        hass = request.app["hass"]
        entity_ids = await hass.async_add_executor_job(_list_tracked_entities, self._db)
        # enrich with friendly name from current HA states
        result = []
        for eid in entity_ids:
            state = hass.states.get(eid)
            result.append({
                "entity_id": eid,
                "friendly_name": (state.attributes.get("friendly_name") if state else None) or eid,
                "state": state.state if state else "unknown",
            })
        return self.json(result)


# ── Integration setup ──────────────────────────────────────────────────────

async def async_setup(hass: HomeAssistant, config: dict) -> bool:
    hass.data.setdefault(DOMAIN, {})
    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    hass.data[DOMAIN][entry.entry_id] = entry.data

    db_path = hass.config.path(DB_FILENAME)
    await hass.async_add_executor_job(_init_db, db_path)
    hass.data[DOMAIN]["db_path"] = db_path

    # Serve static panel files
    await hass.http.async_register_static_paths(
        [StaticPathConfig(STATIC_URL, PANEL_DIR, cache_headers=False)]
    )

    # Register REST endpoints
    hass.http.register_view(GpsTrackerHistoryView(db_path))
    hass.http.register_view(GpsTrackerEntitiesView(db_path))

    # Register sidebar panel
    async_register_built_in_panel(
        hass,
        component_name="iframe",
        sidebar_title=PANEL_TITLE,
        sidebar_icon=PANEL_ICON,
        frontend_url_path=PANEL_URL_PATH,
        config={
            "url": (
                f"{STATIC_URL}/index.html"
                f"?entity={entry.data['entity_id']}"
                f"&days={entry.data.get('days', 3)}"
            )
        },
        require_admin=False,
    )

    # ── Polling loop ──────────────────────────────────────────────────────
    poll_tick = [0]

    async def poll_all_trackers(_now) -> None:
        """Called every minute: snapshot every device_tracker with GPS data."""
        poll_tick[0] += 1

        # Hourly cleanup
        if poll_tick[0] % 60 == 0:
            await hass.async_add_executor_job(_cleanup_old, db_path)

        for state in hass.states.async_all("device_tracker"):
            lat = state.attributes.get("latitude")
            lng = state.attributes.get("longitude")
            if lat is None or lng is None:
                continue
            await hass.async_add_executor_job(
                _store_position,
                db_path,
                state.entity_id,
                float(lat),
                float(lng),
                float(state.attributes.get("gps_accuracy", 0)),
                float(state.attributes.get("altitude", 0)),
            )

    entry.async_on_unload(
        async_track_time_interval(hass, poll_all_trackers, POLL_INTERVAL)
    )

    _LOGGER.info(
        "GPS Tracker Map: polling all device_trackers every %s · DB: %s",
        POLL_INTERVAL,
        db_path,
    )
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    hass.data[DOMAIN].pop(entry.entry_id, None)
    try:
        async_remove_panel(hass, PANEL_URL_PATH)
    except Exception:
        pass
    return True
