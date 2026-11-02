#!/usr/bin/env python3
"""
Mutation : casse chaque mécanisme du vérificateur à tour de rôle et confirme
que le contrôle correspondant passe au rouge. Un contrôle qui reste vert sur
son propre mutant ne protège de rien.

Chaque mutant est appliqué sur une COPIE de sauvegarde restaurée ensuite, y
compris en cas d'exception (sinon le dépôt garde la blessure).
"""
import importlib.util
import os
import shutil
import sys
import traceback

R = "/root/element-android"
SPEC = os.path.join(os.path.dirname(os.path.abspath(__file__)), "verifier-ressources.py")


def charger():
    spec = importlib.util.spec_from_file_location("verif", SPEC)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


m = charger()
FICHIERS = m.fichiers_du_fork(R)
RES = m.inventaire(R)

LAYOUT_SO = "vector/src/main/res/layout/activity_signed_out.xml"
KT_SO = "vector/src/main/java/im/vector/app/features/signout/hard/SignedOutActivity.kt"
THEME = "library/ui-styles/src/main/res/values/theme_light.xml"


def avec_mutation(chemins, muter, lire):
    """Applique `muter`, lit le contrôle via `lire`, restaure dans tous les cas."""
    sauv = {c: open(os.path.join(R, c), "rb").read() for c in chemins}
    try:
        muter()
        return lire()
    finally:
        for c, octets in sauv.items():
            open(os.path.join(R, c), "wb").write(octets)


def remplacer(chemin, avant, apres):
    p = os.path.join(R, chemin)
    t = open(p, encoding="utf-8").read()
    assert avant in t, f"ancre absente dans {chemin} : {avant!r}"
    open(p, "w", encoding="utf-8").write(t.replace(avant, apres, 1))


MUTANTS = []


# [1] XML qui ne parse plus.
def m1():
    def muter():
        p = os.path.join(R, LAYOUT_SO)
        open(p, "a", encoding="utf-8").write("\n<balise_non_fermee>\n")

    def lire():
        _, err = m.xml_parsent(R, FICHIERS)
        return err
    return avec_mutation([LAYOUT_SO], muter, lire)


MUTANTS.append(("[1] XML du fork parsent", "balise non fermée ajoutée", m1))


# [2] Référence @style/ vers une ressource inexistante.
def m2():
    def muter():
        remplacer(THEME, "@style/PreferenceThemeOverlay.v14.Material",
                  "@style/KibareThemeQuiNExistePas")

    def lire():
        _, manquants = m.references_resolues(R, FICHIERS, RES)
        return manquants
    return avec_mutation([THEME], muter, lire)


MUTANTS.append(("[2] références @type/nom résolues",
                "@style/ pointé vers un style inexistant", m2))


# [3a] Identifiant lu par le Kotlin, retiré du layout.
def m3a():
    def muter():
        remplacer(LAYOUT_SO, '@+id/signedOut"', '@+id/signedOutRenomme"')

    def lire():
        _, pbs = m.binding_coherent(R, FICHIERS)
        return pbs
    return avec_mutation([LAYOUT_SO], muter, lire)


MUTANTS.append(("[3a] identifiant de vue absent du layout",
                "android:id renommé dans activity_signed_out.xml", m3a))


# [3b] Type de vue incompatible avec l'appel Kotlin : une MaterialToolbar
# (réelle, dans le layout du fork) à qui on demande setImageResource.
KT_BIV = "vector/src/main/java/im/vector/app/features/media/BigImageViewerActivity.kt"


def m3b():
    def muter():
        remplacer(KT_BIV, "setupToolbar(views.bigImageViewerToolbar)",
                  "setupToolbar(views.bigImageViewerToolbar)\n"
                  "        views.bigImageViewerToolbar.setImageResource(0)")

    def lire():
        _, pbs = m.binding_coherent(R, FICHIERS)
        return pbs
    return avec_mutation([KT_BIV], muter, lire)


MUTANTS.append(("[3b] type de vue incompatible avec l'appel",
                "setImageResource appelé sur la MaterialToolbar", m3b))


# [4] Import Kotlin inutilisé (fatal : allWarningsAsErrors).
def m4():
    def muter():
        p = os.path.join(R, KT_SO)
        t = open(p, encoding="utf-8").read()
        lignes = t.split("\n")
        i = max(n for n, l in enumerate(lignes) if l.startswith("import "))
        lignes.insert(i + 1, "import java.util.concurrent.atomic.AtomicLong")
        open(p, "w", encoding="utf-8").write("\n".join(lignes))

    def lire():
        _, pbs = m.imports_inutilises(R, FICHIERS)
        return pbs
    return avec_mutation([KT_SO], muter, lire)


MUTANTS.append(("[4] imports Kotlin inutilisés",
                "import AtomicLong jamais utilisé ajouté", m4))


def main():
    print(f"Fichiers du fork : {len(FICHIERS)}")
    print()
    # Empreinte de l'arbre AVANT : le fork a déjà des modifications non
    # indexées, donc « propre » ne veut pas dire « git diff vide » — on compare
    # le diff à lui-même.
    import hashlib
    import subprocess

    def empreinte():
        d = subprocess.run(["git", "diff"], cwd=R, capture_output=True, text=True).stdout
        return hashlib.sha256(d.encode()).hexdigest()[:12]

    avant = empreinte()

    survivants = 0
    for nom, description, fn in MUTANTS:
        try:
            trouve = fn()
        except Exception:
            traceback.print_exc()
            trouve = []
        etat = "TUÉ" if trouve else "SURVIVANT"
        print(f"{etat:10} {nom}")
        print(f"           mutant : {description}")
        for t in trouve[:3]:
            print(f"           → {t}")
        if not trouve:
            survivants += 1
        print()

    apres = empreinte()
    intact = avant == apres
    print(f"Arbre de travail après restauration : "
          f"{'identique' if intact else 'DIVERGENT'} ({avant} → {apres})")

    print()
    print(f"Mutants tués : {len(MUTANTS) - survivants}/{len(MUTANTS)}")
    return 1 if survivants or not intact else 0


if __name__ == "__main__":
    sys.exit(main())
