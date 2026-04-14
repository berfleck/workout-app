import streamlit as st
import random
import json
import io
import zipfile
import unicodedata
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

if "sessoes"        not in st.session_state: st.session_state.sessoes        = []
if "sub_alvo"       not in st.session_state: st.session_state.sub_alvo       = []
if "candidatos"     not in st.session_state: st.session_state.candidatos     = []
if "modo_viz"       not in st.session_state: st.session_state.modo_viz       = []
if "config_aberta"  not in st.session_state: st.session_state.config_aberta  = True
if "edit_aluno_idx" not in st.session_state: st.session_state.edit_aluno_idx = None
# painel "adicionar exercício": chave = (t, bloco_idx), valor = lista de candidatos
if "add_ex_alvo"    not in st.session_state: st.session_state.add_ex_alvo    = {}
if "add_ex_cands"   not in st.session_state: st.session_state.add_ex_cands   = {}
# painel "novo bloco": chave = t, valor = lista de candidatos
if "novo_bloco_cands" not in st.session_state: st.session_state.novo_bloco_cands = {}

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


def gerar_zip(sessoes: list, nome_aluno: str, logo_bytes) -> bytes:
    """Gera ZIP com um PNG por treino."""
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        for t, sessao in enumerate(sessoes):
            png = gerar_png(sessao, nome_aluno, logo_bytes=logo_bytes)
            fname = f"treino{t+1}_{nome_aluno.lower().replace(' ', '_')}.png"
            zf.writestr(fname, png)
    buf.seek(0)
    return buf.getvalue()


def _normalizar(texto: str) -> str:
    """Remove acentos e converte para minúsculas para busca fuzzy."""
    return unicodedata.normalize("NFD", texto).encode("ascii", "ignore").decode().lower()


def filtrar_banco(
    texto: str = "",
    padrao: str = None,
    purpose: str = None,
    unilateral: str = None,
    max_cx: int = 5,
) -> list:
    """Filtra o banco — busca por nome é case-insensitive e ignora acentos.
    Passar None (ou '(qualquer)') em padrao/purpose/unilateral = sem filtro."""
    resultado = list(banco)
    if padrao and padrao != "(qualquer)":
        resultado = [e for e in resultado if e.padrao == padrao]
    if purpose and purpose != "(qualquer)":
        resultado = [e for e in resultado if e.purpose == purpose]
    if unilateral and unilateral != "(qualquer)":
        resultado = [e for e in resultado if e.unilateral == unilateral]
    resultado = [e for e in resultado if e.complexidade <= max_cx]
    if texto.strip():
        txt_norm = _normalizar(texto.strip())
        resultado = [e for e in resultado if txt_norm in _normalizar(e.nome)]
    resultado.sort(key=lambda e: (e.purpose != "compound", e.nome))
    return resultado


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
        n_exs = len(exs)

        # Cabeçalho do bloco: label + setas + lixeira
        col_lbl, col_up, col_dn, col_del_bloco = st.columns([12, 1, 1, 1])
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
        with col_del_bloco:
            if st.button("🗑", key=f"del_bloco_{t}_{i}", help="Remover bloco"):
                bl = sessao.blocos[:]
                bl.pop(i)
                for j, b in enumerate(bl): b.label = labels[j]
                st.session_state.sessoes[t].blocos = bl
                st.session_state.add_ex_alvo.pop((t, i), None)
                st.session_state.add_ex_cands.pop((t, i), None)
                st.rerun()

        # Exercícios do bloco
        for idx, ex in enumerate(exs, 1):
            eq  = ex.eq_primario + (f" + {ex.eq_secundario}" if ex.eq_secundario else "")
            obs = f" · {ex.obs}" if ex.obs else ""
            pk  = f"p_{t}_{bloco.label}_{idx}"
            sub_key = f"{t}_{i}_{idx}"

            col_ex, col_sub, col_rm = st.columns([14, 1, 1])
            with col_ex:
                st.markdown(
                    f"<p style='margin:0;font-size:13px;line-height:1.6'>"
                    f"<b>{bloco.label}{idx}</b>&nbsp;{ex.nome}{prescr_badge(ex)} "
                    f"<span style='color:#9ca3af;font-size:11px'>{ex.purpose} · 🔧 {eq}{obs}</span></p>",
                    unsafe_allow_html=True,
                )
            with col_sub:
                sub_aberto = st.session_state.sub_alvo[t] == sub_key
                if st.button("✕" if sub_aberto else "↺",
                             key=f"sub_btn_{t}_{i}_{idx}",
                             help="Fechar" if sub_aberto else "Substituir"):
                    if sub_aberto:
                        st.session_state.sub_alvo[t] = None
                        st.session_state.candidatos[t] = []
                    else:
                        st.session_state.sub_alvo[t] = sub_key
                        st.session_state.candidatos[t] = []
                        st.session_state.add_ex_alvo.pop((t, i), None)
                    st.rerun()
            with col_rm:
                if st.button("✕", key=f"rm_ex_{t}_{i}_{idx}", help="Remover exercício"):
                    target = st.session_state.sessoes[t].blocos[i]
                    ri = idx - 1
                    if ri == 0:
                        target.ex1 = target.ex2
                        target.ex2 = target.ex3
                        target.ex3 = None
                    elif ri == 1:
                        target.ex2 = target.ex3
                        target.ex3 = None
                    else:
                        target.ex3 = None
                    if not any([target.ex1, target.ex2, target.ex3]):
                        bl = st.session_state.sessoes[t].blocos[:]
                        bl.pop(i)
                        for j, b in enumerate(bl): b.label = labels[j]
                        st.session_state.sessoes[t].blocos = bl
                    st.rerun()

            # Prescrição em linha
            pc0, pc1, pc2, pc3, pc4 = st.columns([3, 2, 3, 2, 2])
            with pc0:
                st.markdown(
                    "<p style='font-size:10px;color:#9ca3af;margin:4px 0 2px 0;"
                    "text-transform:uppercase;letter-spacing:0.08em'>Prescrição</p>",
                    unsafe_allow_html=True,
                )
            with pc1:
                new_s = st.number_input("Séries", 1, 10, ex.series or 3, key=f"s_{pk}", label_visibility="collapsed")
            with pc2:
                new_r = st.text_input("Reps", ex.reps or "8-12", key=f"r_{pk}", placeholder="reps", label_visibility="collapsed")
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

            # Painel substituição INLINE — logo abaixo do exercício
            if st.session_state.sub_alvo[t] == sub_key:
                _render_painel_substituicao_inline(t, i, idx, ex, sessao, max_cx)

        # Botão "+ Exercício"
        if n_exs < 3:
            add_key = (t, i)
            painel_aberto = st.session_state.add_ex_alvo.get(add_key, False)
            lbl_add = "✕ Fechar" if painel_aberto else "＋ Exercício"
            if st.button(lbl_add, key=f"toggle_add_{t}_{i}"):
                if painel_aberto:
                    st.session_state.add_ex_alvo.pop(add_key, None)
                    st.session_state.add_ex_cands.pop(add_key, None)
                else:
                    st.session_state.add_ex_alvo[add_key] = True
                    st.session_state.add_ex_cands[add_key] = []
                    st.session_state.sub_alvo[t] = None
                st.rerun()

            if painel_aberto:
                _render_painel_adicionar(t, i, bloco, max_cx)

        st.markdown("<hr class='thin-hr'>", unsafe_allow_html=True)

    # Botão "+ Novo bloco"
    novo_aberto = st.session_state.novo_bloco_cands.get(t) is not None
    lbl_novo = "✕ Fechar" if novo_aberto else "＋ Novo bloco"
    if st.button(lbl_novo, key=f"toggle_novo_bloco_{t}"):
        if novo_aberto:
            st.session_state.novo_bloco_cands.pop(t, None)
        else:
            st.session_state.novo_bloco_cands[t] = []
            st.session_state.sub_alvo[t] = None
        st.rerun()

    if novo_aberto:
        _render_painel_novo_bloco(t, sessao, max_cx)


def _render_painel_substituicao_inline(t: int, i: int, idx: int, ex, sessao: Sessao, max_cx: int):
    """Painel de substituição inline — logo abaixo do exercício, com busca por nome."""
    sub_key = f"{t}_{i}_{idx}"
    st.markdown(
        f"<div class='sub-panel'>"
        f"<p style='font-size:12px;font-weight:700;color:#92400e;margin:0 0 8px 0'>"
        f"↺ Substituir: {ex.nome}</p></div>",
        unsafe_allow_html=True,
    )

    # Filtros — busca por nome + dropdowns
    fs0, fs1, fs2, fs3 = st.columns([3, 2, 2, 2])
    with fs0:
        txt = st.text_input("Buscar por nome", key=f"sub_txt_{sub_key}",
                            placeholder="ex: bul → Búlgaro...")
    with fs1:
        f_pad = st.selectbox("Categoria", ["(qualquer)"] + sorted(PADROES_LABELS.keys()),
            key=f"f_pad_{sub_key}",
            format_func=lambda x: PADROES_LABELS.get(x, x) if x != "(qualquer)" else "Qualquer")
    with fs2:
        f_pur = st.selectbox("Purpose",
            ["(qualquer)", "compound", "isolation", "stability", "explosive"],
            key=f"f_pur_{sub_key}")
    with fs3:
        f_uni = st.selectbox("Lateralidade",
            ["(qualquer)", "bilateral", "unilateral"],
            key=f"f_uni_{sub_key}")

    f_ign = st.checkbox("Ignorar similaridade já usada", value=True, key=f"f_ign_{sub_key}")

    # Nomes e similaridades em uso na sessão (excluindo o exercício alvo)
    nomes_em_uso = {
        e.nome for bloco in sessao.blocos
        for e in [bloco.ex1, bloco.ex2, bloco.ex3] if e and e.nome != ex.nome
    }
    sims_em_uso = {
        e.similaridade for bloco in sessao.blocos
        for e in [bloco.ex1, bloco.ex2, bloco.ex3] if e and e.nome != ex.nome
    }

    cands = filtrar_banco(
        texto=txt,
        padrao=None if f_pad == "(qualquer)" else f_pad,
        purpose=None if f_pur == "(qualquer)" else f_pur,
        unilateral=None if f_uni == "(qualquer)" else f_uni,
        max_cx=max_cx,
    )
    cands = [e for e in cands if e.nome not in nomes_em_uso and e.nome != ex.nome]
    if not f_ign:
        cands = [e for e in cands if e.similaridade not in sims_em_uso]

    cb1, cb2 = st.columns(2)
    with cb1:
        if st.button("🎲 Aleatório", key=f"sub_alea_{sub_key}", use_container_width=True,
                     help="Substitui por exercício do mesmo padrão, aleatório"):
            st.session_state.sessoes[t] = substituir_exercicio(
                sessao, ex.nome, banco, max_complexidade=max_cx)
            st.session_state.sub_alvo[t] = None
            st.session_state.candidatos[t] = []
            st.rerun()
    with cb2:
        st.caption(f"{len(cands)} exercício(s)")

    if cands:
        nomes_c = [f"{e.nome}  [{e.purpose} · {e.eq_primario}]" for e in cands[:60]]
        escolha = st.radio("Escolha o substituto", nomes_c,
                           key=f"sub_radio_{sub_key}", label_visibility="collapsed")
        escolha_nome = escolha.split("  [")[0]
        if st.button("✅ Aplicar", type="primary", key=f"sub_aplicar_{sub_key}"):
            st.session_state.sessoes[t] = substituir_exercicio_por(sessao, ex.nome, escolha_nome, banco)
            st.session_state.sub_alvo[t] = None
            st.session_state.candidatos[t] = []
            st.rerun()
    elif txt or f_pad != "(qualquer)" or f_pur != "(qualquer)" or f_uni != "(qualquer)":
        st.caption("Nenhum exercício encontrado com esses filtros.")


def _render_painel_adicionar(t: int, i: int, bloco: SuperSerie, max_cx: int):
    """Painel para adicionar um exercício a um bloco existente."""
    add_key = (t, i)
    exs_no_bloco = [e for e in [bloco.ex1, bloco.ex2, bloco.ex3] if e]
    nomes_em_uso = {e.nome for e in exs_no_bloco}

    st.markdown(
        f"<div style='background:#f0fdf4;border:1px solid #86efac;border-radius:10px;"
        f"padding:12px 16px;margin:6px 0 8px 0'>"
        f"<p style='font-size:12px;font-weight:700;color:#166534;margin:0 0 8px 0'>"
        f"＋ Adicionar exercício ao Bloco {bloco.label}</p></div>",
        unsafe_allow_html=True,
    )

    fa1, fa2, fa3, fa4 = st.columns([3, 2, 2, 2])
    with fa1:
        txt = st.text_input("Buscar por nome", key=f"add_txt_{t}_{i}", placeholder="Digite para filtrar...")
    with fa2:
        pad = st.selectbox("Categoria", ["(qualquer)"] + sorted(PADROES_LABELS.keys()),
            key=f"add_pad_{t}_{i}",
            format_func=lambda x: PADROES_LABELS.get(x, x) if x != "(qualquer)" else "Qualquer")
    with fa3:
        pur = st.selectbox("Purpose", ["(qualquer)", "compound", "isolation", "stability", "explosive"],
            key=f"add_pur_{t}_{i}")
    with fa4:
        uni = st.selectbox("Lateralidade", ["(qualquer)", "bilateral", "unilateral"],
            key=f"add_uni_{t}_{i}")

    cands = filtrar_banco(texto=txt, padrao=pad, purpose=pur, unilateral=uni, max_cx=max_cx)
    cands = [e for e in cands if e.nome not in nomes_em_uso]

    ab1, ab2 = st.columns(2)
    with ab1:
        if st.button("🎲 Aleatório", key=f"add_alea_{t}_{i}", use_container_width=True,
                     help="Adiciona exercício aleatório com os filtros aplicados"):
            if cands:
                novo_ex = random.choice(cands)
                _aplicar_adicionar(t, i, novo_ex)
            st.rerun()
    with ab2:
        st.caption(f"{len(cands)} exercício(s) encontrado(s)")

    if cands:
        nomes_c = [f"{e.nome}  [{e.purpose} · {e.eq_primario}]" for e in cands[:50]]
        escolha = st.radio("Escolha o exercício", nomes_c, key=f"add_radio_{t}_{i}", label_visibility="collapsed")
        escolha_nome = escolha.split("  [")[0]
        if st.button("✅ Adicionar", type="primary", key=f"add_aplicar_{t}_{i}"):
            novo_ex = next((e for e in cands if e.nome == escolha_nome), None)
            if novo_ex:
                _aplicar_adicionar(t, i, novo_ex)
            st.rerun()
    elif txt or pad != "(qualquer)" or pur != "(qualquer)" or uni != "(qualquer)":
        st.caption("Nenhum exercício encontrado com esses filtros.")


def _aplicar_adicionar(t: int, i: int, novo_ex):
    """Insere novo_ex no próximo slot vazio do bloco i do treino t."""
    target = st.session_state.sessoes[t].blocos[i]
    if target.ex1 is None:
        target.ex1 = novo_ex
    elif target.ex2 is None:
        target.ex2 = novo_ex
    elif target.ex3 is None:
        target.ex3 = novo_ex
    # Fecha o painel
    st.session_state.add_ex_alvo.pop((t, i), None)
    st.session_state.add_ex_cands.pop((t, i), None)


def _render_painel_novo_bloco(t: int, sessao: Sessao, max_cx: int):
    """Painel para criar um novo bloco do zero."""
    nomes_em_uso = {
        ex.nome
        for bloco in sessao.blocos
        for ex in [bloco.ex1, bloco.ex2, bloco.ex3] if ex
    }

    st.markdown(
        "<div style='background:#f0f9ff;border:1px solid #7dd3fc;border-radius:10px;"
        "padding:12px 16px;margin:6px 0 8px 0'>"
        "<p style='font-size:12px;font-weight:700;color:#075985;margin:0 0 8px 0'>"
        "＋ Novo bloco</p></div>",
        unsafe_allow_html=True,
    )

    fn1, fn2, fn3, fn4 = st.columns([3, 2, 2, 2])
    with fn1:
        txt = st.text_input("Buscar por nome", key=f"nb_txt_{t}", placeholder="Digite para filtrar...")
    with fn2:
        pad = st.selectbox("Categoria", ["(qualquer)"] + sorted(PADROES_LABELS.keys()),
            key=f"nb_pad_{t}",
            format_func=lambda x: PADROES_LABELS.get(x, x) if x != "(qualquer)" else "Qualquer")
    with fn3:
        pur = st.selectbox("Purpose", ["(qualquer)", "compound", "isolation", "stability", "explosive"],
            key=f"nb_pur_{t}")
    with fn4:
        uni = st.selectbox("Lateralidade", ["(qualquer)", "bilateral", "unilateral"],
            key=f"nb_uni_{t}")

    cands = filtrar_banco(texto=txt, padrao=pad, purpose=pur, unilateral=uni, max_cx=max_cx)
    cands = [e for e in cands if e.nome not in nomes_em_uso]

    nb1, nb2 = st.columns(2)
    with nb1:
        if st.button("🎲 Bloco aleatório", key=f"nb_alea_{t}", use_container_width=True,
                     help="Cria bloco com 1 exercício aleatório dos filtros aplicados"):
            if cands:
                novo_ex = random.choice(cands)
                _aplicar_novo_bloco(t, sessao, novo_ex)
            st.rerun()
    with nb2:
        st.caption(f"{len(cands)} exercício(s) encontrado(s)")

    if cands:
        nomes_c = [f"{e.nome}  [{e.purpose} · {e.eq_primario}]" for e in cands[:50]]
        escolha = st.radio("Escolha o exercício", nomes_c, key=f"nb_radio_{t}", label_visibility="collapsed")
        escolha_nome = escolha.split("  [")[0]
        if st.button("✅ Criar bloco", type="primary", key=f"nb_aplicar_{t}"):
            novo_ex = next((e for e in cands if e.nome == escolha_nome), None)
            if novo_ex:
                _aplicar_novo_bloco(t, sessao, novo_ex)
            st.rerun()
    elif txt or pad != "(qualquer)" or pur != "(qualquer)" or uni != "(qualquer)":
        st.caption("Nenhum exercício encontrado com esses filtros.")


def _aplicar_novo_bloco(t: int, sessao: Sessao, novo_ex):
    """Cria novo SuperSerie com novo_ex como ex1 e adiciona ao treino t."""
    labels = "ABCDEFGHIJKLMNOP"
    novo_label = labels[len(sessao.blocos)] if len(sessao.blocos) < len(labels) else str(len(sessao.blocos) + 1)
    novo_bloco = SuperSerie(label=novo_label, ex1=novo_ex, ex2=None, ex3=None)
    st.session_state.sessoes[t].blocos.append(novo_bloco)
    st.session_state.novo_bloco_cands.pop(t, None)



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
                "Evitar similaridade entre treinos", value=False, key="variar_entre",
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

        # Botão ZIP quando há mais de 1 treino
        if n_sess > 1:
            ae_zip = st.session_state.get("aluno_exp", "Selecionar aluno...")
            if ae_zip and ae_zip != "Selecionar aluno...":
                lp = Path("logo.png")
                if not lp.exists(): lp = Path("logo.jpg")
                logo_b = lp.read_bytes() if lp.exists() else None
                zip_bytes = gerar_zip(sessoes, ae_zip, logo_b)
                st.download_button(
                    f"⬇ Baixar todos os treinos (ZIP)",
                    data=zip_bytes,
                    file_name=f"treinos_{ae_zip.lower().replace(' ','_')}.zip",
                    mime="application/zip",
                    use_container_width=True,
                    key="dl_zip",
                )
                st.markdown("<div style='margin-bottom:8px'></div>", unsafe_allow_html=True)

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
