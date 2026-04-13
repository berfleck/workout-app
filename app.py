import streamlit as st
import random
import json
from pathlib import Path
from gerador_treino import (
    carregar_banco, gerar_sessao, substituir_exercicio,
    buscar_substitutos, substituir_exercicio_por,
    listar_candidatos, TEMPLATES, EXERCICIOS_POR_PADRAO,
    Exercicio, Sessao, SuperSerie,
)
from gerar_imagem import gerar_png

# ---------------------------------------------------------------------------
# Config e estilo
# ---------------------------------------------------------------------------

st.set_page_config(
    page_title="Gerador de Treinos",
    page_icon="💪",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@300;400;500;600&family=DM+Mono:wght@400;500&display=swap');

html, body, [class*="css"] {
    font-family: 'DM Sans', sans-serif;
}

/* Sidebar — compacta */
section[data-testid="stSidebar"] {
    background: #0f1117;
    border-right: 1px solid #1e2130;
}
section[data-testid="stSidebar"] * {
    color: #c8ccd8 !important;
}

/* Reduzir padding geral dentro da sidebar */
section[data-testid="stSidebar"] .block-container,
section[data-testid="stSidebar"] [data-testid="stVerticalBlock"] {
    gap: 0px !important;
}

/* Checkboxes compactos */
section[data-testid="stSidebar"] .stCheckbox {
    margin-bottom: 0px !important;
    padding: 0px !important;
    min-height: 0 !important;
}
section[data-testid="stSidebar"] .stCheckbox label {
    font-size: 12px !important;
    padding: 1px 0 !important;
    gap: 6px !important;
    color: #c8ccd8 !important;
}
section[data-testid="stSidebar"] .stCheckbox label p {
    font-size: 12px !important;
    margin: 0 !important;
    line-height: 1.4 !important;
}

/* Sliders compactos */
section[data-testid="stSidebar"] .stSlider {
    margin-bottom: 4px !important;
    padding-bottom: 0 !important;
}
section[data-testid="stSidebar"] .stSlider label,
section[data-testid="stSidebar"] .stSlider label p {
    font-size: 11px !important;
    margin-bottom: 0px !important;
    color: #6b7280 !important;
}
section[data-testid="stSidebar"] [data-testid="stSlider"] {
    padding-top: 0 !important;
    padding-bottom: 2px !important;
}

/* Selectbox e multiselect compactos */
section[data-testid="stSidebar"] .stSelectbox,
section[data-testid="stSidebar"] .stMultiSelect {
    margin-bottom: 6px !important;
}
section[data-testid="stSidebar"] .stSelectbox label,
section[data-testid="stSidebar"] .stMultiSelect label,
section[data-testid="stSidebar"] .stSlider > label {
    font-size: 11px !important;
    text-transform: uppercase;
    letter-spacing: 0.07em;
    color: #6b7280 !important;
    margin-bottom: 2px !important;
}

/* Radio compacto */
section[data-testid="stSidebar"] .stRadio {
    margin-bottom: 6px !important;
}
section[data-testid="stSidebar"] .stRadio label,
section[data-testid="stSidebar"] .stRadio label p {
    font-size: 12px !important;
    color: #c8ccd8 !important;
}
section[data-testid="stSidebar"] .stRadio > div {
    gap: 4px !important;
}

/* Markdown headers na sidebar */
section[data-testid="stSidebar"] h2 {
    font-size: 14px !important;
    margin-bottom: 4px !important;
}
section[data-testid="stSidebar"] strong {
    font-size: 11px !important;
    text-transform: uppercase;
    letter-spacing: 0.07em;
    color: #6b7280 !important;
}
section[data-testid="stSidebar"] hr {
    margin: 6px 0 !important;
    border-color: #1e2130 !important;
}

/* Blocos de treino */
.bloco-card {
    background: #ffffff;
    border: 1px solid #e5e7eb;
    border-radius: 12px;
    padding: 16px 20px;
    margin-bottom: 12px;
    position: relative;
}
.bloco-label {
    font-family: 'DM Mono', monospace;
    font-size: 11px;
    font-weight: 500;
    color: #9ca3af;
    letter-spacing: 0.12em;
    text-transform: uppercase;
    margin-bottom: 10px;
}
.ex-row {
    display: flex;
    align-items: flex-start;
    gap: 10px;
    padding: 8px 0;
}
.ex-row + .ex-row {
    border-top: 1px dashed #f3f4f6;
}
.ex-num {
    font-family: 'DM Mono', monospace;
    font-size: 11px;
    font-weight: 500;
    color: #d1d5db;
    min-width: 24px;
    padding-top: 2px;
}
.ex-nome {
    font-size: 15px;
    font-weight: 500;
    color: #111827;
    line-height: 1.3;
}
.ex-meta {
    font-size: 12px;
    color: #9ca3af;
    margin-top: 2px;
    font-family: 'DM Mono', monospace;
}
.ex-equip {
    font-size: 12px;
    color: #6b7280;
    margin-top: 2px;
}
.badge {
    display: inline-block;
    padding: 2px 8px;
    border-radius: 99px;
    font-size: 11px;
    font-weight: 500;
    margin-right: 4px;
}
.badge-compound  { background: #ede9fe; color: #5b21b6; }
.badge-isolation { background: #fce7f3; color: #9d174d; }
.badge-stability { background: #d1fae5; color: #065f46; }
.badge-explosive { background: #fee2e2; color: #991b1b; }
.badge-upper     { background: #dbeafe; color: #1e40af; }
.badge-lower     { background: #dcfce7; color: #166534; }
.badge-core      { background: #fef9c3; color: #854d0e; }

/* Header principal */
.main-header {
    border-bottom: 1px solid #e5e7eb;
    padding-bottom: 16px;
    margin-bottom: 24px;
}
.main-title {
    font-size: 28px;
    font-weight: 600;
    color: #111827;
    letter-spacing: -0.02em;
}
.main-sub {
    font-size: 14px;
    color: #9ca3af;
    margin-top: 4px;
}

/* Botão gerar */
div[data-testid="stButton"] > button[kind="primary"] {
    background: #e85d04 !important;
    color: white !important;
    border: none !important;
    border-radius: 8px !important;
    font-family: 'DM Sans', sans-serif !important;
    font-weight: 600 !important;
    font-size: 15px !important;
    padding: 10px 24px !important;
    width: 100%;
    letter-spacing: 0.02em;
}
div[data-testid="stButton"] > button[kind="primary"]:hover {
    background: #c44d03 !important;
}

/* Fixa o botão gerar no rodapé da sidebar */
section[data-testid="stSidebar"] div[data-testid="stButton"]:has(button[kind="primary"]) {
    position: sticky;
    bottom: 0;
    background: #0f1117;
    padding: 12px 0 8px 0;
    margin-top: 8px;
    border-top: 1px solid #1e2130;
    z-index: 999;
}

/* Separador */
.sep { border: none; border-top: 1px solid #f3f4f6; margin: 16px 0; }
</style>
""", unsafe_allow_html=True)




# ---------------------------------------------------------------------------
# Carregamento do banco (cached)
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
    path = Path("alunos.json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump(lista, f, ensure_ascii=False, indent=2)


banco = get_banco()
alunos = carregar_alunos()
nomes_alunos = ["Selecionar aluno..."] + [a["nome"] for a in alunos]
todos_equipamentos = sorted({e.eq_primario for e in banco if e.eq_primario and e.eq_primario != "Sem equipamento"})
todos_padroes = sorted({e.padrao for e in banco if e.padrao})


# ---------------------------------------------------------------------------
# Sidebar — painel de configuração
# ---------------------------------------------------------------------------

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

with st.sidebar:
    st.markdown("## ⚙️ Configuração")
    st.markdown("---")

    # Modo de seleção — padrão: Categorias
    modo = st.radio(
        "Modo de seleção",
        ["Categorias", "Template"],
        label_visibility="collapsed",
    )

    if modo == "Template":
        template_nome = st.selectbox(
            "Template",
            list(TEMPLATES.keys()),
        )
        padroes_selecionados = TEMPLATES[template_nome]
        st.caption(f"Categorias: {', '.join(padroes_selecionados)}")
    else:
        padroes_selecionados = []
        for padrao, label in PADROES_LABELS.items():
            if padrao in todos_padroes:
                if st.checkbox(label, value=False, key=f"chk_{padrao}"):
                    padroes_selecionados.append(padrao)

    st.markdown("---")

    # Exercícios por categoria
    st.markdown("**Exercícios por categoria**")
    epp_custom = {}
    for p in (padroes_selecionados or []):
        default_n = EXERCICIOS_POR_PADRAO.get(p, 1)
        label_p = PADROES_LABELS.get(p, p)
        epp_custom[p] = st.slider(label_p, 0, 3, default_n, key=f"epp_{p}")

    st.markdown("---")

    # Restrições
    st.markdown("**Restrições**")
    eq_bloqueados = []
    max_cx = st.slider("Complexidade máxima", 1, 5, 5)

    st.markdown("---")

    # Tamanho do bloco
    st.markdown("**Tamanho do bloco**")
    tamanho_bloco = st.radio(
        "Exercícios por bloco",
        [1, 2, 3],
        index=1,
        horizontal=True,
        label_visibility="collapsed",
        key="tamanho_bloco",
    )
    if tamanho_bloco == 3:
        st.caption("Trio: regra de fadiga relaxada")

    st.markdown("---")

    # Exercícios travados — minimizado em expander
    with st.expander("Exercícios obrigatórios"):
        nomes_todos = sorted([e.nome for e in banco])
        t1 = st.selectbox("Obrigatório 1", ["(nenhum)"] + nomes_todos, key="trav1")
        t2 = st.selectbox("Obrigatório 2", ["(nenhum)"] + nomes_todos, key="trav2")
        nomes_travados = [n for n in [t1, t2] if n != "(nenhum)"]
    exercicios_travados = [e for e in banco if e.nome in nomes_travados]

    st.markdown("---")

    # Alunos para exportação
    with st.expander("Exportar treino"):
        aluno_selecionado = st.selectbox("Aluno", nomes_alunos, key="aluno_exp")

    st.markdown("---")

    # Botão gerar no rodapé da sidebar
    gerar = st.button("▶ Gerar treino", type="primary", use_container_width=True, key="gerar_sidebar")




# ---------------------------------------------------------------------------
# Área principal
# ---------------------------------------------------------------------------

st.markdown("""
<div class="main-header">
    <div class="main-title">Gerador de Treinos</div>
    <div class="main-sub">Personal Training · Sessões personalizadas</div>
</div>
""", unsafe_allow_html=True)

# Inicializar estado
if "sessao" not in st.session_state:
    st.session_state.sessao = None
if "historico" not in st.session_state:
    st.session_state.historico = []

tab_treino, tab_alunos = st.tabs(["🏋️ Treino", "👥 Alunos"])

# ===========================================================================
# TAB: TREINO
# ===========================================================================
with tab_treino:
    # Botão duplicado no topo da área principal (útil no mobile e quando sidebar está colapsada)
    gerar_main = st.button("▶ Gerar treino", type="primary", use_container_width=True, key="gerar_main")
    disparar_geracao = gerar or gerar_main

    # Gerar sessão
    if disparar_geracao:
        if not padroes_selecionados:
            st.warning("Selecione ao menos um padrão de movimento.")
        else:
            with st.spinner("Gerando..."):
                padroes_ativos = [p for p in padroes_selecionados if epp_custom.get(p, 1) > 0]
                st.session_state.sessao = gerar_sessao(
                    banco,
                    padroes_ativos,
                    exercicios_por_padrao=epp_custom,
                    equipamentos_bloqueados=eq_bloqueados,
                    max_complexidade=max_cx,
                    exercicios_travados=exercicios_travados,
                    tamanho_bloco=tamanho_bloco,
                )
            st.session_state.sub_alvo = None
            st.session_state.sub_filtros = {}

    # Exibir sessão
    if st.session_state.sessao:
        sessao: Sessao = st.session_state.sessao

        # Cabeçalho da sessão — categorias em destaque
        labels_ativos = [PADROES_LABELS.get(p, p) for p in padroes_selecionados if epp_custom.get(p, 1) > 0]
        cats_str = " · ".join(labels_ativos) if labels_ativos else sessao.tipo
        st.markdown(
            f"<p style='font-size:11px;color:#9ca3af;margin:0 0 2px 0;text-transform:uppercase;letter-spacing:0.08em'>Sessão gerada</p>"
            f"<p style='font-size:20px;font-weight:600;color:#111827;margin:0 0 8px 0;line-height:1.3'>{cats_str}</p>",
            unsafe_allow_html=True,
        )

        # -----------------------------------------------------------------------
        # Toggle visualizar / editar
        # -----------------------------------------------------------------------
        st.markdown("""
        <style>
        /* Toggle pill */
        div[data-testid="stHorizontalBlock"]:has(.modo-toggle) {
            background: #f3f4f6;
            border-radius: 10px;
            padding: 4px;
            gap: 4px !important;
            margin-bottom: 16px;
        }
        .modo-toggle button {
            background: transparent !important;
            border: none !important;
            border-radius: 7px !important;
            color: #6b7280 !important;
            font-size: 13px !important;
            font-weight: 500 !important;
            padding: 6px 0 !important;
            width: 100% !important;
            transition: background 0.15s !important;
        }
        .modo-toggle button:hover {
            background: #e5e7eb !important;
            color: #111827 !important;
        }
        .modo-toggle-ativo button {
            background: #ffffff !important;
            color: #111827 !important;
            font-weight: 600 !important;
            box-shadow: 0 1px 4px rgba(0,0,0,0.10) !important;
            border-radius: 7px !important;
        }
        div[data-testid="stVerticalBlock"] > div { gap: 0rem !important; }
        </style>
        """, unsafe_allow_html=True)

        if "modo_visualizacao" not in st.session_state:
            st.session_state.modo_visualizacao = "visualizar"

        col_v, col_e = st.columns(2)
        modo_atual = st.session_state.modo_visualizacao
        with col_v:
            cls_v = "modo-toggle modo-toggle-ativo" if modo_atual == "visualizar" else "modo-toggle"
            st.markdown(f'<div class="{cls_v}">', unsafe_allow_html=True)
            if st.button("👁  Visualizar", key="modo_ver", use_container_width=True):
                st.session_state.modo_visualizacao = "visualizar"
                st.session_state.sub_alvo_inline = None
                st.session_state.candidatos = []
                st.rerun()
            st.markdown('</div>', unsafe_allow_html=True)
        with col_e:
            cls_e = "modo-toggle modo-toggle-ativo" if modo_atual == "editar" else "modo-toggle"
            st.markdown(f'<div class="{cls_e}">', unsafe_allow_html=True)
            if st.button("✏️  Editar", key="modo_editar", use_container_width=True):
                st.session_state.modo_visualizacao = "editar"
                st.rerun()
            st.markdown('</div>', unsafe_allow_html=True)

        modo = st.session_state.modo_visualizacao

        # -----------------------------------------------------------------------
        # Exportar como PNG + Regerar (linha de ações)
        # -----------------------------------------------------------------------
        col_dl, col_rg = st.columns([3, 1])
        with col_rg:
            if st.button("🔄 Regerar", help="Gera nova sessão com as mesmas configurações", use_container_width=True):
                padroes_ativos = [p for p in padroes_selecionados if epp_custom.get(p, 1) > 0]
                st.session_state.sessao = gerar_sessao(
                    banco,
                    padroes_ativos,
                    exercicios_por_padrao=epp_custom,
                    equipamentos_bloqueados=eq_bloqueados,
                    max_complexidade=max_cx,
                    exercicios_travados=exercicios_travados,
                    tamanho_bloco=tamanho_bloco,
                )
                st.session_state.sub_alvo = None
                st.rerun()
        with col_dl:
            aluno_exp = st.session_state.get("aluno_exp", "Selecionar aluno...")
            if aluno_exp and aluno_exp != "Selecionar aluno...":
                logo_bytes = None
                logo_path = Path("logo.png")
                if not logo_path.exists():
                    logo_path = Path("logo.jpg")
                if logo_path.exists():
                    logo_bytes = logo_path.read_bytes()
                png_bytes = gerar_png(sessao, aluno_exp, logo_bytes=logo_bytes)
                st.download_button(
                    label="⬇ Baixar treino (PNG)",
                    data=png_bytes,
                    file_name=f"treino_{aluno_exp.lower().replace(' ','_')}.png",
                    mime="image/png",
                    use_container_width=True,
                )

        st.markdown("<div style='margin-bottom:4px'></div>", unsafe_allow_html=True)

        # -----------------------------------------------------------------------
        # Inicializar estado de substituição
        # -----------------------------------------------------------------------
        if "sub_alvo_inline" not in st.session_state:
            st.session_state.sub_alvo_inline = None
        if "candidatos" not in st.session_state:
            st.session_state.candidatos = []

        # -----------------------------------------------------------------------
        # Blocos — helper de badge de prescrição (comum aos dois modos)
        # -----------------------------------------------------------------------
        def prescr_badge_html(ex):
            parts = []
            if ex.series:
                parts.append(f"{ex.series}×")
            if ex.reps:
                parts.append(ex.reps)
            if ex.rir is not None:
                parts.append(f"RIR {ex.rir}")
            if not parts:
                return ""
            return (
                f"<span style='background:#fff3e6;color:#e85d04;border-radius:6px;"
                f"padding:1px 7px;font-size:11px;font-weight:700;margin-left:6px'>"
                f"{' · '.join(parts)}</span>"
            )

        n_blocos = len(sessao.blocos)
        labels = "ABCDEFGHIJKLMNOP"

        # ===================================================================
        # MODO VISUALIZAR — slim, sem botões de edição
        # ===================================================================
        if modo == "visualizar":
            for bloco in sessao.blocos:
                exercicios_bloco = [e for e in [bloco.ex1, bloco.ex2, bloco.ex3] if e]
                st.markdown(
                    f"<p style='font-size:10px;font-weight:700;color:#9ca3af;"
                    f"letter-spacing:0.1em;margin:10px 0 4px 0'>BLOCO {bloco.label}</p>",
                    unsafe_allow_html=True,
                )
                for idx, ex in enumerate(exercicios_bloco, 1):
                    badge = prescr_badge_html(ex)
                    eq = ex.eq_primario + (f" + {ex.eq_secundario}" if ex.eq_secundario else "")
                    st.markdown(
                        f"<div style='padding:6px 0 6px 12px;border-left:3px solid #e85d04;margin-bottom:4px'>"
                        f"<span style='font-size:14px;font-weight:600;color:#111827'>"
                        f"{bloco.label}{idx}&nbsp; {ex.nome}</span>{badge}"
                        f"<br><span style='font-size:11px;color:#9ca3af'>"
                        f"{ex.purpose} · 🔧 {eq}</span>"
                        f"</div>",
                        unsafe_allow_html=True,
                    )
                st.markdown("<hr style='margin:4px 0 2px 0;border-color:#f3f4f6'>", unsafe_allow_html=True)

        # ===================================================================
        # MODO EDITAR — reordenação + substituição + prescrição
        # ===================================================================
        else:
            for i, bloco in enumerate(sessao.blocos):
                exercicios_bloco = [e for e in [bloco.ex1, bloco.ex2, bloco.ex3] if e]

                # Cabeçalho do bloco: label + setas
                col_lbl, col_up, col_dn = st.columns([14, 1, 1])
                with col_lbl:
                    st.markdown(
                        f"<p style='font-size:10px;font-weight:700;color:#9ca3af;"
                        f"letter-spacing:0.1em;margin:8px 0 2px 0'>BLOCO {bloco.label}</p>",
                        unsafe_allow_html=True,
                    )
                with col_up:
                    if i > 0:
                        if st.button("↑", key=f"up_{i}", help="Subir bloco"):
                            bl = sessao.blocos[:]
                            bl[i], bl[i-1] = bl[i-1], bl[i]
                            for j, b in enumerate(bl):
                                b.label = labels[j]
                            st.session_state.sessao.blocos = bl
                            st.rerun()
                with col_dn:
                    if i < n_blocos - 1:
                        if st.button("↓", key=f"dn_{i}", help="Descer bloco"):
                            bl = sessao.blocos[:]
                            bl[i], bl[i+1] = bl[i+1], bl[i]
                            for j, b in enumerate(bl):
                                b.label = labels[j]
                            st.session_state.sessao.blocos = bl
                            st.rerun()

                # Exercícios
                for idx, ex in enumerate(exercicios_bloco, 1):
                    eq = ex.eq_primario + (f" + {ex.eq_secundario}" if ex.eq_secundario else "")
                    obs = f" · {ex.obs}" if ex.obs else ""
                    badge = prescr_badge_html(ex)
                    prescr_key = f"prescr_{bloco.label}_{idx}"

                    col_ex, col_sub = st.columns([16, 1])
                    with col_ex:
                        st.markdown(
                            f"<p style='margin:0;font-size:13px;line-height:1.6'>"
                            f"<b>{bloco.label}{idx}</b>&nbsp; {ex.nome}{badge} "
                            f"<span style='color:#9ca3af;font-size:11px'>"
                            f"{ex.purpose} · 🔧 {eq}{obs}</span></p>",
                            unsafe_allow_html=True,
                        )
                    with col_sub:
                        if st.button("↺", key=f"sub_{i}_{idx}", help="Substituir"):
                            st.session_state.sub_alvo_inline = ex.nome
                            st.session_state.candidatos = []

                    # --- Prescrição: 4 campos numa linha, sem expander ---
                    pc0, pc1, pc2, pc3, pc4 = st.columns([3, 2, 3, 2, 2])
                    with pc0:
                        st.markdown(
                            "<p style='font-size:10px;color:#9ca3af;margin:6px 0 2px 0;"
                            "text-transform:uppercase;letter-spacing:0.08em'>Prescrição</p>",
                            unsafe_allow_html=True,
                        )
                    with pc1:
                        new_series = st.number_input(
                            "Séries", min_value=1, max_value=10,
                            value=ex.series if ex.series else 3,
                            key=f"series_{prescr_key}",
                            label_visibility="collapsed",
                        )
                    with pc2:
                        new_reps = st.text_input(
                            "Reps", value=ex.reps if ex.reps else "8-12",
                            key=f"reps_{prescr_key}",
                            placeholder="reps (ex: 8-12)",
                            label_visibility="collapsed",
                        )
                    with pc3:
                        new_rir = st.number_input(
                            "RIR", min_value=0, max_value=4,
                            value=ex.rir if ex.rir is not None else 2,
                            key=f"rir_{prescr_key}",
                            label_visibility="collapsed",
                        )
                    with pc4:
                        if st.button("💾", key=f"save_{prescr_key}", help="Salvar prescrição"):
                            target = st.session_state.sessao.blocos[i]
                            real_idx = idx - 1
                            exs = [target.ex1, target.ex2, target.ex3]
                            if exs[real_idx] is not None:
                                exs[real_idx].series = int(new_series)
                                exs[real_idx].reps = new_reps.strip() or None
                                exs[real_idx].rir = int(new_rir)
                                if real_idx == 0:
                                    target.ex1 = exs[0]
                                elif real_idx == 1:
                                    target.ex2 = exs[1]
                                else:
                                    target.ex3 = exs[2]
                            st.rerun()

                st.markdown("<hr style='margin:4px 0;border-color:#f3f4f6'>", unsafe_allow_html=True)

            # Painel de substituição inline (modo editar)
            if st.session_state.sub_alvo_inline:
                alvo = st.session_state.sub_alvo_inline
                st.markdown(
                    f"<div style='background:#fffbf5;border:1px solid #fed7aa;border-radius:10px;"
                    f"padding:14px 18px;margin-top:8px'>"
                    f"<p style='font-size:13px;font-weight:600;color:#92400e;margin:0 0 10px 0'>"
                    f"↺ Substituir: {alvo}</p></div>",
                    unsafe_allow_html=True,
                )
                fc1, fc2, fc3 = st.columns(3)
                with fc1:
                    f_padrao = st.selectbox(
                        "Categoria", ["(qualquer)"] + sorted(PADROES_LABELS.keys()),
                        key="f_padrao",
                        format_func=lambda x: PADROES_LABELS.get(x, x) if x != "(qualquer)" else "Qualquer",
                    )
                with fc2:
                    f_purpose = st.selectbox(
                        "Purpose",
                        ["(qualquer)", "compound", "isolation", "stability", "explosive"],
                        key="f_purpose",
                    )
                with fc3:
                    f_uni = st.selectbox(
                        "Lateralidade",
                        ["(qualquer)", "bilateral", "unilateral"],
                        key="f_uni",
                    )
                f_ignorar_sim = st.checkbox("Ignorar similaridade já usada", value=True, key="f_ignorar_sim")
                col_b1, col_b2, col_b3 = st.columns(3)
                with col_b1:
                    if st.button("🔍 Buscar", use_container_width=True):
                        st.session_state.candidatos = buscar_substitutos(
                            sessao, nome_atual=alvo, banco=banco,
                            padrao=None if f_padrao == "(qualquer)" else f_padrao,
                            purpose=None if f_purpose == "(qualquer)" else f_purpose,
                            unilateral=None if f_uni == "(qualquer)" else f_uni,
                            equipamentos_bloqueados=eq_bloqueados,
                            max_complexidade=max_cx,
                            ignorar_similaridade_usada=f_ignorar_sim,
                        )
                with col_b2:
                    if st.button("🎲 Aleatório", use_container_width=True):
                        st.session_state.sessao = substituir_exercicio(
                            sessao, alvo, banco,
                            equipamentos_bloqueados=eq_bloqueados,
                            max_complexidade=max_cx,
                        )
                        st.session_state.sub_alvo_inline = None
                        st.session_state.candidatos = []
                        st.rerun()
                with col_b3:
                    if st.button("✕ Cancelar", use_container_width=True):
                        st.session_state.sub_alvo_inline = None
                        st.session_state.candidatos = []
                        st.rerun()

                if st.session_state.candidatos:
                    st.caption(f"{len(st.session_state.candidatos)} candidato(s)")
                    nomes_cand = [
                        f"{e.nome}  [{e.purpose} · {e.eq_primario}]"
                        for e in st.session_state.candidatos
                    ]
                    escolha_str = st.radio("", nomes_cand, key="radio_cand", label_visibility="collapsed")
                    escolha_nome = escolha_str.split("  [")[0]
                    if st.button("✅ Aplicar", type="primary"):
                        st.session_state.sessao = substituir_exercicio_por(sessao, alvo, escolha_nome, banco)
                        st.session_state.sub_alvo_inline = None
                        st.session_state.candidatos = []
                        st.rerun()

    else:
        # Estado inicial — nenhuma sessão gerada ainda
        st.markdown("""
        <div style="text-align:center; padding: 60px 20px; color: #9ca3af;">
            <div style="font-size: 48px; margin-bottom: 16px;">🏋️</div>
            <div style="font-size: 18px; font-weight: 500; color: #374151;">Configure e gere seu primeiro treino</div>
            <div style="font-size: 14px; margin-top: 8px;">Use o painel à esquerda para definir as opções e clique em <strong>Gerar treino</strong></div>
        </div>
        """, unsafe_allow_html=True)


# ===========================================================================
# TAB: ALUNOS
# ===========================================================================
with tab_alunos:
    st.markdown(
        "<p style='font-size:11px;color:#9ca3af;margin:0 0 2px 0;text-transform:uppercase;letter-spacing:0.08em'>Gestão de alunos</p>"
        "<p style='font-size:20px;font-weight:600;color:#111827;margin:0 0 16px 0;line-height:1.3'>Cadastro</p>",
        unsafe_allow_html=True,
    )

    # Estado de edição
    if "edit_aluno_idx" not in st.session_state:
        st.session_state.edit_aluno_idx = None

    # Estado local da lista (recarrega do disco a cada rerun para refletir mudanças)
    alunos_atual = carregar_alunos()

    # --- Formulário de cadastro ---
    with st.expander("➕ Novo aluno", expanded=(len(alunos_atual) == 0)):
        with st.form("form_novo_aluno", clear_on_submit=True):
            c1, c2 = st.columns(2)
            with c1:
                novo_nome = st.text_input("Nome *")
                novo_nivel = st.selectbox(
                    "Nível",
                    ["iniciante", "intermediario", "avancado"],
                    index=1,
                )
            with c2:
                novo_objetivo = st.selectbox(
                    "Objetivo",
                    ["hipertrofia", "forca", "resistencia", "emagrecimento", "condicionamento", "reabilitacao"],
                    index=0,
                )
                novo_restricoes = st.text_input(
                    "Restrições (separadas por vírgula)",
                    placeholder="ex: ombro direito, joelho",
                )
            novo_obs = st.text_area("Observações", placeholder="Qualquer informação relevante...")

            submitted = st.form_submit_button("Salvar aluno", type="primary", use_container_width=True)
            if submitted:
                if not novo_nome.strip():
                    st.error("Nome é obrigatório.")
                elif any(a["nome"].lower() == novo_nome.strip().lower() for a in alunos_atual):
                    st.error(f"Já existe um aluno chamado '{novo_nome.strip()}'.")
                else:
                    restricoes_list = [r.strip() for r in novo_restricoes.split(",") if r.strip()]
                    alunos_atual.append({
                        "nome": novo_nome.strip(),
                        "nivel": novo_nivel,
                        "objetivo": novo_objetivo,
                        "restricoes": restricoes_list,
                        "obs": novo_obs.strip(),
                    })
                    salvar_alunos(alunos_atual)
                    st.success(f"Aluno '{novo_nome.strip()}' cadastrado.")
                    st.rerun()

    st.markdown("---")

    # --- Lista de alunos ---
    if not alunos_atual:
        st.markdown(
            "<div style='text-align:center;padding:40px 20px;color:#9ca3af'>"
            "<div style='font-size:40px;margin-bottom:8px'>👥</div>"
            "<div style='font-size:14px'>Nenhum aluno cadastrado ainda.</div>"
            "</div>",
            unsafe_allow_html=True,
        )
    else:
        st.caption(f"{len(alunos_atual)} aluno(s) cadastrado(s)")
        for i, aluno in enumerate(alunos_atual):
            with st.container():
                # Modo edição inline
                if st.session_state.edit_aluno_idx == i:
                    with st.form(f"form_edit_aluno_{i}"):
                        st.markdown(
                            f"<p style='font-size:13px;font-weight:600;color:#e85d04;margin:0 0 8px 0'>✏️ Editando: {aluno['nome']}</p>",
                            unsafe_allow_html=True,
                        )
                        ec1, ec2 = st.columns(2)
                        with ec1:
                            edit_nome = st.text_input("Nome *", value=aluno["nome"])
                            edit_nivel = st.selectbox(
                                "Nível",
                                ["iniciante", "intermediario", "avancado"],
                                index=["iniciante", "intermediario", "avancado"].index(aluno.get("nivel", "intermediario")),
                            )
                        with ec2:
                            objs = ["hipertrofia", "forca", "resistencia", "emagrecimento", "condicionamento", "reabilitacao"]
                            edit_objetivo = st.selectbox(
                                "Objetivo",
                                objs,
                                index=objs.index(aluno.get("objetivo", "hipertrofia")),
                            )
                            edit_restricoes = st.text_input(
                                "Restrições",
                                value=", ".join(aluno.get("restricoes", [])),
                            )
                        edit_obs = st.text_area("Observações", value=aluno.get("obs", ""))
                        col_save, col_cancel = st.columns(2)
                        with col_save:
                            if st.form_submit_button("💾 Salvar", type="primary", use_container_width=True):
                                if not edit_nome.strip():
                                    st.error("Nome é obrigatório.")
                                else:
                                    alunos_atual[i] = {
                                        "nome": edit_nome.strip(),
                                        "nivel": edit_nivel,
                                        "objetivo": edit_objetivo,
                                        "restricoes": [r.strip() for r in edit_restricoes.split(",") if r.strip()],
                                        "obs": edit_obs.strip(),
                                    }
                                    salvar_alunos(alunos_atual)
                                    st.session_state.edit_aluno_idx = None
                                    st.rerun()
                        with col_cancel:
                            if st.form_submit_button("✕ Cancelar", use_container_width=True):
                                st.session_state.edit_aluno_idx = None
                                st.rerun()
                else:
                    # Modo visualização
                    col_info, col_edit, col_del = st.columns([10, 1, 1])
                    with col_info:
                        restricoes_txt = ", ".join(aluno.get("restricoes", [])) or "—"
                        obs_txt = aluno.get("obs", "") or "—"
                        st.markdown(
                            f"<div style='background:#f9fafb;border:1px solid #e5e7eb;border-radius:8px;padding:12px 16px;margin-bottom:8px'>"
                            f"<p style='margin:0;font-size:15px;font-weight:600;color:#111827'>{aluno['nome']}</p>"
                            f"<p style='margin:4px 0 0 0;font-size:12px;color:#6b7280'>"
                            f"<b>Nível:</b> {aluno.get('nivel','—')} &nbsp;·&nbsp; "
                            f"<b>Objetivo:</b> {aluno.get('objetivo','—')} &nbsp;·&nbsp; "
                            f"<b>Restrições:</b> {restricoes_txt}"
                            f"</p>"
                            f"<p style='margin:4px 0 0 0;font-size:12px;color:#9ca3af'><b>Obs:</b> {obs_txt}</p>"
                            f"</div>",
                            unsafe_allow_html=True,
                        )
                    with col_edit:
                        if st.button("✏️", key=f"edit_aluno_{i}", help=f"Editar {aluno['nome']}"):
                            st.session_state.edit_aluno_idx = i
                            st.rerun()
                    with col_del:
                        if st.button("🗑", key=f"del_aluno_{i}", help=f"Remover {aluno['nome']}"):
                            alunos_atual.pop(i)
                            salvar_alunos(alunos_atual)
                            st.rerun()
