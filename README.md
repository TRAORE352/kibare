# Kibaré — Messagerie souveraine de l'administration

## Concept
Kibaré est une messagerie instantanée souveraine pour l'administration burkinabè, hébergée sur l'infrastructure de l'État, sans aucune dépendance à des services tiers. Elle garantit le chiffrement de bout en bout (Matrix/Olm-Megolm), une identité vérifiée par enrôlement administratif avec OTP obligatoire, une révocation immédiate, et des protections « Zéro fuite » (blocage des captures d'écran, filigrane nominatif, interdiction de copie et de partage externe, effacement à distance).

## Architecture
```
Réseau local (Wi-Fi / réseau de l'État) — Aucune connexion Internet nécessaire

┌──────────────────────┐     HTTPS (CA locale)      ┌──────────────────────────────────────┐
│  Téléphone Android   │ ─────────────────────────▶ │  Serveur (docker compose)            │
│  App « Kibaré »      │                             │  ┌────────┐                         │
│  (fork Element       │                             │  │ Caddy  │ Reverse proxy, HTTPS    │
│   Android, F-Droid)  │                             │  └───┬────┘ (CA locale)            │
└──────────────────────┘                             │      │                               │
                                                     │      ├──▶ Synapse (Matrix)          │
┌──────────────────────┐                             │      ├──▶ Keycloak (identité, OTP)  │
│ Navigateur admin     │ ─────────────────────────▶ │      ├──▶ Console Kibaré (FastAPI)  │
│ Console Kibaré       │                             │      └──▶ Element Web (optionnel)   │
└──────────────────────┘                             │                                    │
                                                     │  PostgreSQL (Synapse + Keycloak)   │
                                                     └────────────────────────────────────┘
```

## Technologies et licences

| Composant | Licence | Lien |
|-----------|---------|------|
| Synapse | AGPL-3.0 | https://github.com/element-hq/synapse |
| Element Android (Element Classic) | AGPL-3.0 | https://github.com/element-hq/element-android |
| Element Web (optionnel) | AGPL-3.0 | https://github.com/element-hq/element-web |
| Matrix Olm/Megolm (vodozemac) | Apache-2.0 | https://github.com/matrix-org/vodozemac |
| Keycloak | Apache-2.0 | https://github.com/keycloak/keycloak |
| PostgreSQL | PostgreSQL License | https://www.postgresql.org |
| Caddy | Apache-2.0 | https://github.com/caddyserver/caddy |
| FastAPI | MIT | https://github.com/fastapi/fastapi |
| Authlib | BSD-3-Clause | https://github.com/lepture/authlib |
| python-qrcode | BSD | https://github.com/lincolnloop/python-qrcode |
| FreeOTP | Apache-2.0 | https://github.com/freeotp |
| Aegis | GPL-3.0 | https://github.com/beemdevelopment/Aegis |
| IBM Plex Sans | SIL OFL 1.1 | https://github.com/IBM/plex |

Licence du projet : **AGPL-3.0** (obligatoire, car nous modifions Element Android et Synapse sous AGPL-3.0). Voir `LICENSE`.

Niveau d'engagement open source : **« Étendre et adapter »** (à partir d'Element Android et Synapse).

## Installation
**Prérequis** : Docker, Docker Compose, 8 Go de RAM minimum.

```bash
./scripts/init.sh      # Génère configs, CA locale, certificats, secrets de démo (une seule fois)
docker compose up -d   # Démarre toute la plateforme
```

Puis sur un téléphone Android :
1. Installer le certificat CA (`caddy/kibare-ca.crt`) : Paramètres → Sécurité → Installer un certificat.
2. Installer l'APK Kibaré (variante F-Droid, téléchargeable via le lien d'activation émis par la Console). Pour construire l'APK soi-même : voir `docs/ANDROID_FORK.md` et appliquer `docs/android-fork.patch` sur un clone d'Element Android (Element Classic).
3. Ouvrir l'app, se connecter via SSO Keycloak (matricule + mot de passe + code OTP FreeOTP/Aegis).

## Comptes de démo
Voir `docs/COMPTES_DEMO.md`. Tous les comptes sont fictifs. Mots de passe de démo dans `.env.example` (marqués « DÉMO »).

## Limites connues
Voir section 13 du brief et `docs/NOTE_SECURITE.md` :
- Photo de l'écran avec un autre appareil : atténuée par filigrane nominatif
- Client Matrix modifié : protections contournables ; atténuation par MDM en production
- Téléphone hors ligne à la révocation : effacement à la reconnexion
- iPhone : hors périmètre (installation via Apple, captures non bloquables)
- Navigateur : protections réduites
- Métadonnées visibles par le serveur (membres de salon, horodatage, taille, IP 1j, appareils, attributs annuaire)
- CA locale à installer sur le téléphone
- Prototype : pas de HA, pas de sauvegarde auto, pas d'audit externe
- Pièces jointes non images/PDF : non consultables dans l'app