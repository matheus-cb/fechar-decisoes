# Onde fica o estado e como retomar

Com o auxiliar, tudo abaixo é feito por
`python -I <pasta da skill>/scripts/fechar_decisoes.py local --id <id> --criar`
(saída em JSON). Sem ele, siga as mesmas regras à mão.

## Identidade do projeto

1. **Raiz:** suba a partir da pasta de trabalho da sessão até achar `.git` (pasta ou
   arquivo); essa é a raiz. Sem `.git`, a raiz é a pasta em que a sessão foi aberta,
   ou a que o usuário indicar; passe-a com `--raiz`. Não use a subpasta onde está a
   fonte: sem git, cada pasta diferente vira outro projeto.
2. **Caminho canônico:** absoluto, links resolvidos, `/` como separador. No Windows,
   tudo em minúsculas e com letra de unidade (`c:/projetos/app`, nunca `/c/projetos/app`).
3. A identidade é esse caminho, gravado em `meta.raiz`. Dois projetos com o mesmo
   nome de pasta e o mesmo `id`, em caminhos diferentes, têm estados separados.

## Pasta do estado

- Base: variável `FECHAR_DECISOES_HOME`, se existir; senão `~/.fechar-decisoes/`.
  Fica fora do projeto: nada a ignorar no controle de versão.
- Pasta do projeto: `<base>/<slug>-<hash>/`, com `slug` = nome da pasta raiz sem
  acentos, em minúsculas, outros caracteres viram `-`, até 40 caracteres (vazio vira
  `projeto`), e `hash` = 8 primeiros hexadecimais do SHA-256 do caminho canônico em
  UTF-8. À mão:
  - PowerShell: `$s='c:/caminho/canonico'; -join ([Security.Cryptography.SHA256]::Create().ComputeHash([Text.Encoding]::UTF8.GetBytes($s)) | % { $_.ToString('x2') })` e use os 8 primeiros.
  - POSIX: `printf '%s' '/caminho/canonico' | sha256sum | cut -c1-8` (ou `shasum -a 256`).
- Arquivo: `<pasta do projeto>/<id>/decisoes.json`. O painel, se gerado, fica ao lado.
- O nome da pasta é só rótulo. Para achar o estado, procure
  `<base>/*/<id>/decisoes.json` e use o que tiver `meta.raiz` igual ao caminho
  canônico atual, mesmo em pasta de outro nome.
- Se a pasta-rótulo já tiver um `decisoes.json` de outra raiz, ou ilegível, não o
  sobrescreva: use o hash completo (64 hexadecimais) no nome e avise do arquivo
  ilegível, se for o caso.

## Retomada

- **Achou o estado:** mostre a cobertura, revalide as fontes citadas e siga do
  próximo ponto aberto. Fonte que não confere mais em ponto **aberto**: o ponto vira
  `validar`, com nota no histórico. Em ponto **já registrado** (por exemplo, porque o
  plano foi aplicado), é só aviso: a escolha não é reaberta sem pedido.
- **Não achou, mas há o mesmo `id` com caminho que não existe mais:** o projeto pode
  ter sido movido. Pergunte antes de gravar:
  1. retomar aquele estado (grave a nova `meta.raiz` e um evento `*` no histórico
     com o caminho antigo);
  2. começar estado novo para este caminho;
  3. só consultar, sem gravar.
- **Não achou, mas há o mesmo `id` numa pasta de mesmo nome que ainda existe:** pode
  ser cópia ou outro projeto. Não pergunte: comece estado novo e diga numa linha que
  existe outro em `<caminho>` e que "retomar de lá" copia as decisões de lá, se for
  o caso.
- Nunca mescle estados nem decisões de projetos diferentes.

## Escrita negada

Se não for possível criar a pasta ou gravar (sandbox, permissão), avise em uma linha
que não haverá retomada e siga com o estado na conversa. No fim, ofereça mostrar o
JSON para o usuário guardar. Ele pode indicar outra pasta, inclusive dentro do
projeto; nesse caso, lembre de ignorá-la no controle de versão.

## Privacidade

O estado guarda caminhos, trechos da conversa e nomes. Não publique, não envie e não
faça commit dele. O hash no nome da pasta é identidade, não proteção.
