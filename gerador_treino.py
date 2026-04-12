"""
Gerador de Treinos — lógica central
Lê o banco de exercícios (.xlsx) e gera sessões respeitando as regras definidas.

Uso:
    python gerador_treino.py
"""

import math
import pandas as pd
import random
from dataclasses import dataclass, field
from typing import Optional

# ---------------------------------------------------------------------------
# Constantes
# ---------------------------------------------------------------------------

XLSX_PATH = "banco_exercicios.xlsx"

TEMPLATES = {
    "Push + Hip":       ["horizontal_push", "vertical_push", "hinge", "core"],
    "Pull + Knee":      ["horizontal_pull", "vertical_pull", "squat", "core"],
    "Full Body":        ["horizontal_push", "horizontal_pull", "squat", "hinge", "core"],
    "Push + Bíceps":    ["horizontal_push", "vertical_push", "biceps", "core"],
    "Pull + Tríceps":   ["horizontal_pull", "vertical_pull", "triceps", "core"],
    "Pull + Core":      ["horizontal_pull", "vertical_pull", "core"],
    "Upper Body":       ["horizontal_push", "vertical_push", "horizontal_pull", "vertical_pull"],
    "Lower Body":       ["squat", "hinge", "abduction", "core"],
    "Braços":           ["biceps", "triceps", "core"],
    "Cardio + Força":   ["cardio", "squat", "hinge", "horizontal_push"],
    "Glúteos + Quadril":["hinge", "abduction", "adduction", "core"],
}

EXERCICIOS_POR_PADRAO = {
    "horizontal_push": 2,
    "horizontal_pull": 2,
    "vertical_push":   1,
    "vertical_pull":   2,
    "squat":           2,
    "hinge":           2,
    "core":            2,
    "cardio":          1,
    "biceps":          2,
    "triceps":         2,
    "flexao_plantar":     2,
    "abduction":       2,
    "adduction":       2,
}

# Não parear dois exercícios com fadiga >= este valor no mesmo bloco
FADIGA_MAX_PAR = 4


# ---------------------------------------------------------------------------
# Estruturas de dados
# ---------------------------------------------------------------------------

@dataclass
class Exercicio:
    nome: str
    variacao_de: Optional[str]
    eq_primario: str
    eq_secundario: Optional[str]
    regiao: str
    padrao: str
    purpose: str
    unilateral: str
    complexidade: int
    fadiga: int
    circuito: str
    similaridade: str
    musculo_primario: str
    obs: Optional[str]


@dataclass
class SuperSerie:
    label: str
    ex1: Exercicio
    ex2: Optional[Exercicio]


@dataclass
class Sessao:
    tipo: str
    blocos: list[SuperSerie] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Carregamento do banco
# ---------------------------------------------------------------------------

def _str(val) -> str:
    if val is None:
        return ""
    try:
        if math.isnan(float(val)):
            return ""
    except (TypeError, ValueError):
        pass
    return str(val).strip()


_EQ_FIXES = {
    "Apoio":           "Sem equipamento",
    "Apoio ajoelhado": "Sem equipamento",
    "Apoio elevado":   "Sem equipamento",
    "Remada trx":      "TRX",
}


def carregar_banco(path: str) -> list[Exercicio]:
    df = pd.read_excel(path, sheet_name="Exercícios")
    df = df.where(pd.notna(df), None)
    exercicios = []
    for _, row in df.iterrows():
        nome = _str(row.get("nome"))
        if not nome:
            continue
        eq_pri = _str(row.get("eq_primario")) or _EQ_FIXES.get(nome, "")
        exercicios.append(Exercicio(
            nome=nome,
            variacao_de=_str(row.get("variacao_de")) or None,
            eq_primario=eq_pri,
            eq_secundario=_str(row.get("eq_secundario")) or None,
            regiao=_str(row.get("regiao")),
            padrao=_str(row.get("padrao")),
            purpose=_str(row.get("purpose")),
            unilateral=_str(row.get("unilateral")),
            complexidade=int(row.get("complexidade") if row.get("complexidade") and not (isinstance(row.get("complexidade"), float) and math.isnan(row.get("complexidade"))) else 1),
            fadiga=int(row.get("fadiga") if row.get("fadiga") and not (isinstance(row.get("fadiga"), float) and math.isnan(row.get("fadiga"))) else 1),
            circuito=_str(row.get("circuito")) or "não",
            similaridade=_str(row.get("similaridade")),
            musculo_primario=_str(row.get("musculo_primario")),
            obs=_str(row.get("obs")) or None,
        ))
    return exercicios


# ---------------------------------------------------------------------------
# Filtros
# ---------------------------------------------------------------------------

def filtrar_por_padrao(banco: list[Exercicio], padrao: str) -> list[Exercicio]:
    return [e for e in banco if e.padrao == padrao]


def filtrar_por_equipamentos(
    banco: list[Exercicio],
    equipamentos_bloqueados: list[str],
) -> list[Exercicio]:
    if not equipamentos_bloqueados:
        return banco
    return [e for e in banco if e.eq_primario not in equipamentos_bloqueados]


def filtrar_por_complexidade(
    banco: list[Exercicio],
    max_complexidade: int,
) -> list[Exercicio]:
    return [e for e in banco if e.complexidade <= max_complexidade]


# ---------------------------------------------------------------------------
# Ordenação: compostos antes de todo o resto
# ---------------------------------------------------------------------------

def ordenar_compostos_primeiro(exercicios: list[Exercicio]) -> list[Exercicio]:
    """
    Compostos vêm primeiro. Dentro de cada grupo (compound vs resto),
    ordena por fadiga decrescente para os mais pesados abrirem o bloco.
    """
    compostos = [e for e in exercicios if e.purpose == "compound"]
    resto     = [e for e in exercicios if e.purpose != "compound"]
    compostos.sort(key=lambda e: e.fadiga, reverse=True)
    resto.sort(key=lambda e: e.fadiga, reverse=True)
    return compostos + resto


# ---------------------------------------------------------------------------
# Regra de similaridade
# ---------------------------------------------------------------------------

def selecionar_sem_repeticao_similaridade(
    candidatos: list[Exercicio],
    similaridades_usadas: set[str],
    variacao_pais_usados: set[str],
    n: int,
) -> list[Exercicio]:
    """
    Seleciona até n exercícios evitando repetir grupos de similaridade.
    Se não houver candidatos suficientes respeitando a regra, relaxa:
    permite repetir grupos de similaridade para completar n exercícios,
    mas nunca repete o mesmo exercício.
    """
    nomes_usados: set[str] = set()

    def _selecionar(pool, respeitar_sim):
        selecionados = []
        sims_desta_selecao = set()
        random.shuffle(pool)
        for e in pool:
            if e.nome in nomes_usados:
                continue
            sim_ok = (not respeitar_sim) or (
                e.similaridade not in similaridades_usadas
                and e.similaridade not in sims_desta_selecao
            )
            var_ok = e.variacao_de is None or e.variacao_de not in variacao_pais_usados
            if sim_ok and var_ok:
                selecionados.append(e)
                sims_desta_selecao.add(e.similaridade)
                nomes_usados.add(e.nome)
            if len(selecionados) >= n:
                break
        return selecionados

    # Tentativa 1: respeitar similaridade
    resultado = _selecionar(list(candidatos), respeitar_sim=True)

    # Se não completou n, relaxar regra de similaridade
    if len(resultado) < n:
        restantes = [e for e in candidatos if e.nome not in nomes_usados]
        resultado += _selecionar(restantes, respeitar_sim=False)

    return resultado[:n]


# ---------------------------------------------------------------------------
# Pareamento em super séries
# ---------------------------------------------------------------------------

def pode_parear(ex1: Exercicio, ex2: Exercicio) -> bool:
    if ex1.fadiga >= FADIGA_MAX_PAR and ex2.fadiga >= FADIGA_MAX_PAR:
        return False
    return True


def montar_pares(exercicios: list[Exercicio]) -> list[tuple]:
    """
    Pareia em super séries priorizando regiões diferentes.
    Retorna lista de (ex1, ex2) ou (ex1, None) se sobrar ímpar.
    """
    if not exercicios:
        return []

    usados = [False] * len(exercicios)
    pares = []

    for i in range(len(exercicios)):
        if usados[i]:
            continue
        pareado = False
        # Prioridade 1: região diferente
        for j in range(i + 1, len(exercicios)):
            if usados[j]:
                continue
            if exercicios[i].regiao != exercicios[j].regiao and pode_parear(exercicios[i], exercicios[j]):
                pares.append((exercicios[i], exercicios[j]))
                usados[i] = usados[j] = True
                pareado = True
                break
        # Prioridade 2: qualquer parceiro válido
        if not pareado:
            for j in range(i + 1, len(exercicios)):
                if usados[j]:
                    continue
                if pode_parear(exercicios[i], exercicios[j]):
                    pares.append((exercicios[i], exercicios[j]))
                    usados[i] = usados[j] = True
                    pareado = True
                    break
        if not pareado:
            pares.append((exercicios[i], None))
            usados[i] = True

    return pares


# ---------------------------------------------------------------------------
# Substituição pontual de exercício
# ---------------------------------------------------------------------------

def substituir_exercicio(
    sessao: Sessao,
    nome_atual: str,
    banco: list[Exercicio],
    equipamentos_bloqueados: Optional[list[str]] = None,
    max_complexidade: int = 5,
) -> Sessao:
    """
    Substitui um exercício específico na sessão por outro do mesmo padrão
    e grupo de similaridade diferente dos já usados.

    Args:
        sessao: sessão atual
        nome_atual: nome do exercício a substituir
        banco: banco completo de exercícios
        equipamentos_bloqueados: equipamentos indisponíveis
        max_complexidade: complexidade máxima permitida

    Returns:
        Sessao atualizada com o exercício substituído
    """
    eq_bloq = equipamentos_bloqueados or []

    # Encontrar o exercício a substituir e seu contexto
    exercicio_alvo = None
    bloco_idx = None
    posicao = None  # "ex1" ou "ex2"

    for i, bloco in enumerate(sessao.blocos):
        if bloco.ex1.nome == nome_atual:
            exercicio_alvo = bloco.ex1
            bloco_idx = i
            posicao = "ex1"
            break
        if bloco.ex2 and bloco.ex2.nome == nome_atual:
            exercicio_alvo = bloco.ex2
            bloco_idx = i
            posicao = "ex2"
            break

    if exercicio_alvo is None:
        print(f"  [!] Exercício '{nome_atual}' não encontrado na sessão.")
        return sessao

    # Similaridades já em uso (excluindo o exercício alvo)
    sims_em_uso = set()
    for i, bloco in enumerate(sessao.blocos):
        if bloco.ex1.nome != nome_atual:
            sims_em_uso.add(bloco.ex1.similaridade)
        if bloco.ex2 and bloco.ex2.nome != nome_atual:
            sims_em_uso.add(bloco.ex2.similaridade)

    # Nomes já em uso na sessão
    nomes_em_uso = set()
    for bloco in sessao.blocos:
        nomes_em_uso.add(bloco.ex1.nome)
        if bloco.ex2:
            nomes_em_uso.add(bloco.ex2.nome)
    nomes_em_uso.discard(nome_atual)

    # Buscar substituto: mesmo padrão, similaridade não usada
    candidatos = filtrar_por_padrao(banco, exercicio_alvo.padrao)
    candidatos = filtrar_por_equipamentos(candidatos, eq_bloq)
    candidatos = filtrar_por_complexidade(candidatos, max_complexidade)
    candidatos = [
        e for e in candidatos
        if e.nome not in nomes_em_uso
        and e.similaridade not in sims_em_uso
    ]

    if not candidatos:
        # Relaxa regra de similaridade se não encontrar nada
        candidatos = filtrar_por_padrao(banco, exercicio_alvo.padrao)
        candidatos = filtrar_por_equipamentos(candidatos, eq_bloq)
        candidatos = filtrar_por_complexidade(candidatos, max_complexidade)
        candidatos = [e for e in candidatos if e.nome not in nomes_em_uso]

    if not candidatos:
        print(f"  [!] Nenhum substituto encontrado para '{nome_atual}'.")
        return sessao

    substituto = random.choice(candidatos)

    # Aplicar substituição
    import copy
    nova_sessao = copy.deepcopy(sessao)
    bloco = nova_sessao.blocos[bloco_idx]
    if posicao == "ex1":
        bloco.ex1 = substituto
    else:
        bloco.ex2 = substituto

    print(f"  [✓] '{nome_atual}' substituído por '{substituto.nome}'")
    return nova_sessao


# ---------------------------------------------------------------------------
# Geração da sessão
# ---------------------------------------------------------------------------

def gerar_sessao(
    banco: list[Exercicio],
    padroes: list[str],
    exercicios_por_padrao: Optional[dict] = None,
    equipamentos_bloqueados: Optional[list[str]] = None,
    max_complexidade: int = 5,
    variacao_pais_usados: Optional[set] = None,
    exercicios_travados: Optional[list[Exercicio]] = None,
) -> Sessao:
    epp      = exercicios_por_padrao or EXERCICIOS_POR_PADRAO
    eq_bloq  = equipamentos_bloqueados or []
    var_pais = variacao_pais_usados or set()
    travados = exercicios_travados or []

    similaridades_usadas: set[str] = set()
    todos_selecionados: list[Exercicio] = []

    # Exercícios travados entram primeiro
    for e in travados:
        todos_selecionados.append(e)
        similaridades_usadas.add(e.similaridade)

    # Selecionar por padrão
    nomes_travados = {e.nome for e in travados}
    for padrao in padroes:
        n = epp.get(padrao, 1)
        candidatos = filtrar_por_padrao(banco, padrao)
        candidatos = filtrar_por_equipamentos(candidatos, eq_bloq)
        candidatos = filtrar_por_complexidade(candidatos, max_complexidade)
        candidatos = [e for e in candidatos if e.nome not in nomes_travados]

        selecionados = selecionar_sem_repeticao_similaridade(
            candidatos, similaridades_usadas, var_pais, n
        )
        for e in selecionados:
            similaridades_usadas.add(e.similaridade)
        todos_selecionados.extend(selecionados)

    # Ordenar: compostos primeiro, depois o resto
    todos_selecionados = ordenar_compostos_primeiro(todos_selecionados)

    # Parear em super séries
    pares = montar_pares(todos_selecionados)

    # Montar blocos
    labels = "ABCDEFGH"
    blocos = []
    for i, (ex1, ex2) in enumerate(pares):
        label = labels[i] if i < len(labels) else str(i + 1)
        blocos.append(SuperSerie(label=label, ex1=ex1, ex2=ex2))

    tipo = " + ".join(padroes)
    return Sessao(tipo=tipo, blocos=blocos)


# ---------------------------------------------------------------------------
# Impressão
# ---------------------------------------------------------------------------

def imprimir_sessao(sessao: Sessao):
    print("=" * 60)
    print(f"  SESSÃO: {sessao.tipo}")
    print("=" * 60)
    for bloco in sessao.blocos:
        print(f"\n  Bloco {bloco.label}")
        ex = bloco.ex1
        eq = ex.eq_primario + (f" + {ex.eq_secundario}" if ex.eq_secundario else "")
        print(f"  {bloco.label}1 — {ex.nome}  [{ex.purpose} | fd:{ex.fadiga} | cx:{ex.complexidade}]")
        print(f"       Equip: {eq}" + (f"  |  {ex.obs}" if ex.obs else ""))
        if bloco.ex2:
            ex = bloco.ex2
            eq = ex.eq_primario + (f" + {ex.eq_secundario}" if ex.eq_secundario else "")
            print(f"  {bloco.label}2 — {ex.nome}  [{ex.purpose} | fd:{ex.fadiga} | cx:{ex.complexidade}]")
            print(f"       Equip: {eq}" + (f"  |  {ex.obs}" if ex.obs else ""))
        else:
            print(f"  {bloco.label}2 — (exercício isolado)")
    print()


# ---------------------------------------------------------------------------
# Demo
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    random.seed()

    banco = carregar_banco(XLSX_PATH)
    print(f"Banco carregado: {len(banco)} exercícios\n")

    # --- Exemplo 1: Push + Hip (compostos primeiro) ---
    print(">>> Exemplo 1: Push + Hip")
    sessao = gerar_sessao(banco, TEMPLATES["Push + Hip"])
    imprimir_sessao(sessao)

    # --- Exemplo 2: Full Body, complexidade máx. 3 ---
    print(">>> Exemplo 2: Full Body — aluno iniciante (cx ≤ 3)")
    sessao = gerar_sessao(banco, TEMPLATES["Full Body"], max_complexidade=3)
    imprimir_sessao(sessao)

    # --- Exemplo 3: substituição pontual ---
    print(">>> Exemplo 3: Pull + Knee com substituição pontual")
    sessao = gerar_sessao(banco, TEMPLATES["Pull + Knee"])
    imprimir_sessao(sessao)
    # Pega o nome do primeiro exercício do bloco A para substituir
    nome_para_substituir = sessao.blocos[0].ex1.nome
    print(f"  Substituindo '{nome_para_substituir}'...")
    sessao = substituir_exercicio(sessao, nome_para_substituir, banco)
    print("  Sessão após substituição:")
    imprimir_sessao(sessao)

    # --- Exemplo 4: exercício travado ---
    print(">>> Exemplo 4: Pull + Knee com Agachamento livre travado")
    travado = next(e for e in banco if e.nome == "Agachamento livre")
    sessao = gerar_sessao(banco, TEMPLATES["Pull + Knee"], exercicios_travados=[travado])
    imprimir_sessao(sessao)

    # --- Exemplo 5: equipamento bloqueado ---
    print(">>> Exemplo 5: Push + Hip sem Crossover")
    sessao = gerar_sessao(banco, TEMPLATES["Push + Hip"], equipamentos_bloqueados=["Crossover"])
    imprimir_sessao(sessao)


# ---------------------------------------------------------------------------
# Busca filtrada de substitutos (escolha manual)
# ---------------------------------------------------------------------------

def buscar_substitutos(
    sessao: Sessao,
    nome_atual: str,
    banco: list[Exercicio],
    padrao: Optional[str] = None,
    regiao: Optional[str] = None,
    purpose: Optional[str] = None,
    unilateral: Optional[str] = None,
    similaridade: Optional[str] = None,
    max_complexidade: int = 5,
    max_fadiga: int = 5,
    equipamentos_bloqueados: Optional[list[str]] = None,
    ignorar_similaridade_usada: bool = False,
) -> list[Exercicio]:
    """
    Retorna lista de candidatos filtrados para substituir um exercício na sessão.
    Você escolhe qual usar e passa para substituir_exercicio_por().

    Filtros disponíveis (todos opcionais):
        padrao               ex: "vertical_pull"
        regiao               ex: "upper", "lower", "core"
        purpose              ex: "compound", "isolation", "stability", "explosive"
        unilateral           ex: "unilateral", "bilateral"
        similaridade         ex: "vertical_pull_compound"
        max_complexidade     ex: 3  (só exercícios com cx <= 3)
        max_fadiga           ex: 3  (só exercícios com fd <= 3)
        equipamentos_bloqueados  ex: ["Crossover"]
        ignorar_similaridade_usada  True = mostra todos, mesmo que similaridade já esteja na sessão
    """
    eq_bloq = equipamentos_bloqueados or []

    # Nomes e similaridades já em uso na sessão (excluindo o alvo)
    nomes_em_uso = set()
    sims_em_uso = set()
    for bloco in sessao.blocos:
        for ex in [bloco.ex1, bloco.ex2]:
            if ex and ex.nome != nome_atual:
                nomes_em_uso.add(ex.nome)
                sims_em_uso.add(ex.similaridade)

    candidatos = list(banco)

    # Filtros
    if padrao:
        candidatos = [e for e in candidatos if e.padrao == padrao]
    if regiao:
        candidatos = [e for e in candidatos if e.regiao == regiao]
    if purpose:
        candidatos = [e for e in candidatos if e.purpose == purpose]
    if unilateral:
        candidatos = [e for e in candidatos if e.unilateral == unilateral]
    if similaridade:
        candidatos = [e for e in candidatos if e.similaridade == similaridade]
    if eq_bloq:
        candidatos = [e for e in candidatos if e.eq_primario not in eq_bloq]

    candidatos = [e for e in candidatos if e.complexidade <= max_complexidade]
    candidatos = [e for e in candidatos if e.fadiga <= max_fadiga]
    candidatos = [e for e in candidatos if e.nome not in nomes_em_uso]

    if not ignorar_similaridade_usada:
        candidatos = [e for e in candidatos if e.similaridade not in sims_em_uso]

    candidatos.sort(key=lambda e: (e.purpose != "compound", e.fadiga * -1, e.nome))
    return candidatos


def substituir_exercicio_por(
    sessao: Sessao,
    nome_atual: str,
    nome_substituto: str,
    banco: list[Exercicio],
) -> Sessao:
    """
    Substitui nome_atual por nome_substituto na sessão.
    Use após buscar_substitutos() para confirmar a escolha.
    """
    import copy
    substituto = next((e for e in banco if e.nome == nome_substituto), None)
    if substituto is None:
        print(f"  [!] '{nome_substituto}' não encontrado no banco.")
        return sessao

    nova_sessao = copy.deepcopy(sessao)
    for bloco in nova_sessao.blocos:
        if bloco.ex1.nome == nome_atual:
            bloco.ex1 = substituto
            print(f"  [✓] '{nome_atual}' → '{nome_substituto}'")
            return nova_sessao
        if bloco.ex2 and bloco.ex2.nome == nome_atual:
            bloco.ex2 = substituto
            print(f"  [✓] '{nome_atual}' → '{nome_substituto}'")
            return nova_sessao

    print(f"  [!] '{nome_atual}' não encontrado na sessão.")
    return sessao


def listar_candidatos(candidatos: list[Exercicio]):
    """Imprime a lista de candidatos retornada por buscar_substitutos()."""
    if not candidatos:
        print("  Nenhum candidato encontrado com esses filtros.")
        return
    print(f"  {len(candidatos)} candidato(s) encontrado(s):\n")
    for i, e in enumerate(candidatos, 1):
        eq = e.eq_primario + (f" + {e.eq_secundario}" if e.eq_secundario else "")
        print(f"  {i:2}. {e.nome}")
        print(f"       [{e.purpose} | {e.padrao} | {e.unilateral} | fd:{e.fadiga} | cx:{e.complexidade}]")
        print(f"       Equip: {eq}" + (f"  |  {e.obs}" if e.obs else ""))


# ---------------------------------------------------------------------------
# Demo
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    random.seed()

    banco = carregar_banco(XLSX_PATH)
    print(f"Banco carregado: {len(banco)} exercícios\n")

    # --- Exemplo 1: Push + Hip ---
    print(">>> Exemplo 1: Push + Hip")
    sessao = gerar_sessao(banco, TEMPLATES["Push + Hip"])
    imprimir_sessao(sessao)

    # --- Exemplo 2: Full Body, iniciante ---
    print(">>> Exemplo 2: Full Body — aluno iniciante (cx ≤ 3)")
    sessao = gerar_sessao(banco, TEMPLATES["Full Body"], max_complexidade=3)
    imprimir_sessao(sessao)

    # --- Exemplo 3: substituição aleatória ---
    print(">>> Exemplo 3: Pull + Knee com substituição aleatória")
    sessao = gerar_sessao(banco, TEMPLATES["Pull + Knee"])
    imprimir_sessao(sessao)
    nome_sub = sessao.blocos[0].ex1.nome
    print(f"  Substituindo '{nome_sub}'...")
    sessao = substituir_exercicio(sessao, nome_sub, banco)
    print("  Sessão após substituição:")
    imprimir_sessao(sessao)

    # --- Exemplo 4: exercício travado ---
    print(">>> Exemplo 4: Pull + Knee com Agachamento livre travado")
    travado = next(e for e in banco if e.nome == "Agachamento livre")
    sessao = gerar_sessao(banco, TEMPLATES["Pull + Knee"], exercicios_travados=[travado])
    imprimir_sessao(sessao)

    # --- Exemplo 5: equipamento bloqueado ---
    print(">>> Exemplo 5: Push + Hip sem Crossover")
    sessao = gerar_sessao(banco, TEMPLATES["Push + Hip"], equipamentos_bloqueados=["Crossover"])
    imprimir_sessao(sessao)

    # --- Exemplo 6: busca filtrada + substituição manual ---
    print(">>> Exemplo 6: Pull + Knee com substituição manual via filtros")
    sessao6 = gerar_sessao(banco, TEMPLATES["Pull + Knee"])
    imprimir_sessao(sessao6)

    nome_sub6 = sessao6.blocos[0].ex1.nome
    print(f"  Quero substituir: '{nome_sub6}'")
    print(f"  Filtros: vertical_pull + bilateral\n")

    candidatos6 = buscar_substitutos(
        sessao6,
        nome_atual=nome_sub6,
        banco=banco,
        padrao="vertical_pull",
        unilateral="bilateral",
        ignorar_similaridade_usada=True,
    )
    listar_candidatos(candidatos6)

    if candidatos6:
        escolhido = candidatos6[0].nome
        print(f"\n  Escolhido: '{escolhido}'")
        sessao6 = substituir_exercicio_por(sessao6, nome_sub6, escolhido, banco)
        print("  Sessão após substituição manual:")
        imprimir_sessao(sessao6)
