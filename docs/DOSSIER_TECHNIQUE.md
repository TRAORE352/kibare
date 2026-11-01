# Kibaré — Dossier technique complet

> **Objet de ce document.** Exposer de façon exhaustive ce qui a été conçu,
> réalisé, vérifié et ce qui ne l'est pas. Il sert de source unique pour
> rédiger le document de soumission. Chaque affirmation technique renvoie à un
> fichier du dépôt ou à une vérification exécutée.
>
> **Dépôt** : https://github.com/TRAORE352/kibare — licence AGPL-3.0
> **APK** : https://github.com/TRAORE352/kibare/releases/latest
> **État** : prototype fonctionnel, 64 commits, données entièrement fictives.

---

## 1. Le problème traité

L'administration burkinabè échange aujourd'hui des informations sensibles —
notes de service, documents budgétaires, coordination d'opérations — sur des
messageries grand public hébergées à l'étranger. Trois conséquences :

1. **Perte de souveraineté.** Les métadonnées (qui parle à qui, quand, depuis
   où) sont détenues par une entreprise étrangère soumise à un droit étranger.
2. **Identités non vérifiées.** N'importe qui peut créer un compte et se
   présenter comme agent de l'État. Aucun lien avec le matricule réel.
3. **Fuite incontrôlée des contenus.** Une capture d'écran, un transfert vers
   une conversation privée, un compte qui reste actif après la mutation ou le
   départ d'un agent.

Kibaré répond aux trois, dans cet ordre de priorité.

### Ce que le nom signifie

*Kibaré* signifie « nouvelle, information » en mooré. Le nom désigne ce que
l'outil transporte, non la technologie qui le transporte.

---

## 2. Principe de la solution

Une messagerie instantanée **hébergée par l'État**, où l'identité de chaque
agent est **vérifiée par l'administration**, et où le contenu **ne peut pas
sortir** de l'application.

Trois décisions structurent tout le reste.

**Décision 1 — Étendre l'existant plutôt que réécrire.**
Le chiffrement de bout en bout est le composant où une erreur est à la fois
invisible et catastrophique. Nous partons donc de Matrix/Synapse et d'Element
Android, éprouvés et audités. **Aucune ligne de code cryptographique n'a été
écrite ni modifiée par l'équipe.** Notre travail porte sur l'identité,
l'administration et le confinement des contenus.

Niveau d'engagement open source : **« Étendre et adapter »**.

**Décision 2 — Aucune dépendance à un service en ligne.**
Pas de Firebase, pas de Let's Encrypt, pas de serveur d'identité externe, pas
de télémétrie, pas de cartes, pas de visioconférence tierce. La plateforme
fonctionne sur un réseau local sans aucun accès Internet. C'est vérifiable :
pendant la démonstration, on coupe les données mobiles des téléphones et la
messagerie continue de fonctionner.

**Décision 3 — Énoncer les limites plutôt que les laisser découvrir.**
Un prototype qui prétend tout résoudre n'est pas crédible. La section 10 de ce
document liste douze limites connues, dont celles qu'aucune technique ne peut
lever.

---

## 3. Architecture

### 3.1 Vue d'ensemble

```
Réseau local (Wi-Fi ou réseau de l'État) — aucune connexion Internet requise

┌────────────────────────┐   HTTPS, autorité de l'État   ┌──────────────────────────────┐
│  Téléphone Android     │ ────────────────────────────▶ │  Serveur (docker compose)    │
│  Application Kibaré    │                                │  ┌──────────┐                │
│  (fork Element,        │                                │  │  Caddy   │ porte unique   │
│   variante F-Droid)    │                                │  └────┬─────┘ ports 443/80   │
└────────────────────────┘                                │       │                      │
                                                          │       ├──▶ Synapse (Matrix)  │
┌────────────────────────┐                                │       ├──▶ Keycloak (OTP)    │
│  Navigateur            │ ─────────────────────────────▶ │       └──▶ Console (FastAPI) │
│  Console Kibaré        │                                │                              │
└────────────────────────┘                                │  PostgreSQL                  │
                                                          │  (synapse, keycloak,         │
                                                          │   kibare_console)            │
                                                          └──────────────────────────────┘
```

### 3.2 Composants et versions figées

| Composant | Rôle | Version |
|---|---|---|
| Caddy | Reverse proxy HTTPS, point d'entrée unique | 2.11.7-alpine |
| Synapse | Serveur Matrix — stocke les messages **chiffrés** | v1.164.1 |
| Keycloak | Identité : comptes, mots de passe, OTP, rôles, attributs | 26.8.1 |
| PostgreSQL | Bases `synapse`, `keycloak`, `kibare_console` | 17.11-alpine |
| Console Kibaré | Enrôlement, activation, révocation, annuaire, journal | développée (FastAPI) |
| Application Android | Fork d'Element Android, variante F-Droid | base 1.6.66 |

Les versions sont **épinglées** : aucune image en `latest`. Le déploiement est
reproductible à l'identique.

### 3.3 Réseau

Un réseau Docker dédié (`kibare-internal`). Seul Caddy publie les ports 443 et
80 ; aucun autre service n'est joignable de l'extérieur.

Un point d'honnêteté technique : l'option `internal: true` de Docker, qui
couperait physiquement l'accès Internet aux conteneurs, **n'est pas activée**
— sous Docker Desktop elle empêche Caddy de publier 80/443. L'absence de
sortie vers Internet est garantie par conception (fédération coupée, aucun
service tiers configuré, aucune URL externe) et non par cette option. En
production, on ré-isolerait avec un réseau « edge » dédié portant le proxy.

### 3.4 L'adresse du serveur, valeur critique

L'adresse IP du serveur est inscrite dans trois endroits : le certificat TLS,
le `public_baseurl` de Synapse, les redirections de Keycloak.

Une valeur erronée **ne provoque aucune erreur au démarrage**. Les cinq
services tournent normalement, mais le téléphone reçoit une adresse
injoignable et l'écran de connexion reste blanc, sans message. Ce défaut a été
rencontré en démonstration.

`scripts/init.sh` détecte désormais l'adresse de l'interface portant la route
par défaut, l'affiche dans un encadré et **exige une confirmation explicite**.
Une adresse mal formée est refusée avant toute génération.

---

## 4. Sécurité

### 4.1 Chiffrement de bout en bout

- Protocole **Matrix Olm/Megolm**, fourni par Synapse et le SDK d'Element.
- Le serveur **impose** le chiffrement à tous les salons
  (`encryption_enabled_by_default_for_room_type: all`).
- L'application interdit en outre de créer un salon non chiffré : l'appel
  d'activation est inconditionnel et l'interrupteur de l'écran de création a
  été remplacé par un texte non modifiable.
- Les messages sont stockés comme événements `m.room.encrypted` : le serveur
  ne voit qu'un contenu opaque.
- Les fichiers sont chiffrés côté client avant envoi.
- Les aperçus de liens sont désactivés (`url_preview_enabled: false`) : le
  serveur ne va jamais lire une URL à la place de l'utilisateur.

**Mécanisme à connaître pour comprendre la révocation.** La clé de session
Megolm n'est remise qu'aux appareils connus au moment de l'envoi. Un appareil
qui apparaît après coup ne la reçoit jamais. C'est ce mécanisme — et non une
suppression de données côté serveur — qui empêche un agent révoqué de lire les
messages postérieurs à sa révocation.

### 4.2 Identité vérifiée

- Inscription libre **désactivée** des deux côtés : Keycloak
  (`registrationAllowed: false`) et Synapse (`enable_registration: false`).
- Seul un administrateur enrôle un agent : nom, prénom, matricule, ministère,
  direction, fonction, rôle.
- **OTP (TOTP) obligatoire**, configuré à la première connexion puis demandé à
  chaque connexion. Pas d'OTP par SMS — ce serait un service tiers.
- Mot de passe : 12 caractères minimum, protection anti force brute.
- Trois rôles : `super-admin`, `admin-ministere` (cloisonné à son ministère),
  `agent`.

### 4.3 Révocation immédiate

1. L'administrateur clique « Révoquer » et confirme en saisissant le matricule.
2. **Keycloak** : compte désactivé, toutes les sessions fermées.
3. **Synapse** : compte désactivé, jetons supprimés sur tous les appareils,
   sortie des salons.
4. **Chiffrement** : les membres restants créent une nouvelle session Megolm.
5. **Application** : à la prochaine tentative, elle reçoit
   `M_UNKNOWN_TOKEN` sans `soft_logout`, **efface toutes ses données locales**
   et affiche l'écran terminal « Accès révoqué ».

### 4.4 Confinement des contenus — protections « Zéro fuite »

| Protection | Mise en œuvre |
|---|---|
| Captures et enregistrements d'écran bloqués | `FLAG_SECURE` forcé sur toutes les activités |
| Filigrane nominatif | `WatermarkView` : nom, matricule et date en surimpression discrète |
| Copie de texte impossible | Sélection désactivée sur les messages |
| Pas de partage externe | « Ouvrir avec » et le partage retirés des pièces jointes |
| Pas de téléchargement | Enregistrement des pièces jointes retiré |
| Effacement à distance | Déclenché par la révocation |

Le filigrane répond à la seule fuite qu'aucune technique ne peut empêcher :
photographier l'écran avec un second appareil. Il ne l'empêche pas — il permet
d'identifier l'agent dont l'écran a été photographié.

### 4.5 Connexion SSO interne à l'application

La page de connexion Keycloak s'affiche **dans l'application**, dans un écran
dédié (`KibareSsoWebActivity`), et non dans le navigateur du téléphone.

Element ouvre normalement cette page dans un onglet Chrome. Or le navigateur
est une autre application : il ne connaît pas l'autorité de l'État embarquée
dans Kibaré, rejette le certificat du serveur et n'affiche rien — écran blanc
sans message. C'est ce défaut qui a été rencontré en démonstration.

Avant d'afficher la page, l'application ouvre **sa propre connexion sécurisée**
vers le serveur, avec un magasin de confiance ne contenant que l'autorité de
l'État. Si la négociation aboutit, le serveur est authentique : chaîne de
certificats, dates de validité et correspondance du nom avec l'adresse sont
validées par la bibliothèque standard de Java. Nous ne réécrivons aucune règle
de confiance — nous remplaçons seulement la liste des autorités acceptées.
Sinon l'accès est refusé avec un message explicite.

Deux bénéfices au-delà de la correction :

- le mot de passe et le code à usage unique ne transitent par **aucune
  application tierce** susceptible de les enregistrer ou de les synchroniser
  vers un service en ligne ;
- l'application refuse tout serveur dont le certificat ne vient pas de l'État,
  y compris muni d'un certificat acheté dans le commerce.

Cet écran porte `FLAG_SECURE` : ni capture d'écran ni aperçu dans les
applications récentes pendant la saisie des identifiants. L'écran de connexion
d'Element ne le faisait pas.

### 4.6 Autorité de certification embarquée

Le serveur présente un certificat délivré par l'autorité de l'État, générée
localement par `init.sh` — pas de Let's Encrypt, pas d'autorité commerciale.

Cette autorité est **embarquée dans l'application** (`res/raw/kibare_ca.pem`),
déclarée comme **seule de confiance** dans la configuration réseau Android.
Les autorités préinstallées par Google sont refusées.

Conséquence pratique : l'installation de l'application est un **geste unique**.
Aucune manipulation dans les paramètres Android, aucun avertissement rouge,
et aucun certificat ajouté à la main qu'un agent pourrait retirer par erreur.

Un piège technique mérite d'être signalé, car il illustre la différence entre
« présent » et « actif » : Element déclare une ressource
`network_security_config` dans **deux** modules. À la fusion, celle du module
applicatif l'emporte. Modifier uniquement celle du SDK n'a **aucun effet** —
le certificat est bien dans l'APK, mais Android ne le charge jamais. Le
vérificateur d'APK contrôle désormais la configuration réellement compilée, et
non la seule présence du fichier.

### 4.7 Minimisation des métadonnées

Mesures appliquées : présence désactivée, adresses IP conservées 1 jour,
rétention des événements 30 jours, profils limités aux salons partagés, accusés
de lecture en mode privé (`m.read.private`), indicateur de frappe désactivé,
notifications sans contenu ni nom d'expéditeur.

**Ce que le serveur voit malgré tout**, énoncé sans détour :

- qui est membre de quel salon ;
- l'horodatage et la taille approximative des messages ;
- l'adresse IP des appareils (conservée 1 jour) ;
- la liste des appareils de chaque agent ;
- les noms d'affichage et attributs d'annuaire.

Aucune messagerie ne peut masquer ces éléments à son propre serveur. La
différence tient à **qui détient ce serveur** : ici, l'État burkinabè.

---

## 5. La Console d'administration

Application web développée pour le projet — FastAPI, environ 1 500 lignes de
Python, templates HTML server-side.

### 5.1 Fonctions

| Écran | Adresse | Fonction |
|---|---|---|
| Agents | `/console/agents` | Liste filtrée selon le rôle de l'administrateur |
| Enrôlement | `/console/agents/enroll` | Création d'un agent, génère un lien d'activation |
| Fiche agent | `/console/agents/{matricule}` | Détail, appareils, révocation |
| Annuaire | `/console/annuaire` | Répertoire par ministère et direction |
| Journal | `/console/journal` | Traçabilité des actions d'administration |
| Activation | `/activer/{token}` | Page publique à usage unique pour l'agent |

### 5.2 Enrôlement puis activation

1. L'administrateur enrôle un agent. La Console crée un compte Keycloak **sans
   mot de passe**, un compte Matrix, et un jeton d'activation dont seul le
   **condensat** est stocké en base.
2. L'agent ouvre le lien à usage unique et choisit son mot de passe.
3. À la première connexion, Keycloak impose la configuration de l'OTP.

L'administrateur ne connaît donc jamais le mot de passe d'un agent, et le jeton
d'activation ne peut servir qu'une fois.

### 5.3 Cloisonnement par ministère

Un `admin-ministere` ne voit, ne modifie et ne révoque que les agents de son
propre ministère. Cette règle est appliquée côté serveur, à chaque requête, et
non par un masquage d'interface. Elle est couverte par des tests automatisés
(`console/tests/test_authorization.py`).

---

## 6. L'application Android

### 6.1 Nature du travail

Fork d'Element Android (variante **F-Droid**, donc sans aucune bibliothèque
Google), livré sous forme de **patch versionné** : `docs/android-fork.patch`,
7 181 lignes, 56 fichiers modifiés dont 12 binaires (polices IBM Plex, icône
de lancement).

Ce choix a une raison : le dépôt reste léger et lisible, et le patch est
réappliquable sur n'importe quel clone d'Element. Il est vérifié à chaque
compilation : si le patch ne s'applique pas, le build s'arrête avec un message
explicite au lieu de produire un APK incomplet.

### 6.2 Modifications principales

| Domaine | Modification |
|---|---|
| Identité visuelle | Nom « Kibaré », icône adaptative, police IBM Plex Sans, palette institutionnelle |
| Serveur | Adresse fixée, écran de choix du serveur retiré, inscription supprimée |
| Connexion | Écran SSO interne validant l'autorité de l'État (`KibareSsoWebActivity`) |
| Certificat | Autorité de l'État embarquée et seule de confiance |
| Zéro fuite | `FLAG_SECURE`, filigrane, copie/partage/téléchargement retirés |
| Révocation | Écran terminal « Accès révoqué » + effacement local |
| Chiffrement | Création de salon non chiffré rendue impossible |
| Métadonnées | Accusés de lecture privés, frappe désactivée, notifications sans contenu |
| Services tiers | Statistiques, Sentry, Jitsi, cartes, annuaire public, liens d'aide externes neutralisés |

### 6.3 Compilation

Deux chemins équivalents.

**En local, sans aucun service en ligne** — JDK 21 et SDK Android suffisent :

```bash
git clone --depth 1 --branch main https://github.com/element-hq/element-android.git
cd element-android
git apply --check ../kibare/docs/android-fork.patch   # doit être silencieux
git apply ../kibare/docs/android-fork.patch
./gradlew :vector-app:assembleFdroidDebug
```

**Par GitHub Actions** (`.github/workflows/apk.yml`), qui automatise exactement
ces commandes. C'est un **confort de développement, pas une dépendance du
produit** : la plateforme et l'application fonctionnent sans Internet.

### 6.4 Taille de l'APK

Le premier artefact pesait 465 Mo, inexploitable pour un jury. Analyse plutôt
que supposition :

- un APK « universal » de 181 Mo contenant les quatre architectures à la fois,
  alors qu'un téléphone n'utilise que celle de son processeur ;
- deux APK x86 et x86_64, utiles aux seuls émulateurs sur ordinateur ;
- plus de 60 traductions embarquées.

Après correction — APK universel supprimé, architectures limitées à
`arm64-v8a` et `armeabi-v7a`, langues restreintes au français et à l'anglais :

| | Avant | Après |
|---|---|---|
| Archive de téléchargement | 465 Mo | 148 Mo |
| Nombre de fichiers APK | 5 | 2 |
| APK installé (arm64) | 88 Mo | 80 Mo |

### 6.5 Les deux fichiers livrés

| Fichier | Pour quel téléphone | Taille |
|---|---|---|
| `kibare-arm64-v8a.apk` | tout téléphone vendu depuis 2016 — par défaut | 80 Mo |
| `kibare-armeabi-v7a.apk` | appareils 32 bits plus anciens | 76 Mo |

Liens **permanents**, valables après publication de nouvelles versions :

```
https://github.com/TRAORE352/kibare/releases/latest/download/kibare-arm64-v8a.apk
https://github.com/TRAORE352/kibare/releases/latest/download/kibare-armeabi-v7a.apk
```

---

## 7. Vérifications — ce qui est prouvé, et comment

Notre règle : **un contrôle qui ne sait pas détecter le défaut ne prouve
rien.** Chaque vérification importante a été éprouvée par mutation, c'est-à-dire
en réintroduisant volontairement le défaut pour confirmer que le contrôle passe
au rouge.

### 7.1 « Le serveur ne lit rien »

Deux agents fictifs échangent un message réellement chiffré. Le destinataire le
déchiffre. Le texte est ensuite recherché dans la base de données.

Résultat : **0 occurrence** dans `event_json`, aucun événement
`m.room.message` en clair, rien dans les journaux.

**Mutation** : chiffrement coupé volontairement, le même test trouve alors le
message **en clair (1 occurrence)**. Le test distingue donc réellement les deux
situations.

### 7.2 « Intrus »

Un client Matrix automatisé tente de créer un compte et de rejoindre un salon
sans passer par l'enrôlement. L'inscription est refusée, l'accès au salon
refusé.

### 7.3 « Révocation »

Avant révocation, le jeton de l'agent répond `200`. Après révocation, le serveur
renvoie `401 M_UNKNOWN_TOKEN` **sans** `soft_logout` — c'est précisément ce
signal qui déclenche l'effacement des données sur le téléphone — et la
reconnexion est refusée (`403`).

### 7.4 Tests unitaires de la Console

13 tests, exécutés et passants : jeton d'activation à usage unique, autorisation
par rôle et cloisonnement par ministère, enrôlement, révocation.

```
$ python3 -m pytest tests/ -q
............. 13 passed
```

### 7.5 Vérificateur d'APK

`scripts/verifier_apk.py` ouvre l'APK produit et contrôle **20 points** :

- absence de Firebase, Google Play Services, Google Maps, Crashlytics ;
- absence de statistiques (PostHog), visioconférence (Jitsi), cartes (MapLibre) ;
- variante F-Droid confirmée (aucun service Firebase Messaging) ;
- autorité de l'État présente **et effectivement déclarée seule de confiance**
  dans la configuration réseau compilée ;
- aucune dérogation acceptant les autorités du téléphone ;
- protections « Zéro fuite » présentes dans le code compilé : `WatermarkView`,
  étiquette « Consultation interne uniquement », écran « Accès révoqué »,
  appel à `FLAG_SECURE` ;
- serveur fixé sur l'infrastructure Kibaré, inscription retirée ;
- APK signé, donc installable.

Résultat sur les deux fichiers publiés : **20/20**.

**Mutation** : ces contrôles ont été exécutés contre une version antérieure de
l'APK où le certificat était présent mais inactif. Trois contrôles passent au
rouge et le script sort en code 1. La vérification détecte donc bien le défaut.

### 7.6 Validation du certificat, éprouvée hors Android

La logique de validation du certificat a été testée contre un serveur TLS réel
portant le vrai certificat du serveur Kibaré, dans trois situations :

| Situation | Résultat attendu | Résultat obtenu |
|---|---|---|
| Autorité de l'État, bonne adresse | accepté | accepté |
| Autorité de l'État, adresse absente du certificat | refusé | refusé |
| Autorités publiques du système | refusé | refusé |

Les deux refus comptent davantage que l'acceptation : ils prouvent que le
contrôle sait dire non.

### 7.7 Accessibilité du dossier, vérifiée depuis Internet

Dépôt, documentation, licence et les deux APK ont été téléchargés **sans
authentification**, comme le fera un membre du jury. Codes de réponse 200 sur
l'ensemble, fichiers reçus intacts et reconnus comme paquets Android.

---

## 8. Parcours d'installation et de démonstration

### 8.1 Serveur, trois commandes

```bash
./scripts/init.sh        # autorité locale, certificats, secrets, configuration
                         # détecte l'adresse du serveur et la fait confirmer
docker compose up -d     # démarre les cinq services
python3 scripts/demo_seed.py   # comptes et salons de démonstration
```

### 8.2 Téléphone, un geste

1. Télécharger l'APK depuis la page des versions.
2. L'ouvrir, autoriser l'installation depuis cette source.
3. Ouvrir Kibaré, saisir l'adresse du serveur, se connecter.

Rien d'autre : le certificat est dans l'application.

### 8.3 Console d'administration

`https://<ADRESSE_SERVEUR>/console/`

Sur un ordinateur, le navigateur affiche un avertissement de certificat tant
que `caddy/kibare-ca.crt` n'est pas ajouté à son magasin — c'est le
comportement normal d'une autorité d'organisation. Dans un déploiement réel,
ce certificat serait distribué par la gestion de parc.

### 8.4 Comptes de démonstration

Dix comptes fictifs répartis sur quatre ministères (MTDPCE, Santé, Sécurité,
Économie et Finances), couvrant les trois rôles.
Mot de passe au format `DemoPass<matricule>!`. Détail dans
`docs/COMPTES_DEMO.md`.

Pour montrer le cloisonnement : se connecter avec `demo-101`
(`admin-ministere` du MTDPCE) et constater qu'aucun agent des autres
ministères n'apparaît.

### 8.5 Démonstration de la souveraineté

Une fois la plateforme en service, **couper les données mobiles** des
téléphones. La messagerie continue de fonctionner. C'est la démonstration la
plus directe que rien ne passe par Internet.

---

## 9. Défauts rencontrés et corrigés

Cette section est volontairement présente. Un prototype sans historique de
correction n'a pas été éprouvé.

| Défaut | Cause réelle | Correction |
|---|---|---|
| Artefact de 465 Mo | APK « universal » de 181 Mo + architectures d'émulateur | Universel supprimé, deux architectures conservées |
| Certificat embarqué mais inactif | Element déclare `network_security_config` dans deux modules ; celui du SDK est écrasé | Configuration déplacée dans le module applicatif ; contrôle ajouté sur la configuration compilée |
| Page de connexion blanche (1) | Le SSO s'ouvrait dans Chrome, qui ignore l'autorité de l'État | Écran SSO interne validant le certificat |
| Page de connexion blanche (2) | `public_baseurl` de Synapse pointait l'adresse d'exemple du projet | Adresse corrigée ; `init.sh` détecte et fait confirmer l'adresse |
| Page Keycloak blanche | La politique de sécurité du contenu interdisait les scripts dont Keycloak a besoin | Politique retirée sur `/auth/*` uniquement, conservée ailleurs |
| Compilation en échec | Classe `SslCertificate` inaccessible depuis le module | Validation par connexion TLS réelle, plus robuste et sans API variable |

Deux enseignements méritent d'être cités dans la soutenance.

**Un contrôle vert ne vaut que s'il peut passer au rouge.** Le vérificateur
d'APK affichait 17/17 sur un APK dont le certificat n'était jamais chargé : il
vérifiait la présence du fichier, non son effet. Corrigé, il contrôle
désormais la configuration réellement compilée.

**Une erreur silencieuse est plus dangereuse qu'un plantage.** L'adresse de
serveur erronée ne provoquait aucune erreur : les cinq services démarraient
normalement. Seul l'écran blanc sur le téléphone, sans message, signalait le
problème. D'où le garde-fou ajouté à `init.sh`.

---

## 10. Limites connues

Énoncées sans atténuation.

1. **Photographier l'écran avec un autre appareil** : techniquement
   impossible à empêcher. Atténuation : filigrane nominatif permettant
   d'identifier l'agent concerné.
2. **Client Matrix tiers** : les protections « Zéro fuite » vivent dans
   l'application. Un agent utilisant Element officiel pourrait copier et
   capturer. Atténuation : gestion de parc (MDM) en production.
3. **Téléphone hors ligne lors de la révocation** : l'effacement a lieu à la
   reconnexion. Entre-temps, les données restent protégées par le
   verrouillage du téléphone.
4. **Pas d'auto-désinstallation** : Android ne le permet pas sans MDM.
5. **iPhone** : hors périmètre — distribution via Apple, captures d'écran non
   bloquables par le système.
6. **Element Web** : protections réduites dans un navigateur.
7. **Métadonnées visibles par le serveur** : détaillées en section 4.7.
8. **Autorité de certification sur ordinateur** : embarquée dans
   l'application Android, mais à installer manuellement sur un PC pour
   consulter la Console sans avertissement.
9. **Prototype** : pas de haute disponibilité, pas de sauvegarde automatique,
   pas d'audit de sécurité externe.
10. **Pièces jointes non images** : la visionneuse PDF interne n'est pas
    implémentée. Ces fichiers ne sont pas consultables dans l'application —
    ils ne peuvent pas non plus en sortir, ce qui reste conforme au thème.
11. **Compilation par GitHub Actions** : confort de développement, pas une
    dépendance. L'APK se compile entièrement hors ligne.
12. **Signature de l'APK** : les fichiers publiés sont signés avec la clé de
    test d'Element, pour être directement installables. Un déploiement réel
    exigerait une clé propre à l'État, conservée hors du dépôt.

---

## 11. Perspectives

Par ordre de valeur pour l'administration.

**Court terme.** Clé de signature propre à l'État. Visionneuse PDF interne.
Déploiement par gestion de parc (MDM), qui lèverait les limites 2 et 4.
Personnalisation graphique aboutie de l'application et de la Console.

**Moyen terme.** Serveur de notifications souverain (UnifiedPush) pour
remplacer la synchronisation en arrière-plan. Sauvegarde chiffrée et
restauration. Haute disponibilité. Journalisation d'audit exportable.

**Long terme.** Fédération **contrôlée** entre ministères, chacun hébergeant
son propre serveur sous une liste blanche. Intégration à un annuaire d'État
existant. Audit de sécurité externe avant tout déploiement réel.

---

## 12. Ce que le jury peut vérifier lui-même

| Affirmation | Commande ou lien |
|---|---|
| Aucun service Google dans l'APK | `python3 scripts/verifier_apk.py kibare-arm64-v8a.apk` → 20/20 |
| Le serveur ne lit pas les messages | `./scripts/run_tests.sh` |
| Cloisonnement par ministère | `cd console && python3 -m pytest tests/ -q` → 13 passed |
| Le fork est reproductible | `git apply --check docs/android-fork.patch` sur un clone neuf d'Element |
| Aucune dépendance en ligne | Couper les données mobiles : la messagerie fonctionne |
| Licence | AGPL-3.0, fichier `LICENSE` |

---

## 13. Repères du dépôt

```
kibare/
├── docker-compose.yml          5 services, versions épinglées
├── caddy/Caddyfile             porte d'entrée HTTPS unique
├── synapse/homeserver.yaml     Matrix : chiffrement imposé, fédération coupée
├── keycloak/realm-*.json       identité : rôles, OTP, inscription fermée
├── console/                    Console d'administration (FastAPI, ~1 500 lignes)
│   ├── app/routers/            agents, activation, révocation, annuaire, journal
│   ├── app/services/           enrôlement, activation, révocation, amorçage
│   └── tests/                  13 tests unitaires
├── scripts/
│   ├── init.sh                 autorité locale, certificats, secrets, configuration
│   ├── demo_seed.py            comptes et salons de démonstration
│   ├── verifier_apk.py         20 contrôles sur l'APK produit
│   └── run_tests.sh            toutes les vérifications
├── tests/integration/          épreuves « intrus », « le serveur ne lit rien », « révocation »
├── docs/
│   ├── ARCHITECTURE.md         composants, flux, réseau
│   ├── NOTE_SECURITE.md        sécurité détaillée et limites
│   ├── GUIDE_DEMONSTRATION.md  installation pas à pas, script vidéo, dépannage
│   ├── ANDROID_FORK.md         emplacements précis des modifications
│   ├── COMPTES_DEMO.md         comptes fictifs
│   └── android-fork.patch      le fork, 56 fichiers, 7 181 lignes
└── .github/workflows/apk.yml   compilation automatisée de l'APK
```

**Chiffres clés** : 64 commits · 5 services · ~1 500 lignes Python ·
56 fichiers Android modifiés · 13 tests unitaires · 3 épreuves d'intégration ·
20 contrôles d'APK · 2 APK livrés · 0 ligne de cryptographie écrite.

---

*Document établi le 1er novembre 2026 à partir du dépôt à l'état du commit
`e2802c7`. Toutes les données de démonstration sont fictives.*
