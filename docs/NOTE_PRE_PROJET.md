# Note de pré-projet — Kibaré

> Hackathon 226 — Challenge « La messagerie souveraine de l'administration »
> (MTDPCE – DGTD). Toutes les données du prototype sont fictives.

## Problème

Les agents publics du Burkina Faso échangent des informations de service,
parfois sensibles, sur des messageries grand public (WhatsApp, Telegram…) dont
les serveurs sont à l'étranger. L'État a besoin d'une **messagerie instantanée
souveraine** : simple d'usage, hébergée sur son infrastructure, à haut niveau
de sécurité.

## Solution : Kibaré

Kibaré est une messagerie instantanée souveraine pour l'administration,
construite à partir de **composants open source éprouvés** (Matrix/Synapse pour
la messagerie chiffrée, Keycloak pour l'identité), avec :

- **chiffrement de bout en bout** (Olm/Megolm) : le serveur ne lit rien ;
- **identité vérifiée** : enrôlement administratif + OTP obligatoire + rôles ;
- **révocation immédiate** : accès coupé et données effacées à distance ;
- des protections **« Zéro fuite »** : aucune information ne sort de l'app.

Nous n'avons écrit **aucune ligne de cryptographie**. Le chiffrement est celui
du protocole Matrix, utilisé tel quel.

## Thème « Zéro fuite »

1. Blocage des captures et enregistrements d'écran.
2. Filigrane nominatif (qui a affiché quoi, quand).
3. Interdiction de copier, partager ou télécharger hors de l'app.
4. Effacement à distance en cas de révocation ou de téléphone perdu.

## Architecture (résumé)

- **Synapse** (Matrix) : salons chiffrés, fédération coupée.
- **Keycloak** : comptes, OTP (TOTP), rôles, attributs (matricule, ministère…).
- **Console Kibaré** (FastAPI) : enrôlement, lien d'activation à usage unique,
  révocation, annuaire, journal.
- **App Android** : fork d'Element Android (variante F-Droid, sans Google).
- **Caddy** : HTTPS avec CA locale, sans Let's Encrypt.
- Le tout sur un réseau local, **sans aucune dépendance à Internet**.

## État d'avancement au dépôt

**Fonctionne et vérifié automatiquement** (`./scripts/run_tests.sh`, 29
vérifications) :

| Élément | Preuve |
|---|---|
| Plateforme complète | `docker compose up -d` : Caddy, PostgreSQL, Synapse, Keycloak, Console |
| Chiffrement de bout en bout | message réellement chiffré, **introuvable** en clair dans la base et les journaux |
| Épreuve « Intrus » | connexion et inscription du compte non enrôlé refusées (403) |
| Épreuve « Révocation » | jeton rejeté (`M_UNKNOWN_TOKEN`), reconnexion impossible |
| Console Kibaré | enrôlement, lien d'activation à usage unique, révocation, annuaire, journal — 13 tests unitaires |
| Fork Android | 47 fichiers modifiés, patch vérifié applicable sur un clone neuf |

Nos tests ont été éprouvés **par mutation** : en coupant volontairement le
chiffrement, le test trouve le message **en clair** dans la base. Ils
distinguent donc réellement une protection active d'une protection absente.

**Partiel** : la visionneuse PDF interne n'est pas implémentée (les fichiers
non images ne sont pas consultables dans l'app — ils ne peuvent pas non plus en
sortir, ce qui reste conforme au thème).

## Engagement open source : « Étendre et adapter »

Nous partons d'Element Android et de Synapse (AGPL-3.0) et les adaptons au
contexte de l'administration burkinabè. Notre projet est sous **AGPL-3.0**.
Toutes les licences des composants sont citées dans le README.

## Périmètre assumé

- Plateforme principale : **Android** (toutes les protections « Zéro fuite »).
- **iPhone** : hors périmètre — l'installation passerait obligatoirement par
  Apple (service tiers) et iOS ne permet pas de bloquer les captures d'écran.
- **Navigateur** : protections réduites, documenté.
- **Prototype** : pas de haute disponibilité, pas de sauvegarde automatique,
  pas d'audit de sécurité externe.

Les limites complètes sont détaillées dans `docs/NOTE_SECURITE.md`. Nous
préférons les énoncer clairement plutôt que de les laisser découvrir.
