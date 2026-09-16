# ⚽ Football Events Data & Image Pipeline

[![Update Football Events](https://github.com/hashirhamxa/football-data-hash/actions/workflows/update-events.yml/badge.svg)](https://github.com/hashirhamxa/football-data-hash/actions/workflows/update-events.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Python 3.10+](https://img.shields.io/badge/Python-3.10%2B-brightgreen.svg)](https://www.python.org/)

A production-ready automated pipeline that ingests upcoming football fixtures using a **Multi-Source Architecture (ESPN Public API primary + OpenFootball secondary fallback)**, resolves high-resolution team crests, renders broadcast-grade 1200x630 matchday banner cards, and publishes normalized, Android-ready JSON via GitHub Raw URLs.

**100% Free & Serverless**: Runs completely on GitHub Actions on a scheduled cron (every 6 hours) with zero paid infrastructure required.

---

## 🚀 Live Raw Endpoints (Android Ready)

### 1. Global Feeds (All Leagues Combined)

| Feed | Raw GitHub Endpoint | Description |
| :--- | :--- | :--- |
| **Today's Matches (PKT)** | [`https://raw.githubusercontent.com/hashirhamxa/football-data-hash/main/output/today_events.json`](https://raw.githubusercontent.com/hashirhamxa/football-data-hash/main/output/today_events.json) | Matches taking place **Today in Pakistan Time (PKT, Asia/Karachi)** |
| **Tomorrow's Matches (PKT)** | [`https://raw.githubusercontent.com/hashirhamxa/football-data-hash/main/output/tomorrow_events.json`](https://raw.githubusercontent.com/hashirhamxa/football-data-hash/main/output/tomorrow_events.json) | Matches taking place **Tomorrow in Pakistan Time (PKT, Asia/Karachi)** |
| **All Upcoming Matches** | [`https://raw.githubusercontent.com/hashirhamxa/football-data-hash/main/output/upcoming_events.json`](https://raw.githubusercontent.com/hashirhamxa/football-data-hash/main/output/upcoming_events.json) | Full 30-day schedule across all monitored competitions |
| **Competition Status** | [`https://raw.githubusercontent.com/hashirhamxa/football-data-hash/main/output/competition_status.json`](https://raw.githubusercontent.com/hashirhamxa/football-data-hash/main/output/competition_status.json) | Upstream provider status and availability report |
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
| **UEFA Europa League** | `europa-league` | [`today.json`](https://raw.githubusercontent.com/hashirhamxa/football-data-hash/main/output/competitions/europa-league/today.json) | [`tomorrow.json`](https://raw.githubusercontent.com/hashirhamxa/football-data-hash/main/output/competitions/europa-league/tomorrow.json) | [`upcoming.json`](https://raw.githubusercontent.com/hashirhamxa/football-data-hash/main/output/competitions/europa-league/upcoming.json) |
| **UEFA Conference League** | `conference-league` | [`today.json`](https://raw.githubusercontent.com/hashirhamxa/football-data-hash/main/output/competitions/conference-league/today.json) | [`tomorrow.json`](https://raw.githubusercontent.com/hashirhamxa/football-data-hash/main/output/competitions/conference-league/tomorrow.json) | [`upcoming.json`](https://raw.githubusercontent.com/hashirhamxa/football-data-hash/main/output/competitions/conference-league/upcoming.json) |

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
    @SerialName("source_date") val sourceDate: String? = null,
    @SerialName("match_date") val matchDate: String,
    @SerialName("match_date_utc") val matchDateUtc: String? = null,
    @SerialName("match_date_pkt") val matchDatePkt: String? = null,
    @SerialName("start_time_utc") val startTimeUtc: String?,
    @SerialName("start_time_pkt") val startTimePkt: String?,
    @SerialName("start_timestamp") val startTimestamp: Long?,
    @SerialName("display_date") val displayDate: String? = null,
    @SerialName("display_time") val displayTime: String? = null,
    @SerialName("display_timezone") val displayTimezone: String? = null,
    @SerialName("time_status") val timeStatus: String, // "confirmed" | "tbd"
    @SerialName("home_team") val homeTeam: TeamInfo,
    @SerialName("away_team") val awayTeam: TeamInfo,
    @SerialName("event_image_url") val eventImageUrl: String,
    @SerialName("data_source") val dataSource: DataSourceMeta,
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
    @SerialName("espn_id") val espnId: String? = null,
    @SerialName("logo_url") val logoUrl: String,
    @SerialName("logo_resolution") val logoResolution: LogoResolution
)

@Serializable
data class LogoResolution(
    val source: String, // "espn_direct" | "exact" | "alias" | "fuzzy" | "fallback"
    val confidence: Double,
    @SerialName("matched_name") val matchedName: String? = null,
    @SerialName("is_fallback") val isFallback: Boolean
)

@Serializable
data class DataSourceMeta(
    val provider: String,
    val season: String? = null,
    @SerialName("source_url") val sourceUrl: String? = null
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

Every fixture automatically generates a unique 1200x630 matchday banner featuring the competition header, high-res team crests, "VS" emblem, and kickoff times in UTC & PKT:

```
+-----------------------------------------------------------------------------+
|               [ UEFA EUROPA LEAGUE  •  REGULAR FIXTURE ]                    |
|                                                                             |
|      +---------------+                       +---------------+              |
|      |               |                       |               |              |
|      |   HOME LOGO   |       (  VS  )        |   AWAY LOGO   |              |
|      |               |                       |               |              |
|      +---------------+                       +---------------+              |
|         AC Milan                                 Benfica                    |
|                                                                             |
|          +-------------------------------------------------------+          |
|          |  📅 WEDNESDAY, 16 SEP 2026  |  ⏰ 19:00 UTC / 00:00 PKT |          |
|          +-------------------------------------------------------+          |
+-----------------------------------------------------------------------------+
```

---

## ⚖️ Upstream Data Sources & Licenses

| Source | Identifier / URL | Type | Purpose |
| :--- | :--- | :--- | :--- |
| **ESPN Public Scoreboard API** | `site.api.espn.com/apis/site/v2/sports/soccer/{slug}/scoreboard` | Primary Live Source | Live scores, confirmed UTC kickoffs, official club logos |
| **OpenFootball** | [openfootball/football.json](https://github.com/openfootball/football.json) | Secondary Fallback | Historical fixtures, season backup schedules |
| **Luuk Hopman Football Logos** | [luukhopman/football-logos](https://github.com/luukhopman/football-logos) | Logo Catalog | European club crests |
| **Leo4815162342 Logos** | [Leo4815162342/football-logos](https://github.com/Leo4815162342/football-logos) | Fallback Catalog | Secondary crests and national teams |

---

## 🛠️ Local Development & Testing

```bash
# 1. Run Complete Pipeline
python scripts/main.py

# 2. Run Test Suite (23 automated unit/integration tests)
python -m unittest discover -s tests -p "test_*.py" -v
```
