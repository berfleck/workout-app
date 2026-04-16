# CLAUDE.md — BF Treinamento · Gerador de Treinos

Contexto permanente para o Claude Code. Atualizar sempre que houver decisões de arquitetura, novas funcionalidades ou mudanças relevantes.

---

## Visão geral

App Streamlit (Python) para personal trainer gerar, editar e exportar sessões de treino personalizadas. Roda localmente, sem servidor, sem nuvem. Todos os dados persistem em arquivos locais (JSON + XLSX).

---

## Estrutura de arquivos

```
app.py                  — UI principal (~1640 linhas), Streamlit
gerador_treino.py       — Lógica de geração de treinos (~1070 linhas)
gerar_imagem.py         — Exportação de PNG (fontes DejaVu embutidas)
banco_exercicios.xlsx   — Banco de dados de exercícios (aba "Exercícios")
alunos.json             — Cadastro de alunos (CRUD)
sessoes_salvas.json     — Snapshot das sessões ativas (restauração pós-timeout)
historico_treinos.json  — Histórico salvo manualmente pelo usuário
logo.png                — Logo usada nos PNGs exportados
DejaVuSans.ttf          — Fonte para geração de imagem
DejaVuSans-Bold.ttf     — Fonte bold para geração de imagem
requirements.txt        — Dependências Python
backup/                 — Cópias de segurança manuais de app.py e gerador_treino.py
```

---

## Estruturas de dados principais

### `Exercicio` (dataclass)
Campos do banco: `nome`, `variacao_de`, `eq_primario`, `eq_secundario`, `regiao`, `subregiao`, `padrao`, `purpose`, `unilateral`, `complexidade` (1-5), `fadiga` (1-5), `circuito`, `similaridade`, `musculo_primario`, `obs`
Campos de prescrição (definidos na UI): `series`, `reps` (str, ex: "8-12"), `rir` (0-4)

### `SuperSerie` (dataclass)
`label` (A/B/C...), `ex1`, `ex2` (opcional), `ex3` (opcional)

### `Sessao` (dataclass)
`tipo` (string de padrões concatenados), `blocos` (lista de SuperSerie)

### `alunos.json`
Lista de objetos: `{ nome, nivel, objetivo, restricoes, obs }`

### `historico_treinos.json`
Lista de registros: `{ id, data, aluno, etiqueta, n_treinos, sessoes[] }`

---

## Lógica de geração (`gerador_treino.py`)

### Hierarquia de classificação dos exercícios

Três níveis. Cada exercício pertence a UM padrão; padrão deriva subregião e região via mapeamento canônico.

| Região | Subregiões | Padrões |
|---|---|---|
| `upper` | peito | empurrar_compostos, empurrar_isolados |
| | costas | remadas, puxadas |
| | ombro | ombro_composto, ombro_isolado, posterior_ombro |
| | bracos | biceps, triceps |
| `lower` | perna_anterior | squat |
| | perna_posterior | hinge, knee_flexion, abduction |
| | adutores | adduction |
| | panturrilha | flexao_plantar |
| `core` | core | core_isometrico, core_dinamico |
| `cardio` | cardio | cardio |

Constantes em `gerador_treino.py`:
- `PADRAO_PARA_SUBREGIAO`, `SUBREGIAO_PARA_REGIAO` — mapeamentos canônicos (autoridade)
- `REGIAO_PARA_SUBREGIOES`, `SUBREGIAO_PARA_PADROES` — derivados automaticamente
- `PADROES_COMPOSTOS` — padrões priorizados na geração: `squat`, `hinge`, `empurrar_compostos`, `remadas`, `puxadas`, `ombro_composto`
- `PROPORCAO_COMPOSTOS = 0.6` — ao menos 60% compostos em demandas de nível região

Funções auxiliares de hierarquia:
- `expandir_para_padroes(regioes, subregioes, padroes)` — recebe seleções de qualquer nível e retorna lista plana de padrões (usada pelo `gerar_sessao()` legado e pelos templates)
- `_padroes_de_escopo(nivel, escopo)` — retorna padrões de um escopo (região/subregião/padrão)
- `_ordenar_padroes_por_prioridade(padroes)` — compostos primeiro, depois isolados; **embaralhado aleatoriamente** dentro de cada grupo para evitar viés determinístico

### Dois modos de geração

**1. `gerar_sessao()` (modo legado, usado por Templates)**
Recebe lista plana de padrões + `exercicios_por_padrao` (EPP). Seleciona N exercícios de cada padrão fixo.

**2. `gerar_sessao_por_demandas()` (modo principal, usado pelo modo Hierarquia)**
Recebe lista de **demandas** `[(nivel, escopo, quantidade)]`. Para cada demanda:
- Lista todos os padrões do escopo
- Se nível = "regiao" e o escopo tem compostos E isolados: aplica regra de proporção (`PROPORCAO_COMPOSTOS = 0.6`). Preenche compostos primeiro (ciclando equilibradamente), depois isolados.
- Se nível = "subregiao" ou "padrao": sem proporção forçada, Opção C pura (1 de cada padrão antes de repetir, compostos primeiro).
- Dentro de cada grupo de prioridade, a ordem dos padrões é **aleatória** a cada geração.

### Fluxo principal (comum a ambos os modos)
1. `gerar_sessao()` — seleciona exercícios por padrão respeitando similaridade, depois chama `montar_blocos()`
2. `selecionar_sem_repeticao_similaridade()` — evita repetir grupos de similaridade; relaxa a regra se não houver candidatos suficientes
3. `ordenar_compostos_primeiro()` — compostos por fadiga desc, depois o resto por fadiga desc
4. `montar_blocos()` — distribui exercícios em blocos via helper `_buscar_candidato()` com 4 níveis de prioridade:
   - P1: região diferente **E** padrão diferente (ideal)
   - P2: região diferente
   - P3: padrão diferente
   - P4: qualquer válido (respeitando regra de fadiga)
   - Em blocos de **2 exercícios**: faz uma passagem extra antes das prioridades tentando evitar 2 exercícios unilaterais no mesmo bloco (blocos de 3 ignoram essa regra)
5. `gerar_multiplos_treinos()` — gera N sessões com três camadas de bloqueio entre treinos:
   - `nomes_globais`: bloqueia nomes exatos já usados (sempre ativo)
   - `variacao_pais_globais`: bloqueia variações de exercícios usados via campo `variacao_de` (sempre ativo, bidirecional — se "V-up" foi usado bloqueia "V-up unilateral" e vice-versa)
   - `sims_globais`: bloqueia grupos de similaridade (só quando "Evitar similaridade entre treinos" está ativo)

### Regra de fadiga
`FADIGA_MAX_PAR = 4` — exercícios com fadiga ≥ 4 são "alta fadiga".
Blocos de 1-2 exercícios: máx 1 alta fadiga. Blocos de 3: máx 2 alta fadiga.

---

## Funcionalidades atuais (`app.py`)

### Aba Treinos
- Configuração via **Hierarquia** (modo padrão) ou **Template** pré-definido
- **Modo Hierarquia** (expansível em 3 níveis: Região → Subregião → Padrão):
  - Cada região tem checkbox + toggle "refinar". Marcar pai = atalho (Comportamento A): se filhos específicos forem marcados, apenas eles valem; senão, o pai expande para todos os filhos
  - Permite mistura livre de níveis (ex: "Membros superiores=4 + Pernas posterior=2")
  - **1 slider por checkbox marcado** — o slider define a quantidade total de exercícios daquele escopo (não 1 slider por padrão filho)
  - Defaults: região=6, subregião=2, padrão=1
  - Usa `gerar_sessao_por_demandas()` internamente, com regra de proporção 60% compostos para demandas de região
- **Modo Template**: templates pré-definidos com 1 slider por padrão do template. Usa `gerar_sessao()` legado
- Opções gerais: nº de treinos (1-5), exercícios por bloco (1/2/3), complexidade máxima, evitar similaridade entre treinos
- **Exercícios fixos** (por treino): expander "📌 Exercícios fixos" no painel de config; até 3 exercícios garantidos por treino; busca por nome + radio + botão Fixar; chave session_state `fixos_{t}` (lista de nomes); passados como `exercicios_travados` para `gerar_sessao` / `gerar_sessao_por_demandas`
- Botão **Gerar treinos** → gera e exibe sessões
- Botão **Resetar** → desmarca todas as seleções (prefixos `reg_`, `sub_`, `pad_`, `reg_exp_`, `sub_exp_`, `qtd_`, `epp_`), limpa sliders e exercícios fixos
- Por sessão: **Baixar PNG**, **Regerar** (detecta automaticamente se config usa demandas ou padrões; respeita exercícios dos outros treinos, incluindo regra `variacao_de`), **Editar/Visualizar**
- ZIP com todos os treinos (quando há mais de 1 e aluno selecionado)
- Salvar no histórico (com etiqueta opcional)
- Restauração automática de sessão após timeout do browser (via `sessoes_salvas.json`)

### Modo Editar (por sessão)
- Reordenar blocos (↑↓)
- Deletar bloco inteiro
- Por exercício: substituir (↺), mover para outro bloco (↗), remover (✕)
- Painel de substituição inline com filtros (nome, categoria, purpose, lateralidade, equipamento, músculo)
- Painel de adição de exercício a um bloco existente
- Painel de novo bloco do zero
- Edição de prescrição inline (séries × reps × RIR) com salvar individual

### Aba Alunos
- CRUD completo: nome, nível, objetivo, restrições, observações
- Dados persistidos em `alunos.json`

### Aba Histórico
- Lista registros salvos com data, aluno/turma, nº de treinos
- Expandir para ver exercícios do registro
- Carregar registro para edição na aba Treinos
- Apagar registro

---

## Decisões técnicas e convenções

- **Framework:** Streamlit (versão 1.56.0 no ambiente do usuário)
- **Persistência:** JSON puro (sem banco de dados por enquanto — ver Roadmap)
- **Exportação:** PNG gerado via Pillow com fontes DejaVu embutidas
- **Reset de widgets Streamlit:** usar flag `_do_reset` no session_state processada no início do script (antes de qualquer widget renderizar), pois deletar chaves de checkbox não reseta o browser — é necessário setar `= False` explicitamente antes da renderização
- **Sem sidebar:** sidebar escondida via CSS; layout max-width 960px
- **Cores:** laranja primário `#e85d04`, fundo cinza claro `#f9fafb`
- **Fonte UI:** DM Sans (Google Fonts)

---

## Roadmap / Funcionalidades futuras planejadas

> Estas são direções discutidas mas **ainda não implementadas**.

### Periodização e histórico por aluno (próxima grande feature)

**Problema a resolver:** hoje o aluno é só um nome para o PNG. A ideia é torná-lo a entidade central do app.

**O que precisaria mudar:**

1. **Alunos e Turmas como entidade central**
   - Abrir um aluno/turma → ver histórico de treinos → gerar o próximo a partir daí
   - "Turma" = grupo de alunos que treina junto e recebe o mesmo programa

2. **Histórico vinculado ao aluno/turma**
   - Ao salvar, associar o registro a um aluno/turma específica (não só etiqueta livre)
   - Linha do tempo de treinos por aluno

3. **Geração inteligente com base no histórico**
   - Ao gerar, ler os últimos N treinos do aluno e passar exercícios já usados como bloqueados para `gerar_multiplos_treinos()`
   - Configuração: "evitar exercícios dos últimos X treinos" (controle do grau de variação entre períodos)

4. **Lista de exercícios pausados por aluno**
   - Exercícios "pausados" por lesão, preferência ou equipamento indisponível
   - App respeita automaticamente ao gerar (extensão natural dos `exercicios_travados`)

**Decisão arquitetural pendente:** continuar com **JSON** ou migrar para **SQLite**?
- SQLite facilita consultas como "todos os exercícios usados pelo aluno X nos últimos 30 dias"
- Para volume de um personal trainer (dezenas de alunos), SQLite é mais que suficiente
- SQLite ainda é um arquivo único na pasta do projeto — sem servidor, sem nuvem
- JSON ainda é possível mas começa a ficar trabalhoso para queries de histórico

**→ Decisão a tomar antes de implementar esta feature.**

---

## Como rodar

```bash
cd "g:/My Drive/Projeto Workout App"
streamlit run app.py
```
