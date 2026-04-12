import streamlit as st
import random
from gerador_treino import (
    carregar_banco, gerar_sessao, substituir_exercicio,
    buscar_substitutos, substituir_exercicio_por,
    listar_candidatos, TEMPLATES, EXERCICIOS_POR_PADRAO,
    Exercicio, Sessao, SuperSerie,
)

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
    background: #111827 !important;
    color: white !important;
    border: none !important;
    border-radius: 8px !important;
    font-family: 'DM Sans', sans-serif !important;
    font-weight: 500 !important;
    font-size: 15px !important;
    padding: 10px 24px !important;
    width: 100%;
}
div[data-testid="stButton"] > button[kind="primary"]:hover {
    background: #374151 !important;
}

/* Separador */
.sep { border: none; border-top: 1px solid #f3f4f6; margin: 16px 0; }

/* Topo da área principal sticky — fixa os primeiros elementos */
[data-testid="stAppViewContainer"] > section.main > div.block-container > div:first-child {
    position: sticky;
    top: 0;
    z-index: 100;
    background: var(--background-color, white);
    padding-bottom: 8px;
}
</style>
""", unsafe_allow_html=True)




# ---------------------------------------------------------------------------
# Carregamento do banco (cached)
# ---------------------------------------------------------------------------

@st.cache_data
def get_banco():
    return carregar_banco("banco_exercicios.xlsx")


banco = get_banco()
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
    eq_bloqueados = st.multiselect(
        "Equipamentos indisponíveis",
        todos_equipamentos,
    )

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

    # Exercícios travados
    st.markdown("**Travar exercícios**")
    nomes_todos = sorted([e.nome for e in banco])
    nomes_travados = st.multiselect(
        "Exercícios obrigatórios",
        nomes_todos,
    )
    exercicios_travados = [e for e in banco if e.nome in nomes_travados]

    # Botão gerar nativo na sidebar (para capturar o clique)
    gerar = st.button("▶ Gerar treino", type="primary", use_container_width=True)


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

# Gerar sessão
if gerar:
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

    # Cabeçalho da sessão
    col_h1, col_h2 = st.columns([3, 1])
    with col_h1:
        st.markdown(f"### 📋 Sessão gerada")
        st.caption(f"Padrões: {sessao.tipo}")
    with col_h2:
        if st.button("🔄 Regerar", help="Gera nova sessão com as mesmas configurações"):
            padroes_ativos = [p for p in padroes_selecionados if epp_custom.get(p, 1) > 0]
            st.session_state.sessao = gerar_sessao(
                banco,
                padroes_ativos,
                exercicios_por_padrao=epp_custom,
                equipamentos_bloqueados=eq_bloqueados,
                max_complexidade=max_cx,
                exercicios_travados=exercicios_travados,
            )
            st.session_state.sub_alvo = None
            st.rerun()

    st.markdown("---")

    # Inicializar estado de substituição inline
    if "sub_alvo_inline" not in st.session_state:
        st.session_state.sub_alvo_inline = None
    if "candidatos" not in st.session_state:
        st.session_state.candidatos = []

    # CSS para compactar botões inline
    st.markdown("""
    <style>
    .btn-tiny button {
        padding: 0px 4px !important;
        font-size: 11px !important;
        height: 22px !important;
        min-height: 0 !important;
        line-height: 1 !important;
    }
    div[data-testid="stVerticalBlock"] > div { gap: 0rem !important; }
    </style>
    """, unsafe_allow_html=True)

    # Exibir blocos com reordenação e substituição inline
    n_blocos = len(sessao.blocos)
    labels = "ABCDEFGHIJKLMNOP"

    for i, bloco in enumerate(sessao.blocos):
        exercicios_bloco = [e for e in [bloco.ex1, bloco.ex2, bloco.ex3] if e]

        # Linha de cabeçalho do bloco: label + ▲▼ em HTML compacto
        ativo = st.session_state.sub_alvo_inline
        up_key = f"up_{i}"
        dn_key = f"dn_{i}"

        col_lbl, col_up, col_dn = st.columns([14, 1, 1])
        with col_lbl:
            st.markdown(
                f"<p style='font-size:10px;font-weight:700;color:#9ca3af;letter-spacing:0.1em;margin:4px 0 0 0'>BLOCO {bloco.label}</p>",
                unsafe_allow_html=True,
            )
        with col_up:
            if i > 0:
                if st.button("↑", key=up_key, help="Subir bloco"):
                    blocos = sessao.blocos[:]
                    blocos[i], blocos[i-1] = blocos[i-1], blocos[i]
                    for j, b in enumerate(blocos):
                        b.label = labels[j]
                    st.session_state.sessao.blocos = blocos
                    st.rerun()
        with col_dn:
            if i < n_blocos - 1:
                if st.button("↓", key=dn_key, help="Descer bloco"):
                    blocos = sessao.blocos[:]
                    blocos[i], blocos[i+1] = blocos[i+1], blocos[i]
                    for j, b in enumerate(blocos):
                        b.label = labels[j]
                    st.session_state.sessao.blocos = blocos
                    st.rerun()

        # Exercícios — uma linha por exercício, botão ↺ bem pequeno
        for idx, ex in enumerate(exercicios_bloco, 1):
            eq = ex.eq_primario + (f" + {ex.eq_secundario}" if ex.eq_secundario else "")
            obs = f" · {ex.obs}" if ex.obs else ""
            col_ex, col_sub = st.columns([16, 1])
            with col_ex:
                st.markdown(
                    f"<p style='margin:0;font-size:13px;line-height:1.6'>"
                    f"<b>{bloco.label}{idx}</b>&nbsp; {ex.nome} "
                    f"<span style='color:#9ca3af;font-size:11px'>{ex.purpose} · 🔧 {eq}{obs}</span></p>",
                    unsafe_allow_html=True,
                )
            with col_sub:
                if st.button("↺", key=f"sub_{i}_{idx}", help=f"Substituir"):
                    st.session_state.sub_alvo_inline = ex.nome
                    st.session_state.candidatos = []

        st.markdown("<hr style='margin:2px 0 4px 0;border-color:#f3f4f6'>", unsafe_allow_html=True)

    # Painel de substituição inline
    if st.session_state.sub_alvo_inline:
        alvo = st.session_state.sub_alvo_inline
        st.markdown(f"<p style='font-size:13px;margin:4px 0'><b>Substituir:</b> {alvo}</p>", unsafe_allow_html=True)

        fc1, fc2, fc3 = st.columns(3)
        with fc1:
            f_padrao = st.selectbox("Categoria", ["(qualquer)"] + sorted(PADROES_LABELS.keys()), key="f_padrao",
                format_func=lambda x: PADROES_LABELS.get(x, x) if x != "(qualquer)" else "Qualquer")
        with fc2:
            f_purpose = st.selectbox("Purpose", ["(qualquer)", "compound", "isolation", "stability", "explosive"], key="f_purpose")
        with fc3:
            f_uni = st.selectbox("Lateralidade", ["(qualquer)", "bilateral", "unilateral"], key="f_uni")

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
        elif st.session_state.candidatos == [] and "radio_cand" not in st.session_state:
            pass

else:
    # Estado inicial — nenhuma sessão gerada ainda
    st.markdown("""
    <div style="text-align:center; padding: 60px 20px; color: #9ca3af;">
        <div style="font-size: 48px; margin-bottom: 16px;">🏋️</div>
        <div style="font-size: 18px; font-weight: 500; color: #374151;">Configure e gere seu primeiro treino</div>
        <div style="font-size: 14px; margin-top: 8px;">Use o painel à esquerda para definir as opções e clique em <strong>Gerar treino</strong></div>
    </div>
    """, unsafe_allow_html=True)
