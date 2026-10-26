# Seletor visual: escolher vendo a composição

Modo para decisões **visuais** (layout, aparência, ordem de blocos, texto que muda a
composição). Em vez de cartões de texto, o interlocutor escolhe numa prévia que se
recompõe a cada resposta. O seletor é só a forma de perguntar: o processo continua o
mesmo do `SKILL.md` (fonte, tipo, `rec`, estado, registro, diff).

## Quando usar

- Os pontos mudam o que a pessoa **vê**: composição, superfície, ordem no celular,
  título, hierarquia de texto, rótulo de botão, animação.
- O host desenha interface na conversa (no Claude Code, a ferramenta de widget que
  renderiza HTML e oferece `sendPrompt`). Sem isso, use o mesmo modelo como arquivo
  HTML local (ver "Sem widget") ou siga no modo conversa.
- Ofereça quando o interlocutor pedir para "ver", "comparar" ou "escolher na tela", ou
  quando a escolha depender de como as peças ficam juntas.

## Formato

Use [../assets/seletor-visual.html](../assets/seletor-visual.html) como base. Ele já
traz a casca. O que muda por projeto são a lista de pontos e a função `construir`.

1. **Uma decisão por vez.** Pergunta, nota curta e opções em cima; a prévia logo
   abaixo. Ninguém precisa rolar a lista inteira para ver o efeito.
2. **Barra de IDs** clicáveis (D-01, D-02…), com ✓ nas respondidas, e
   Anterior/Próxima.
3. **Prévia composta.** A função `construir(estado, celular, destaque, animar)`
   monta a parte da tela em decisão aplicando **todas** as escolhas feitas; onde falta
   escolha, mostra como é hoje. Use as cores, fontes e textos reais do projeto, lidos
   do código. Nada de imagem fixa: a prévia precisa recompor quando o interlocutor
   combina opções ("B + C").
4. **Contorno do que muda.** O trecho afetado pela decisão atual ganha contorno
   tracejado (`destaque` = ID atual).
5. **Comparar opções.** Miniaturas lado a lado, uma por opção da decisão atual, já com
   as outras escolhas aplicadas; clicar numa miniatura escolhe.
6. **Computador / Celular.** Alterna a largura da prévia. Pontos só de celular dizem
   isso na nota.
7. **Animação.** Se algum ponto decide movimento, um botão "Reproduzir animação"
   roda a entrada na prévia.
8. **Texto da opção à vista.** Quando a opção é redação, mostre a frase que ela põe
   na tela, embaixo do rótulo, para comparar sem abrir a prévia.
9. **Recomendação** só onde o estado tem `rec`, marcada "Recomendado" com o porquê na
   nota.
10. **Campos livres** (e-mail, usuário, número) quando uma opção pede dado: valide com
    a mesma regra que o projeto usa para publicar e mostre o erro junto do campo.
11. **Enviar escolhas ↗** só envia com todas respondidas; se faltar, vai para a
    primeira pendente e diz quais faltam.

O resumo enviado tem a forma:

```
Escolhas <do quê> no seletor: D-01 <título>: <opção>; D-02 <título>: <opção> (campo: valor); ...
```

## Baterias

Com muitos pontos interdependentes (mais de ~10, ou textos que dependem de quais
blocos ficam), divida em baterias, cada uma com o seu seletor:

1. **Estrutura:** composição, superfície, o que fica e o que sai, repetições entre
   partes, informações novas, animação, ordem no celular.
2. **Textos:** a redação do que sobrou, já sobre a estrutura escolhida, que vira fixa
   na prévia.

Ofereça a divisão como ponto de escopo, primeiro na ordem (ver `SKILL.md`, seção 2).
Repetições percebidas só depois da primeira bateria entram na segunda.

## Conteúdo das opções

- **Texto concreto.** Quando o interlocutor aprova o conteúdo, proponha a frase pronta,
  não marcadores como `[cidade]`. Use marcador só para dado que ninguém informou, e
  diga quem precisa informar.
- **Voz e gênero.** Mantenha a voz que a página já usa (por exemplo, "você") e aponte
  no `contra` palavra que supõe gênero de quem lê ("decidido", "juntas").
- **Dado verificável.** E-mail, domínio, link e perfil são conferidos antes de virar
  opção ou registro, quando houver como (por exemplo, `dig MX` para o domínio do
  e-mail). Se não confere, o ponto fica `validar` com o motivo na `obs`.
- **Repetição entre partes.** Leia as partes vizinhas que o escopo toca. Se a mesma
  garantia ou etapa aparece em mais de um lugar, isso vira ponto, com as fontes de
  cada lugar.

## Ao receber o envio

- O envio é a resposta explícita: registre cada ponto com
  `origem: interlocutor` e `obs` dizendo que veio do seletor.
- **Respostas que se contradizem** (por exemplo, "animar o elemento" e "sem
  elemento") não são registradas: diga a contradição em uma linha e transforme-a em
  ponto `validar` da próxima bateria.
- Ponto que o interlocutor escolheu mas disse que quer melhorar ("preciso melhorar o
  texto") fica `validar`, e o texto vira ponto da próxima bateria.

## Sem widget

Sem interface na conversa, salve o modelo como arquivo `.html` (acrescente
`<!doctype html>`, `<meta charset="utf-8">` e um `<body>`) ao lado do estado, entregue
o caminho e peça para abrir no navegador. Sem `sendPrompt`, o botão copia o resumo e o
mostra numa caixa de texto: o interlocutor cola na conversa. Como no painel, o arquivo
não grava nada.

## Regras do widget no Claude Code

- Nada de `position: fixed`, rolagem interna nem seção escondida durante o
  carregamento: a prévia fica no fluxo da página.
- Cores fixas só dentro da prévia, que imita o produto; os controles usam as
  variáveis do host (`--text-primary`, `--border` etc.), para funcionar no tema escuro.
- Sem comentários dentro do código enviado ao widget.
- Se o host tem memória entre sessões e o interlocutor aprovar o formato, registre a
  preferência para oferecer o seletor nas próximas decisões visuais.
