"""Constants for the FireLabs integration."""

from datetime import timedelta

DOMAIN = "firelabs"
MANUFACTURER = "FireLabs"
DEFAULT_SCAN_INTERVAL = 5  # seconds
HTTP_TIMEOUT = 8  # seconds

# Firmware updates. The device reports its running version as `fw` in
# /api/status; the latest release is read from the model's GitHub repo, and
# install pushes the release .bin to the device's existing /update endpoint.
GITHUB_LATEST = "https://api.github.com/repos/{repo}/releases/latest"
FIRMWARE_REPOS: dict[str, str] = {
    "S31": "FireLabsCA/firelabs-s31-firmware",
    "WX": "FireLabsCA/firelabs-weather-display",
}
RELEASE_TTL = 6 * 3600  # seconds; GitHub unauthenticated is 60 req/hr/IP
LATEST_POLL_INTERVAL = timedelta(hours=6)
OTA_DOWNLOAD_TIMEOUT = 60  # seconds to pull the .bin from GitHub
OTA_UPLOAD_TIMEOUT = 120  # seconds to upload + flash on the device
RELEASES_KEY = "firelabs_releases"  # shared release cache in hass.data

# Weather Display (model "WX"). Unlike the S31 this is a sleepy device: HA does
# not poll it. It wakes, POSTs telemetry to a per-entry webhook, and gets a
# weather bundle back in the response. The integration mostly configures the
# device and serves it data.
MODEL_WX = "WX"
CONF_WEBHOOK_ID = "webhook_id"

# Current-conditions bundle fields mapped to the option key holding the source
# entity_id. Every field is optional; an unmapped or unavailable source is just
# left out of the bundle.
WX_CURRENT_FIELDS: dict[str, str] = {
    "temp": "ent_temp",
    "feels_like": "ent_feels_like",
    "condition": "ent_condition",
    "humidity": "ent_humidity",
    "wind": "ent_wind",
    "gust": "ent_gust",
    "precip": "ent_precip",
    "uv": "ent_uv",
    "high": "ent_high",
    "low": "ent_low",
    "pop": "ent_pop",
}
CONF_WEATHER_ENTITY = "ent_weather"  # a weather.* entity drives the hourly strip
WX_FORECAST_SLOTS = 5

CONF_SLEEP_MIN = "sleep_min"
CONF_QUIET_START = "quiet_start"
CONF_QUIET_END = "quiet_end"
DEFAULT_SLEEP_MIN = 30
DEFAULT_QUIET_START = 21
DEFAULT_QUIET_END = 6

# A check-in is expected about every sleep_min (30 by default). Mark the device
# unavailable after it misses roughly three cycles.
WX_AVAILABLE_WINDOW = timedelta(minutes=95)
