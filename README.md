# fechar-decisoes

Skill para fechar as decisões em aberto de um plano, especificação, lista de tarefas ou trecho
da conversa antes de implementar. Ela levanta cada ponto com fonte e opções, conversa ponto a
ponto, grava as escolhas num estado local por projeto e propõe o diff para o plano.

- A skill fica em [`fechar-decisoes/`](fechar-decisoes/). Comece por [`SKILL.md`](fechar-decisoes/SKILL.md).
- A invocação é **só manual**: `disable-model-invocation: true` no Claude Code e
  `allow_implicit_invocation: false` em `agents/openai.yaml` no Codex.
- O auxiliar `scripts/fechar_decisoes.py` é opcional, usa só a biblioteca padrão e roda em
  Python 3.8 ou mais novo. Sem Python, o fluxo em texto funciona, mas o painel HTML não.
- O estado fica em `~/.fechar-decisoes/` (ou em `FECHAR_DECISOES_HOME`), fora do repositório
  do projeto.

Licença: **nenhuma licença pública foi escolhida.** O repositório é privado, para uso do dono.

## Instalação em outra máquina

Pré-requisito: `gh` autenticado numa conta com acesso a este repositório privado (`gh auth status`).

Destino, conforme a documentação oficial de cada host:

| Host | Pasta pessoal da skill | Invocação |
|---|---|---|
| Claude Code | `~/.claude/skills/fechar-decisoes/` | `/fechar-decisoes [fonte] [id=slug] [modo=...]` |
| Codex | `~/.agents/skills/fechar-decisoes/` | `$fechar-decisoes ...` (ou `/skills`) |

Os comandos abaixo baixam o ZIP da release, conferem o SHA-256 e copiam a skill. **Se já
existir uma skill com o mesmo nome no destino, eles param sem sobrescrever.** Para instalar no
Codex, troque o destino.

### PowerShell (Windows)

```powershell
$tag = 'v0.1.0'; $repo = 'matheus-cb/fechar-decisoes'
$tmp = Join-Path ([IO.Path]::GetTempPath()) ("fechar-decisoes-" + [guid]::NewGuid())
New-Item -ItemType Directory $tmp | Out-Null
gh release download $tag -R $repo -p 'fechar-decisoes-portatil.zip' -p 'SHA256SUMS.txt' -D $tmp
$esperado = (Get-Content (Join-Path $tmp 'SHA256SUMS.txt')).Split(' ')[0]
$obtido = (Get-FileHash (Join-Path $tmp 'fechar-decisoes-portatil.zip') -Algorithm SHA256).Hash.ToLower()
if ($obtido -ne $esperado) { throw "SHA-256 divergente: $obtido" }
Expand-Archive (Join-Path $tmp 'fechar-decisoes-portatil.zip') -DestinationPath $tmp
$destino = Join-Path $HOME '.claude\skills\fechar-decisoes'   # Codex: Join-Path $HOME '.agents\skills\fechar-decisoes'
if (Test-Path $destino) { throw "Já existe: $destino. Renomeie ou remova antes de instalar." }
New-Item -ItemType Directory -Force (Split-Path $destino) | Out-Null
Copy-Item -Recurse (Join-Path $tmp 'fechar-decisoes') $destino
```

### POSIX (Linux, macOS, Git Bash)

```sh
tag=v0.1.0; repo=matheus-cb/fechar-decisoes
tmp=$(mktemp -d)
gh release download "$tag" -R "$repo" -p 'fechar-decisoes-portatil.zip' -p 'SHA256SUMS.txt' -D "$tmp"
(cd "$tmp" && { sha256sum -c SHA256SUMS.txt 2>/dev/null || shasum -a 256 -c SHA256SUMS.txt; }) &&
unzip -q "$tmp/fechar-decisoes-portatil.zip" -d "$tmp" &&
dest="$HOME/.claude/skills/fechar-decisoes" &&   # Codex: dest="$HOME/.agents/skills/fechar-decisoes"
if [ -e "$dest" ]; then echo "Já existe: $dest. Renomeie ou remova antes de instalar."; \
else mkdir -p "$(dirname "$dest")" && cp -R "$tmp/fechar-decisoes" "$dest" && echo "Instalada em $dest"; fi
```

Para atualizar: renomeie ou remova a pasta instalada e repita com a nova tag. O estado em
`~/.fechar-decisoes/` não é tocado.

## Teste rápido

1. Auxiliar (opcional): `python -I ~/.claude/skills/fechar-decisoes/scripts/fechar_decisoes.py --help`.
   No Windows use `py -3 -I` ou `python -I` com `$HOME\.claude\skills\...`.
2. Abra uma sessão nova do host, num projeto de teste, e invoque `/fechar-decisoes conversa`
   (Claude Code) ou `$fechar-decisoes conversa` (Codex).
3. Confira que a skill **não** é carregada sozinha quando você só conversa sobre decisões.

## Limites conhecidos

- O auxiliar e o painel foram testados no Windows com Python 3.13. Em Python 3.8, só a
  sintaxe foi conferida.
- A invocação real dentro do Claude Code e do Codex ainda não foi testada de ponta a ponta,
  nem o bloqueio de invocação automática. Faça o teste rápido acima na primeira instalação.
- Ainda não há plugin nem marketplace: a instalação é por cópia da pasta da skill.
