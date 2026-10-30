# Note de sécurité — Kibaré (brouillon)

> Brouillon destiné à être finalisé par l'équipe. 2 pages max.

## 1. Chiffrement de bout en bout

- Protocole **Matrix Olm/Megolm**, fourni par Synapse + le SDK d'Element.
  **Aucun code cryptographique écrit ou modifié par l'équipe.**
- Le serveur impose le chiffrement pour **tous** les salons
  (`encryption_enabled_by_default_for_room_type: all`).
- Les messages sont stockés en base sous forme d'événements `m.room.encrypted` :
  le serveur ne voit que du contenu chiffré opaque.
- Les fichiers sont chiffrés côté client avant envoi (pièces jointes Matrix).
- Les aperçus de liens sont désactivés (`url_preview_enabled: false`) : le
  serveur ne va pas lire les URLs.

## 2. Hébergement souverain

- Tout fonctionne sur un réseau local, **sans Internet**.
- Aucun service tiers : pas de Firebase/FCM, pas de Let's Encrypt, pas de
  serveur d'identité externe (vector.im/matrix.org), pas de Jitsi, pas de
  cartes, pas de statistiques (`report_stats: false`), pas de télémétrie.
- Fédération Matrix **désactivée** (aucun port 8448, `federation_domain_whitelist: []`).
- HTTPS via une **CA locale** générée par `scripts/init.sh` (pas d'ACME).

## 3. Identité vérifiée

- Inscription libre **désactivée** (Keycloak `registrationAllowed: false`,
  Synapse `enable_registration: false`).
- Seul un administrateur enrôle un agent (nom, prénom, matricule, ministère,
  fonction, rôle).
- **OTP (TOTP) obligatoire** : configuré à la première connexion, demandé ensuite
  à chaque connexion. Pas d'OTP par SMS (service tiers interdit).
- Politique de mot de passe : 12 caractères minimum. Protection anti force brute.
- Rôles : `super-admin`, `admin-ministere` (limité à son ministère), `agent`.

## 4. Révocation immédiate

- La Console désactive le compte dans **Keycloak** (compte + sessions) puis dans
  **Synapse** (jetons supprimés sur tous les appareils, quitte les salons).
- Côté chiffrement, les membres restants créent une **nouvelle session Megolm** :
  l'agent révoqué ne peut plus lire les nouveaux messages.
- Côté application, à la prochaine connexion, l'app reçoit une erreur
  d'authentification définitive et **efface toutes ses données locales** puis
  affiche « Accès révoqué ».

## 5. Minimisation des métadonnées

Mesures : présence désactivée, IP conservées 1 jour, rétention des événements
30 jours, profils limités aux salons partagés, accusés de lecture en mode privé,
indicateur de frappe désactivé, notifications sans contenu.

**Ce que le serveur voit malgré tout** (à connaître honnêtement) :
- qui est membre de quel salon ;
- l'horodatage et la taille approximative des messages ;
- l'adresse IP des appareils (gardée 1 jour) ;
- la liste des appareils de chaque agent ;
- les noms d'affichage et attributs d'annuaire (ministère, fonction).

## 6. Protections « Zéro fuite » (côté application)

- Blocage des captures/ enregistrements d'écran (`FLAG_SECURE` forcé).
- Filigrane nominatif discret (nom + matricule + date) pour identifier l'auteur
  d'une photo d'écran prise avec un autre appareil.
- Copie, partage externe et téléchargement des pièces jointes retirés
  (transfert interne uniquement).
- Effacement à distance à la révocation.

## 7. Limites connues

1. Photo d'écran avec un autre appareil : impossible à empêcher (atténuée par le filigrane).
2. Client Matrix modifié/officiel : contourne les protections (atténuation : MDM en production).
3. Téléphone hors ligne : l'effacement a lieu à la reconnexion.
4. Pas d'auto-désinstallation (Android l'interdit sans MDM).
5. iPhone hors périmètre (installation via Apple, captures non bloquables).
6. Navigateur : protections réduites.
7. Métadonnées visibles par le serveur (section 5).
8. CA locale à installer sur le téléphone pour l'écran de connexion.
9. Prototype : pas de haute disponibilité, pas de sauvegarde auto, pas d'audit externe.
10. Pièces jointes non images/PDF : non consultables dans l'app.
