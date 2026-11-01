# Note de sécurité — Kibaré

> Prototype du Hackathon 226 (MTDPCE). Toutes les données sont fictives.

## 1. Chiffrement de bout en bout

- Protocole **Matrix Olm/Megolm**, fourni par Synapse + le SDK d'Element.
  **Aucun code cryptographique écrit ou modifié par l'équipe.**
- Le serveur impose le chiffrement pour **tous** les salons
  (`encryption_enabled_by_default_for_room_type: all`).
- L'application interdit en plus de créer un salon non chiffré : l'appel
  d'activation du chiffrement est inconditionnel, et l'interrupteur de
  l'écran de création a été remplacé par un texte non modifiable.
- Les messages sont stockés en base sous forme d'événements `m.room.encrypted` :
  le serveur ne voit que du contenu chiffré opaque.
- Les fichiers sont chiffrés côté client avant envoi (pièces jointes Matrix).
- Les aperçus de liens sont désactivés (`url_preview_enabled: false`) : le
  serveur ne va pas lire les URLs.

**Vérifié automatiquement** (`./scripts/run_tests.sh`) : deux agents fictifs
échangent un message réellement chiffré ; le destinataire le déchiffre ; le
texte est **introuvable** dans la base (`0 occurrence` dans `event_json`),
aucun événement `m.room.message` en clair, et rien dans les journaux.

Ces tests ont été éprouvés par **mutation** : chiffrement coupé volontairement,
le même test trouve alors le message **en clair** (`1 occurrence`). La
vérification distingue donc réellement les deux situations.

### Comment les clés circulent (mécanisme à connaître)

La clé de session Megolm n'est remise **qu'aux appareils connus et vérifiés au
moment de l'envoi**. Un appareil qui n'a pas publié ses clés, ou qui apparaît
après coup, ne la reçoit jamais et ne peut rien déchiffrer. C'est ce mécanisme —
et non une suppression de données côté serveur — qui empêche un agent révoqué de
lire les messages envoyés après sa révocation.

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

**Vérifié automatiquement** : avant révocation le jeton répond `200` ; après,
le serveur renvoie `401 M_UNKNOWN_TOKEN` **sans** `soft_logout` — c'est
précisément ce signal qui déclenche l'effacement sur le téléphone — et la
reconnexion est refusée (`403`).

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

Nous préférons les énoncer clairement plutôt que de les laisser découvrir.

1. **Photo de l'écran avec un autre appareil** : impossible à empêcher
   techniquement. Atténuation : filigrane nominatif, qui permet d'identifier
   l'agent dont l'écran a été photographié.
2. **Client Matrix modifié ou Element officiel** : les protections « Zéro
   fuite » vivent dans l'application. Un agent utilisant un autre client
   pourrait copier et capturer. Atténuation : en production, gestion des
   téléphones par MDM.
3. **Téléphone hors ligne à la révocation** : l'effacement a lieu à la
   reconnexion. Entre-temps, les données restent protégées par le
   verrouillage du téléphone.
4. **Pas d'auto-désinstallation** : Android ne le permet pas sans MDM.
5. **iPhone** : hors périmètre (installation via Apple, captures non
   bloquables par le système).
6. **Navigateur** (Element Web) : protections réduites.
7. **Métadonnées** visibles par le serveur (voir section 5).
8. **Autorité de certification** : l'autorité de l'État est **embarquée dans
   l'application** — aucune installation manuelle sur le téléphone. Sur un
   ordinateur en revanche, le navigateur affichera un avertissement sur la
   Console tant que `caddy/kibare-ca.crt` n'est pas ajouté à son magasin de
   certificats.
9. **Prototype** : pas de haute disponibilité, pas de sauvegarde automatique,
   pas d'audit de sécurité externe.
10. **Pièces jointes non images** : la visionneuse PDF interne n'est pas
    implémentée ; ces fichiers ne sont pas consultables dans l'app (ils ne
    peuvent pas non plus en sortir, ce qui est conforme au thème).
11. **Compilation de l'APK** : nous utilisons GitHub Actions pour produire
    l'APK. C'est un confort de développement, **pas une dépendance du
    produit** : la messagerie fonctionne sans Internet, et l'APK peut être
    compilé entièrement en local (voir README, « Compiler l'APK en local »).
12. **Signature de l'APK** : l'APK de démonstration est signé avec la clé de
    test d'Element. Un déploiement réel dans l'administration exigerait une
    clé de signature propre à l'État, conservée hors du dépôt.
