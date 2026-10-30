# Architecture technique — Kibaré

## Vue d'ensemble

```
Réseau local (Wi-Fi / réseau de l'État) — aucune connexion Internet nécessaire

┌──────────────────────┐     HTTPS (CA locale)      ┌──────────────────────────────────────┐
│  Téléphone Android   │ ─────────────────────────▶ │  Serveur (docker compose)            │
│  App « Kibaré »      │                             │  ┌────────┐                         │
│  (fork Element       │                             │  │ Caddy  │ porte d'entrée unique    │
│   Android, F-Droid)  │                             │  └───┬────┘ HTTPS (CA locale)       │
└──────────────────────┘                             │      │                               │
                                                     │      ├──▶ Synapse (Matrix)          │
┌──────────────────────┐                             │      ├──▶ Keycloak (identité, OTP)  │
│ Navigateur admin     │ ──────────────────────────▶ │      ├──▶ Console Kibaré (FastAPI)  │
│ Console Kibaré       │                             │      └──▶ (Element Web, optionnel)  │
└──────────────────────┘                             │                                     │
                                                     │  PostgreSQL (Synapse + Keycloak     │
                                                     │             + Console)              │
                                                     └──────────────────────────────────────┘
```

## Composants

| Composant | Rôle | Version figée |
|---|---|---|
| Caddy | Reverse proxy HTTPS (CA locale), point d'entrée unique | 2.11.7 |
| Synapse | Serveur Matrix : stocke les messages CHIFFRÉS, salons | 1.164.1 |
| Keycloak | Identité : comptes, mots de passe, OTP (TOTP), rôles, attributs | 26.8.1 |
| PostgreSQL | Bases `synapse`, `keycloak`, `kibare_console` | 17.11 |
| Console Kibaré | Enrôlement, activation, révocation, annuaire, journal (FastAPI) | — |
| App Android | Fork d'Element Android (variante F-Droid) avec protections « Zéro fuite » | 1.6.66 |

## Flux principaux

### Connexion (OIDC)
1. L'app ou le navigateur redirige vers Keycloak (`/auth/realms/kibare`).
2. L'agent saisit matricule + mot de passe + code OTP (TOTP).
3. Keycloak renvoie un code d'autorisation, échangé contre des jetons.
4. Synapse (ou la Console) valide le sujet OIDC et ouvre la session.

### Enrôlement → activation
1. Un admin enrôle un agent (formulaire) → compte Keycloak (sans mot de passe)
   + compte Matrix + jeton d'activation (seul le hash est stocké).
2. L'agent ouvre le lien à usage unique, choisit son mot de passe.
3. À la première connexion, Keycloak impose la configuration de l'OTP.

### Révocation
1. L'admin clique « Révoquer » (confirmation en tapant le matricule).
2. Keycloak : compte désactivé + sessions fermées.
3. Synapse : compte désactivé (jetons supprimés, quitte les salons).
4. L'app reçoit `M_UNKNOWN_TOKEN` → efface ses données → « Accès révoqué ».

## Réseau

- Réseau Docker interne (`internal: true`) : aucun accès Internet depuis les
  conteneurs. Seul Caddy publie les ports 443 et 80.
- Adresse canonique : l'IP du serveur (`KIBARE_SERVER_ADDRESS`). Le nom
  `kibare.test` est uniquement le `server_name` Matrix (identifiant stable
  des comptes `@matricule:kibare.test`).
