# Vidéo de démonstration Kibaré — 3 minutes

Prompt destiné à Claude pour produire la vidéo de candidature, avec
sous-titres incrustés en français.

---

## 1. Ce qui est fourni, et ce qui ne l'est pas

### Captures disponibles

Dossier : `kibare-video/captures/`

| Fichier | Contenu | Format |
|---|---|---|
| `01-connexion-desktop.png` | Page de connexion Keycloak, état nominal | 1440×900 |
| `02-connexion-mobile.png` | Même page, téléphone | 390×844 |
| `03-agents.png` | Console — liste des agents, compteurs | 1440×900 |
| `04-agent-detail.png` | Console — fiche agent + bloc de révocation | 1440×900 |
| `05-annuaire.png` | Console — annuaire groupé par ministère | 1440×900 |
| `06-enrolement.png` | Console — formulaire d'enrôlement | 1440×900 |
| `07-journal.png` | Console — journal d'audit | 1440×900 |
| `08-agents-mobile.png` | Console sur téléphone | 390×844 |
| `09-android-accueil-MAQUETTE.png` | Écran d'accueil de l'application | 390×844 |
| `10-connexion-refus.png` | Connexion refusée (identifiants invalides) | 1440×900 |

### Avertissement à respecter impérativement

**`09-android-accueil-MAQUETTE.png` est une MAQUETTE, pas une capture de
l'application en fonctionnement.** Elle reproduit fidèlement le layout
`fragment_ftue_auth_splash.xml` du fork (mêmes textes, même vert `#027435`),
mais aucun appareil Android n'a été filmé.

Conséquences pour le montage :

- ne jamais la présenter comme une capture d'écran de l'APK ;
- l'accompagner d'une mention discrète en bas d'image : `Maquette de l'interface` ;
- ne pas prétendre dans la narration que l'application « tourne » à l'écran.

Si une vraie capture d'appareil est obtenue d'ici le montage, elle remplace ce
fichier et la mention disparaît. Voir la section 6.

### Les écrans de la messagerie elle-même manquent

Il n'existe aucune capture de la conversation, du filigrane sur les images, ni
de l'écran « accès révoqué ». Ces fonctions existent dans le code, mais **la
vidéo ne doit pas les montrer** : pas d'écran, pas de démonstration. La
narration peut les citer comme capacités, au passé technique, sans visuel.

---

## 2. Spécifications techniques

- Durée : **3 minutes maximum**. Viser 2 min 50 pour garder une marge.
- Format : 1920×1080, 30 ips, MP4 / H.264.
- Sous-titres : **incrustés** (pas de fichier séparé), français, bas de l'écran,
  texte blanc sur bandeau sombre translucide, taille lisible sur téléphone.
- Voix off : optionnelle. Si absente, les sous-titres portent seuls le récit et
  leur rythme doit être ralenti d'environ 15 %.
- Musique : aucune, ou très discrète. Le sujet est institutionnel.

### Charte visuelle

Reprendre exactement l'identité des captures, sans en inventer :

- Vert : `#027435` — couleur d'action, titres de section
- Rouge : `#DB1E1D` — alertes et révocation uniquement
- Encre : `#14181B` · Gris secondaire : `#646E74`
- Fond : `#FAFBFB` · Surface : `#FFFFFF`
- Police : IBM Plex Sans (Regular et Bold)

Le jaune de l'étoile du logo est **décoratif seulement** : ne jamais l'utiliser
comme couleur de texte ou de fond.

### Traitement des images

- Transitions : fondu enchaîné de 300 ms. Pas d'effet 3D, pas de rotation.
- Mouvement : léger zoom avant (1.0 → 1.04) sur les plans fixes de plus de
  4 secondes, pour éviter l'image morte.
- Captures desktop : cadrer plein écran, recadrer si nécessaire sur la zone
  utile plutôt que de tout réduire.
- Captures mobile : présenter dans un cadre de téléphone neutre, centré, sur
  fond `#FAFBFB`.
- Surbrillance : quand le sous-titre cite un élément précis (un compteur, un
  bouton), l'encadrer d'un trait vert 2 px, coins arrondis 6 px, apparition en
  200 ms.

---

## 3. Découpage, plan par plan

Durées indicatives, total 2 min 50.

### Séquence 1 — Le problème (0:00 → 0:22)

**Visuel** : écran noir `#14181B`, texte blanc centré, apparition mot à mot.
Puis le logo Kibaré en fondu.

**Sous-titres**
1. `Aujourd'hui, les agents de l'administration échangent sur WhatsApp.` (0:00–0:05)
2. `Des documents officiels transitent par des serveurs étrangers.` (0:05–0:11)
3. `L'État n'a aucun moyen de couper l'accès d'un agent qui part.` (0:11–0:17)
4. `Kibaré répond à ces trois problèmes.` (0:17–0:22)

### Séquence 2 — L'application de l'agent (0:22 → 0:52)

**Visuel** : `09-android-accueil-MAQUETTE.png` dans un cadre de téléphone.
Mention `Maquette de l'interface` en bas à droite, gris `#646E74`, 14 px.
Zoom lent. Surbrillance successive des trois garanties au fil des sous-titres.

**Sous-titres**
5. `L'agent reçoit un téléphone déjà enrôlé par son administration.` (0:22–0:28)
6. `Pas d'inscription, pas de choix de service : un seul bouton.` (0:28–0:34)
7. `Les échanges sont chiffrés de bout en bout.` (0:34–0:40)
8. `Le serveur de l'État lui-même ne peut pas les lire.` (0:40–0:46)
9. `Aucune donnée ne quitte le territoire national.` (0:46–0:52)

### Séquence 3 — La connexion souveraine (0:52 → 1:12)

**Visuel** : `01-connexion-desktop.png`, puis fondu vers
`10-connexion-refus.png` au sous-titre 12. Surbrillance du message rouge.

**Sous-titres**
10. `L'accès passe par le fournisseur d'identité de l'État.` (0:52–0:58)
11. `Keycloak, auto-hébergé, aux couleurs de l'administration.` (0:58–1:05)
12. `Un identifiant invalide est refusé à la porte.` (1:05–1:12)

### Séquence 4 — La console d'administration (1:12 → 2:10)

**Visuel** : enchaînement `03-agents.png` → `06-enrolement.png` →
`04-agent-detail.png` → `05-annuaire.png` → `07-journal.png`.

Surbrillances : les quatre compteurs (sous-titre 13), le bouton « Enrôler un
agent » (15), le bloc rouge de révocation (17), les groupes de ministères (19).

**Sous-titres**
13. `L'administrateur voit l'état du parc en un coup d'œil.` (1:12–1:18)
14. `Quatre agents enrôlés, deux accès actifs, un révoqué.` (1:18–1:25)
15. `L'enrôlement crée le compte et son jeton d'activation.` (1:25–1:32)
16. `Chaque agent est rattaché à son ministère et à sa direction.` (1:32–1:39)
17. `La révocation coupe l'accès immédiatement.` (1:39–1:46)
18. `Les sessions sont fermées, l'appareil ne reçoit plus rien.` (1:46–1:53)
19. `L'annuaire reste cloisonné par ministère.` (1:53–2:02)
20. `Et chaque action sensible laisse une trace horodatée.` (2:02–2:10)

### Séquence 5 — La souveraineté technique (2:10 → 2:36)

**Visuel** : fond `#FAFBFB`. Schéma simple apparaissant par blocs — trois
rectangles bordés vert reliés verticalement :
`Application Android (fork Element)` → `Synapse + Keycloak` → `Serveur de l'État`.
Sous le schéma, quatre pastilles : `Chiffrement E2E` · `Aucune télémétrie` ·
`Certificat de l'État` · `100 % logiciel libre`.

**Sous-titres**
21. `Toute la pile est auto-hébergée et open source.` (2:10–2:17)
22. `Matrix et Synapse pour la messagerie, Keycloak pour l'identité.` (2:17–2:24)
23. `Aucune télémétrie, aucun service tiers, aucun appel sortant.` (2:24–2:30)
24. `Le code est auditable, ligne par ligne.` (2:30–2:36)

### Séquence 6 — Clôture (2:36 → 2:50)

**Visuel** : logo Kibaré centré sur fond blanc, puis la ligne institutionnelle
en gris. Fondu au blanc.

**Sous-titres**
25. `Kibaré — la messagerie souveraine de l'administration burkinabè.` (2:36–2:43)
26. `Le code, la documentation et l'application : github.com/TRAORE352/kibare` (2:43–2:50)

---

## 4. Règles de rédaction des sous-titres

- Deux lignes maximum, 42 caractères par ligne.
- Une idée par sous-titre. Jamais de phrase coupée entre deux plans.
- Vocabulaire simple : le jury n'est pas forcément technique.
- Accents et apostrophes typographiques corrects — c'est un produit d'État.
- Durée minimale d'affichage : 2 secondes, même pour une phrase courte.

---

## 5. Ce qu'il ne faut pas dire

Ces affirmations seraient fausses et décrédibiliseraient le dossier :

- « Application disponible sur le Play Store » — elle ne l'est pas.
- « Déployé dans les ministères » — aucun déploiement réel à ce jour.
- « X agents utilisent Kibaré » — les données montrées sont fictives, et la
  console l'indique elle-même en pied de page.
- « Audité par un tiers » — aucun audit externe n'a eu lieu.
- Toute démonstration d'une fonction dont aucune capture n'existe.

Si un plan manque pour illustrer une affirmation, **supprimer l'affirmation**,
pas inventer le plan.

---

## 6. Si une vraie capture d'appareil devient disponible

L'APK se trouve dans les artefacts de compilation du dépôt. Sur un téléphone
Android ou un émulateur :

1. installer l'APK correspondant à l'architecture de l'appareil ;
2. capturer l'écran d'accueil, l'écran de connexion, une conversation ;
3. remplacer `09-android-accueil-MAQUETTE.png` par la capture réelle ;
4. **retirer la mention `Maquette de l'interface`** du plan correspondant ;
5. les captures de conversation permettent alors d'ajouter un plan à la
   séquence 2, en reprenant 4 à 5 secondes à la séquence 4.

Attention : les APK publiés au 1er novembre sont antérieurs à la refonte
graphique. Une capture faite à partir de ces fichiers montrerait l'ancienne
interface. Recompiler avant de capturer.
