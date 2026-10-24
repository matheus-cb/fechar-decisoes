# Formato do decisoes.json

Um arquivo por `id`: pontos, escolhas e histórico juntos. Exemplo fictício e neutro:

```json
{
  "versao": 1,
  "meta": {
    "id": "exportacao-v2",
    "titulo": "Decisões da exportação de relatórios",
    "fontes": ["docs/plano.md"],
    "escopo": "Etapa 2",
    "raiz": "c:/projetos/app-relatorios",
    "criado": "2026-01-15T10:00",
    "atualizado": "2026-01-15T10:40",
    "auditoria": "1 passada: 2 correções"
  },
  "camadas": [ { "id": "exportar", "nome": "Exportação" } ],
  "pontos": [
    {
      "id": "D-03",
      "camada": "exportar",
      "titulo": "Formato da exportação",
      "pergunta": "Em que formato o relatório exportado deve sair?",
      "situacao": "decisao",
      "tipo": 1,
      "contexto": "O plano pede exportação para quem usa planilha e para a integração.",
      "fontes": [ { "ref": "docs/plano.md:42", "trecho": "exportar para planilha e integração" } ],
      "opcoes": [
        { "nome": "CSV", "favor": "Abre direto em planilha.", "contra": "Perde a estrutura aninhada." },
        { "nome": "JSON", "favor": "Mantém a estrutura para a integração.", "contra": "Quem usa planilha não abre direto." },
        { "nome": "Os dois, escolhidos na tela", "favor": "Atende os dois públicos.", "contra": "Dois formatos para testar e manter.", "origem": "proposta" }
      ],
      "rec": {
        "opcao": 0,
        "porque": "O plano põe a planilha como uso principal.",
        "fontes": [ { "ref": "docs/plano.md:44", "trecho": "uso principal: planilha" } ]
      },
      "sem": "A exportação fica sem formato e não é implementada.",
      "depende_de": [],
      "registro": {
        "escolha": 0, "texto": null, "obs": "Revisar se a integração pedir JSON.",
        "quem": "interlocutor", "origem": "interlocutor",
        "data": "2026-01-15T10:40", "status": "aceito"
      }
    }
  ],
  "resolvidos": [
    {
      "id": "Q-01", "titulo": "Codificação do arquivo",
      "resposta": "UTF-8, já definido no módulo de arquivos.",
      "fontes": [ { "ref": "src/arquivos.py:12", "trecho": "encoding=\"utf-8\"" } ]
    }
  ],
  "historico": [
    { "data": "2026-01-15T10:40", "ponto": "D-03", "evento": "registrado: CSV (aceito)" }
  ]
}
```

## Campos do ponto

| Campo | Obrigatório | Regra |
|---|---|---|
| `id` | sim | Único. Mantém o ID da fonte (D-03, Q-07) |
| `camada` | se houver `camadas` | Um `id` de `camadas` |
| `titulo`, `pergunta` | sim | Pergunta respondível, terminada em `?` |
| `situacao` | sim | `decisao` (escolher antes de implementar) · `validar` (tem resposta, falta confirmar) · `externo` (depende de alguém ou algo fora da sessão) |
| `tipo` | sim | 1 difícil de desfazer · 2 reversível |
| `contexto` | sim | Só fatos cobertos por `fontes`; sem fonte, diga "sem fonte" ou que é preferência |
| `fontes` | não | Lista de `{ref, trecho}`. Vazia é permitida: preferência não precisa de fonte |
| `opcoes` | sim | 2 a 4, nomes distintos, cada uma com `favor` e `contra` concretos. Sem base na fonte: `"origem": "proposta"` |
| `rec` | quando houver fonte | `{opcao, porque, fontes}` com `opcao` = índice a partir de 0 e `fontes` não vazia. `null` sem fonte que apoie uma opção |
| `sem` | sim | O que acontece se ninguém decidir |
| `depende_de` | não | IDs de pontos existentes; sem ciclo nem autorreferência |
| `validar` | não | O que falta confirmar e com quem |
| `aprovador` | não | `{quem, fontes}` só quando uma fonte do projeto exige aprovação de outra pessoa ou papel para o assunto. `fontes` não vazia |
| `registro` | não | A escolha atual; `null` enquanto pendente |

`resolvidos`: pontos respondidos pelo código ou pela fonte, com `id`, `titulo`,
`resposta` e `fontes` (não vazia). Não repetem IDs de `pontos`.

## Registro e histórico

| Campo do registro | Regra |
|---|---|
| `escolha` | Índice da opção (a partir de 0), ou `null` com resposta em `texto` |
| `texto`, `obs` | Resposta livre e observação; podem ser `null` |
| `quem` | Quem respondeu: `interlocutor` ou o nome que ele mesmo informar |
| `origem` | `interlocutor` (respondeu na sessão) · `relato` (conta o que outra pessoa disse) · `registro` (cita o registro de quem decide; exige `fontes`) · `delegacao` (o interlocutor delegou a escolha ao agente; `quem` = quem delegou, `obs` obrigatória com as palavras da delegação) |
| `status` | `aceito` · `validar` · `adiado` · `fora_do_escopo`. `aceito` e `validar` exigem `escolha` ou `texto` |
| `data` | ISO local, minuto (`2026-01-15T10:40`) |

Ponto com `aprovador` só fica `aceito` com `origem: registro`; antes disso a
escolha do interlocutor fica `validar`; `delegacao` também não dispensa o aprovador.
Se o interlocutor disser que a exigência não vale mais, remova `aprovador`, anote no
histórico com o trecho dele e registre, salvo se a exigência vier de instrução que o
host aplica à sessão e que o interlocutor não tem como dispensar ali; nesse caso,
mantenha e diga por quê.

Histórico: lista de `{data, ponto, evento}`. `ponto` é um ID existente em `pontos` ou
`resolvidos`, ou `*` para eventos do estado (raiz alterada, auditoria). Ao trocar a
resposta de um ponto, a entrada leva `anterior` = registro antigo com
`status: "superado"`. Nada é apagado. Correções de ponto também entram aqui.

Sem o auxiliar, grave o arquivo inteiro de uma vez (escreva numa cópia temporária na
mesma pasta e renomeie por cima, se o ambiente permitir).

## Formatos de `ref`

| Formato | Conferência |
|---|---|
| `caminho/arquivo.ext:42` ou `:40-55` | Arquivo existe (relativo à `meta.raiz`, ou absoluto), linha existe, `trecho` aparece até 5 linhas em volta |
| `conversa:<resumo>` | Exige `trecho` com as palavras do usuário |
| `doc:<documento fora do projeto>` | Exige `trecho` |
| `url:https://...` | Exige `trecho`; o auxiliar não acessa a rede |
| `decisao:<data e quem>` | Decisão registrada em outro lugar; exige `trecho` |

Só refs de arquivo são abertas pelo auxiliar. As demais ele aceita como citação; a
veracidade fica com quem citou.

## Linguagem

- Pergunta e opções em palavras do dia a dia; termo técnico com explicação curta na
  primeira vez.
- `favor` e `contra` dizem o efeito concreto: o que o usuário vê, o que quebra, o que
  custa. Sem "melhor" ou "mais robusto" sem dizer em quê.

Ruim: `"contexto": "A biblioteca X já suporta streaming."`, `"fontes": []`, com `rec`
preenchida. Fato sem fonte e recomendação sem base.
Bom: o mesmo ponto com `"situacao": "validar"`, `"rec": null` e contexto "Sem fonte
que confirme suporte a streaming; o plano só cita a biblioteca (docs/plano.md:61)".

## Seção no plano

Acrescente ou atualize no fim do plano, e reescreva o trecho que cada decisão muda:

```
## Decisões
### Sessão AAAA-MM-DD

| ID | Decisão | Quem | Origem | Status |
|---|---|---|---|---|

Cobertura: N aceitos · N pelo código · N a validar · N adiados · N fora do escopo · N pendentes
```
