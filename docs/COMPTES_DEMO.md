# Comptes de démo — Kibaré

Tous les comptes sont **fictifs**. Les mots de passe sont des valeurs de DÉMO
(voir `.env.example`). Le domaine d'e-mail `.test` est réservé et inexistant.

## Comptes

| Matricule | Nom (fictif) | Ministère | Direction / Service | Fonction | Rôle |
|---|---|---|---|---|---|
| `demo-000` | Admin PLATEFORME | MTDPCE | DGTD / Exploitation | Administrateur système | super-admin |
| `demo-101` | Awa KONATÉ | MTDPCE | DGTD / Sécurité des SI | Cheffe de service | admin-ministere |
| `demo-102` | Issouf SAWADOGO | MTDPCE | DGTD / Sécurité des SI | Analyste sécurité | agent |
| `demo-201` | Mariam OUÉDRAOGO | SANTE | Dir. veille sanitaire | Directrice | admin-ministere |
| `demo-202` | Boukary ZONGO | SANTE | Dir. veille sanitaire | Épidémiologiste | agent |
| `demo-203` | Karim TIENDRÉBÉOGO | SANTE | Dir. veille sanitaire | Chargé de liaison | agent (**révoqué en démo**) |
| `demo-301` | Salif COMPAORÉ | SECURITE | Dir. des opérations | Directeur | admin-ministere |
| `demo-302` | Rasmata KABORÉ | SECURITE | Dir. des opérations | Officière de liaison | agent |
| `demo-401` | Adama OUATTARA | MEF | Dir. du budget | Directeur | admin-ministere |
| `demo-402` | Fatimata DIALLO | MEF | Dir. du budget | Chargée d'études | agent |
| `intrus` | — | — | — | — | **non enrôlé** (n'existe pas) |

## Mots de passe de démo

Format : `DemoPass<matricule>!` (ex. `demo-101` → `DemoPass101!`). 12 caractères,
satisfont la politique `length(12)`.

## Salons de démo

- « MTDPCE — Canal officiel », « Santé — Canal officiel »,
  « Sécurité — Canal officiel », « MEF — Canal officiel ».
- « Cellule de crise sanitaire » : demo-101, demo-102, demo-201, demo-202,
  demo-203, demo-301, demo-302.

## E-mails (fictifs)

`prenom-initiale.nom@kibare.test` — ex. `a.konate@kibare.test`.

## OTP

À la première connexion, chaque agent doit configurer son OTP (TOTP, 6 chiffres,
30 s) avec FreeOTP ou Aegis. L'OTP est ensuite demandé à chaque connexion.
