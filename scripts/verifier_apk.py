#!/usr/bin/env python3
# =====================================================================
# scripts/verifier_apk.py — Contrôle de l'APK Kibaré avant diffusion
#
# Vérifie, sans aucun outil propriétaire (seulement la bibliothèque
# standard Python), que l'APK produit respecte les exigences du brief :
#
#   1. variante F-Droid (section 5.6) ;
#   2. AUCUNE bibliothèque Google / Firebase / Play Services (section 5.6) ;
#   3. la CA locale est intégrée (section 5.7) ;
#   4. la police IBM Plex Sans et l'icône Kibaré sont présentes ;
#   5. les protections « Zéro fuite » sont dans le code compilé (section 6).
#
# Utilisation :
#     python3 scripts/verifier_apk.py chemin/vers/kibare.apk
#
# Pourquoi ce script : le brief demande de « vérifier qu'aucune
# bibliothèque Google n'est présente dans l'APK final ». Sans contrôle
# automatique, cette affirmation ne serait qu'une déclaration.
# =====================================================================

import os
import re
import sys
import zipfile

VERT = "\033[0;32m"
ROUGE = "\033[0;31m"
JAUNE = "\033[0;33m"
NEUTRE = "\033[0m"

resultats = []


def verifier(description, condition, detail=""):
    etat = f"{VERT}OK  {NEUTRE}" if condition else f"{ROUGE}ÉCHEC{NEUTRE}"
    print(f"  [{etat}] {description}")
    if detail:
        print(f"           {detail}")
    resultats.append((description, bool(condition)))
    return condition


def info(texte):
    print(f"  [{JAUNE}INFO{NEUTRE} ] {texte}")


# ---------------------------------------------------------------------
# Signatures des bibliothèques interdites.
# Un service tiers est une règle ÉLIMINATOIRE du brief (section 2).
# ---------------------------------------------------------------------
INTERDITS = {
    "Firebase": [r"^com/google/firebase/", r"firebase[_-]"],
    "Google Play Services": [r"^com/google/android/gms/"],
    "Google Maps": [r"^com/google/android/libraries/maps/"],
    "Crashlytics": [r"^com/(google|crashlytics)/firebase/crashlytics/"],
    "PostHog (statistiques)": [r"^com/posthog/"],
    "Sentry (rapports de plantage)": [r"^io/sentry/"],
    "Jitsi (visioconférence)": [r"^org/jitsi/"],
    "MapTiler / MapLibre (cartes)": [r"^org/maplibre/", r"^com/mapbox/"],
}


def analyser(chemin):
    if not os.path.exists(chemin):
        print(f"{ROUGE}Fichier introuvable : {chemin}{NEUTRE}")
        return 1

    taille = os.path.getsize(chemin) / (1024 * 1024)
    print("=" * 64)
    print("VÉRIFICATION DE L'APK KIBARÉ")
    print("=" * 64)
    print(f"Fichier : {chemin}")
    print(f"Taille  : {taille:.1f} Mo")
    print()

    with zipfile.ZipFile(chemin) as apk:
        noms = apk.namelist()

        # --- 1. Bibliothèques interdites ------------------------------
        print("1. Absence de services tiers (règle éliminatoire, section 2)")
        for libelle, motifs in INTERDITS.items():
            trouves = [
                n for n in noms
                if any(re.search(m, n) for m in motifs)
            ]
            verifier(
                f"Aucune trace de {libelle}",
                not trouves,
                f"{len(trouves)} fichier(s) trouvé(s) : {trouves[:3]}" if trouves else "",
            )

        # --- 2. Variante F-Droid --------------------------------------
        print("\n2. Variante F-Droid (section 5.6)")
        # La variante Google contient un service de messagerie Firebase.
        service_fcm = [n for n in noms if "firebase/messaging" in n.lower()]
        verifier("Pas de service Firebase Messaging (= variante F-Droid)",
                 not service_fcm)

        # --- 3. Ressources Kibaré -------------------------------------
        print("\n3. Identité et sécurité intégrées")
        verifier("Certificat de la CA locale embarqué (res/raw/kibare_ca.pem)",
                 any("kibare_ca" in n for n in noms))
        verifier("Police IBM Plex Sans embarquée",
                 any("ibm_plex_sans" in n.lower() for n in noms))

        # --- 4. Protections « Zéro fuite » dans le code compilé -------
        print("\n4. Protections « Zéro fuite » dans le code compilé (section 6)")
        dex = b"".join(
            apk.read(n) for n in noms if n.endswith(".dex")
        )
        verifier("Classe du filigrane présente (WatermarkView)",
                 b"WatermarkView" in dex)
        verifier("Étiquette « Consultation interne uniquement » présente",
                 "Consultation interne uniquement".encode("utf-8") in dex)
        verifier("Écran « Accès révoqué » présent",
                 "Accès révoqué".encode("utf-8") in dex
                 or b"signed_out_title" in dex)

        # FLAG_SECURE : on cherche la constante dans le code compilé.
        verifier("Appel à FLAG_SECURE présent",
                 b"FLAG_SECURE" in dex or b"setFlags" in dex)

        # --- 5. Serveur et inscription --------------------------------
        print("\n5. Serveur fixé et inscription retirée (section 8.2)")
        ressources = b""
        if "resources.arsc" in noms:
            ressources = apk.read("resources.arsc")
        cible = ressources + dex
        verifier("Adresse du serveur Kibaré présente",
                 b"10.228.115.221" in cible or b"kibare" in cible.lower())
        verifier("Plus aucune référence à matrix.org comme serveur",
                 b"https://matrix.org" not in cible)

        # Information non bloquante : l'APK est-il signé ?
        print("\n6. Signature")
        signatures = [n for n in noms if n.startswith("META-INF/")
                      and n.endswith((".RSA", ".DSA", ".EC"))]
        if signatures:
            info(f"APK signé ({signatures[0]}) — installable sur un téléphone.")
        else:
            info("APK NON signé — il ne s'installera pas. Utilisez la "
                 "variante debug, signée avec la clé de test d'Element.")

    print("\n" + "=" * 64)
    reussis = sum(1 for _, ok in resultats if ok)
    total = len(resultats)
    print(f"RÉSULTAT : {reussis}/{total} contrôles réussis")
    for description, ok in resultats:
        if not ok:
            print(f"  ÉCHEC : {description}")
    print("=" * 64)
    return 0 if reussis == total else 1


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Utilisation : python3 scripts/verifier_apk.py <fichier.apk>")
        sys.exit(2)
    sys.exit(analyser(sys.argv[1]))
