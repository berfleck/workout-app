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

/* Sidebar */
section[data-testid="stSidebar"] {
    background: #0f1117;
    border-right: 1px solid #1e2130;
}
section[data-testid="stSidebar"] * {
    color: #c8ccd8 !important;
}
section[data-testid="stSidebar"] .stSelectbox label,
section[data-testid="stSidebar"] .stMultiSelect label,
section[data-testid="stSidebar"] .stSlider label,
section[data-testid="stSidebar"] .stCheckbox label {
    font-size: 12px !important;
    text-transform: uppercase;
    letter-spacing: 0.08em;
    color: #6b7280 !important;
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

with st.sidebar:
    st.markdown("## ⚙️ Configuração")
    st.markdown("---")

    # Estrutura do treino
    st.markdown("**Estrutura**")
    modo = st.radio(
        "Modo de seleção",
        ["Template", "Padrões livres"],
        label_visibility="collapsed",
    )

    if modo == "Template":
        template_nome = st.selectbox(
            "Template",
            list(TEMPLATES.keys()),
        )
        padroes_selecionados = TEMPLATES[template_nome]
        st.caption(f"Padrões: {', '.join(padroes_selecionados)}")
    else:
        # Ordem e labels amigáveis para os checkboxes
        PADROES_LABELS = {
            "horizontal_push": "Horizontal Push (supino, flexão...)",
            "horizontal_pull": "Horizontal Pull (remada...)",
            "vertical_push":   "Vertical Push (desenvolvimento, elevação...)",
            "vertical_pull":   "Vertical Pull (puxada, barra fixa...)",
            "squat":           "Squat (agachamento, leg press...)",
            "hinge":           "Hinge (terra, hip thrust, hiperextensão...)",
            "abduction":       "Abduction (abdução de quadril...)",
            "adduction":       "Adduction (adução, copenhagen...)",
            "core":            "Core (prancha, crunch, roda...)",
            "biceps":          "Bíceps (rosca...)",
            "triceps":         "Tríceps",
            "flexao_plantar":     "Panturrilha (elevação, flexão plantar...)",
            "cardio":          "Cardio (air bike...)",
        }
        padroes_selecionados = []
        for padrao, label in PADROES_LABELS.items():
            if padrao in todos_padroes:
                checked = padrao in ["horizontal_push", "hinge", "vertical_pull"]
                if st.checkbox(label, value=checked, key=f"chk_{padrao}"):
                    padroes_selecionados.append(padrao)

    st.markdown("---")

    # Exercícios por padrão
    st.markdown("**Exercícios por padrão**")
    epp_custom = {}
    for p in (padroes_selecionados or []):
        default_n = EXERCICIOS_POR_PADRAO.get(p, 1)
        epp_custom[p] = st.slider(p, 1, 3, default_n, key=f"epp_{p}")

    st.markdown("---")

    # Restrições
    st.markdown("**Restrições**")
    eq_bloqueados = st.multiselect(
        "Equipamentos indisponíveis",
        todos_equipamentos,
    )

    max_cx = st.slider("Complexidade máxima", 1, 5, 5)

    st.markdown("---")

    # Exercícios travados
    st.markdown("**Travar exercícios**")
    nomes_todos = sorted([e.nome for e in banco])
    nomes_travados = st.multiselect(
        "Exercícios obrigatórios",
        nomes_todos,
    )
    exercicios_travados = [e for e in banco if e.nome in nomes_travados]

    st.markdown("---")

    gerar = st.button("Gerar treino", type="primary")


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
            st.session_state.sessao = gerar_sessao(
                banco,
                padroes_selecionados,
                exercicios_por_padrao=epp_custom,
                equipamentos_bloqueados=eq_bloqueados,
                max_complexidade=max_cx,
                exercicios_travados=exercicios_travados,
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
            st.session_state.sessao = gerar_sessao(
                banco,
                padroes_selecionados,
                exercicios_por_padrao=epp_custom,
                equipamentos_bloqueados=eq_bloqueados,
                max_complexidade=max_cx,
                exercicios_travados=exercicios_travados,
            )
            st.session_state.sub_alvo = None
            st.rerun()

    st.markdown("---")

    # Exibir blocos
    for bloco in sessao.blocos:
        exercicios_bloco = [bloco.ex1]
        if bloco.ex2:
            exercicios_bloco.append(bloco.ex2)

        with st.container(border=True):
            st.caption(f"BLOCO {bloco.label}")
            for idx, ex in enumerate(exercicios_bloco, 1):
                eq = ex.eq_primario + (f" + {ex.eq_secundario}" if ex.eq_secundario else "")
                obs = f" · *{ex.obs}*" if ex.obs else ""
                col_n, col_info = st.columns([1, 11])
                with col_n:
                    st.markdown(f"**{bloco.label}{idx}**")
                with col_info:
                    st.markdown(f"**{ex.nome}**")
                    st.caption(f"`{ex.purpose}` · `{ex.regiao}` · fd:{ex.fadiga} · cx:{ex.complexidade} · 🔧 {eq}{obs}")
                if idx < len(exercicios_bloco):
                    st.divider()

    st.markdown("---")

    # ---------------------------------------------------------------------------
    # Painel de substituição
    # ---------------------------------------------------------------------------

    st.markdown("### 🔁 Substituir exercício")

    col_s1, col_s2 = st.columns([2, 2])

    with col_s1:
        nomes_na_sessao = []
        for bloco in sessao.blocos:
            nomes_na_sessao.append(bloco.ex1.nome)
            if bloco.ex2:
                nomes_na_sessao.append(bloco.ex2.nome)

        sub_alvo = st.selectbox(
            "Exercício a substituir",
            nomes_na_sessao,
            key="select_sub_alvo",
        )

    with col_s2:
        if st.button("🎲 Substituição aleatória", help="Substitui por exercício do mesmo padrão"):
            st.session_state.sessao = substituir_exercicio(
                sessao, sub_alvo, banco,
                equipamentos_bloqueados=eq_bloqueados,
                max_complexidade=max_cx,
            )
            st.rerun()

    # Filtros para substituição manual
    with st.expander("🔍 Filtrar candidatos manualmente"):
        fc1, fc2, fc3, fc4 = st.columns(4)
        with fc1:
            f_padrao = st.selectbox("Padrão", ["(qualquer)"] + todos_padroes, key="f_padrao")
        with fc2:
            f_regiao = st.selectbox("Região", ["(qualquer)", "upper", "lower", "core"], key="f_regiao")
        with fc3:
            f_purpose = st.selectbox("Purpose", ["(qualquer)", "compound", "isolation", "stability", "explosive"], key="f_purpose")
        with fc4:
            f_uni = st.selectbox("Lateral.", ["(qualquer)", "bilateral", "unilateral"], key="f_uni")

        fc5, fc6 = st.columns(2)
        with fc5:
            f_max_fd = st.slider("Fadiga máx.", 1, 5, 5, key="f_fd")
        with fc6:
            f_max_cx = st.slider("Complexidade máx.", 1, 5, max_cx, key="f_cx")

        f_ignorar_sim = st.checkbox(
            "Mostrar mesmo que similaridade já usada na sessão",
            value=True,
            key="f_ignorar_sim",
        )

        if st.button("🔍 Buscar candidatos"):
            candidatos = buscar_substitutos(
                sessao,
                nome_atual=sub_alvo,
                banco=banco,
                padrao=None if f_padrao == "(qualquer)" else f_padrao,
                regiao=None if f_regiao == "(qualquer)" else f_regiao,
                purpose=None if f_purpose == "(qualquer)" else f_purpose,
                unilateral=None if f_uni == "(qualquer)" else f_uni,
                max_fadiga=f_max_fd,
                max_complexidade=f_max_cx,
                equipamentos_bloqueados=eq_bloqueados,
                ignorar_similaridade_usada=f_ignorar_sim,
            )
            st.session_state.candidatos = candidatos

        if "candidatos" in st.session_state and st.session_state.candidatos:
            candidatos = st.session_state.candidatos
            st.caption(f"{len(candidatos)} candidato(s) encontrado(s)")

            nomes_cand = [
                f"{e.nome}  [{e.purpose} | fd:{e.fadiga} | cx:{e.complexidade} | {e.eq_primario}]"
                for e in candidatos
            ]
            escolha_str = st.radio(
                "Escolha o substituto",
                nomes_cand,
                key="radio_cand",
                label_visibility="collapsed",
            )
            escolha_nome = escolha_str.split("  [")[0]

            if st.button("✅ Aplicar substituição"):
                st.session_state.sessao = substituir_exercicio_por(
                    sessao, sub_alvo, escolha_nome, banco
                )
                st.session_state.candidatos = []
                st.rerun()

        elif "candidatos" in st.session_state and not st.session_state.candidatos:
            st.warning("Nenhum candidato encontrado com esses filtros.")

else:
    # Estado inicial — nenhuma sessão gerada ainda
    st.markdown("""
    <div style="text-align:center; padding: 60px 20px; color: #9ca3af;">
        <div style="font-size: 48px; margin-bottom: 16px;">🏋️</div>
        <div style="font-size: 18px; font-weight: 500; color: #374151;">Configure e gere seu primeiro treino</div>
        <div style="font-size: 14px; margin-top: 8px;">Use o painel à esquerda para definir as opções e clique em <strong>Gerar treino</strong></div>
    </div>
    """, unsafe_allow_html=True)
