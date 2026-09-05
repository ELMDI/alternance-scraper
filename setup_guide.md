# 🚀 Guide de setup — Alternance Scraper

Ce guide vous accompagne pas à pas pour configurer et déployer le scraper
d'offres d'alternance sur GitHub Actions.

---

## Table des matières

1. [Créer le bot Telegram](#1-créer-le-bot-telegram)
2. [Récupérer votre Chat ID Telegram](#2-récupérer-votre-chat-id-telegram)
3. [Créer un webhook Discord (optionnel)](#3-créer-un-webhook-discord-optionnel)
4. [S'inscrire à La Bonne Alternance API (optionnel)](#4-sinscrire-à-la-bonne-alternance-api-optionnel)
5. [S'inscrire à l'API France Travail (optionnel)](#5-sinscrire-à-lapi-france-travail-optionnel)
6. [Configurer les GitHub Secrets](#6-configurer-les-github-secrets)
7. [Déployer et tester](#7-déployer-et-tester)
8. [Personnaliser la configuration](#8-personnaliser-la-configuration)

---

## 1. Créer le bot Telegram

1. Ouvrez Telegram et cherchez **@BotFather**
2. Envoyez la commande : `/newbot`
3. Donnez un **nom** au bot (ex: `Alternance Tracker`)
4. Donnez un **username** au bot (ex: `essec_alternance_bot`)
5. BotFather vous renvoie un message contenant le **token** :
   ```
   Use this token to access the HTTP API:
   123456789:ABCDefGhIjKlMnOpQrStUvWxYz
   ```
6. **Copiez ce token** — c'est votre `TELEGRAM_BOT_TOKEN`

## 2. Récupérer votre Chat ID Telegram

1. Ouvrez une conversation avec votre bot et envoyez-lui un message (ex: `/start` ou `hello`)
2. Dans votre navigateur, ouvrez :
   ```
   https://api.telegram.org/bot<VOTRE_TOKEN>/getUpdates
   ```
   (remplacez `<VOTRE_TOKEN>` par le token obtenu à l'étape 1)
3. Cherchez dans la réponse JSON le champ `"chat":{"id": 123456789}` :
   ```json
   {
     "result": [{
       "message": {
         "chat": {
           "id": 123456789,
           "type": "private"
         }
       }
     }]
   }
   ```
4. **Copiez cet ID** — c'est votre `TELEGRAM_CHAT_ID`

> **Astuce :** Pour un groupe Telegram, ajoutez le bot au groupe, envoyez
> un message, et le chat ID sera négatif (ex: `-1001234567890`).

## 3. Créer un webhook Discord (optionnel)

1. Dans votre serveur Discord, allez dans **Paramètres du serveur** → **Intégrations** → **Webhooks**
2. Cliquez **Nouveau Webhook**
3. Choisissez le canal de destination (ex: `#alternance`)
4. Cliquez **Copier l'URL du Webhook**
5. L'URL ressemble à :
   ```
   https://discord.com/api/webhooks/1234567890/AbCdEfGh...
   ```
6. **Copiez cette URL** — c'est votre `DISCORD_WEBHOOK_URL`

## 4. S'inscrire à La Bonne Alternance API (optionnel)

> L'API LBA fonctionne mieux avec un token d'accès. Sans token, elle 
> peut toujours fonctionner mais pourrait être rate-limitée.

1. Rendez-vous sur https://api.apprentissage.beta.gouv.fr
2. Créez un compte (connexion par lien magique envoyé par email)
3. Accédez à votre dashboard et créez une clé API
4. **Copiez la clé** — c'est votre `LBA_API_KEY`

## 5. S'inscrire à l'API France Travail (optionnel)

> Ce module est **totalement optionnel**. La Bonne Alternance agrège déjà
> la majorité des offres de France Travail. Ce module sert de complément.

1. Rendez-vous sur https://francetravail.io/data/api
2. Créez un compte développeur
3. Souscrivez à l'API **« Offres d'emploi v2 »**
4. Récupérez votre `Client ID` et `Client Secret`
5. Ce sont vos `FRANCE_TRAVAIL_CLIENT_ID` et `FRANCE_TRAVAIL_CLIENT_SECRET`

## 6. Configurer les GitHub Secrets

1. Allez dans votre repository GitHub → **Settings** → **Secrets and variables** → **Actions**
2. Cliquez **New repository secret** pour chacun des secrets ci-dessous :

| Secret | Obligatoire | Description |
|--------|:-----------:|-------------|
| `TELEGRAM_BOT_TOKEN` | ✅ | Token du bot Telegram |
| `TELEGRAM_CHAT_ID` | ✅ | Votre Chat ID Telegram |
| `DISCORD_WEBHOOK_URL` | ⬜ | URL du webhook Discord (secours) |
| `LBA_API_KEY` | ⬜ | Clé API La Bonne Alternance |
| `FRANCE_TRAVAIL_CLIENT_ID` | ⬜ | Client ID France Travail |
| `FRANCE_TRAVAIL_CLIENT_SECRET` | ⬜ | Client Secret France Travail |

> **Note :** Les clés Algolia WTTJ sont pré-configurées dans le code
> (`CSEKHVMS53` / `4bd8f6215d0cc52b26430765769e65a0`). Si elles
> changent, vous pouvez les override via les secrets `WTTJ_ALGOLIA_APP_ID`
> et `WTTJ_ALGOLIA_API_KEY`.

## 7. Déployer et tester

### Premier déploiement

```bash
# 1. Cloner ou créer le repo
git init alternance-scraper
cd alternance-scraper

# 2. Copier tous les fichiers du projet

# 3. Initialiser la base de données vide
python -c "from src.dedup import DedupStore; DedupStore().open(); print('DB created')"

# 4. Commit initial
git add .
git commit -m "feat: initial alternance scraper setup"
git push origin main
```

### Test en local

```bash
# Créer un fichier .env avec vos secrets
cat > .env << EOF
TELEGRAM_BOT_TOKEN=123456789:ABCDef...
TELEGRAM_CHAT_ID=123456789
DISCORD_WEBHOOK_URL=https://discord.com/api/webhooks/...
DRY_RUN=1
EOF

# Installer les dépendances
pip install -r requirements.txt

# Lancer en mode dry-run (pas de notifications)
DRY_RUN=1 python -m src.main

# Lancer avec notifications
python -m src.main
```

### Déclencher manuellement sur GitHub

1. Allez dans votre repo → **Actions** → **Daily Alternance Scraper**
2. Cliquez **Run workflow**
3. Optionnel : cochez **dry_run** pour tester sans envoyer de notifications
4. Cliquez **Run workflow**

## 8. Personnaliser la configuration

### Ajouter des entreprises ATS

Éditez `src/config.py` et ajoutez des identifiants dans les listes :

```python
# SmartRecruiters — identifiant = slug dans l'URL career page
SMARTRECRUITERS_COMPANIES = [
    "SopraSteria",
    "Ubisoft",
    "VotreEntreprise",  # ← ajoutez ici
]

# Greenhouse — token = slug du job board
GREENHOUSE_COMPANIES = [
    "doctolib",
    "votre-entreprise",  # ← ajoutez ici
]

# Lever — slug de l'entreprise
LEVER_COMPANIES = [
    "brevo",
    "votre-entreprise",  # ← ajoutez ici
]
```

### Modifier les mots-clés

```python
SEARCH_KEYWORDS = [
    "finance",
    "votre domaine",  # ← ajoutez ici
]
```

### Ajuster le scoring

```python
# Augmenter le score minimum pour ne garder que les offres très pertinentes
MIN_SCORE = 3

# Ajouter des patterns positifs
POSITIVE_PATTERNS["école de commerce"] = 3
```

---

## ❓ FAQ

### Le scraper ne trouve aucune offre WTTJ
Les clés Algolia sont publiques mais peuvent changer. Vérifiez :
1. Ouvrez https://www.welcometothejungle.com/fr/jobs
2. DevTools (F12) → onglet Network → filtrez sur `algolia`
3. Copiez les headers `x-algolia-application-id` et `x-algolia-api-key`
4. Mettez-les dans les GitHub Secrets

### Le workflow échoue au push de seen_jobs.db
Vérifiez que le workflow a la permission `contents: write` et que la
branche n'est pas protégée (ou ajoutez le bot GitHub Actions comme
exception).

### Comment vérifier les entreprises ATS ?
Testez directement dans votre navigateur :
- SmartRecruiters : `https://api.smartrecruiters.com/v1/companies/{id}/postings`
- Greenhouse : `https://boards-api.greenhouse.io/v1/boards/{token}/jobs`
- Lever : `https://api.lever.co/v0/postings/{company}?mode=json`
