# Public Web App – Requirements (draft)

Status: draft from discussion on 2026-10-21. Origin column: **user** = requested by the user, **suggested** = proposed by Claude, waiting for the user's review.

## 1. Context

Each Raspberry Pi already detects and tracks vehicles and pedestrians, measures speed and noise, and stores events in local SQLite or Postgres. The web app publishes these statistics on a public map and gives device owners and the operator an admin interface.

The product is sold to **owners**: people who buy a device, set it up and publish its results. The **operator** (the project author) manages all devices.

## 2. Roles

| Role | Can do |
|---|---|
| Public visitor | See the map and aggregated statistics of locations the owner has made public |
| Owner | Claim and configure their own devices, see detailed and raw data, decide what is published |
| Operator | Access all devices (support, updates, training-image collection), manage keys and the fleet |

## 3. Architecture decisions (so far)

- Static frontend on **GitLab Pages**. It holds no secrets and only reads public data.
- Pis upload **minute statistics** over HTTPS to a separate upload endpoint. Each upload is signed with that device's own key.
- Database / API options (decision open, see Q7):

| Option | Cost (2026, verify before deciding) | Notes |
|---|---|---|
| Cloudflare Worker + D1 | free tier (100k requests/day, 100k rows written/day, 5 GB storage); paid from $5/mo | No server to maintain. Store one row per device per minute, or the write limit is hit quickly. |
| Supabase (Postgres) | free 500 MB; Pro $25/mo | Includes authentication and database-level per-row access rules. Close to the existing `PostgresHandler`. |
| Hetzner Cloud VPS (CX23: 2 vCPU, 4 GB RAM, 40 GB SSD, 20 TB traffic) | €3.99/mo + €0.50 IPv4 + 20% backups + VAT ≈ €6/mo | Full control. You maintain the OS, security and backups. Hourly billing, good network and API, servers in Germany and Finland. Prices rose about 33% in April 2026. |
| Contabo Cloud VPS 10 (4 vCPU, 8 GB RAM, 75 GB NVMe, unlimited traffic at 200 Mbit/s) | about €4.50/mo + VAT; automatic backups cost extra | Most resources for the money. Full control, same maintenance as Hetzner. CPU is shared more heavily, support is slower, there's no hourly billing, and there may be a setup fee on short contracts. Prices rose about 22% in June 2026. |

- Map: MapLibre/Leaflet with OpenFreeMap or self-hosted PMTiles. No per-request map fees.
- Rejected: Pis pushing data into the GitLab repo (every push starts a Pages build, the free plan's CI minutes run out, and the repo keeps growing).

## 4. Requirements

### 4.1 Public interface

| ID | Requirement | Origin |
|---|---|---|
| rwa-1 | Map showing all public measuring locations | user |
| rwa-2 | Current statistics for a location (most recent period), shown on click | user |
| rwa-3 | Historical statistics for a location (day / week / month / year) | user |
| rwa-4 | Counts of cars and pedestrians, plus other detected classes (bicycle, truck, bus, motorcycle) | user |
| rwa-5 | Speeds of cars and pedestrians: average, V85 (speed 85% of vehicles stay under), distribution. Only speeds the Pi marks as valid (`speed_is_valid`). | user |
| rwa-6 | Dangerous traffic situations, shown publicly only as totals per period | user |
| rwa-7 | Statistics for decision makers (see rwa-12) | user |
| rwa-8 | Periods with missing data shown on charts ("sensor offline"), so an outage doesn't look like zero traffic | suggested |
| rwa-9 | Compare periods (week vs week, before vs after a change on the street) | suggested |
| rwa-10 | Data export (CSV / open data) | suggested |
| rwa-11 | Noise level (dB), already stored as `noise_db_a` | suggested |
| rwa-12 | Decision-maker indicators: average daily traffic, peak hour, V85, % over the speed limit, share of heavy vehicles, pedestrian volume, dangerous situations per 1,000 vehicles | suggested |
| rwa-13 | Methodology page: how measurement works, stated accuracy, what isn't counted | suggested |
| rwa-14 | Czech + English, works on mobile | suggested |
| rwa-15 | Embeddable widget for a single location (iframe) | suggested |
| rwa-16 | Removed devices keep their history on the map, marked "inactive since …" | user (Q1) |

### 4.2 Owner and operator administration

| ID | Requirement | Origin |
|---|---|---|
| rwa-20 | User accounts with roles: owner sees only their own devices, operator sees all | user (Q4) |
| rwa-21 | Claiming a device: the operator prepares the device and its key before shipping; the owner enters a claim code (e.g. a QR code on the box), then sets the location (lat/lon, camera direction) | user / suggested |
| rwa-22 | Uptime per device | user |
| rwa-23 | Raw statistics view (minute data) per device, including rejected uploads | user |
| rwa-24 | Remove a device: revoke its key immediately, keep its history (rwa-16) | user |
| rwa-25 | Publishing settings per device: public / private / public with a delay | suggested |
| rwa-26 | Owner-only detail: exact times of events, raw data, images | user (Q2) |
| rwa-27 | Replace a device's key without removing the device | suggested |
| rwa-28 | Device states: active / maintenance / disabled (data from maintenance mode isn't published) | suggested |
| rwa-29 | Alert the owner and operator when a device goes offline (email / Telegram) | suggested |
| rwa-30 | Log of admin actions | suggested |
| rwa-31 | Version history of zone settings and speed calibration; charts mark when they change | suggested |

### 4.3 Device upload and data reliability

| ID | Requirement | Origin |
|---|---|---|
| rwa-40 | Pis upload minute statistics every 1–5 min | user |
| rwa-41 | Each device has its own key; the database stores only the key hash (or a public key) | user / suggested |
| rwa-42 | Each upload is signed (HMAC-SHA256 or Ed25519) and carries a timestamp; uploads older than about 5 min are rejected so captured requests can't be replayed | suggested |
| rwa-43 | `(device_id, minute)` is unique; repeat uploads overwrite, so retries never double-count | suggested |
| rwa-44 | Values are checked on arrival (no minutes in the future, counts within physical limits, a device writes only to its own station); failures are logged | suggested |
| rwa-45 | The Pi keeps minutes that haven't been uploaded in local SQLite and resends them when the connection returns | suggested |
| rwa-46 | Heartbeat with the upload: alive, temperature, FPS, disk, software version, camera status | suggested |
| rwa-47 | Totals and retention: minutes → hours → days; minute rows deleted after N months | suggested |
| rwa-48 | Dangerous-situation events use a separate upload channel (single events, not minute totals) | suggested |
| rwa-49 | The read API allows requests only from the Pages domain (CORS) and caches responses for about 60 s | suggested |

### 4.4 Training data and custom models

| ID | Requirement | Origin |
|---|---|---|
| rwa-50 | Collect images for model training, only from operator-managed devices, on a separate server | user (Q3) |
| rwa-51 | Owner consent switch per device for image collection | suggested |
| rwa-52 | Operator chooses what to collect (device + time range, or frames with low detection confidence) | suggested |
| rwa-53 | Faces and number plates blurred on the Pi before upload; images kept only for a limited time | suggested |
| rwa-54 | Notification by vehicle type (garbage truck, bus, tractor, ambulance, oversized truck) using a custom model | user / suggested |
| rwa-55 | Notification of unusual events (vehicle stopped in a no-stopping area, vehicle in a pedestrian zone), built as rules on top of tracking | suggested |

## 5. Risks

| ID | Risk | Mitigation |
|---|---|---|
| risk-1 | Recognising specific vehicles or number plates in public space amounts to tracking people; private plate recognition on a public street in the Czech Republic is legally very questionable | Don't offer recognition of specific vehicles on public streets. Allow it only on the owner's private property, if at all. Offer vehicle types (rwa-54) instead. |
| risk-2 | Privacy: exact event times or images reveal too much | Public sees only totals (rwa-6); detail is owner-only (rwa-26); blurring (rwa-53) |
| risk-3 | GDPR roles: the owner is responsible for the data (controller), the operator processes it on their behalf (processor) | Data-processing agreement with each owner; state operator access in the purchase terms. Legal review needed. |
| risk-4 | A stolen Pi's key is copied (the Pi 5 has no secure chip for keys) | Per-device keys, revocation (rwa-24, rwa-27), checks on arrival (rwa-44) |
| risk-5 | An outage is mistaken for zero traffic, so the statistics lose credibility | Heartbeat (rwa-46), outages shown on charts (rwa-8) |
| risk-6 | Moving zones or recalibrating breaks comparisons with earlier data | Version history of zone settings (rwa-31) |
| risk-7 | Free tiers or prices change (Hetzner raised prices about 33% in April 2026, Contabo about 22% in June 2026) | Keep the API layer thin so it can move between providers |
| risk-8 | Public numbers are challenged | Methodology page with stated accuracy (rwa-13) |

## 6. Open questions

| ID | Question |
|---|---|
| Q5 | Do owners install devices themselves (mount the camera, draw zones), or does the operator install them? |
| Q6 | Which types of dangerous situations are needed: speeding, high speed at night, wrong way, near-misses between a car and a pedestrian, vehicles in a pedestrian zone? |
| Q7 | Database / API choice: Cloudflare D1, Supabase, Hetzner VPS or Contabo VPS |
| Q8 | How fresh must "current" statistics be (1 min / 5 min / 15 min)? |
