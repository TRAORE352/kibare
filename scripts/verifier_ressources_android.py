#!/usr/bin/env python3
"""
Contrôle statique des ressources Android modifiées pour Kibaré.

Pourquoi : le conteneur de l'agent n'a ni JDK ni SDK Android, donc aucun
`assembleFdroidRelease` ne peut être lancé ici. Ce script ne remplace pas une
compilation — il attrape la classe d'erreurs détectable sans compiler, et qui
casserait le build de l'équipe :

  1. un XML qui ne parse pas ;
  2. une référence @string / @drawable / @color / @style introuvable ;
  3. un identifiant de vue lu par du Kotlin via ViewBinding mais absent du
     layout, ou dont le TYPE est devenu incompatible avec les appels Kotlin ;
  4. un import Kotlin devenu inutilisé — fatal ici, allWarningsAsErrors = true.

PORTÉE : uniquement les fichiers que le fork Kibaré modifie ou ajoute, listés
par `git status`. Contrôler les 1429 XML d'Element produisait 234 signalements
dont aucun n'était imputable au fork : un contrôle qui crie partout ne se lit
plus, donc ne protège plus.

TROIS ERREURS À NE PAS REFAIRE (elles ont toutes produit de faux défauts) :

  - Lire le TEXTE d'un XML voit aussi les commentaires. `vector_settings_labs.xml`
    cite `@string/room_settings_labs_end_to_end` dans un bloc commenté : la
    chaîne n'existe pas, et c'est normal. On parse donc l'ARBRE, dont
    ElementTree a déjà retiré les commentaires.
  - Les types de vues s'héritent. `TextInputEditText` est un `EditText`, donc un
    `TextView` : lui appeler `.text` est licite. Une table plate de types
    produit un faux défaut par champ de saisie du projet.
  - Un layout peut en inclure un autre (`<include>`) ou poser des vues à
    l'exécution. Un identifiant absent du fichier n'est donc pas forcément
    absent de l'écran : on suit les `<include>` avant de conclure.

Usage : python3 verifier-ressources.py [/root/element-android]
"""
import os
import re
import subprocess
import sys
import xml.etree.ElementTree as ET

ANDROID = "{http://schemas.android.com/apk/res/android}"

# Ressources fournies par les bibliothèques (Material, AndroidX, Google Play
# Services) : déclarées hors du dépôt, donc introuvables ici sans que ce soit
# une erreur.
EXTERIEURES = {
    "appbar_scrolling_view_behavior", "bottom_sheet_behavior",
    "com_google_android_gms_fonts_certs_dev", "com_google_android_gms_fonts_certs_prod",
    "character_counter_pattern", "path_password_eye", "abc_action_bar_home_description",
    # androidx.preference : thème de la bibliothèque de préférences.
    "PreferenceThemeOverlay.v14.Material",
    # appcompat : attribut de thème du framework, référencé en ?attr/.
    "actionBarSize",
}

# Hiérarchie des vues Android utile ici : chaque type et ce dont il hérite.
HERITAGE = {
    "TextView": {"TextView"},
    "AppCompatTextView": {"TextView"},
    "MaterialTextView": {"TextView"},
    "Button": {"TextView", "Button"},
    "AppCompatButton": {"TextView", "Button"},
    "MaterialButton": {"TextView", "Button"},
    "CheckBox": {"TextView", "Button", "CheckBox"},
    "MaterialCheckBox": {"TextView", "Button", "CheckBox"},
    "RadioButton": {"TextView", "Button"},
    "SwitchMaterial": {"TextView", "Button"},
    "EditText": {"TextView", "EditText"},
    "AppCompatEditText": {"TextView", "EditText"},
    "TextInputEditText": {"TextView", "EditText"},
    "AutoCompleteTextView": {"TextView", "EditText"},
    "ImageView": {"ImageView"},
    "AppCompatImageView": {"ImageView"},
    "ShapeableImageView": {"ImageView"},
    "ImageButton": {"ImageView"},
    "ViewPager2": {"ViewPager2"},
    "RecyclerView": {"RecyclerView"},
    # Conteneurs et barres : ne sont ni TextView ni ImageView, donc tout appel
    # de EXIGENCES sur eux est une erreur de compilation. Les lister ici rend
    # ces erreurs détectables au lieu de « type inconnu, on ne conclut pas ».
    "Toolbar": {"Toolbar"},
    "MaterialToolbar": {"Toolbar"},
    "View": {"View"},
    "FrameLayout": {"ViewGroup"},
    "LinearLayout": {"ViewGroup"},
    "RelativeLayout": {"ViewGroup"},
    "ConstraintLayout": {"ViewGroup"},
    "CoordinatorLayout": {"ViewGroup"},
    "AppBarLayout": {"ViewGroup"},
    "NestedScrollView": {"ViewGroup"},
    "ScrollView": {"ViewGroup"},
    "TextInputLayout": {"ViewGroup"},
}

# Méthode ou propriété → type de base requis.
EXIGENCES = {
    "setText": "TextView", "text": "TextView", "setTextColor": "TextView",
    "setImageResource": "ImageView", "setImageDrawable": "ImageView",
}


def fichiers_du_fork(racine):
    """Les fichiers modifiés ou ajoutés par le fork, d'après git."""
    out = subprocess.run(["git", "status", "--porcelain"], cwd=racine,
                         capture_output=True, text=True).stdout
    fichiers = []
    for ligne in out.split("\n"):
        if not ligne.strip():
            continue
        chemin = ligne[3:].strip().strip('"')
        if " -> " in chemin:
            chemin = chemin.split(" -> ")[1]
        if os.path.exists(os.path.join(racine, chemin)):
            fichiers.append(chemin)
    return fichiers


def tous_les_fichiers(racine, suffixe=""):
    for dirpath, dirnames, noms in os.walk(racine):
        dirnames[:] = [d for d in dirnames if d not in (".git", "build", ".gradle")]
        for n in noms:
            if n.endswith(suffixe):
                yield os.path.join(dirpath, n)


# --- 1. Les XML du fork parsent --------------------------------------------

def xml_parsent(racine, fichiers):
    erreurs, n = [], 0
    for f in fichiers:
        if not f.endswith(".xml"):
            continue
        n += 1
        try:
            ET.parse(os.path.join(racine, f))
        except ET.ParseError as e:
            erreurs.append(f"{f} : {e}")
    return n, erreurs


# --- 2. Inventaire des ressources déclarées ---------------------------------

ALIAS = {"string-array": "array", "integer-array": "array",
         "declare-styleable": "attr"}


def inventaire(racine):
    res = {}
    for chemin in tous_les_fichiers(racine):
        p = chemin.replace("\\", "/")
        if "/res/" not in p:
            continue
        dossier = os.path.basename(os.path.dirname(p))
        nom = os.path.basename(p)
        type_base = dossier.split("-")[0]
        if type_base in ("drawable", "mipmap", "layout", "font", "raw", "anim",
                         "animator", "menu", "xml", "color"):
            res.setdefault(type_base, set()).add(os.path.splitext(nom)[0])
            continue
        if type_base == "values" and nom.endswith(".xml"):
            try:
                arbre = ET.parse(p).getroot()
            except ET.ParseError:
                continue
            for el in arbre:
                t = el.tag
                if t == "declare-styleable":
                    for a in el:
                        if a.get("name"):
                            res.setdefault("attr", set()).add(a.get("name"))
                    continue
                if t == "item":
                    t = el.get("type", "")
                t = ALIAS.get(t, t)
                if el.get("name"):
                    res.setdefault(t, set()).add(el.get("name"))
    # app_name est produit par build.gradle (resValue), pas par un fichier de ressources.
    res.setdefault("string", set()).add("app_name")
    return res


REF = re.compile(r'[@?](?:(android|tools):)?'
                 r'(string|drawable|color|style|dimen|mipmap|attr|font|plurals|array|raw|layout)'
                 r'/([A-Za-z0-9_.]+)')


def refs_d_un_arbre(chemin):
    """
    Toutes les références @type/nom d'un XML, lues dans l'ARBRE : les blocs
    commentés sont donc ignorés, puisqu'ils ne compilent pas.
    """
    try:
        arbre = ET.parse(chemin).getroot()
    except ET.ParseError:
        return []
    trouvees = []
    for el in arbre.iter():
        for valeur in el.attrib.values():
            trouvees += REF.findall(valeur)
        for texte in (el.text, el.tail):
            if texte:
                trouvees += REF.findall(texte)
    return trouvees


def references_resolues(racine, fichiers, res):
    manquants, n = [], 0
    for f in fichiers:
        if not f.endswith(".xml") or "/res/" not in f.replace("\\", "/"):
            continue
        for espace, t, nom in refs_d_un_arbre(os.path.join(racine, f)):
            # @android:... et @tools:... désignent le framework, pas le dépôt.
            if espace:
                continue
            n += 1
            if nom in EXTERIEURES or nom in res.get(t, set()):
                continue
            if t == "style" and any(s.startswith(nom) for s in res.get("style", set())):
                continue
            manquants.append(f"{f} → @{t}/{nom}")
    return n, sorted(set(manquants))


# --- 3. ViewBinding : identifiants et types ---------------------------------

def ids_et_types(racine, layout, vus=None):
    """
    {identifiant: type} d'un layout, en suivant les <include> : un identifiant
    peut venir d'un layout inclus, pas seulement du fichier lui-même.
    """
    vus = vus or set()
    if layout in vus:
        return {}
    vus.add(layout)
    out = {}
    try:
        arbre = ET.parse(layout).getroot()
    except (ET.ParseError, OSError):
        return out
    dossier = os.path.dirname(layout)
    for el in arbre.iter():
        ident = el.get(ANDROID + "id")
        if ident:
            out[ident.split("/")[-1]] = el.tag.split(".")[-1]
        if el.tag == "include":
            ref = el.get("layout", "")
            if ref.startswith("@layout/"):
                inclus = os.path.join(dossier, ref.split("/")[-1] + ".xml")
                if os.path.exists(inclus):
                    out.update(ids_et_types(racine, inclus, vus))
    return out


# `views.X` n'est un identifiant de vue que si `views` n'est pas la fin d'un nom
# qualifié (le paquet `…core.ui.views.CurrentCallsView`) et si X n'est pas
# immédiatement appelé — `views.hideComposerViews()` est une fonction
# d'extension sur le binding, pas une vue. Le `(?![\w(])` après l'identifiant
# empêche le retour arrière d'amputer le nom pour contourner cette garde
# (`hideComposerViews` relu comme `hideComposerView` + `s`).
USAGE_VIEWS = re.compile(r"(?<![\w.])views\.(\w+)(?![\w(])(?:\.(\w+)\b)?")

# Une fonction qui redéfinit `views` localement (binding d'une boîte de dialogue,
# d'un item de liste) parle d'un AUTRE layout : ses lignes ne concernent pas
# l'écran contrôlé.
SHADOW = re.compile(r"\bval\s+views\s*=\s*(\w+Binding)\b")


def lignes_hors_shadow(texte):
    """
    Le texte privé de ses imports et des blocs où `views` est une variable
    locale. Découpage sur l'indentation : le bloc court de la redéfinition
    jusqu'au retour au niveau d'indentation de celle-ci.
    """
    lignes = texte.split("\n")
    garder, i = [], 0
    while i < len(lignes):
        l = lignes[i]
        if l.startswith("import "):
            i += 1
            continue
        if SHADOW.search(l):
            niveau = len(l) - len(l.lstrip())
            i += 1
            while i < len(lignes):
                suite = lignes[i]
                if suite.strip() and (len(suite) - len(suite.lstrip())) < niveau:
                    break
                i += 1
            continue
        garder.append(l)
        i += 1
    return "\n".join(garder)


def kotlin_candidats(racine, fichiers):
    """
    Les .kt susceptibles de porter un binding : ceux que le fork modifie, plus
    ceux qu'un grep désigne comme inflant un binding. Lire les 4198 .kt du
    dépôt coûtait 177 s sur ce système de fichiers ; grep le fait en une.
    """
    out = {f for f in fichiers if f.endswith(".kt")}
    res = subprocess.run(["grep", "-rl", "--include=*.kt", r"Binding\.inflate", "."],
                         cwd=racine, capture_output=True, text=True)
    for l in res.stdout.split("\n"):
        l = l.strip().lstrip("./")
        if l.endswith(".kt"):
            out.add(l)
    return sorted(out)


def binding_coherent(racine, fichiers):
    """
    Pour les écrans touchés par le fork : chaque `views.X` lu par le Kotlin
    existe-t-il dans le layout, et son type supporte-t-il l'appel ?
    """
    layouts = {}
    for chemin in tous_les_fichiers(racine, ".xml"):
        p = chemin.replace("\\", "/")
        if "/res/layout" in p:
            layouts.setdefault(os.path.splitext(os.path.basename(p))[0], p)

    # Les layouts du fork, et les Kotlin du fork : on contrôle les deux sens.
    layouts_touches = {os.path.splitext(os.path.basename(f))[0]
                       for f in fichiers if "/res/layout" in f.replace("\\", "/")}
    kotlin_touches = {f for f in fichiers if f.endswith(".kt")}

    binding_re = re.compile(r"(\w+Binding)\.inflate")
    problemes, controles = [], []
    for rel in kotlin_candidats(racine, fichiers):
        kt = os.path.join(racine, rel)
        if not os.path.exists(kt):
            continue
        texte = open(kt, encoding="utf-8", errors="replace").read()
        m = binding_re.search(texte)
        if not m:
            continue
        snake = re.sub(r"(?<!^)(?=[A-Z])", "_", m.group(1)[:-len("Binding")]).lower()
        # On ne retient que ce que le fork touche : un layout refait, ou un
        # Kotlin modifié.
        if snake not in layouts_touches and rel not in kotlin_touches:
            continue
        layout = layouts.get(snake)
        if not layout:
            continue
        table = ids_et_types(racine, layout)
        if not table:
            continue
        controles.append(f"{snake}.xml ↔ {os.path.basename(rel)}")
        for ident, membre in USAGE_VIEWS.findall(lignes_hors_shadow(texte)):
            if ident not in table:
                problemes.append(f"{rel} : views.{ident} absent de {snake}.xml")
                continue
            requis = EXIGENCES.get(membre)
            if not requis:
                continue
            reel = table[ident]
            # Un type inconnu de la table d'héritage (vue personnalisée du
            # projet) ne permet pas de conclure : on ne signale rien.
            if reel in HERITAGE and requis not in HERITAGE[reel]:
                problemes.append(
                    f"{rel} : views.{ident}.{membre} exige un {requis}, "
                    f"mais {ident} est un <{reel}> dans {snake}.xml")
    return controles, sorted(set(problemes))


# --- 4. Imports Kotlin inutilisés -------------------------------------------

def imports_inutilises(racine, fichiers):
    problemes, n = [], 0
    for f in fichiers:
        if not f.endswith(".kt"):
            continue
        n += 1
        lignes = open(os.path.join(racine, f), encoding="utf-8",
                      errors="replace").read().split("\n")
        corps = "\n".join(l for l in lignes if not l.startswith("import "))
        for l in lignes:
            if not l.startswith("import "):
                continue
            cible = l.split(" ")[1].strip().split(".")[-1]
            if cible == "*":
                continue
            if not re.search(rf"\b{re.escape(cible)}\b", corps):
                problemes.append(f"{f} : import inutilisé → {cible}")
    return n, problemes


def main(racine):
    fichiers = fichiers_du_fork(racine)
    print(f"Fichiers modifiés ou ajoutés par le fork : {len(fichiers)}")
    print()
    echecs = 0

    n, err = xml_parsent(racine, fichiers)
    print(f"[1] XML du fork analysés : {n}")
    for e in err:
        print("    ÉCHEC", e)
    echecs += len(err)

    res = inventaire(racine)
    nref, manquants = references_resolues(racine, fichiers, res)
    print(f"[2] Références @type/nom contrôlées dans ces fichiers : {nref}")
    for m in manquants:
        print("    ÉCHEC référence introuvable :", m)
    echecs += len(manquants)

    controles, pbs = binding_coherent(racine, fichiers)
    print(f"[3] Écrans contrôlés (layout ↔ Kotlin) : {len(controles)}")
    for c in controles:
        print("      ", c)
    for p in pbs:
        print("    ÉCHEC", p)
    echecs += len(pbs)

    n, pbs = imports_inutilises(racine, fichiers)
    print(f"[4] Fichiers Kotlin du fork contrôlés : {n}")
    for p in pbs:
        print("    ÉCHEC", p)
    echecs += len(pbs)

    print()
    print("RÉSULTAT :", "aucun défaut détecté" if echecs == 0 else f"{echecs} défaut(s)")
    return 1 if echecs else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1] if len(sys.argv) > 1 else "/root/element-android"))
