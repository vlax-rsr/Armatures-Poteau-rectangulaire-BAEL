# Calcul d'Armatures — Poteau Rectangulaire (BAEL 91 mod. 99)

Application de bureau Python/PySide6 pour le dimensionnement automatisé des armatures longitudinales et transversales d'un poteau rectangulaire en béton armé, selon la norme **BAEL 91 révisé 99**.

![Python](https://img.shields.io/badge/Python-3.10%2B-blue?logo=python)
![PySide6](https://img.shields.io/badge/PySide6-6.x-green?logo=qt)
![Norme](https://img.shields.io/badge/Norme-BAEL%2091%20mod.%2099-orange)
![Licence](https://img.shields.io/badge/Licence-MIT-lightgrey)

---

## Aperçu

![Capture d'écran de l'interface](screenshot.png)

L'outil prend en entrée les données géométriques et mécaniques d'un poteau, calcule la section d'armature nécessaire selon le BAEL 91, puis propose et classe automatiquement les meilleures solutions de ferraillage (nappe simple ou mixte), avec vérification des armatures transversales.

---

## Fonctionnalités

- **Calcul de la section d'armature** — élancement, coefficient de flambement α, section réduite Br, armature minimale / théorique / maximale / retenue
- **Optimisation multi-critères** des solutions longitudinales :
  - Nappe simple (un seul diamètre HA)
  - Nappe mixte (deux diamètres consécutifs)
  - Mode personnalisé (saisie libre)
- **Vérification des espacements** ea et eb selon BAEL 91 (20 mm ≤ e ≤ 300 mm)
- **Dimensionnement des armatures transversales** (diamètre du cadre, espacement e1 et e2)
- **Score de classement** pondéré : homogénéité des espacements, économie, diamètre, adéquation à la forme du poteau
- Interface graphique soignée (thème clair, couleur accentuée)

---

## Prérequis

| Dépendance | Version minimale |
|------------|-----------------|
| Python     | 3.10            |
| PySide6    | 6.4             |

---

## Installation

```bash
# Cloner le dépôt
git clone https://github.com/<votre-utilisateur>/armatures-poteau-rectangulaire.git
cd armatures-poteau-rectangulaire

# Créer un environnement virtuel (recommandé)
python -m venv .venv
source .venv/bin/activate        # Windows : .venv\Scripts\activate

# Installer les dépendances
pip install -r requirements.txt

# Lancer l'application
python V1_00_armatures_poteau_rectangulaire_PySide6.py
```

---

## Utilisation

1. Renseigner les données du poteau :
   - Petit côté **a** et grand côté **b** (en mètres)
   - Longueur de flambement **l₀** (en mètres)
   - Effort normal de calcul **Nu** (en MN)
   - Enrobage (en mm), résistances **fc28** et **fe** (en MPa)
   - Conditions d'appui et d'âge du chargement
2. Cliquer sur **CALCULER**
3. Sélectionner le mode de ferraillage souhaité : *Simple*, *Mixte* ou *Personnalisé*
4. Cliquer sur une solution dans la liste pour afficher le détail complet (disposition, espacement, cadre transversal)

---

## Structure du projet

```
armatures-poteau-rectangulaire/
├── V1_00_armatures_poteau_rectangulaire_PySide6.py   # Script principal
├── requirements.txt                                   # Dépendances Python
├── README.md                                          # Documentation
└── LICENSE                                            # Licence MIT
```

---

## Algorithme de calcul (BAEL 91)

### Section d'armature longitudinale

```
Br  = (a − 0,02) × (b − 0,02)          [section réduite, m²]
λ   = 2√3 · lf / a                      [élancement]
α   = 0,85 / (1 + 0,2·(λ/35)²)         si λ ≤ 50
α   = 0,6 · (50/λ)²                     si λ > 50
Ath = (Nu/αm − Br·fc28/1,35) · 1,15/fe [armature théorique, cm²]
```

### Armatures transversales

```
φt  ≥ φl_min / 3
e1  = min(400 mm ; 15·φl ; min(a,b) + 100)
e2  = 0,6 · e1
```

---

## Paramètres disponibles

| Paramètre | Valeurs acceptées |
|-----------|------------------|
| fc28 | 20, 25, 30, 35, 40, 45, 50, 55, 60 MPa |
| fe | 400, 500 MPa |
| Conditions d'appui | ART-ART, ART-ENC |
| Âge du chargement | APRES_90j, AVANT_90j, AVANT_28j |
| Diamètres longitudinaux | HA8, HA10, HA12, HA14, HA16, HA20, HA25 |
| Diamètres transversaux | HA6, HA8, HA10, HA12, HA14, HA16, HA20, HA25 |

---

## Licence

Distribué sous licence **MIT**. Voir le fichier [LICENSE](LICENSE) pour plus de détails.

---

## Auteur

Développé dans le cadre d'un portfolio de calcul de structures en béton armé.  
Contributions et retours bienvenus via les *Issues* GitHub.
