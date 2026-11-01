# Guide de démonstration — Kibaré

Document pratique pour installer la plateforme, tester l'application sur deux
téléphones et filmer la vidéo de 3 minutes.

---

# Étape 1 — Préparer le réseau

Le PC serveur et les deux téléphones doivent être sur **le même réseau Wi-Fi**.
Un partage de connexion depuis un téléphone fonctionne très bien, et permet même
de montrer que **rien ne passe par Internet**.

**Relever l'adresse IP du PC serveur** :

```bash
ip addr show | grep "inet "        # Linux
```

Notez l'adresse qui ressemble à `192.168.x.x` ou `10.x.x.x`.
C'est **l'adresse du serveur** : elle revient partout ensuite.

> Astuce pour la démonstration : une fois tout installé, coupez les données
> mobiles des téléphones. La messagerie continue de fonctionner — c'est la
> preuve de la souveraineté.

---

# Étape 2 — Démarrer le serveur

Sur le PC serveur, dans le dossier du projet :

```bash
# 1. Indiquer l'adresse du serveur (remplacez par la vôtre)
export KIBARE_SERVER_ADDRESS=192.168.1.42

# 2. Générer la CA locale, les certificats et les secrets de démo
./scripts/init.sh

# 3. Démarrer toute la plateforme
docker compose up -d

# 4. Vérifier que les cinq services tournent
docker compose ps
```

Vous devez voir `kibare-caddy`, `kibare-postgres`, `kibare-synapse`,
`kibare-keycloak` et `kibare-console` en état **running**.

```bash
# 5. Créer les comptes et les salons de démo
python3 scripts/demo_seed.py
```

**Vérification rapide** depuis le PC :

```bash
curl -k https://$KIBARE_SERVER_ADDRESS/_matrix/client/versions
```
Une réponse en JSON = le serveur Matrix répond.

Ouvrez ensuite la Console dans un navigateur :
`https://<ADRESSE_SERVEUR>/console/`
(le navigateur affichera un avertissement de certificat : c'est normal, notre CA
est locale. Cliquez sur « Avancé » puis « Continuer ».)

---

# Étape 3 — Installer le certificat sur les téléphones

**À faire sur les DEUX téléphones.** Sans cette étape, l'application refusera de
se connecter — c'est voulu : elle ne fait confiance qu'à notre autorité locale.

1. Sur le PC, rendez le certificat téléchargeable :
   ```bash
   cd caddy && python3 -m http.server 8080
   ```
2. Sur le téléphone, ouvrez le navigateur et allez à :
   `http://<ADRESSE_SERVEUR>:8080/kibare-ca.crt`
3. Le fichier se télécharge.
4. Ouvrez **Paramètres → Sécurité → Chiffrement et identifiants →
   Installer un certificat → Certificat CA**.
   (le chemin varie un peu selon la marque ; cherchez « certificat » dans la
   recherche des paramètres)
5. Un avertissement s'affiche, confirmez. Choisissez le fichier téléchargé.
6. Nommez-le « Kibaré CA ».

**Vérification** : dans le navigateur du téléphone, allez sur
`https://<ADRESSE_SERVEUR>/console/`. Si la page s'ouvre **sans avertissement de
sécurité**, le certificat est bien installé.

---

# Étape 4 — Installer l'application

1. Récupérez le fichier `kibare.apk` (produit par GitHub Actions ou compilé en
   local, voir le README).
2. Transférez-le sur chaque téléphone (câble USB, ou en le servant depuis le PC
   comme au point précédent).
3. Sur le téléphone, ouvrez le fichier. Android demandera d'autoriser
   l'installation depuis cette source : acceptez.
4. L'application **Kibaré** apparaît dans la liste des applications.

> L'APK de démonstration est signé avec la clé de test d'Element. Il s'installe
> normalement. Pour un déploiement réel, l'État utiliserait sa propre clé.

---

# Étape 5 — Se connecter avec deux comptes

Nous utilisons deux agents du **ministère de la Santé**, tous deux membres du
groupe « Cellule de crise sanitaire » :

| Téléphone | Matricule | Nom (fictif) | Mot de passe de démo |
|---|---|---|---|
| **Téléphone A** | `demo-202` | Boukary ZONGO | `DemoPass202!` |
| **Téléphone B** | `demo-203` | Karim TIENDRÉBÉOGO | `DemoPass203!` |

`demo-203` est le compte que l'on **révoque pendant la démonstration**.

**Avant de commencer**, installez une application OTP sur chaque téléphone :
**FreeOTP** ou **Aegis** (toutes deux libres, disponibles sur F-Droid).

**Procédure de connexion**, identique sur les deux téléphones :

1. Ouvrir Kibaré → « Se connecter ».
   L'adresse du serveur est déjà remplie : il n'y a **aucun choix de serveur**.
2. La page de connexion Keycloak s'affiche.
3. Saisir le matricule (ex. `demo-202`) et le mot de passe.
4. Keycloak demande de **configurer l'OTP** : un QR code s'affiche.
   Ouvrir FreeOTP/Aegis → scanner le QR code → l'application génère un code à
   6 chiffres.
5. Saisir ce code. La connexion aboutit.
6. Aux connexions suivantes : matricule + mot de passe + code OTP du moment.

---

# Étape 6 — Vérifier que l'échange chiffré fonctionne

Sur le **téléphone A** (`demo-202`) :

1. Ouvrir le salon « Cellule de crise sanitaire ».
2. Envoyer un message, par exemple : `MESSAGE-TEST-JURY-123`.

Sur le **téléphone B** (`demo-203`) : le message doit arriver en quelques
secondes et être **lisible**.

Puis, sur le PC serveur, prouver que le serveur, lui, ne le lit pas :

```bash
./scripts/verif_serveur_ne_lit_rien.sh
```

Toutes les lignes doivent afficher **PASS**.

---

# Étape 7 — Checklist à tester avant de filmer

Cochez chaque point. En face : **ce que vous devez voir si ça marche**.

### 1. Échange de message
- Envoyer un texte de A vers B.
- **Attendu** : le message arrive en quelques secondes et s'affiche sur B.

### 2. Échange de fichier
- Depuis A, joindre une image (trombone → galerie) et l'envoyer.
- **Attendu** : B reçoit l'image et peut l'ouvrir **dans l'application**.

### 3. Capture d'écran bloquée
- Dans une conversation, faire une capture d'écran
  (Volume bas + Bouton marche, selon le modèle).
- **Attendu** : Android affiche un message du type « Impossible de faire une
  capture d'écran » **ou** l'image enregistrée est entièrement **noire**.
  Vérifiez aussi la vue des applications récentes : l'aperçu de Kibaré doit être
  noir.

### 4. Filigrane visible
- Regarder l'arrière-plan de la conversation, et ouvrir une image reçue.
- **Attendu** : un texte très pâle répété en diagonale, de la forme
  « Boukary ZONGO · demo-202 · 01/11/2026 ».
  Il est **volontairement discret** (opacité 7 %) : regardez de près, ou inclinez
  l'écran. Il ne doit pas gêner la lecture ni réagir aux doigts.

### 5. Copie impossible
- Appuyer longuement sur un message.
- **Attendu** : le menu propose « Répondre » et « Transférer », mais **pas**
  « Copier », **pas** « Partager », **pas** « Voir la source ».
- Essayer de sélectionner du texte dans une bulle.
- **Attendu** : impossible de sélectionner.

### 6. Pièce jointe non exportable
- Appuyer longuement sur un fichier reçu.
- **Attendu** : pas de « Enregistrer », pas de « Télécharger », pas de
  « Partager », pas de « Ouvrir avec… ».
  L'étiquette « Consultation interne uniquement » est visible sur la pièce jointe.
- Sur un fichier non image : un message « Consultation interne uniquement »
  s'affiche au lieu de l'ouvrir dans une autre application.

### 7. Transfert interne possible
- Appuyer longuement sur un message → « Transférer ».
- **Attendu** : la liste des **salons Kibaré** s'affiche, et seulement eux.
  Le transfert vers un autre salon fonctionne.

### 8. Révocation en direct
- Sur le PC, ouvrir `https://<ADRESSE_SERVEUR>/console/`, se connecter avec
  `demo-201` (Mariam OUÉDRAOGO, admin du ministère de la Santé,
  mot de passe `DemoPass201!`).
- Aller dans « Agents » → `demo-203` → bouton rouge **« Révoquer »**.
- Confirmer en tapant le matricule `demo-203`.
- **Attendu sur le téléphone B**, en quelques secondes :
  l'écran plein « **Accès révoqué** » s'affiche, sans bouton retour.
  L'historique des messages a disparu de l'appareil.
- Depuis le téléphone A, envoyer un nouveau message dans le groupe.
- **Attendu** : B ne le reçoit pas. Une tentative de reconnexion est refusée.

---

# Étape 8 — Script de la vidéo (3 minutes)

Filmez en plan fixe, les deux téléphones côte à côte, l'écran du PC derrière ou
en incrustation. Parlez lentement, phrases courtes.

---

### 0:00 – 0:20 · Le problème et la solution

**À l'écran** : la page d'accueil de Kibaré sur un téléphone, logo visible.

**À dire** :
> « Aujourd'hui, les agents de l'administration burkinabè échangent des
> informations de service sur WhatsApp ou Telegram, dont les serveurs sont à
> l'étranger. Kibaré est une messagerie souveraine, hébergée sur
> l'infrastructure de l'État, chiffrée de bout en bout. Notre thème :
> **Zéro fuite** — aucune information ne sort de l'application. »

---

### 0:20 – 1:10 · Échange chiffré, serveur aveugle

**À l'écran** :
1. Téléphone A : taper et envoyer `MESSAGE-TEST-JURY-123` dans
   « Cellule de crise sanitaire ».
2. Téléphone B : le message arrive, bien lisible.
3. Basculer sur le PC : lancer `./scripts/verif_serveur_ne_lit_rien.sh`.
4. Montrer les lignes **PASS** qui défilent.

**À dire** :
> « Boukary envoie un message à Karim. Il arrive immédiatement, en clair pour
> eux deux. Maintenant, regardons ce que voit le serveur. »
>
> *(pendant le script)*
>
> « Le message est introuvable dans la base de données. Aucun message en clair.
> Tout est stocké en `m.room.encrypted`. Rien dans les journaux. Le chiffrement
> est celui de Matrix, Olm et Megolm : **nous n'avons écrit aucune ligne de
> cryptographie**, nous avons utilisé un protocole éprouvé. »

---

### 1:10 – 2:00 · Révocation en direct

**À l'écran** :
1. La conversation de groupe est ouverte sur les deux téléphones.
2. Sur le PC : Console Kibaré → fiche de `demo-203` → « Révoquer » → confirmer.
3. Filmer le téléphone B : l'écran « **Accès révoqué** » apparaît.
4. Depuis A, envoyer un nouveau message.
5. Montrer que B ne le reçoit pas.

**À dire** :
> « Karim quitte le service, ou perd son téléphone. L'administratrice le révoque
> depuis la Console. »
>
> *(l'écran change)*
>
> « En quelques secondes : accès coupé, et **les données de l'appareil sont
> effacées** — messages, fichiers, clés de chiffrement. Boukary continue
> d'écrire dans le groupe : Karim ne reçoit plus rien, et ne pourra plus
> jamais lire ces messages, même s'il retrouvait son mot de passe. »

---

### 2:00 – 2:50 · Zéro fuite

**À l'écran** :
1. Tenter une capture d'écran → montrer le refus ou l'image noire.
2. Zoomer sur le filigrane en diagonale.
3. Appuyer longuement sur un message → montrer le menu sans « Copier » ni
   « Partager ».
4. Appuyer longuement sur une pièce jointe → pas de téléchargement, étiquette
   « Consultation interne uniquement ».

**À dire** :
> « Notre innovation : empêcher l'information de sortir. »
>
> « Capture d'écran : bloquée par le système, l'image est noire. Même dans les
> applications récentes. »
>
> « Une photo prise avec un autre téléphone, elle, est impossible à empêcher.
> Alors nous ajoutons un **filigrane nominatif** : nom, matricule, date, répété
> en diagonale. Si une image fuite, on sait de quel agent vient l'écran. »
>
> « Copier : retiré. Partager : retiré. Télécharger une pièce jointe : retiré.
> Le transfert reste possible, mais **uniquement vers un autre salon Kibaré**. »

---

### 2:50 – 3:00 · Conclusion

**À l'écran** : les deux téléphones côte à côte, puis le dépôt GitHub.

**À dire** :
> « Kibaré : souverain, chiffré de bout en bout, et sans fuite. Construit à
> partir de logiciels libres éprouvés — Matrix, Synapse, Keycloak — étendus et
> adaptés à l'administration burkinabè. Tout notre code est publié sous
> AGPL-3.0. Merci. »

---

## Conseils de tournage

- **Couper les données mobiles** avant de filmer : cela prouve que tout
  fonctionne sans Internet, et évite les notifications parasites.
- **Mode « Ne pas déranger »** sur les deux téléphones.
- Augmenter la **luminosité au maximum** : le filigrane est discret, il doit
  rester visible à la caméra.
- Répéter une fois sans filmer : la révocation ne se rejoue qu'après
  `python3 scripts/demo_reset.py`.
- Si une étape échoue pendant le tournage, **ne la coupez pas au montage sans
  la refaire** : le jury préfère une démonstration honnête.
