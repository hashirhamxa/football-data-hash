# ⚽ Football Events Data & Image Pipeline

[![Update Football Events](https://github.com/Bicodes/Football-Events/actions/workflows/update-events.yml/badge.svg)](https://github.com/Bicodes/Football-Events/actions/workflows/update-events.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Python 3.10+](https://img.shields.io/badge/Python-3.10%2B-brightgreen.svg)](https://www.python.org/)

A production-ready automated pipeline that ingests upcoming football fixtures, resolves high-resolution team crests, renders broadcast-grade 1200x630 matchday banner cards, and publishes normalized, Android-ready JSON via GitHub Raw URLs.

**100% Free & Serverless**: Runs completely on GitHub Actions on a scheduled cron (every 6 hours) with zero paid infrastructure required.

---

## 🚀 Live Raw Endpoints (Android Ready)

Your Android or client application can consume the published JSON and images directly:

| Artifact | Raw GitHub Endpoint | Description |
| :--- | :--- | :--- |
| **Upcoming Events JSON** | `https://raw.githubusercontent.com/Bicodes/Football-Events/main/output/upcoming_events.json` | Main payload of upcoming matches |
| **Competition Status** | `https://raw.githubusercontent.com/Bicodes/Football-Events/main/output/competition_status.json` | Availability and season metadata |
| **Unmatched Teams** | `https://raw.githubusercontent.com/Bicodes/Football-Events/main/output/unmatched_teams.json` | Teams using fallback initials badges |
| **Match Banner Images** | `https://raw.githubusercontent.com/Bicodes/Football-Events/main/output/images/{event_id}.png` | Broadcast 1200x630 match graphics |

---

## 📱 Android Integration Guide

### 1. Kotlin Data Models (Kotlinx Serialization or Gson/Moshi)

```kotlin
import kotlinx.serialization.Serializable
import kotlinx.serialization.SerialName

@Serializable
data class UpcomingEventsResponse(
    val version: String,
    @SerialName("generated_at") val generatedAt: String,
    @SerialName("total_events") val totalEvents: Int,
    @SerialName("date_range") val dateRange: DateRange,
    val events: List<FootballEvent>
)

@Serializable
data class DateRange(
    @SerialName("start_date") val startDate: String,
    @SerialName("days_ahead") val daysAhead: Int
)

@Serializable
data class FootballEvent(
    @SerialName("event_id") val eventId: String,
    val competition: CompetitionInfo,
    val round: String,
    @SerialName("home_team") val homeTeam: TeamInfo,
    @SerialName("away_team") val awayTeam: TeamInfo,
    @SerialName("event_image_url") val eventImageUrl: String,
    @SerialName("match_date") val matchDate: String,
    @SerialName("start_time_utc") val startTimeUtc: String?,
    @SerialName("start_time_pkt") val startTimePkt: String?,
    @SerialName("start_timestamp") val startTimestamp: Long?,
    @SerialName("time_status") val timeStatus: String, // "confirmed" | "tbd"
    @SerialName("match_status") val matchStatus: String,
    @SerialName("last_updated") val lastUpdated: String
)

@Serializable
data class CompetitionInfo(
    val id: String,
    val name: String,
    val country: String,
    val round: String? = null,
    val group: String? = null
)

@Serializable
data class TeamInfo(
    val name: String,
    val slug: String,
    @SerialName("logo_url") val logoUrl: String,
    @SerialName("logo_resolution") val logoResolution: LogoResolution
)

@Serializable
data class LogoResolution(
    val source: String, // "exact" | "alias" | "fuzzy" | "fallback"
    val confidence: Double,
    @SerialName("matched_name") val matchedName: String? = null,
    @SerialName("is_fallback") val isFallback: Boolean
)
```

### 2. Retrofit API Interface

```kotlin
import retrofit2.http.GET

interface FootballEventsApi {
    @GET("Bicodes/Football-Events/main/output/upcoming_events.json")
    suspend fun getUpcomingEvents(): UpcomingEventsResponse
}
```

---

## 🎨 Sample Generated Event Banner

Every fixture automatically generates a unique 1200x630 matchday banner featuring the competition header, team logos/crests, "VS" emblem, and kickoff times in UTC & PKT:

```
+-----------------------------------------------------------------------------+
|               [ ENGLISH PREMIER LEAGUE  *  MATCHDAY 5 ]                    |
|                                                                             |
|      +---------------+                       +---------------+              |
|      |               |                       |               |              |
|      |   HOME LOGO   |       (  VS  )        |   AWAY LOGO   |              |
|      |               |                       |               |              |
|      +---------------+                       +---------------+              |
|         Arsenal FC                               Chelsea FC                 |
|                                                                             |
|          +-------------------------------------------------------+          |
|          |    [Date] SUNDAY, 20 SEP 2026   |   15:00 UTC / 20:00 PKT     |          |
|          +-------------------------------------------------------+          |
+-----------------------------------------------------------------------------+
```

---

## 📊 Monitored Competitions & Upstream Availability

| Competition | Country | Source File | Source Timezone | Current Status |
| :--- | :--- | :--- | :--- | :--- |
| **English Premier League** | England | `en.1.json` | `Europe/London` | `AVAILABLE` (2026-27) |
| **English Championship** | England | `en.2.json` | `Europe/London` | `AVAILABLE` (2026-27) |
| **Spanish La Liga** | Spain | `es.1.json` | `Europe/Madrid` | `AVAILABLE` (2026-27) |
| **Italian Serie A** | Italy | `it.1.json` | `Europe/Rome` | `AVAILABLE` (2026-27) |
| **German Bundesliga** | Germany | `de.1.json` | `Europe/Berlin` | `AVAILABLE` (2026-27) |
| **French Ligue 1** | France | `fr.1.json` | `Europe/Paris` | `AVAILABLE` (2026-27) |
| **UEFA Champions League** | Europe | `uefa.cl.json` | `Europe/Paris` | `AVAILABLE` (2024-25) |
| **UEFA Europa League** | Europe | `uefa.el.json` | `Europe/Paris` | `UNAVAILABLE` (Upstream Pending) |
| **FIFA World Cup** | International | `worldcup.json` | `UTC` | `UNAVAILABLE` (Upstream Pending) |

*Note: In accordance with project requirements, if an upstream competition is not yet populated by OpenFootball, it is recorded cleanly as unavailable without injecting synthetic or fake matches.*

---

## ⚖️ Upstream Data Sources & Licenses

| Source | Repository URL | License | Purpose |
| :--- | :--- | :--- | :--- |
| **OpenFootball** | [openfootball/football.json](https://github.com/openfootball/football.json) | Public Domain (CC0 / Open Data) | Match fixtures, kickoff dates, times, and rounds |
| **Luuk Hopman Football Logos** | [luukhopman/football-logos](https://github.com/luukhopman/football-logos) | MIT / Fair Use | High-resolution European football club crests |
| **National Teams Logos** | [Leo4815162342/football-logos](https://github.com/Leo4815162342/football-logos) | Open Data / CC0 | International team logos and fallback crests |

---

## ⚙️ Repository Structure

```
football-events/
├── .github/
│   └── workflows/
│       └── update-events.yml       # Scheduled GitHub Actions automation
├── assets/
│   ├── backgrounds/                # Background assets and templates
│   └── fonts/                      # Typography fonts
├── config/
│   ├── competitions.json           # Declarative competition configuration
│   └── settings.json               # Pipeline and output settings
├── mappings/
│   ├── team_aliases.json           # Explicit team name to logo mappings
│   └── logo_index.json             # Fast indexed catalog of 2,160+ team logos
├── output/
│   ├── upcoming_events.json        # Published normalized events JSON
│   ├── competition_status.json     # Upstream status report
│   ├── unmatched_teams.json        # Fallback/low-confidence teams report
│   └── images/                     # Generated 1200x630 matchday banner cards
├── scripts/
│   ├── fetch_fixtures.py           # Ingestion from OpenFootball
│   ├── normalize_fixtures.py       # Timezone conversions and event normalization
│   ├── resolve_logos.py            # Multi-tier deterministic logo resolver
│   ├── generate_event_images.py    # Multi-threaded Pillow banner generator
│   ├── validate_output.py          # Pydantic schema validation
│   └── main.py                     # Pipeline orchestrator
├── tests/
│   ├── test_normalize.py           # Timezone & normalization unit tests
│   ├── test_logo_resolver.py       # Matching & alias unit tests
│   ├── test_image_generator.py     # Banner rendering tests
│   └── test_validation.py          # Pydantic validation tests
├── .gitignore
├── LICENSE
├── README.md
└── requirements.txt
```

---

## 🛠️ Local Development & Testing

### 1. Install Dependencies
```bash
python -m pip install --upgrade pip
pip install -r requirements.txt
```

### 2. Run Test Suite
```bash
python -m unittest discover -s tests -p "test_*.py" -v
```

### 3. Run Pipeline Locally
```bash
python scripts/main.py
```

### 4. Validate Output Schema
```bash
python scripts/validate_output.py output/upcoming_events.json
```

---

## ➕ Adding New Competitions

To monitor an additional league (e.g. Dutch Eredivisie, Portuguese Liga, or Turkish Super Lig), simply append a new entry to `config/competitions.json`:

```json
{
  "id": "eredivisie",
  "name": "Dutch Eredivisie",
  "country": "Netherlands",
  "source_file": "nl.1.json",
  "source_timezone": "Europe/Amsterdam",
  "logo_league_dir": "Netherlands - Eredivisie",
  "enabled": true
}
```

No changes to core Python code are required.
