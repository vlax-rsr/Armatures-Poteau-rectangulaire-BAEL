import sys
import math
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QLineEdit, QComboBox, QPushButton, QGridLayout,
    QFrame, QRadioButton, QListWidget, QSizePolicy
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont, QColor, QPalette

# ── THÈME ──────────────────────────────────────────────────────────────────────
BG_MAIN        = "#F4F3EF"
BG_CARD        = "#FFFFFF"
BG_PANEL       = "#ECEAE4"
BORDER         = "#C8C5BC"
DIVIDER        = "#D8D5CC"
TEXT_PRIMARY   = "#1A1A1A"
TEXT_RESULT    = "#C0392B"
TEXT_SECONDARY = "#5A5650"
ACCENT         = "#C0392B"
ACCENT_LIGHT   = "#F5EDEC"
HEADER_BG      = "#2B2B28"
HEADER_FG      = "#F4F3EF"

# ── LOGIQUE MÉTIER ─────────────────────────────────────────────────────────────
DIAMETRES      = [6, 8, 10, 12, 14, 16, 20, 25]
DIAMETRES_LONG = [8, 10, 12, 14, 16, 20, 25]          # HA6 exclu pour armatures longitudinales
SECTIONS       = {6: 28.27, 8: 50.27, 10: 78.54, 12: 113.1,
                  14: 153.94, 16: 201.06, 20: 314.16, 25: 490.87}

M_TO_MM    = 1000
M2_TO_CM2  = 10000
CM2_TO_MM2 = 100
MM2_TO_CM2 = 1 / CM2_TO_MM2
MM_TO_CM   = 0.1

# Espacements limites (mm) — BAEL 91
e_min = 20
e_max = 300


# ── FONCTIONS D'OPTIMISATION (issues du notebook) ──────────────────────────────

def solution_realiste(a_mm, b_mm, enrobage, list_variante, index):
    """
    Filtre les variantes pour ne garder que celles dont le nombre de barres
    correspond exactement à une disposition périphérique réaliste sur le
    poteau (na barres côté a, nb barres côté b), avec vérification des
    espacements ea et eb individuellement.

    Paramètres
    ----------
    a_mm, b_mm : dimensions du poteau en mm (petit côté, grand côté)
    enrobage   : enrobage en mm
    list_variante : liste de dicts de variantes à tester
    index      : clé du dict donnant le nombre de barres à placer sur le
                 périmètre ('nb_barres' pour nappe simple, 'n1' pour nappe mixte)
    """
    solutions = []

    for variante in list_variante:
        d          = variante['diametre']
        nb_barres  = variante[index]

        # Nombre de barres sur chaque côté — côté a
        na_min = max(2, math.ceil((a_mm - 2 * enrobage - d) / (d + e_max)))
        na_max = math.floor((a_mm - 2 * enrobage - d) / (d + e_min))

        # Nombre de barres sur chaque côté — côté b
        nb_min = max(2, math.ceil((b_mm - 2 * enrobage - d) / (d + e_max)))
        nb_max = math.floor((b_mm - 2 * enrobage - d) / (d + e_min))

        if na_max < na_min or nb_max < nb_min:
            continue

        for na in range(na_min, na_max + 1):
            for nb in range(nb_min, nb_max + 1):
                
                if a_mm == b_mm and na != nb:
                    continue

                n_total = 2 * (na + nb) - 4

                if n_total != nb_barres:
                    continue

                ea = round((a_mm - 2 * enrobage - na * d) / (na - 1), 2)
                eb = round((b_mm - 2 * enrobage - nb * d) / (nb - 1), 2)

                if not (e_min <= ea <= e_max):
                    continue
                if not (e_min <= eb <= e_max):
                    continue

                sol = variante.copy()
                sol["type"] = "Simple nappe" if index == "nb_barres" else "Double nappe"
                sol.update({"na": na, "nb": nb, "ea": ea, "eb": eb})
                solutions.append(sol)

    return solutions


def optimisation_ferraillage(a_mm, b_mm, list_solutions):
    """
    Classe les solutions par un score multi-critères pondéré :
      - homogénéité des espacements ea/eb
      - économie (nombre de barres)
      - diamètre (influence sur la mise en œuvre)
      - adéquation à la forme du poteau (rapport b/a vs nb/na)
      - excès de section par rapport à A_retenu
    """
    for sol in list_solutions:
        if sol["type"] == "Simple nappe":
            score_type = 1.0
        else:  # Double nappe
            score_type = 1.2  # pénalise légèrement les doubles nappes pour favoriser la simplicité
        score = (
            abs(sol["ea"] - sol["eb"])                       * 1.0
            + sol["nb_barres"]                               * 5.0
            + sol["diametre"]                                * 0.8
            + abs((b_mm / a_mm) - (sol["nb"] / sol["na"]))   * 30.0
            + sol["ecart"]                                   * 5.0
            + score_type
        )
        sol["score"] = round(score, 2)

    list_solutions.sort(key=lambda s: s["score"])
    return list_solutions


def solution_simple_nappe(a_mm, b_mm, enrobage, A_retenue_cm2, nb_sol):
    """
    Génère et classe les solutions à nappe simple (un seul diamètre).
    La recherche couvre tous les nombres de barres jusqu'à 100 et
    élimine les sections supérieures à 1.5 × A_retenu.
    """
    VARIANTES = []
    solutions = []
    for n in range(4, 100, 2):
        for d in DIAMETRES_LONG:
            section_cm2 = n * SECTIONS[d] * MM2_TO_CM2
            if A_retenue_cm2 <= section_cm2 < A_retenue_cm2 * 1.5:
                VARIANTES.append({
                    "affichage":   f"{n} HA{d}",
                    "nb_barres":   n,
                    "diametre":    d,
                    "diametre_mm": d,        # clé attendue par armature_transversal
                    "section_cm2": round(section_cm2, 2),
                    "ecart":       round(section_cm2 - A_retenue_cm2, 2),
                })

    solutions = solution_realiste(a_mm, b_mm, enrobage, VARIANTES, "nb_barres")
    solutions = optimisation_ferraillage(a_mm, b_mm, solutions)
    return solutions[:nb_sol]


def solution_double_nappe(a_mm, b_mm, enrobage, A_retenue_cm2, nb_sol):
    """
    Génère et classe les solutions à nappe mixte (deux diamètres consécutifs).
    Les barres n1 (grand diamètre d1) forment le cadre périphérique ;
    les barres n2 (diamètre d2 adjacent) complètent le ferraillage.
    La recherche couvre tous les nombres de barres jusqu'à 100 et
    élimine les sections supérieures à 1.5 × A_retenu.
    """
    VARIANTES = []
    solutions = []
    for i in range(len(DIAMETRES_LONG)):
        for j in range(len(DIAMETRES_LONG)):
            if i != j + 1:
                continue  # uniquement diamètres consécutifs (ex : HA16 + HA14)

            d1, d2       = DIAMETRES_LONG[i], DIAMETRES_LONG[j]
            s1_cm2, s2_cm2 = SECTIONS[d1] * MM2_TO_CM2, SECTIONS[d2] * MM2_TO_CM2

            for n1 in range(4, 100, 2):
                for n2 in range(4, n1 + 2, 2):   # n1 >= n2 >= 4
                    section_cm2 = n1 * s1_cm2 + n2 * s2_cm2
                    if A_retenue_cm2 <= section_cm2 < A_retenue_cm2 * 1.5:
                        VARIANTES.append({
                            "affichage":    f"{n1} HA{d1} + {n2} HA{d2}",
                            "nb_barres":    n1 + n2,
                            "n1":           n1,
                            "n2":           n2,
                            "d1":           d1,
                            "d2":           d2,
                            "diametre":     d1,
                            "diametre_mm":  d1,    # grand diamètre (périmètre)
                            "diametre_2_mm": d2,   # clé attendue par armature_transversal mixte
                            "section_cm2":  round(section_cm2, 2),
                            "ecart":        round(section_cm2 - A_retenue_cm2, 2),
                        })

    solutions_simple_nappe = solution_realiste(a_mm, b_mm, enrobage, VARIANTES, "nb_barres")
    solutions_double_nappe = solution_realiste(a_mm, b_mm, enrobage, VARIANTES, "n1")

    simples_existantes = {(s["n1"], s["d1"]) for s in solutions_simple_nappe}

    solutions = solutions_simple_nappe  # éviter de modifier la liste originale
    for s2 in solutions_double_nappe:
        if (s2["n1"], s2["d1"]) in simples_existantes:
            continue  # éviter les doublons entre simple et double nappe
        solutions.append(s2)

    solutions = optimisation_ferraillage(a_mm, b_mm, solutions)
    return solutions[:nb_sol]


# ── CALCUL SECTION POTEAU ──────────────────────────────────────────────────────

def calculer_section_armature(a, b, l0, nu, fc28, fe, t_appui, t_charge):
    br  = (a - 0.02) * (b - 0.02)
    ca  = {"ART-ART": 1.0, "ART-ENC": 0.7}
    cc  = {"APRES_90j": 1.0, "AVANT_90j": 1 / 1.10, "AVANT_28j": 1 / 1.20}
    lf  = ca[t_appui] * l0
    lam = 2 * math.sqrt(3) * lf / a
    alpha   = (0.85 / (1 + 0.2 * (lam / 35) ** 2)) if lam <= 50 else 0.6 * (50 / lam) ** 2
    alpha_m = alpha * cc[t_charge]
    ath_cm2 = (((nu / alpha_m) - (br * fc28 / (0.9 * 1.5))) * (1.15 / fe)) * M2_TO_CM2
    per     = 2 * (a + b)
    amin    = max(4 * per, 0.002 * a * b * M2_TO_CM2)
    amax    = 0.05 * a * b * M2_TO_CM2
    return {"lam": lam, "alpha": alpha_m, "br": br, "amin": amin,
            "ath": ath_cm2, "amax": amax, "aretenu": max(amin, ath_cm2)}


# ── ARMATURES TRANSVERSALES ────────────────────────────────────────────────────

def armature_transversal(v, a, b, mode="simple"):
    phi_min = v['diametre_mm'] if mode == "simple" else v['diametre_2_mm']
    sup = [n for n in DIAMETRES if n > phi_min / 3]
    v['diam_t'] = min(sup, key=lambda n: n - phi_min / 3)
    v['e1'] = min(400, 15 * phi_min, min(a, b) * M_TO_MM + 100)
    v['e2'] = 0.6 * v['e1']
    return v


# ── WIDGETS UTILITAIRES ────────────────────────────────────────────────────────

def mk_lbl(text, bold=False, size=9, color=TEXT_PRIMARY):
    w = QLabel(text)
    f = QFont("Arial", size); f.setBold(bold)
    w.setFont(f)
    w.setStyleSheet(f"color:{color}; background:transparent;")
    return w


def mk_inp_lbl(text):
    w = QLabel(text)
    w.setFont(QFont("Arial", 9))
    w.setStyleSheet(f"color:{TEXT_PRIMARY}; background:transparent;")
    w.setSizePolicy(QSizePolicy.Minimum, QSizePolicy.Fixed)
    return w


def mk_val(text="—"):
    w = QLabel(text)
    w.setFont(QFont("Arial", 8))
    w.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
    w.setMinimumWidth(88)
    w.setFixedHeight(19)
    w.setStyleSheet(
        f"color:{TEXT_PRIMARY}; background:{BG_PANEL};"
        f"border:1px solid {BORDER}; padding:0 5px; border-radius:1px;")
    return w


def mk_inp(placeholder="", w=84):
    e = QLineEdit()
    e.setPlaceholderText(placeholder)
    e.setFixedWidth(w); e.setFixedHeight(22)
    e.setFont(QFont("Arial", 9))
    e.setStyleSheet(
        f"color:{TEXT_PRIMARY}; background:{BG_CARD};"
        f"border:1px solid {BORDER}; border-bottom:2px solid {ACCENT};"
        f"padding:0 5px; border-radius:0px;")
    return e


def mk_combo(items, w=110):
    c = QComboBox(); c.addItems(items)
    c.setFixedWidth(w); c.setFixedHeight(22)
    c.setFont(QFont("Arial", 9))
    c.setStyleSheet(
        f"QComboBox {{ color:{TEXT_PRIMARY}; background:{BG_CARD};"
        f"border:1px solid {BORDER}; border-bottom:2px solid {ACCENT};"
        f"padding:0 5px; border-radius:0px; }}"
        f"QComboBox::drop-down {{ border:none; width:14px; }}"
        f"QComboBox QAbstractItemView {{ color:{TEXT_PRIMARY}; background:{BG_CARD};"
        f"selection-background-color:{ACCENT_LIGHT}; }}")
    return c


def mk_divider():
    f = QFrame(); f.setFrameShape(QFrame.HLine)
    f.setFixedHeight(1); f.setStyleSheet(f"background:{DIVIDER};")
    return f


def mk_section(title):
    w = QWidget(); h = QHBoxLayout(w)
    h.setContentsMargins(0, 2, 0, 2); h.setSpacing(6)
    bar = QFrame(); bar.setFixedWidth(3); bar.setFixedHeight(13)
    bar.setStyleSheet(f"background:{ACCENT};")
    h.addWidget(bar)
    t = QLabel(title.upper())
    t.setFont(QFont("Arial", 8, QFont.Bold))
    t.setStyleSheet(f"color:{TEXT_PRIMARY}; background:transparent; letter-spacing:0.5px;")
    h.addWidget(t); h.addStretch()
    return w


# ── FENÊTRE PRINCIPALE ─────────────────────────────────────────────────────────
class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Armatures — Poteau rectangulaire — BAEL 91 mod 99")
        self.setFixedSize(600, 800)
        self._a = self._b = 0.35
        self._enrobage = 25.0
        self._aretenu  = 0.0
        self._sols_s = []; self._sols_m = []
        self._build()
        self._apply_style()
        self.statusBar().setSizeGripEnabled(False)

    def _apply_style(self):
        self.setStyleSheet(f"""
            QMainWindow, QWidget {{ background:{BG_MAIN}; }}
            QListWidget {{
                background:{BG_PANEL}; border:1px solid {BORDER};
                color:{TEXT_PRIMARY};
                outline: none;
            }}
            QListWidget::item {{
                padding:3px 8px;
                border-bottom:1px solid {DIVIDER};
                font-size:8pt;
                background: transparent;
            }}
            QListWidget::item:selected {{
                background:{ACCENT_LIGHT};
                border-left:4px solid {ACCENT};
                color:{ACCENT};
                font-weight:bold;
            }}
            QListWidget::item:hover {{ background:{BG_CARD}; }}
            QStatusBar {{
                background:{HEADER_BG}; color:{BORDER};
                font-size:7pt; padding:0 10px;
            }}
        """)

    def _build(self):
        root = QWidget(); self.setCentralWidget(root)
        main = QVBoxLayout(root)
        main.setContentsMargins(0, 0, 0, 0); main.setSpacing(0)

        # ── HEADER ─────────────────────────────────────────────────────────────
        hdr = QWidget(); hdr.setFixedHeight(34)
        hdr.setStyleSheet(f"background:{HEADER_BG};")
        hl = QHBoxLayout(hdr); hl.setContentsMargins(14, 0, 14, 0)
        ht = QLabel("CALCUL D'ARMATURES — POTEAU RECTANGULAIRE")
        ht.setFont(QFont("Arial", 10, QFont.Bold))
        ht.setStyleSheet(f"color:{HEADER_FG}; letter-spacing:1px; background:transparent;")
        hl.addWidget(ht); hl.addStretch()
        hs = QLabel("v1.0.0-beta"); hs.setFont(QFont("Arial", 7))
        hs.setStyleSheet(f"color:{BORDER}; background:transparent;")
        hl.addWidget(hs)
        accent_bar = QFrame(hdr); accent_bar.setFixedHeight(2)
        accent_bar.setStyleSheet(f"background:{ACCENT};")
        accent_bar.setGeometry(0, 32, 600, 2)
        main.addWidget(hdr)

        # ── BODY ───────────────────────────────────────────────────────────────
        body = QWidget()
        bl = QVBoxLayout(body)
        bl.setContentsMargins(20, 10, 20, 10)
        bl.setSpacing(8)
        main.addWidget(body, 1)

        # ── 1. SAISIE ──────────────────────────────────────────────────────────
        bl.addWidget(mk_section("Données du Poteau"))

        saisie_box = QWidget()
        saisie_box.setStyleSheet(f"background:{BG_MAIN};")
        sg = QGridLayout(saisie_box)
        sg.setHorizontalSpacing(10); sg.setVerticalSpacing(5)
        sg.setContentsMargins(0, 0, 0, 0)

        self.e_a  = mk_inp("0.35", 50)
        self.e_b  = mk_inp("0.35", 50)
        self.e_l0 = mk_inp("4.00", 50)
        self.e_nu = mk_inp("2.325", 50)
        self.e_en = mk_inp("25", 50)

        self.cb_appui  = mk_combo(["ART-ART", "ART-ENC"], 90)
        self.cb_charge = mk_combo(["APRES_90j", "AVANT_90j", "AVANT_28j"], 90)
        self.cb_fc28   = mk_combo([str(v) for v in [20, 25, 30, 35, 40, 45, 50, 55, 60]], 50)
        self.cb_fc28.setCurrentText("25")
        self.cb_fe     = mk_combo(["500", "400"], 50)
        self.cb_nbsol  = mk_combo([str(i) for i in range(2, 6)], 50)

        # Ligne 0
        sg.addWidget(mk_inp_lbl("Petit côté a (m)"), 0, 0); sg.addWidget(self.e_a,       0, 1)
        sg.addWidget(mk_inp_lbl("fc28 (MPa)"),       0, 2); sg.addWidget(self.cb_fc28,   0, 3)
        sg.addWidget(mk_inp_lbl("l₀ (m)"),           0, 4); sg.addWidget(self.e_l0,      0, 5)
        sg.addWidget(mk_inp_lbl("Appuis"),            0, 6); sg.addWidget(self.cb_appui,  0, 7)

        # Ligne 1
        sg.addWidget(mk_inp_lbl("Grand côté b (m)"), 1, 0); sg.addWidget(self.e_b,       1, 1)
        sg.addWidget(mk_inp_lbl("fe (MPa)"),         1, 2); sg.addWidget(self.cb_fe,     1, 3)
        sg.addWidget(mk_inp_lbl("Nu (MN)"),          1, 4); sg.addWidget(self.e_nu,      1, 5)
        sg.addWidget(mk_inp_lbl("Charge"),           1, 6); sg.addWidget(self.cb_charge, 1, 7)

        # Ligne 2
        sg.addWidget(mk_inp_lbl("Enrobage (mm)"),    2, 0); sg.addWidget(self.e_en,      2, 1)

        # Ligne 3
        sg.addWidget(mk_inp_lbl("Nb de solutions"),  3, 0); sg.addWidget(self.cb_nbsol,  3, 1)

        bl.addWidget(saisie_box)

        btn = QPushButton("CALCULER")
        btn.setFixedHeight(26); btn.setCursor(Qt.PointingHandCursor)
        btn.setFont(QFont("Arial", 9, QFont.Bold))
        btn.setStyleSheet(f"""QPushButton {{ background:{ACCENT}; color:white;
            border:none; border-radius:0px; letter-spacing:1px; }}
            QPushButton:hover {{ background:#A93226; }}
            QPushButton:pressed {{ background:#922B21; }}""")
        btn.clicked.connect(self._calc)
        bl.addWidget(btn)

        bl.addWidget(mk_divider())

        # ── 2. RÉSULTATS LONGITUDINAUX ─────────────────────────────────────────
        bl.addWidget(mk_section("Armatures Longitudinales"))

        rg = QGridLayout(); rg.setHorizontalSpacing(10); rg.setVerticalSpacing(3)
        self._rv = {}
        fields = [
            ("Elancement λ",             "v_lam"),
            ("Coef. de flambement α",    "v_alp"),
            ("Section réduite Br (m²)",  "v_br"),
            ("Armature minimale (cm²)",  "v_amin"),
            ("Armature théorique (cm²)", "v_ath"),
            ("Armature maximale (cm²)",  "v_amax"),
            ("Armature retenue (cm²)",   "v_aret"),
        ]
        for i, (t, k) in enumerate(fields):
            r, c = divmod(i, 2)
            rg.addWidget(mk_lbl(t, color=TEXT_SECONDARY), r, c * 2)
            v = mk_val(); self._rv[k] = v
            rg.addWidget(v, r, c * 2 + 1)
        bl.addLayout(rg)

        self.lbl_warn = QLabel("")
        self.lbl_warn.setFont(QFont("Arial", 8, QFont.Bold))
        self.lbl_warn.setStyleSheet(f"color:{ACCENT}; background:transparent;")
        self.lbl_warn.setWordWrap(True); self.lbl_warn.setFixedHeight(20)
        bl.addWidget(self.lbl_warn)

        bl.addWidget(mk_divider())

        # ── 3. SOLUTIONS ───────────────────────────────────────────────────────
        bl.addWidget(mk_section("Solutions d'Armatures"))

        # Radio buttons (Simple / Mixte / Personnalisé)
        mr = QHBoxLayout(); mr.setSpacing(18)
        self.rb_s = QRadioButton("Simple")
        self.rb_m = QRadioButton("Mixte")
        self.rb_p = QRadioButton("Personnalisé")
        self.rb_s.setChecked(True)

        rb_css = f"""QRadioButton {{ color:{TEXT_PRIMARY}; background:transparent;
            font-size:9pt; spacing:5px; }}
            QRadioButton::indicator {{ width:11px; height:11px; border-radius:6px;
            border:2px solid {BORDER}; }}
            QRadioButton::indicator:checked {{ background:{ACCENT}; border:2px solid {ACCENT}; }}"""
        self.rb_s.setStyleSheet(rb_css)
        self.rb_m.setStyleSheet(rb_css)
        self.rb_p.setStyleSheet(rb_css)

        self.rb_s.toggled.connect(self._populate)
        self.rb_m.toggled.connect(self._populate)
        self.rb_p.toggled.connect(self._populate)

        mr.addWidget(self.rb_s); mr.addWidget(self.rb_m); mr.addWidget(self.rb_p)
        mr.addStretch()
        bl.addLayout(mr)

        # List widget (Simple / Mixte)
        self.list_sol = QListWidget(); self.list_sol.setMinimumHeight(40)
        self.list_sol.currentRowChanged.connect(self._on_select)
        bl.addWidget(self.list_sol)

        # ── PANNEAU PERSONNALISÉ ────────────────────────────────────────────────
        self.perso_panel = QWidget()
        self.perso_panel.setStyleSheet(
            f"background: transparent; border:1px solid {BORDER}; border-radius:0px;")
        pp = QVBoxLayout(self.perso_panel)
        pp.setContentsMargins(8, 6, 8, 6)
        pp.setSpacing(5)

        nb_diam_container = QWidget()
        nb_diam_container.setStyleSheet("background:transparent; border:none;")
        nb_diam_row = QHBoxLayout(nb_diam_container)
        nb_diam_row.setContentsMargins(0, 0, 0, 0)
        nb_diam_row.setSpacing(6)

        lbl_nb = mk_inp_lbl("Nb de diamètres différents :")
        self.cb_nb_diam = mk_combo(["1", "2"], 50)
        self.cb_nb_diam.currentIndexChanged.connect(self._update_perso_rows)

        nb_diam_row.addWidget(lbl_nb)
        nb_diam_row.addWidget(self.cb_nb_diam)
        nb_diam_row.addStretch()
        pp.addWidget(nb_diam_container)

        # Ligne 1 : toujours visible
        self.perso_row1 = QWidget()
        self.perso_row1.setStyleSheet("background:transparent; border:none;")
        r1l = QHBoxLayout(self.perso_row1)
        r1l.setContentsMargins(0, 0, 0, 0); r1l.setSpacing(6)
        self.cb_n1 = mk_combo([str(i) for i in range(4, 22, 2)], 56)
        self.cb_n1.setCurrentText("4")
        self.cb_d1 = mk_combo([str(d) for d in DIAMETRES], 56)
        self.cb_d1.setCurrentText("12")
        r1l.addWidget(mk_inp_lbl("Barres :"))
        r1l.addWidget(self.cb_n1)
        r1l.addWidget(mk_inp_lbl("HA"))
        r1l.addWidget(self.cb_d1)
        r1l.addWidget(mk_inp_lbl("mm"))
        r1l.addStretch()
        pp.addWidget(self.perso_row1)

        # Ligne 2 : visible seulement si nb_diam = 2
        self.perso_row2 = QWidget()
        self.perso_row2.setStyleSheet("background:transparent; border:none;")
        r2l = QHBoxLayout(self.perso_row2)
        r2l.setContentsMargins(0, 0, 0, 0); r2l.setSpacing(6)
        self.cb_n2 = mk_combo([str(i) for i in range(4, 22, 2)], 56)
        self.cb_n2.setCurrentText("4")
        self.cb_d2 = mk_combo([str(d) for d in DIAMETRES], 56)
        self.cb_d2.setCurrentText("10")
        r2l.addWidget(mk_inp_lbl("Barres :"))
        r2l.addWidget(self.cb_n2)
        r2l.addWidget(mk_inp_lbl("HA"))
        r2l.addWidget(self.cb_d2)
        r2l.addWidget(mk_inp_lbl("mm"))
        r2l.addStretch()
        pp.addWidget(self.perso_row2)
        self.perso_row2.setVisible(False)

        # Ligne de total + statut
        sum_container = QWidget()
        sum_container.setStyleSheet("background:transparent; border:none;")
        sum_row = QHBoxLayout(sum_container)
        sum_row.setContentsMargins(0, 0, 0, 0)
        self.lbl_perso_sum = mk_lbl("Section totale : — cm²", bold=True, size=9)
        self.lbl_perso_status = QLabel("")
        self.lbl_perso_status.setFont(QFont("Arial", 9, QFont.Bold))
        self.lbl_perso_status.setStyleSheet("background:transparent; border:none;")
        sum_row.addWidget(self.lbl_perso_sum)
        sum_row.addWidget(self.lbl_perso_status)
        sum_row.addStretch()
        pp.addWidget(sum_container)

        # Bouton Actualiser
        self.btn_actualiser = QPushButton("Actualiser le ferraillage transversal")
        self.btn_actualiser.setFixedHeight(24)
        self.btn_actualiser.setCursor(Qt.PointingHandCursor)
        self.btn_actualiser.setFont(QFont("Arial", 8, QFont.Bold))
        self.btn_actualiser.setStyleSheet(f"""
            QPushButton {{
                background:{BG_PANEL}; color:{TEXT_PRIMARY};
                border:1px solid {BORDER}; border-bottom:2px solid {ACCENT};
                border-radius:0px; padding:0 8px; letter-spacing:0.5px;
            }}
            QPushButton:hover {{ background:{ACCENT_LIGHT}; border-bottom:2px solid {ACCENT}; }}
            QPushButton:pressed {{ background:{ACCENT}; color:white; }}
        """)
        self.btn_actualiser.clicked.connect(self._actualiser_perso)
        pp.addWidget(self.btn_actualiser)

        self.cb_n1.currentIndexChanged.connect(self._update_perso_section)
        self.cb_d1.currentIndexChanged.connect(self._update_perso_section)
        self.cb_n2.currentIndexChanged.connect(self._update_perso_section)
        self.cb_d2.currentIndexChanged.connect(self._update_perso_section)

        bl.addWidget(self.perso_panel)
        self.perso_panel.setVisible(False)

        bl.addWidget(mk_divider())

        # ── 4. ARMATURES TRANSVERSALES ─────────────────────────────────────────
        bl.addWidget(mk_section("Armatures Transversales"))

        tg = QGridLayout(); tg.setHorizontalSpacing(8); tg.setVerticalSpacing(3)
        self._tv = {}
        for i, (t, k) in enumerate([
            ("Diamètre des armatures transversales", "v_dt"),
            ("Espacement e1 — Zone normale (cm)",    "v_e1"),
            ("Espacement e2 — Zone critique (cm)",   "v_e2"),
        ]):
            tg.addWidget(mk_lbl(t, color=TEXT_SECONDARY), i, 0)
            v = mk_val(); self._tv[k] = v
            tg.addWidget(v, i, 1)
        bl.addLayout(tg)

        bl.addWidget(mk_divider())

        # ── 5. RÉSULTAT SYNTHÈSE ───────────────────────────────────────────────
        self.result_card = QFrame()
        self.result_card.setStyleSheet(
            f"background:{BG_CARD}; border:1px solid {BORDER};"
            f"border-top:3px solid {ACCENT}; border-radius:0px;")
        rc_layout = QVBoxLayout(self.result_card)
        rc_layout.setContentsMargins(12, 8, 12, 10)
        rc_layout.setSpacing(4)

        self.lbl_r0 = QLabel("—")
        self.lbl_r1 = QLabel("—")
        self.lbl_r2 = QLabel("—")
        self.lbl_r3 = QLabel("")   # ligne disposition na × nb + espacements

        styles = [
            (8,  False, TEXT_SECONDARY),
            (12, True,  TEXT_RESULT),
            (9,  False, TEXT_PRIMARY),
            (8,  False, TEXT_SECONDARY),
        ]
        for lbl, (sz, bd, col) in zip(
                [self.lbl_r0, self.lbl_r1, self.lbl_r2, self.lbl_r3], styles):
            f = QFont("Georgia", sz); f.setBold(bd)
            lbl.setFont(f)
            lbl.setAlignment(Qt.AlignCenter)
            lbl.setStyleSheet(f"color:{col}; background:transparent; border:none;")
            rc_layout.addWidget(lbl)

        bl.addWidget(self.result_card)

        bl.addStretch(1)

        self.statusBar().showMessage(
            'Renseignez les données puis cliquez sur CALCULER')

        # ── 6. SIGNATURE ───────────────────────────────────────────────────────────────
        container = QWidget()
        container.setStyleSheet("QWidget { background: transparent; }")
        layout = QHBoxLayout(container)
        layout.setContentsMargins(0, 0, 10, 0)
        layout.setSpacing(4)

        lbl_sign = QLabel("© 2026  R. Stellia")
        lbl_sign.setFont(QFont("Footlight MT", 7))
        lbl_sign.setStyleSheet(f"color:{BORDER}; background:transparent; letter-spacing:0.5px;")

        layout.addWidget(lbl_sign)
        self.statusBar().addPermanentWidget(container)

    # ── CALCUL ─────────────────────────────────────────────────────────────────
    def _calc(self):
        self.lbl_warn.setText("")
        self.list_sol.clear()
        for v in self._rv.values(): v.setText("—")
        for v in self._tv.values(): v.setText("—")
        self._reset_result_card()
        self._sols_s = []; self._sols_m = []

        try:
            a  = float(self.e_a.text().replace(",", "."))
            b  = float(self.e_b.text().replace(",", "."))
            l0 = float(self.e_l0.text().replace(",", "."))
            nu = float(self.e_nu.text().replace(",", "."))
            en = float(self.e_en.text().replace(",", "."))
        except ValueError:
            self.lbl_warn.setText("⚠ Valeurs numériques invalides."); return

        self._a = a; self._b = b; self._enrobage = en
        fc28 = int(self.cb_fc28.currentText())
        fe   = int(self.cb_fe.currentText())
        nb   = int(self.cb_nbsol.currentText())

        r = calculer_section_armature(a, b, l0, nu, fc28, fe,
                                    self.cb_appui.currentText(),
                                    self.cb_charge.currentText())
        self._aretenu = r['aretenu']

        self._rv["v_lam"].setText(f"{r['lam']:.2f}")
        self._rv["v_alp"].setText(f"{r['alpha']:.2f}")
        self._rv["v_br"].setText(f"{r['br']:.2f}")
        self._rv["v_amin"].setText(f"{r['amin']:.2f}")
        self._rv["v_ath"].setText(f"{max(0, r['ath']):.2f}")
        self._rv["v_amax"].setText(f"{r['amax']:.2f}")
        self._rv["v_aret"].setText(f"{r['aretenu']:.2f}")

        if r['lam'] > 70:
            self.lbl_warn.setText("⚠ λ > 70 — Flambement non vérifié."); return
        if r['ath'] > r['amax']:
            self.lbl_warn.setText("⚠ Ath > Amax — Augmenter la section béton."); return

        # Conversion en mm pour les fonctions d'optimisation
        a_mm = a * M_TO_MM
        b_mm = b * M_TO_MM

        self._sols_s = solution_simple_nappe(a_mm, b_mm, en, r['aretenu'], nb)
        self._sols_m = solution_double_nappe(a_mm, b_mm, en, r['aretenu'], nb)
        self._populate()

        n_s = len(self._sols_s)
        n_m = len(self._sols_m)
        self.statusBar().showMessage(
            f"λ = {r['lam']:.1f}  |  Section retenue = {r['aretenu']:.2f} cm²"
            f"  |  {n_s} solution simple{'s' if n_s > 1 else ''}"
            f"  —  {n_m} solution mixte{'s' if n_m > 1 else ''}")

    # ── PEUPLEMENT DE LA LISTE ─────────────────────────────────────────────────
    def _populate(self):
        is_perso = self.rb_p.isChecked()
        self.list_sol.setVisible(not is_perso)
        self.perso_panel.setVisible(is_perso)

        if is_perso:
            self._update_perso_section()
            return

        self.list_sol.clear()
        mode = "simple" if self.rb_s.isChecked() else "mixte"
        sols = self._sols_s if mode == "simple" else self._sols_m

        # --- CAS : LISTE VIDE OU INITIALE ---
        if not sols:
            self.list_sol.addItem("Aucune solution trouvée.")
            self.list_sol.doItemsLayout()
            h_unit = self.list_sol.sizeHintForRow(0) if self.list_sol.count() > 0 else 28
            self.list_sol.setFixedHeight(h_unit + 2)
            self._reset_result_card()
            return

        # --- CAS : AVEC SOLUTIONS ---
        # Affichage enrichi : ferraillage + section + disposition + espacements + score
        for s in sols:
            disp = (
                f"  {s['affichage']}"
                f"   →   {s['section_cm2']:.2f} cm²"
                f"   |  {s['na']} × {s['nb']} barres"
            )
            self.list_sol.addItem(disp)

        self.list_sol.doItemsLayout()
        hauteur_totale = sum(
            self.list_sol.sizeHintForRow(i) for i in range(self.list_sol.count())
        )
        self.list_sol.setFixedHeight(hauteur_totale + 2)
        self.list_sol.setCurrentRow(0)

    def _on_select(self, row):
        mode = "simple" if self.rb_s.isChecked() else "mixte"
        sols = self._sols_s if mode == "simple" else self._sols_m
        if row < 0 or row >= len(sols):
            return
        v = armature_transversal(dict(sols[row]), self._a, self._b, mode)

        self._tv["v_dt"].setText(f"HA {v['diam_t']}")
        self._tv["v_e1"].setText(f"{v['e1'] * MM_TO_CM:.1f} cm")
        self._tv["v_e2"].setText(f"{v['e2'] * MM_TO_CM:.1f} cm")

        self.lbl_r0.setText(
            f"Section d'armature nécessaire : {self._aretenu:.2f} cm²")
        self.lbl_r1.setText(
            f"{v['affichage']}  —  {v['section_cm2']:.2f} cm²")
        self.lbl_r2.setText(
            f"Cadre HA {v['diam_t']}  |  e1 = {v['e1'] * MM_TO_CM:.1f} cm"
            f"  |  e2 = {v['e2'] * MM_TO_CM:.1f} cm")
        self.lbl_r3.setText(
            f"Disposition : {v['na']} barres côté a (espacement = {v['ea']:.0f} mm)"
            f"  ×  {v['nb']} barres côté b (espacement = {v['eb']:.0f} mm)")

    # ── PANNEAU PERSONNALISÉ ────────────────────────────────────────────────────
    def _update_perso_rows(self):
        nb = int(self.cb_nb_diam.currentText())
        self.perso_row2.setVisible(nb == 2)
        self._update_perso_section()

    def _update_perso_section(self):
        n1 = int(self.cb_n1.currentText())
        d1 = int(self.cb_d1.currentText())
        total_mm2 = n1 * SECTIONS[d1]

        nb = int(self.cb_nb_diam.currentText())
        if nb == 2:
            n2 = int(self.cb_n2.currentText())
            d2 = int(self.cb_d2.currentText())
            total_mm2 += n2 * SECTIONS[d2]

        total_cm2 = total_mm2 / CM2_TO_MM2
        self.lbl_perso_sum.setText(f"Section totale : {total_cm2:.2f} cm²")

        if self._aretenu > 0:
            if total_cm2 >= self._aretenu:
                self.lbl_perso_status.setText("✔  Armatures suffisantes")
                self.lbl_perso_status.setStyleSheet(
                    "color:#27AE60; background:transparent; border:none; font-weight:bold;")
            else:
                self.lbl_perso_status.setText("✘  Armatures insuffisantes")
                self.lbl_perso_status.setStyleSheet(
                    f"color:{ACCENT}; background:transparent; border:none; font-weight:bold;")
        else:
            self.lbl_perso_status.setText("")

    def _actualiser_perso(self):
        n1 = int(self.cb_n1.currentText())
        d1 = int(self.cb_d1.currentText())
        nb = int(self.cb_nb_diam.currentText())

        if nb == 1:
            sol = {
                'affichage':   f"{n1} HA {d1}",
                'diametre_mm': d1,
                'section_cm2': n1 * SECTIONS[d1] / CM2_TO_MM2,
            }
            mode = "simple"
        else:
            n2 = int(self.cb_n2.currentText())
            d2 = int(self.cb_d2.currentText())
            d_min = min(d1, d2)
            sol = {
                'affichage':    f"{n1} HA {d1} + {n2} HA {d2}",
                'diametre_mm':  max(d1, d2),
                'diametre_2_mm': d_min,
                'section_cm2':  (n1 * SECTIONS[d1] + n2 * SECTIONS[d2]) / CM2_TO_MM2,
            }
            mode = "mixte"

        v = armature_transversal(dict(sol), self._a, self._b, mode)

        self._tv["v_dt"].setText(f"HA {v['diam_t']}")
        self._tv["v_e1"].setText(f"{v['e1'] * MM_TO_CM:.1f} cm")
        self._tv["v_e2"].setText(f"{v['e2'] * MM_TO_CM:.1f} cm")

        self.lbl_r0.setText(
            f"Section d'armature nécessaire : {self._aretenu:.2f} cm²")
        self.lbl_r1.setText(
            f"{sol['affichage']}  —  {sol['section_cm2']:.2f} cm²")
        self.lbl_r2.setText(
            f"Cadre HA {v['diam_t']}  |  e1 = {v['e1'] * MM_TO_CM:.1f} cm"
            f"  |  e2 = {v['e2'] * MM_TO_CM:.1f} cm")
        self.lbl_r3.setText("")   # pas de disposition connue en mode perso

    def _reset_result_card(self):
        self.lbl_r0.setText("—")
        self.lbl_r1.setText("—")
        self.lbl_r2.setText("—")
        self.lbl_r3.setText("")


# ── MAIN ───────────────────────────────────────────────────────────────────────
def main():
    app = QApplication(sys.argv); app.setStyle("Fusion")
    p = QPalette()
    p.setColor(QPalette.Window,          QColor(BG_MAIN))
    p.setColor(QPalette.WindowText,      QColor(TEXT_PRIMARY))
    p.setColor(QPalette.Base,            QColor(BG_CARD))
    p.setColor(QPalette.AlternateBase,   QColor(BG_PANEL))
    p.setColor(QPalette.Button,          QColor(BG_PANEL))
    p.setColor(QPalette.ButtonText,      QColor(TEXT_PRIMARY))
    p.setColor(QPalette.Highlight,       QColor(ACCENT))
    p.setColor(QPalette.HighlightedText, QColor("#FFFFFF"))
    app.setPalette(p)
    w = MainWindow(); w.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
