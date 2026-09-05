"""Centralized configuration for the Alternance Scraper.

All tunables — keywords, ROME codes, company lists, scoring weights,
and environment-variable names — live here so the rest of the codebase
stays declarative.
"""

from __future__ import annotations

import os
from typing import Dict, List


# ======================================================================
# 1. Search keywords (used by WTTJ, ATS scrapers)
# ======================================================================

SEARCH_KEYWORDS: List[str] = [
    "finance",
    "contrôle de gestion",
    "audit",
    "trésorerie",
    "marketing",
    "marketing digital",
    "business development",
    "commercial",
    "data analyst",
    "business intelligence",
    "consulting",
    "stratégie",
    "supply chain",
    "achats",
    "logistique",
]

# ======================================================================
# 2. ROME codes (La Bonne Alternance / France Travail)
# ======================================================================

ROME_CODES: List[str] = [
    "M1201",  # Analyse et ingénierie financière
    "M1202",  # Audit et contrôle comptables et financiers
    "M1204",  # Contrôle de gestion
    "M1207",  # Trésorerie et financement
    "M1705",  # Marketing
    "E1401",  # Développement et promotion publicitaire
    "E1103",  # Communication
    "D1406",  # Management en force de vente
    "D1407",  # Relation technico-commerciale
    "D1402",  # Relation commerciale grands comptes
    "M1403",  # Études et prospectives socio-économiques
    "M1402",  # Conseil en organisation et management
    "N1301",  # Conception et organisation chaîne logistique
    "M1101",  # Achats
]

# Maximum ROME codes per LBA API call (to avoid timeouts).
LBA_ROME_BATCH_SIZE: int = 5

# ======================================================================
# 3. Geography
# ======================================================================

PARIS_LAT: float = 48.8566
PARIS_LON: float = 2.3522
SEARCH_RADIUS_KM: int = 30

# Île-de-France department codes (for France Travail)
IDF_DEPARTMENTS: List[str] = [
    "75", "77", "78", "91", "92", "93", "94", "95",
]

# ======================================================================
# 4. Filtering — negative / positive signals
# ======================================================================

NEGATIVE_PATTERNS: List[str] = [
    "bac+5 obligatoire",
    "bac+5 uniquement",
    "bac+5 requis",
    "master 2 requis",
    "master 2 obligatoire",
    "stage de fin d'études",
    "stage de fin d'etudes",
    "stage 6 mois",
    "cdi uniquement",
    "expérience 5 ans",
]

POSITIVE_PATTERNS: Dict[str, int] = {
    # Education level match
    "bac+3": 3,
    "bac+4": 3,
    "licence": 2,
    "bachelor": 2,
    "l3": 2,
    "m1": 2,
    # Contract type match
    "alternance": 1,
    "apprentissage": 1,
    "contrat d'apprentissage": 2,
    "contrat de professionnalisation": 2,
    # Start date match
    "septembre 2027": 5,
    "sept 2027": 5,
    "rentrée 2027": 5,
    "rentree 2027": 5,
    "2027-2028": 4,
}

# Minimum score for an offer to pass the filter (0 = accept everything
# that isn't excluded by negative patterns).
MIN_SCORE: int = 4

# ======================================================================
# 5. WTTJ — Algolia credentials (public, embedded in their frontend JS)
# ======================================================================

WTTJ_ALGOLIA_APP_ID: str = os.getenv("WTTJ_ALGOLIA_APP_ID") or "CSEKHVMS53"
WTTJ_ALGOLIA_API_KEY: str = os.getenv("WTTJ_ALGOLIA_API_KEY") or "4bd8f6215d0cc52b26430765769e65a0"
WTTJ_ALGOLIA_INDEX: str = "wk_cms_jobs_production"
WTTJ_HITS_PER_PAGE: int = 50

# ======================================================================
# 6. La Bonne Alternance
# ======================================================================

LBA_BASE_URL: str = "https://api.apprentissage.beta.gouv.fr/api/v1/jobs"
LBA_CALLER: str = "alternance-scraper-essec"
LBA_API_KEY: str = os.getenv("LBA_API_KEY", "")

# ======================================================================
# 7. France Travail / 1jeune1solution (optional — needs OAuth2)
# ======================================================================

FT_TOKEN_URL: str = (
    "https://entreprise.francetravail.fr/connexion/oauth2/access_token"
)
FT_API_URL: str = (
    "https://api.francetravail.io/partenaire/offresdemploi/v2/offres/search"
)
FT_CLIENT_ID: str = os.getenv("FRANCE_TRAVAIL_CLIENT_ID", "")
FT_CLIENT_SECRET: str = os.getenv("FRANCE_TRAVAIL_CLIENT_SECRET", "")

# ======================================================================
# 8. ATS company lists (SmartRecruiters / Greenhouse / Lever)
# ======================================================================

SMARTRECRUITERS_COMPANIES: List[str] = [
    "Altarea",           # 24 postings — real estate, finance, HR
    "Devoteam",          # 77 postings — consulting, cloud, data
    "SMCP",              # 10 postings — fashion (Sandro, Maje, Claudie Pierlot)
    "COVEA1",            # 67 postings — insurance (MAAF, MMA, GMF)
    "SchneiderElectric",  # 82 postings — energy management, automation
    "ENGIE",             # 119 postings — energy, services
    "Thales",            # 110 postings — defense, aerospace, digital
    "DassaultSystemes",  # 11 postings — 3D software, engineering
    "Carrefour",         # 41 postings — retail, supply chain
    "Mazars",            # 64 postings — audit, accounting, consulting
    "natixis",           # 12 postings — banking, finance, asset mgmt
    "Danone",            # 3 postings — FMCG, marketing, supply chain
]

GREENHOUSE_COMPANIES: List[str] = [
    "doctolib",
    "mirakl",
    "algolia",
    "aircall",
    "shifttechnology",
    "teads",
]

LEVER_COMPANIES: List[str] = [
    "pennylane",       # fintech/accounting unicorn
    "spendesk",        # expense management
    "payfit",          # payroll/HR platform
    "qonto",           # business banking
    "contentsquare",   # digital analytics
    "criteo",          # adtech / data science
]

# ATS keyword patterns to detect alternance offers in titles/descriptions.
ATS_ALTERNANCE_KEYWORDS: List[str] = [
    "alternance",
    "alternant",
    "apprenti",
    "apprentice",
    "apprentissage",
    "apprenticeship",
    "contrat pro",
]

# Delay between ATS API calls in seconds (respect rate limits).
ATS_REQUEST_DELAY: float = 1.5

# ======================================================================
# 9. Notifications
# ======================================================================

TELEGRAM_BOT_TOKEN: str = os.getenv("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT_ID: str = os.getenv("TELEGRAM_CHAT_ID", "")
DISCORD_WEBHOOK_URL: str = os.getenv("DISCORD_WEBHOOK_URL", "")

# Maximum Telegram message length (API limit).
TELEGRAM_MAX_LENGTH: int = 4096

# Send a heartbeat message when no new offers are found?
HEARTBEAT_ENABLED: bool = False

# ======================================================================
# 10. Database
# ======================================================================

DB_PATH: str = os.getenv("DB_PATH", "seen_jobs.db")

# ======================================================================
# 11. Misc
# ======================================================================

# Set DRY_RUN=1 to skip notifications (useful for local testing).
DRY_RUN: bool = os.getenv("DRY_RUN", "0") == "1"

# HTTP request timeout in seconds.
HTTP_TIMEOUT: int = 30

# User-Agent for requests.
USER_AGENT: str = (
    "AlternanceScraper/1.0 (ESSEC-BBA; contact@example.com)"
)
