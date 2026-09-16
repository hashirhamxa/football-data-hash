# ⚽ Football Events Data & Image Pipeline

[![Update Football Events](https://github.com/hashirhamxa/football-data-hash/actions/workflows/update-events.yml/badge.svg)](https://github.com/hashirhamxa/football-data-hash/actions/workflows/update-events.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Python 3.10+](https://img.shields.io/badge/Python-3.10%2B-brightgreen.svg)](https://www.python.org/)

A production-ready automated pipeline that ingests upcoming football fixtures, resolves high-resolution team crests, renders broadcast-grade 1200x630 matchday banner cards, and publishes normalized, Android-ready JSON via GitHub Raw URLs.

**100% Free & Serverless**: Runs completely on GitHub Actions on a scheduled cron (every 6 hours) with zero paid infrastructure required.

---

## 🚀 Live Raw Endpoints (Android Ready)

### 1. Global Feeds (All Leagues Combined)

| Feed | Raw GitHub Endpoint | Description |
| :--- | :--- | :--- |
| **Today's Matches (PKT)** | [`https://raw.githubusercontent.com/hashirhamxa/football-data-hash/main/output/today_events.json`](https://raw.githubusercontent.com/hashirhamxa/football-data-hash/main/output/today_events.json) | Matches taking place **Today in Pakistan Time (PKT)** |
| **Tomorrow's Matches (PKT)** | [`https://raw.githubusercontent.com/hashirhamxa/football-data-hash/main/output/tomorrow_events.json`](https://raw.githubusercontent.com/hashirhamxa/football-data-hash/main/output/tomorrow_events.json) | Matches taking place **Tomorrow in Pakistan Time (PKT)** |
| **All Upcoming Matches** | [`https://raw.githubusercontent.com/hashirhamxa/football-data-hash/main/output/upcoming_events.json`](https://raw.githubusercontent.com/hashirhamxa/football-data-hash/main/output/upcoming_events.json) | Full 30-day schedule across all monitored competitions |
| **Competition Status** | [`https://raw.githubusercontent.com/hashirhamxa/football-data-hash/main/output/competition_status.json`](https://raw.githubusercontent.com/hashirhamxa/football-data-hash/main/output/competition_status.json) | Upstream data availability and seasons |
| **Unmatched Teams** | [`https://raw.githubusercontent.com/hashirhamxa/football-data-hash/main/output/unmatched_teams.json`](https://raw.githubusercontent.com/hashirhamxa/football-data-hash/main/output/unmatched_teams.json) | Teams using fallback initials badges |

---

### 2. Tournament Category Feeds (`output/competitions/{id}/`)

Each tournament has its dedicated directory containing `today.json`, `tomorrow.json`, and `upcoming.json`:

| Competition | Folder ID | Today (PKT) | Tomorrow (PKT) | Upcoming 30-Day |
| :--- | :--- | :--- | :--- | :--- |
| **English Premier League** | `premier-league` | [`today.json`](https://raw.githubusercontent.com/hashirhamxa/football-data-hash/main/output/competitions/premier-league/today.json) | [`tomorrow.json`](https://raw.githubusercontent.com/hashirhamxa/football-data-hash/main/output/competitions/premier-league/tomorrow.json) | [`upcoming.json`](https://raw.githubusercontent.com/hashirhamxa/football-data-hash/main/output/competitions/premier-league/upcoming.json) |
| **Spanish La Liga** | `la-liga` | [`today.json`](https://raw.githubusercontent.com/hashirhamxa/football-data-hash/main/output/competitions/la-liga/today.json) | [`tomorrow.json`](https://raw.githubusercontent.com/hashirhamxa/football-data-hash/main/output/competitions/la-liga/tomorrow.json) | [`upcoming.json`](https://raw.githubusercontent.com/hashirhamxa/football-data-hash/main/output/competitions/la-liga/upcoming.json) |
| **Italian Serie A** | `serie-a` | [`today.json`](https://raw.githubusercontent.com/hashirhamxa/football-data-hash/main/output/competitions/serie-a/today.json) | [`tomorrow.json`](https://raw.githubusercontent.com/hashirhamxa/football-data-hash/main/output/competitions/serie-a/tomorrow.json) | [`upcoming.json`](https://raw.githubusercontent.com/hashirhamxa/football-data-hash/main/output/competitions/serie-a/upcoming.json) |
| **German Bundesliga** | `bundesliga` | [`today.json`](https://raw.githubusercontent.com/hashirhamxa/football-data-hash/main/output/competitions/bundesliga/today.json) | [`tomorrow.json`](https://raw.githubusercontent.com/hashirhamxa/football-data-hash/main/output/competitions/bundesliga/tomorrow.json) | [`upcoming.json`](https://raw.githubusercontent.com/hashirhamxa/football-data-hash/main/output/competitions/bundesliga/upcoming.json) |
| **French Ligue 1** | `ligue-1` | [`today.json`](https://raw.githubusercontent.com/hashirhamxa/football-data-hash/main/output/competitions/ligue-1/today.json) | [`tomorrow.json`](https://raw.githubusercontent.com/hashirhamxa/football-data-hash/main/output/competitions/ligue-1/tomorrow.json) | [`upcoming.json`](https://raw.githubusercontent.com/hashirhamxa/football-data-hash/main/output/competitions/ligue-1/upcoming.json) |
| **English Championship** | `championship` | [`today.json`](https://raw.githubusercontent.com/hashirhamxa/football-data-hash/main/output/competitions/championship/today.json) | [`tomorrow.json`](https://raw.githubusercontent.com/hashirhamxa/football-data-hash/main/output/competitions/championship/tomorrow.json) | [`upcoming.json`](https://raw.githubusercontent.com/hashirhamxa/football-data-hash/main/output/competitions/championship/upcoming.json) |
| **UEFA Champions League** | `champions-league` | [`today.json`](https://raw.githubusercontent.com/hashirhamxa/football-data-hash/main/output/competitions/champions-league/today.json) | [`tomorrow.json`](https://raw.githubusercontent.com/hashirhamxa/football-data-hash/main/output/competitions/champions-league/tomorrow.json) | [`upcoming.json`](https://raw.githubusercontent.com/hashirhamxa/football-data-hash/main/output/competitions/champions-league/upcoming.json) |

---

## 📱 Android Integration Guide

### 1. Kotlin Data Models (Kotlinx Serialization / Gson / Moshi)

```kotlin
import kotlinx.serialization.Serializable
import kotlinx.serialization.SerialName

@Serializable
data class EventsFeedResponse(
    val version: String,
    val competition: CompetitionHeader? = null,
    val timezone: String? = null,
    @SerialName("timezone_label") val timezoneLabel: String? = null,
    @SerialName("target_date_pkt") val targetDatePkt: String? = null,
    @SerialName("target_day_name") val targetDayName: String? = null,
    @SerialName("feed_type") val feedType: String? = null,
    @SerialName("generated_at") val generatedAt: String,
    @SerialName("total_events") val totalEvents: Int,
    val events: List<FootballEvent>
)

@Serializable
data class CompetitionHeader(
    val id: String,
    val name: String,
    val country: String
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
import retrofit2.http.Path

interface FootballEventsApi {
    // Global Feeds
    @GET("hashirhamxa/football-data-hash/main/output/today_events.json")
    suspend fun getGlobalTodayPKT(): EventsFeedResponse

    @GET("hashirhamxa/football-data-hash/main/output/tomorrow_events.json")
    suspend fun getGlobalTomorrowPKT(): EventsFeedResponse

    @GET("hashirhamxa/football-data-hash/main/output/upcoming_events.json")
    suspend fun getAllUpcomingEvents(): EventsFeedResponse

    // League-Specific Feeds
    @GET("hashirhamxa/football-data-hash/main/output/competitions/{leagueId}/today.json")
    suspend fun getLeagueTodayPKT(@Path("leagueId") leagueId: String): EventsFeedResponse

    @GET("hashirhamxa/football-data-hash/main/output/competitions/{leagueId}/tomorrow.json")
    suspend fun getLeagueTomorrowPKT(@Path("leagueId") leagueId: String): EventsFeedResponse

    @GET("hashirhamxa/football-data-hash/main/output/competitions/{leagueId}/upcoming.json")
    suspend fun getLeagueUpcoming(@Path("leagueId") leagueId: String): EventsFeedResponse
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
│   ├── upcoming_events.json        # 30-day global upcoming events
│   ├── today_events.json           # Global today matches (PKT)
│   ├── tomorrow_events.json        # Global tomorrow matches (PKT)
│   ├── competitions/               # Tournament Category Folders
│   │   ├── premier-league/         # (today.json, tomorrow.json, upcoming.json)
│   │   ├── la-liga/
│   │   ├── serie-a/
│   │   ├── bundesliga/
│   │   ├── ligue-1/
│   │   ├── championship/
│   │   └── champions-league/
│   ├── competition_status.json     # Upstream status report
│   ├── unmatched_teams.json        # Fallback/low-confidence teams report
│   └── images/                     # Generated 1200x630 matchday banner cards
├── scripts/
│   ├── fetch_fixtures.py           # Ingestion from OpenFootball
│   ├── normalize_fixtures.py       # Timezone conversions and event normalization
│   ├── resolve_logos.py            # Multi-tier deterministic logo resolver
│   ├── generate_event_images.py    # Multi-threaded Pillow banner generator
│   ├── fetch_today_events.py       # Today (PKT) filter & publisher
│   ├── fetch_tomorrow_events.py    # Tomorrow (PKT) filter & publisher
│   ├── generate_competition_feeds.py # Tournament category feeds generator
│   ├── validate_output.py          # Pydantic schema validation
│   └── main.py                     # Pipeline orchestrator
├── tests/
│   ├── test_normalize.py           # Timezone & normalization unit tests
│   ├── test_logo_resolver.py       # Matching & alias unit tests
│   ├── test_image_generator.py     # Banner rendering tests
│   ├── test_today_tomorrow.py      # PKT Today/Tomorrow unit tests
│   ├── test_competition_feeds.py   # Tournament category unit tests
│   └── test_validation.py          # Pydantic validation tests
├── .gitignore
├── LICENSE
├── README.md
└── requirements.txt
```

---

## 🛠️ Local Development & Testing

### 1. Run Complete Pipeline
```bash
python scripts/main.py
```

### 2. Run Dedicated Generators
```bash
# Global today matches in PKT
python scripts/fetch_today_events.py

# Global tomorrow matches in PKT
python scripts/fetch_tomorrow_events.py

# Tournament category feeds
python scripts/generate_competition_feeds.py
```

### 3. Run Test Suite
```bash
python -m unittest discover -s tests -p "test_*.py" -v
```
