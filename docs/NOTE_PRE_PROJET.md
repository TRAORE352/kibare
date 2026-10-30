# Note de pré-projet — Kibaré (brouillon)

> Brouillon destiné à être finalisé par l'équipe. 2 pages max.

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

## Engagement open source : « Étendre et adapter »

Nous partons d'Element Android et de Synapse (AGPL-3.0) et les adaptons au
contexte de l'administration burkinabè. Notre projet est sous **AGPL-3.0**.
Toutes les licences des composants sont citées dans le README.

## Équipe et périmètre

- Plateforme principale : Android (toutes les protections « Zéro fuite »).
- iPhone et navigateur : hors périmètre ou protections réduites (documenté).
- Délai : prototype fonctionnel pour le dépôt du 1er novembre 2026.
