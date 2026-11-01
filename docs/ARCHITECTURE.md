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

- Réseau Docker dédié (`kibare-internal`, pilote *bridge*). Seul Caddy publie
  les ports 443 et 80 ; aucun autre service n'est joignable depuis l'extérieur.
- L'option `internal: true` n'est **pas** utilisée : sous Docker Desktop elle
  empêche Caddy de publier 80/443. L'absence de sortie vers Internet est
  garantie par conception — fédération coupée, aucun service tiers configuré,
  aucune URL externe. En production, on ré-isolerait avec un réseau « edge »
  dédié portant le proxy.
- Adresse canonique : l'IP du serveur (`KIBARE_SERVER_ADDRESS`), détectée et
  confirmée par `scripts/init.sh`. Elle est inscrite dans le certificat
  serveur, dans `public_baseurl` de Synapse et dans les redirections Keycloak.
- Le nom `kibare.test` est uniquement le `server_name` Matrix (identifiant
  stable des comptes `@matricule:kibare.test`).

## Connexion SSO depuis l'application Android

La page de connexion Keycloak s'affiche **dans l'application**, dans un écran
dédié (`KibareSsoWebActivity`), et non dans le navigateur du téléphone.

Element ouvre normalement cette page dans un onglet Chrome. Or le navigateur
est une autre application : il ne connaît pas l'autorité de l'État embarquée
dans Kibaré, rejette le certificat du serveur et n'affiche **rien** — écran
blanc sans message.

Avant d'afficher la page, l'application ouvre sa propre connexion sécurisée
vers le serveur avec un magasin de confiance ne contenant **que** l'autorité
de l'État. Si la négociation aboutit, le serveur est authentique (chaîne,
dates et correspondance du nom validées par la bibliothèque standard de Java) ;
sinon l'accès est refusé avec un message explicite. Cet écran porte en outre
`FLAG_SECURE` : ni capture d'écran ni aperçu dans les applications récentes
pendant la saisie du mot de passe et du code OTP.

Conséquence : le mot de passe et le code à usage unique ne transitent par
aucune application tierce susceptible de les enregistrer ou de les
synchroniser vers un service en ligne.
