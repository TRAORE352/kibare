# Identité visuelle — Kibaré

Ce dossier contient la source de l'identité visuelle et les règles qui la
gouvernent. Toute modification du logo ou des couleurs commence ici.

## Fichiers

| Fichier | Rôle |
|---|---|
| `logo-original.png` | Logo fourni par l'équipe, intact, fond blanc |
| `logo-kibare.png` | Même logo, fond rendu transparent et recadré — version de travail |
| `icone-kibare.svg` | Icône d'application, **redessinée** (voir plus bas) |
| `icone-512.png` | Icône composée sur fond blanc, pour les magasins d'applications |
| `icone-glyphe-512.png` | Icône sans fond, pour le web et la documentation |

## Couleurs

Relevées au pixel sur le logo fourni, pour qu'aucun écart ne soit perceptible
entre le logo et les interfaces qui l'entourent.

| Rôle | Valeur | Usage |
|---|---|---|
| Vert | `#027435` | Actions principales, liens, onglet actif |
| Rouge | `#DB1E1D` | Révocation et alertes **uniquement** |
| Jaune | `#FECE15` | Étoile du logo, filet tricolore — décoratif |

Les neutres (encre `#14181B`, texte `#2E3438`, gris `#646E74`, bordures
`#E4E7E9`) sont légèrement chauds. Le noir pur n'est jamais utilisé : il durcit
l'écran et jure avec les couleurs du drapeau.

## Principe directeur

**Les couleurs nationales sont portées par le logo, pas par l'interface.**

Le drapeau burkinabè est déjà présent dans le symbole. Le répéter en aplats sur
les fonds, les en-têtes et les boutons produirait une interface saturée et
datée, et affaiblirait le logo lui-même.

L'interface est donc construite sur une base claire et typographiée. Le vert et
le rouge n'apparaissent qu'en accents fonctionnels : une action, un état, un
lien. La seule présence franche des trois couleurs est un filet de 2 px sous
l'en-tête — une signature, jamais un habillage.

L'autorité institutionnelle se lit dans la retenue.

## Pourquoi l'icône est redessinée et non rétrécie

Une icône d'application n'est pas un logo réduit.

Dans le logo, les trois points et le cadenas sont proportionnés pour une
lecture à grande taille. Réduits à 48 px — la taille réelle d'une icône sur un
téléphone — ils se confondent en une tache illisible. L'arc et l'étoile, qui
dépassent en haut, seraient de surcroît rognés par les lanceurs Android, qui
découpent les icônes selon un cercle ou un carré arrondi.

`icone-kibare.svg` reprend donc la composition et les couleurs du logo, mais
avec des proportions optiques : bulle resserrée, points agrandis et espacés,
cadenas élargi et dégagé du bord. Le dessin tient dans le cercle inscrit du
repère 120×120, c'est-à-dire dans la zone sûre des icônes adaptatives.

Résultat vérifié par rendu aux tailles réelles : les trois points et le cadenas
restent distincts à 48 px, et rien n'est rogné en version ronde.

## Règles à respecter

- Ne jamais déformer le logo : seule la hauteur se règle, la largeur suit.
- Ne jamais poser le logo sur un fond coloré saturé — il perd sa lisibilité.
- Le rouge est réservé aux actions irréversibles et aux erreurs. L'utiliser
  pour une action ordinaire détruit sa valeur de signal.
- Les boutons principaux sont verts, les secondaires blancs à bordure.
- Pas de rayons de bordure supérieurs à 12 px : une administration n'est pas
  une application grand public.

## Régénérer les icônes Android

Après toute modification de `icone-kibare.svg` :

```bash
python3 - <<'EOF'
import cairosvg, io
from PIL import Image, ImageDraw
def rendu(t):
    return Image.open(io.BytesIO(cairosvg.svg2png(
        url="design/icone-kibare.svg", output_width=t, output_height=t))).convert("RGBA")
def icone(t, rond=False):
    img = Image.new("RGBA", (t, t), (0, 0, 0, 0)); d = ImageDraw.Draw(img)
    if rond: d.ellipse([0, 0, t-1, t-1], fill="#FFFFFF")
    else:    d.rounded_rectangle([0, 0, t-1, t-1], radius=int(t*0.22), fill="#FFFFFF")
    s = int(t * 0.80); g = rendu(s)
    img.paste(g, ((t-s)//2, (t-s)//2), g); return img
for dens, t in (("mdpi",48), ("hdpi",72), ("xhdpi",96), ("xxhdpi",144), ("xxxhdpi",192)):
    icone(t).save(f"ic_launcher_{dens}.png", optimize=True)
    icone(t, rond=True).save(f"ic_launcher_round_{dens}.png", optimize=True)
EOF
```

Contrôler ensuite le rendu **à 48 px**, pas seulement en grand. Une icône qui
ne survit pas à la réduction n'est pas une icône.
