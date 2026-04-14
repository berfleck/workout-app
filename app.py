import streamlit as st
import random
import json
from pathlib import Path
from gerador_treino import (
    carregar_banco, gerar_sessao, gerar_multiplos_treinos,
    substituir_exercicio, buscar_substitutos, substituir_exercicio_por,
    TEMPLATES, TEMPLATE_EPP, EXERCICIOS_POR_PADRAO,
    Exercicio, Sessao, SuperSerie,
)
from gerar_imagem import gerar_png

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

st.set_page_config(
    page_title="BF Treinamento — Gerador",
    page_icon="💪",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# ---------------------------------------------------------------------------
# Estilos globais
# ---------------------------------------------------------------------------

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=DM+Sans:ital,wght@0,300;0,400;0,500;0,600;0,700&family=DM+Mono:wght@400;500&display=swap');

html, body, [class*="css"] { font-family: 'DM Sans', sans-serif; }

/* Layout */
.block-container { padding-top: 2rem !important; padding-bottom: 4rem !important; max-width: 960px !important; }

/* Esconde sidebar */
button[data-testid="collapsedControl"] { display: none !important; }
section[data-testid="stSidebar"] { display: none !important; }

/* Header */
.app-header {
    display: flex; align-items: center; gap: 16px;
    border-bottom: 1px solid #e5e7eb;
    padding-bottom: 20px; margin-bottom: 28px;
}
.app-header h1 { font-size: 22px; font-weight: 700; color: #111827; margin: 0; letter-spacing: -0.02em; }
.app-header p  { font-size: 13px; color: #9ca3af; margin: 2px 0 0 0; }

/* Config panel */
.config-panel { background: #f9fafb; border: 1px solid #e5e7eb; border-radius: 14px; padding: 20px 24px; margin-bottom: 20px; }
.config-title  { font-size: 11px; font-weight: 700; color: #6b7280; text-transform: uppercase; letter-spacing: 0.1em; margin: 0 0 14px 0; }

/* Slim view */
.ex-slim { padding: 6px 0 6px 12px; border-left: 3px solid #e85d04; margin-bottom: 5px; }
.ex-slim-nome { font-size: 14px; font-weight: 600; color: #111827; }
.ex-slim-meta { font-size: 11px; color: #9ca3af; margin-top: 1px; }
.prescr-badge { display: inline-block; background: #fff3e6; color: #e85d04; border-radius: 6px; padding: 1px 7px; font-size: 11px; font-weight: 700; margin-left: 6px; }
.bloco-lbl { font-size: 10px; font-weight: 700; color: #9ca3af; letter-spacing: 0.1em; text-transform: uppercase; margin: 10px 0 4px 0; }
.thin-hr { border: none; border-top: 1px solid #f3f4f6; margin: 6px 0; }

/* Sub panel */
.sub-panel { background: #fffbf5; border: 1px solid #fed7aa; border-radius: 10px; padding: 14px 18px; margin-top: 8px; }

/* Checkboxes compactos */
.stCheckbox { margin-bottom: 0px !important; padding: 0px !important; min-height: 0 !important; }
.stCheckbox label { font-size: 12px !important; padding: 1px 0 !important; }
.stCheckbox label p { font-size: 12px !important; margin: 0 !important; line-height: 1.4 !important; }

/* Sliders compactos */
.stSlider { margin-bottom: 2px !important; padding-bottom: 0 !important; }
.stSlider label, .stSlider label p { font-size: 11px !important; margin-bottom: 0px !important; color: #6b7280 !important; }

/* Botão primário laranja */
div[data-testid="stButton"] > button[kind="primary"] {
    background: #e85d04 !important; color: white !important;
    border: none !important; border-radius: 8px !important;
    font-weight: 600 !important; font-size: 15px !important;
}
div[data-testid="stButton"] > button[kind="primary"]:hover { background: #c44d03 !important; }
</style>
""", unsafe_allow_html=True)

# ---------------------------------------------------------------------------
# Dados
# ---------------------------------------------------------------------------

@st.cache_data
def get_banco():
    return carregar_banco("banco_exercicios.xlsx")

def carregar_alunos():
    path = Path("alunos.json")
    if not path.exists():
        return []
    with open(path, encoding="utf-8") as f:
        return json.load(f)

def salvar_alunos(lista):
    with open(Path("alunos.json"), "w", encoding="utf-8") as f:
        json.dump(lista, f, ensure_ascii=False, indent=2)

banco = get_banco()
alunos = carregar_alunos()
nomes_alunos = ["Selecionar aluno..."] + [a["nome"] for a in alunos]
todos_padroes = sorted({e.padrao for e in banco if e.padrao})

PADROES_LABELS = {
    "horizontal_push": "Horizontal Push",
    "horizontal_pull": "Horizontal Pull",
    "vertical_push":   "Vertical Push",
    "vertical_pull":   "Vertical Pull",
    "squat":           "Squat",
    "hinge":           "Hinge",
    "abduction":       "Abdução",
    "adduction":       "Adução",
    "core":            "Core",
    "biceps":          "Bíceps",
    "triceps":         "Tríceps",
    "flexao_plantar":  "Flexão Plantar",
    "cardio":          "Cardio",
}

# ---------------------------------------------------------------------------
# Session state
# ---------------------------------------------------------------------------

if "sessoes"       not in st.session_state: st.session_state.sessoes       = []
if "sub_alvo"      not in st.session_state: st.session_state.sub_alvo      = []
if "candidatos"    not in st.session_state: st.session_state.candidatos    = []
if "modo_viz"      not in st.session_state: st.session_state.modo_viz      = []
if "config_aberta" not in st.session_state: st.session_state.config_aberta = True
if "edit_aluno_idx" not in st.session_state: st.session_state.edit_aluno_idx = None

# ---------------------------------------------------------------------------
# Helpers visuais
# ---------------------------------------------------------------------------

def prescr_badge(ex):
    parts = []
    if ex.series: parts.append(f"{ex.series}×")
    if ex.reps:   parts.append(ex.reps)
    if ex.rir is not None: parts.append(f"RIR {ex.rir}")
    if not parts: return ""
    return f"<span class='prescr-badge'>{' · '.join(parts)}</span>"


def render_slim(sessao: Sessao):
    for bloco in sessao.blocos:
        exs = [e for e in [bloco.ex1, bloco.ex2, bloco.ex3] if e]
        st.markdown(f"<p class='bloco-lbl'>Bloco {bloco.label}</p>", unsafe_allow_html=True)
        for idx, ex in enumerate(exs, 1):
            eq = ex.eq_primario + (f" + {ex.eq_secundario}" if ex.eq_secundario else "")
            st.markdown(
                f"<div class='ex-slim'>"
                f"<div class='ex-slim-nome'>{bloco.label}{idx}&nbsp; {ex.nome}{prescr_badge(ex)}</div>"
                f"<div class='ex-slim-meta'>{ex.purpose} · 🔧 {eq}</div>"
                f"</div>",
                unsafe_allow_html=True,
            )
        st.markdown("<hr class='thin-hr'>", unsafe_allow_html=True)


def render_editar(sessao: Sessao, t: int, max_cx: int):
    labels = "ABCDEFGHIJKLMNOP"
    n_blocos = len(sessao.blocos)

    for i, bloco in enumerate(sessao.blocos):
        exs = [e for e in [bloco.ex1, bloco.ex2, bloco.ex3] if e]

        col_lbl, col_up, col_dn = st.columns([14, 1, 1])
        with col_lbl:
            st.markdown(f"<p class='bloco-lbl'>Bloco {bloco.label}</p>", unsafe_allow_html=True)
        with col_up:
            if i > 0 and st.button("↑", key=f"up_{t}_{i}"):
                bl = sessao.blocos[:]
                bl[i], bl[i-1] = bl[i-1], bl[i]
                for j, b in enumerate(bl): b.label = labels[j]
                st.session_state.sessoes[t].blocos = bl
                st.rerun()
        with col_dn:
            if i < n_blocos - 1 and st.button("↓", key=f"dn_{t}_{i}"):
                bl = sessao.blocos[:]
                bl[i], bl[i+1] = bl[i+1], bl[i]
                for j, b in enumerate(bl): b.label = labels[j]
                st.session_state.sessoes[t].blocos = bl
                st.rerun()

        for idx, ex in enumerate(exs, 1):
            eq  = ex.eq_primario + (f" + {ex.eq_secundario}" if ex.eq_secundario else "")
            obs = f" · {ex.obs}" if ex.obs else ""
            pk  = f"p_{t}_{bloco.label}_{idx}"

            col_ex, col_sub = st.columns([16, 1])
            with col_ex:
                st.markdown(
                    f"<p style='margin:0;font-size:13px;line-height:1.6'>"
                    f"<b>{bloco.label}{idx}</b>&nbsp;{ex.nome}{prescr_badge(ex)} "
                    f"<span style='color:#9ca3af;font-size:11px'>{ex.purpose} · 🔧 {eq}{obs}</span></p>",
                    unsafe_allow_html=True,
                )
            with col_sub:
                if st.button("↺", key=f"sub_btn_{t}_{i}_{idx}", help="Substituir"):
                    st.session_state.sub_alvo[t] = ex.nome
                    st.session_state.candidatos[t] = []

            # Prescrição em linha
            pc0, pc1, pc2, pc3, pc4 = st.columns([3, 2, 3, 2, 2])
            with pc0:
                st.markdown(
                    "<p style='font-size:10px;color:#9ca3af;margin:4px 0 2px 0;"
                    "text-transform:uppercase;letter-spacing:0.08em'>Prescrição</p>",
                    unsafe_allow_html=True,
                )
            with pc1:
                new_s = st.number_input("S", 1, 10, ex.series or 3, key=f"s_{pk}", label_visibility="collapsed")
            with pc2:
                new_r = st.text_input("R", ex.reps or "8-12", key=f"r_{pk}", placeholder="reps", label_visibility="collapsed")
            with pc3:
                new_rir = st.number_input("RIR", 0, 4, ex.rir if ex.rir is not None else 2, key=f"rir_{pk}", label_visibility="collapsed")
            with pc4:
                if st.button("💾", key=f"save_{pk}", help="Salvar prescrição"):
                    target = st.session_state.sessoes[t].blocos[i]
                    slot = [target.ex1, target.ex2, target.ex3]
                    ri = idx - 1
                    if slot[ri] is not None:
                        slot[ri].series = int(new_s)
                        slot[ri].reps   = new_r.strip() or None
                        slot[ri].rir    = int(new_rir)
                        if ri == 0: target.ex1 = slot[0]
                        elif ri == 1: target.ex2 = slot[1]
                        else: target.ex3 = slot[2]
                    st.rerun()

        st.markdown("<hr class='thin-hr'>", unsafe_allow_html=True)

    # Painel substituição
    alvo = st.session_state.sub_alvo[t]
    if alvo:
        st.markdown(
            f"<div class='sub-panel'>"
            f"<p style='font-size:13px;font-weight:600;color:#92400e;margin:0 0 10px 0'>"
            f"↺ Substituir: {alvo}</p></div>",
            unsafe_allow_html=True,
        )
        sess_atual = st.session_state.sessoes[t]
        fc1, fc2, fc3 = st.columns(3)
        with fc1:
            f_pad = st.selectbox("Categoria", ["(qualquer)"] + sorted(PADROES_LABELS.keys()), key=f"f_pad_{t}",
                format_func=lambda x: PADROES_LABELS.get(x, x) if x != "(qualquer)" else "Qualquer")
        with fc2:
            f_pur = st.selectbox("Purpose", ["(qualquer)", "compound", "isolation", "stability", "explosive"], key=f"f_pur_{t}")
        with fc3:
            f_uni = st.selectbox("Lateralidade", ["(qualquer)", "bilateral", "unilateral"], key=f"f_uni_{t}")
        f_ign = st.checkbox("Ignorar similaridade já usada", value=True, key=f"f_ign_{t}")

        cb1, cb2, cb3 = st.columns(3)
        with cb1:
            if st.button("🔍 Buscar", key=f"buscar_{t}", use_container_width=True):
                st.session_state.candidatos[t] = buscar_substitutos(
                    sess_atual, nome_atual=alvo, banco=banco,
                    padrao=None if f_pad == "(qualquer)" else f_pad,
                    purpose=None if f_pur == "(qualquer)" else f_pur,
                    unilateral=None if f_uni == "(qualquer)" else f_uni,
                    max_complexidade=max_cx,
                    ignorar_similaridade_usada=f_ign,
                )
        with cb2:
            if st.button("🎲 Aleatório", key=f"alea_{t}", use_container_width=True):
                st.session_state.sessoes[t] = substituir_exercicio(sess_atual, alvo, banco, max_complexidade=max_cx)
                st.session_state.sub_alvo[t] = None
                st.session_state.candidatos[t] = []
                st.rerun()
        with cb3:
            if st.button("✕ Cancelar", key=f"cancel_{t}", use_container_width=True):
                st.session_state.sub_alvo[t] = None
                st.session_state.candidatos[t] = []
                st.rerun()

        cands = st.session_state.candidatos[t]
        if cands:
            st.caption(f"{len(cands)} candidato(s)")
            nomes_c = [f"{e.nome}  [{e.purpose} · {e.eq_primario}]" for e in cands]
            escolha = st.radio("", nomes_c, key=f"radio_{t}", label_visibility="collapsed")
            escolha_nome = escolha.split("  [")[0]
            if st.button("✅ Aplicar", type="primary", key=f"aplicar_{t}"):
                st.session_state.sessoes[t] = substituir_exercicio_por(sess_atual, alvo, escolha_nome, banco)
                st.session_state.sub_alvo[t] = None
                st.session_state.candidatos[t] = []
                st.rerun()


# ---------------------------------------------------------------------------
# Config UI de um treino — retorna dict
# ---------------------------------------------------------------------------

def ui_config_treino(t: int) -> dict:
    modo = st.radio(
        "Modo", ["Categorias", "Template"],
        key=f"modo_{t}", horizontal=True, label_visibility="collapsed",
    )

    padroes_sel = []
    epp = {}

    if modo == "Template":
        tmpl = st.selectbox("Template", list(TEMPLATES.keys()), key=f"tmpl_{t}")
        padroes_tmpl = TEMPLATES[tmpl]
        tmpl_epp = TEMPLATE_EPP.get(tmpl, {})
        st.markdown(
            "<p style='font-size:11px;color:#6b7280;text-transform:uppercase;"
            "letter-spacing:0.07em;margin:10px 0 4px 0'>Exercícios por categoria</p>",
            unsafe_allow_html=True,
        )
        cols = st.columns(min(len(padroes_tmpl), 4))
        for ci, p in enumerate(padroes_tmpl):
            with cols[ci % len(cols)]:
                epp[p] = st.slider(PADROES_LABELS.get(p, p), 0, 5, tmpl_epp.get(p, 1), key=f"epp_{t}_{p}")
        padroes_sel = [p for p in padroes_tmpl if epp.get(p, 0) > 0]

    else:
        padroes_disp = [p for p in PADROES_LABELS if p in todos_padroes]
        st.markdown(
            "<p style='font-size:11px;color:#6b7280;text-transform:uppercase;"
            "letter-spacing:0.07em;margin:8px 0 4px 0'>Categorias</p>",
            unsafe_allow_html=True,
        )
        col_a, col_b, col_c = st.columns(3)
        cols3 = [col_a, col_b, col_c]
        sel_raw = []
        for ci, p in enumerate(padroes_disp):
            with cols3[ci % 3]:
                if st.checkbox(PADROES_LABELS[p], key=f"chk_{t}_{p}"):
                    sel_raw.append(p)

        if sel_raw:
            st.markdown(
                "<p style='font-size:11px;color:#6b7280;text-transform:uppercase;"
                "letter-spacing:0.07em;margin:10px 0 4px 0'>Exercícios por categoria</p>",
                unsafe_allow_html=True,
            )
            cols_sl = st.columns(min(len(sel_raw), 4))
            for ci, p in enumerate(sel_raw):
                with cols_sl[ci % len(cols_sl)]:
                    epp[p] = st.slider(PADROES_LABELS.get(p, p), 0, 5, 1, key=f"epp_{t}_{p}")
            padroes_sel = [p for p in sel_raw if epp.get(p, 0) > 0]

    return {"padroes": padroes_sel, "exercicios_por_padrao": epp}


# ===========================================================================
# LAYOUT
# ===========================================================================

st.markdown("""
<div class="app-header">
    <div>
        <h1>💪 BF Treinamento</h1>
        <p>Gerador de sessões personalizadas</p>
    </div>
</div>
""", unsafe_allow_html=True)

tab_treino, tab_alunos = st.tabs(["🏋️ Treinos", "👥 Alunos"])

# ===========================================================================
# TAB TREINOS
# ===========================================================================
with tab_treino:

    # -----------------------------------------------------------------------
    # Painel de configuração
    # -----------------------------------------------------------------------
    lbl_toggle = "▲ Fechar configuração" if st.session_state.config_aberta else "▼ Configurar treinos"
    if st.button(lbl_toggle, key="toggle_config"):
        st.session_state.config_aberta = not st.session_state.config_aberta
        st.rerun()

    configs_ui = []   # preenchido dentro do painel

    if st.session_state.config_aberta:
        st.markdown("<div class='config-panel'>", unsafe_allow_html=True)

        # Configurações gerais
        st.markdown("<p class='config-title'>Configurações gerais</p>", unsafe_allow_html=True)
        cg1, cg2, cg3, cg4, cg5 = st.columns([2, 2, 2, 3, 3])
        with cg1:
            n_treinos = st.number_input("Nº de treinos", 1, 5, 1, key="n_treinos")
        with cg2:
            tamanho_bloco = st.radio("Exerc./bloco", [1, 2, 3], index=1, horizontal=True, key="tamanho_bloco")
        with cg3:
            max_cx = st.slider("Complexidade máx.", 1, 5, 5, key="max_cx")
        with cg4:
            variar = st.checkbox(
                "Variar exercícios entre treinos", value=True, key="variar_entre",
                help="Evita repetir grupos de similaridade entre treinos",
            )
        with cg5:
            aluno_exp = st.selectbox("Aluno (PNG)", nomes_alunos, key="aluno_exp")

        st.markdown("<hr class='thin-hr' style='margin:16px 0'>", unsafe_allow_html=True)

        # Config por treino
        n = int(n_treinos)
        if n == 1:
            st.markdown("<p class='config-title'>Treino 1</p>", unsafe_allow_html=True)
            cfg = ui_config_treino(0)
            cfg.update({"max_complexidade": max_cx, "tamanho_bloco": tamanho_bloco, "equipamentos_bloqueados": []})
            configs_ui.append(cfg)
        else:
            tabs_cfg = st.tabs([f"Treino {i+1}" for i in range(n)])
            for i, tab_c in enumerate(tabs_cfg):
                with tab_c:
                    cfg = ui_config_treino(i)
                    cfg.update({"max_complexidade": max_cx, "tamanho_bloco": tamanho_bloco, "equipamentos_bloqueados": []})
                    configs_ui.append(cfg)

        st.markdown("</div>", unsafe_allow_html=True)

        # Botão gerar
        st.markdown("<div style='margin-top:12px'>", unsafe_allow_html=True)
        if st.button("▶ Gerar treinos", type="primary", use_container_width=True):
            vazios = [i+1 for i, c in enumerate(configs_ui) if not c["padroes"]]
            if vazios:
                st.warning(f"Selecione ao menos uma categoria no(s) Treino(s) {', '.join(str(x) for x in vazios)}.")
            else:
                with st.spinner("Gerando..."):
                    sessoes = gerar_multiplos_treinos(banco, configs_ui, variar_entre_treinos=variar)
                n_sess = len(sessoes)
                st.session_state.sessoes     = sessoes
                st.session_state.sub_alvo    = [None] * n_sess
                st.session_state.candidatos  = [[] for _ in range(n_sess)]
                st.session_state.modo_viz    = ["visualizar"] * n_sess
                st.session_state.config_aberta = False
                st.rerun()
        st.markdown("</div>", unsafe_allow_html=True)

    # -----------------------------------------------------------------------
    # Resultados
    # -----------------------------------------------------------------------
    sessoes: list = st.session_state.sessoes

    if sessoes:
        n_sess = len(sessoes)

        # Garante tamanho das listas de estado
        for k, default in [("sub_alvo", None), ("candidatos", []), ("modo_viz", "visualizar")]:
            while len(st.session_state[k]) < n_sess:
                st.session_state[k].append([] if default == [] else default)

        result_tabs = st.tabs([f"Treino {i+1}" for i in range(n_sess)]) if n_sess > 1 else [st.container()]

        for t, container in enumerate(result_tabs):
            with container:
                sessao: Sessao = sessoes[t]
                cats = " · ".join(PADROES_LABELS.get(p, p) for p in sessao.tipo.split(" + ") if p)

                st.markdown(
                    f"<p style='font-size:11px;color:#9ca3af;margin:16px 0 2px 0;"
                    f"text-transform:uppercase;letter-spacing:0.08em'>Sessão {t+1}</p>"
                    f"<p style='font-size:18px;font-weight:700;color:#111827;"
                    f"margin:0 0 12px 0'>{cats}</p>",
                    unsafe_allow_html=True,
                )

                # Linha de ações
                ca1, ca2, ca3 = st.columns([3, 2, 2])
                with ca1:
                    ae = st.session_state.get("aluno_exp", "Selecionar aluno...")
                    if ae and ae != "Selecionar aluno...":
                        lp = Path("logo.png")
                        if not lp.exists(): lp = Path("logo.jpg")
                        logo_b = lp.read_bytes() if lp.exists() else None
                        png = gerar_png(sessao, ae, logo_bytes=logo_b)
                        st.download_button(
                            "⬇ Baixar PNG", data=png,
                            file_name=f"treino{t+1}_{ae.lower().replace(' ','_')}.png",
                            mime="image/png", use_container_width=True, key=f"dl_{t}",
                        )
                with ca2:
                    if st.button("🔄 Regerar", key=f"regen_{t}", use_container_width=True):
                        # Tenta usar configs_ui; fallback usa padrões da sessão
                        if configs_ui and t < len(configs_ui):
                            cfg_r = configs_ui[t]
                        else:
                            pats = [p for p in sessao.tipo.split(" + ") if p]
                            cfg_r = {
                                "padroes": pats,
                                "exercicios_por_padrao": {p: 1 for p in pats},
                                "max_complexidade": st.session_state.get("max_cx", 5),
                                "tamanho_bloco": st.session_state.get("tamanho_bloco", 2),
                                "equipamentos_bloqueados": [],
                            }
                        nova = gerar_sessao(
                            banco, cfg_r["padroes"],
                            exercicios_por_padrao=cfg_r["exercicios_por_padrao"],
                            equipamentos_bloqueados=cfg_r.get("equipamentos_bloqueados", []),
                            max_complexidade=cfg_r.get("max_complexidade", 5),
                            tamanho_bloco=cfg_r.get("tamanho_bloco", 2),
                        )
                        st.session_state.sessoes[t] = nova
                        st.session_state.sub_alvo[t] = None
                        st.session_state.candidatos[t] = []
                        st.rerun()
                with ca3:
                    modo_atual = st.session_state.modo_viz[t]
                    lbl_m = "✏️ Editar" if modo_atual == "visualizar" else "👁 Visualizar"
                    if st.button(lbl_m, key=f"toggle_modo_{t}", use_container_width=True):
                        st.session_state.modo_viz[t] = "editar" if modo_atual == "visualizar" else "visualizar"
                        st.session_state.sub_alvo[t] = None
                        st.session_state.candidatos[t] = []
                        st.rerun()

                st.markdown("<div style='margin-top:8px'></div>", unsafe_allow_html=True)

                if st.session_state.modo_viz[t] == "visualizar":
                    render_slim(sessao)
                else:
                    render_editar(sessao, t, max_cx=st.session_state.get("max_cx", 5))

    else:
        st.markdown("""
        <div style="text-align:center; padding: 60px 20px; color: #9ca3af;">
            <div style="font-size: 52px; margin-bottom: 16px;">🏋️</div>
            <div style="font-size: 18px; font-weight: 600; color: #374151;">Configure e gere seu primeiro treino</div>
            <div style="font-size: 14px; margin-top: 8px;">
                Use o painel acima para definir as categorias e clique em <strong>Gerar treinos</strong>
            </div>
        </div>
        """, unsafe_allow_html=True)


# ===========================================================================
# TAB ALUNOS
# ===========================================================================
with tab_alunos:
    st.markdown(
        "<p style='font-size:11px;color:#9ca3af;margin:0 0 2px 0;"
        "text-transform:uppercase;letter-spacing:0.08em'>Gestão de alunos</p>"
        "<p style='font-size:20px;font-weight:600;color:#111827;margin:0 0 16px 0'>Cadastro</p>",
        unsafe_allow_html=True,
    )

    alunos_atual = carregar_alunos()
    objs  = ["hipertrofia", "forca", "resistencia", "emagrecimento", "condicionamento", "reabilitacao"]
    nivis = ["iniciante", "intermediario", "avancado"]

    with st.expander("➕ Novo aluno", expanded=(len(alunos_atual) == 0)):
        with st.form("form_novo_aluno", clear_on_submit=True):
            c1, c2 = st.columns(2)
            with c1:
                novo_nome  = st.text_input("Nome *")
                novo_nivel = st.selectbox("Nível", nivis, index=1)
            with c2:
                novo_obj  = st.selectbox("Objetivo", objs)
                novo_rest = st.text_input("Restrições (vírgula)", placeholder="ex: ombro direito, joelho")
            novo_obs = st.text_area("Observações")
            if st.form_submit_button("Salvar aluno", type="primary", use_container_width=True):
                if not novo_nome.strip():
                    st.error("Nome é obrigatório.")
                elif any(a["nome"].lower() == novo_nome.strip().lower() for a in alunos_atual):
                    st.error(f"Já existe '{novo_nome.strip()}'.")
                else:
                    alunos_atual.append({
                        "nome": novo_nome.strip(), "nivel": novo_nivel, "objetivo": novo_obj,
                        "restricoes": [r.strip() for r in novo_rest.split(",") if r.strip()],
                        "obs": novo_obs.strip(),
                    })
                    salvar_alunos(alunos_atual)
                    st.success(f"Aluno '{novo_nome.strip()}' cadastrado.")
                    st.rerun()

    st.markdown("---")

    if not alunos_atual:
        st.markdown(
            "<div style='text-align:center;padding:40px 20px;color:#9ca3af'>"
            "<div style='font-size:40px;margin-bottom:8px'>👥</div>"
            "<div style='font-size:14px'>Nenhum aluno cadastrado ainda.</div>"
            "</div>", unsafe_allow_html=True,
        )
    else:
        st.caption(f"{len(alunos_atual)} aluno(s)")
        for i, aluno in enumerate(alunos_atual):
            if st.session_state.edit_aluno_idx == i:
                with st.form(f"form_edit_{i}"):
                    st.markdown(
                        f"<p style='font-size:13px;font-weight:600;color:#e85d04;margin:0 0 8px 0'>"
                        f"✏️ Editando: {aluno['nome']}</p>", unsafe_allow_html=True,
                    )
                    ec1, ec2 = st.columns(2)
                    with ec1:
                        en  = st.text_input("Nome *", value=aluno["nome"])
                        enl = st.selectbox("Nível", nivis, index=nivis.index(aluno.get("nivel", "intermediario")))
                    with ec2:
                        eo = st.selectbox("Objetivo", objs, index=objs.index(aluno.get("objetivo", "hipertrofia")))
                        er = st.text_input("Restrições", value=", ".join(aluno.get("restricoes", [])))
                    eob = st.text_area("Observações", value=aluno.get("obs", ""))
                    cs, cc = st.columns(2)
                    with cs:
                        if st.form_submit_button("💾 Salvar", type="primary", use_container_width=True):
                            if not en.strip():
                                st.error("Nome obrigatório.")
                            else:
                                alunos_atual[i] = {
                                    "nome": en.strip(), "nivel": enl, "objetivo": eo,
                                    "restricoes": [r.strip() for r in er.split(",") if r.strip()],
                                    "obs": eob.strip(),
                                }
                                salvar_alunos(alunos_atual)
                                st.session_state.edit_aluno_idx = None
                                st.rerun()
                    with cc:
                        if st.form_submit_button("✕ Cancelar", use_container_width=True):
                            st.session_state.edit_aluno_idx = None
                            st.rerun()
            else:
                col_info, col_ed, col_del = st.columns([10, 1, 1])
                with col_info:
                    rt = ", ".join(aluno.get("restricoes", [])) or "—"
                    ob = aluno.get("obs", "") or "—"
                    st.markdown(
                        f"<div style='background:#f9fafb;border:1px solid #e5e7eb;"
                        f"border-radius:8px;padding:12px 16px;margin-bottom:8px'>"
                        f"<p style='margin:0;font-size:15px;font-weight:600;color:#111827'>{aluno['nome']}</p>"
                        f"<p style='margin:4px 0 0 0;font-size:12px;color:#6b7280'>"
                        f"<b>Nível:</b> {aluno.get('nivel','—')} &nbsp;·&nbsp; "
                        f"<b>Objetivo:</b> {aluno.get('objetivo','—')} &nbsp;·&nbsp; "
                        f"<b>Restrições:</b> {rt}</p>"
                        f"<p style='margin:4px 0 0 0;font-size:12px;color:#9ca3af'><b>Obs:</b> {ob}</p></div>",
                        unsafe_allow_html=True,
                    )
                with col_ed:
                    if st.button("✏️", key=f"edit_{i}", help=f"Editar {aluno['nome']}"):
                        st.session_state.edit_aluno_idx = i
                        st.rerun()
                with col_del:
                    if st.button("🗑", key=f"del_{i}", help=f"Remover {aluno['nome']}"):
                        alunos_atual.pop(i)
                        salvar_alunos(alunos_atual)
                        st.rerun()
