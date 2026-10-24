#!/usr/bin/env python3
"""Auxiliar opcional da skill fechar-decisoes. Só biblioteca padrão (Python 3.8+).

Subcomandos:
  local      resolve raiz, identidade e pasta de estado; lista estados do mesmo id em outro caminho
  validar    confere decisoes.json (estrutura, escolhas, histórico) e as fontes citadas
  registrar  grava a resposta de um ponto, com histórico, de forma atômica
  painel     gera painel.html autocontido (sem rede) a partir do decisoes.json

Códigos de saída: 0 ok · 1 erro de validação ou de uso · 2 arquivo ilegível · 3 escrita negada.
Nenhum conteúdo lido (fontes, estado) é executado: tudo é tratado como dado.
"""
import argparse
import datetime
import hashlib
import json
import os
import re
import sys
import tempfile
import unicodedata

VERSAO = 1
SITUACOES = {"decisao", "validar", "externo"}
STATUS = {"aceito", "validar", "adiado", "fora_do_escopo"}
ORIGENS = {"interlocutor", "relato", "registro", "delegacao"}
PREFIXOS_LIVRES = ("conversa:", "url:", "doc:", "decisao:")
REF_ARQUIVO = re.compile(r"^(?P<caminho>.+?):(?P<ini>\d+)(?:-(?P<fim>\d+))?$")
ID_SEGURO = re.compile(r"^[a-z0-9](?:[a-z0-9-]{0,62})$")
JANELA = 5
FONTE_MUDOU = ("trecho não encontrado", "fora do arquivo", "arquivo não existe", "não foi possível ler")
NOME_ESTADO = "decisoes.json"
MARCA_DADOS = "__DADOS_JSON__"


# ---------- identidade e caminhos ----------

def slug(texto, maximo=40, vazio="projeto"):
    t = unicodedata.normalize("NFKD", str(texto or "")).encode("ascii", "ignore").decode("ascii")
    t = re.sub(r"[^a-z0-9]+", "-", t.lower()).strip("-")
    return t[:maximo].strip("-") or vazio


def canonico(caminho):
    """Caminho absoluto, links resolvidos, '/' como separador; no Windows, minúsculas."""
    c = str(caminho)
    if os.name == "nt":
        m = re.match(r"^/([a-zA-Z])(/.*)?$", c)  # /c/Users/... (Git Bash/MSYS)
        if m:
            c = m.group(1) + ":" + (m.group(2) or "/")
    c = os.path.normcase(os.path.realpath(os.path.abspath(c)))
    c = c.replace("\\", "/")
    if len(c) > 1 and c.endswith("/") and not re.match(r"^[a-z]:/$", c):
        c = c.rstrip("/")
    return c


def achar_raiz(inicio):
    atual = os.path.realpath(os.path.abspath(inicio))
    while True:
        if os.path.exists(os.path.join(atual, ".git")):
            return atual
        pai = os.path.dirname(atual)
        if pai == atual:
            return os.path.realpath(os.path.abspath(inicio))
        atual = pai


def hash_curto(canon, n=8):
    return hashlib.sha256(canon.encode("utf-8")).hexdigest()[:n]


def base_padrao():
    return os.environ.get("FECHAR_DECISOES_HOME") or os.path.join(os.path.expanduser("~"), ".fechar-decisoes")


def nome_pasta_projeto(canon, n=8):
    return f"{slug(os.path.basename(canon.rstrip('/')) or canon)}-{hash_curto(canon, n)}"


# ---------- leitura e escrita ----------

def ler_json(caminho):
    with open(caminho, encoding="utf-8-sig") as f:
        return json.load(f)


def gravar_atomico(caminho, texto, mtime_esperado=None):
    pasta = os.path.dirname(os.path.abspath(caminho))
    fd, tmp = tempfile.mkstemp(prefix=".tmp-", suffix=".json", dir=pasta)
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as f:
            f.write(texto)
            f.flush()
            os.fsync(f.fileno())
        if mtime_esperado is not None and os.path.exists(caminho):
            if os.stat(caminho).st_mtime_ns != mtime_esperado:
                raise RuntimeError("o arquivo mudou durante a gravação; leia de novo e repita")
        os.replace(tmp, caminho)
    finally:
        if os.path.exists(tmp):
            os.remove(tmp)


def dump(dados):
    return json.dumps(dados, ensure_ascii=False, indent=2) + "\n"


def agora():
    return datetime.datetime.now().replace(second=0, microsecond=0).isoformat(timespec="minutes")


# ---------- validação ----------

def normalizar(texto):
    return re.sub(r"\s+", " ", str(texto or "")).strip().casefold()


def texto_ok(v):
    return isinstance(v, str) and v.strip() != ""


def inteiro(v):
    return isinstance(v, int) and not isinstance(v, bool)


def conferir_fonte(fonte, raiz, cache, onde, erros, conferir_arquivos):
    if not isinstance(fonte, dict) or not texto_ok(fonte.get("ref")):
        erros.append(f"{onde}: fonte sem 'ref'")
        return
    ref = fonte["ref"].strip()
    trecho = fonte.get("trecho")
    if ref.startswith(PREFIXOS_LIVRES):
        if not texto_ok(trecho):
            erros.append(f"{onde}: '{ref[:40]}' exige 'trecho'")
        return
    m = REF_ARQUIVO.match(ref)
    if not m:
        erros.append(f"{onde}: ref '{ref[:60]}' fora dos formatos aceitos")
        return
    if not conferir_arquivos:
        return
    caminho = m.group("caminho")
    completo = caminho if os.path.isabs(caminho) else os.path.join(raiz, caminho)
    if not os.path.isfile(completo):
        erros.append(f"{onde}: arquivo não existe: {caminho}")
        return
    if completo not in cache:
        try:
            with open(completo, encoding="utf-8-sig", errors="replace") as f:
                cache[completo] = f.read().splitlines()
        except OSError as e:
            erros.append(f"{onde}: não foi possível ler {caminho}: {e}")
            return
    linhas = cache[completo]
    ini = int(m.group("ini"))
    fim = int(m.group("fim") or ini)
    if ini < 1 or fim < ini or fim > len(linhas):
        erros.append(f"{onde}: linha {ini}-{fim} fora do arquivo ({len(linhas)} linhas): {caminho}")
        return
    if texto_ok(trecho):
        a = max(0, ini - 1 - JANELA)
        b = min(len(linhas), fim + JANELA)
        if normalizar(trecho) not in normalizar(" ".join(linhas[a:b])):
            erros.append(f"{onde}: trecho não encontrado perto de {ref}: \"{trecho[:60]}\"")


def conferir_lista_fontes(lista, raiz, cache, onde, erros, conferir_arquivos):
    if not isinstance(lista, list):
        erros.append(f"{onde}: precisa ser lista")
        return []
    for i, f in enumerate(lista):
        conferir_fonte(f, raiz, cache, f"{onde}[{i}]", erros, conferir_arquivos)
    return lista


def conferir_registro(r, opcoes, onde, erros, raiz, cache, conferir_arquivos, anterior=False):
    if not isinstance(r, dict):
        erros.append(f"{onde}: registro precisa ser objeto ou null")
        return
    status = r.get("status")
    validos = STATUS | {"superado"} if anterior else STATUS
    if status not in validos:
        erros.append(f"{onde}: status '{status}' inválido")
    esc = r.get("escolha")
    if esc is not None and (not inteiro(esc) or not 0 <= esc < len(opcoes)):
        erros.append(f"{onde}: escolha {esc!r} não aponta para opção existente")
    if esc is None and not texto_ok(r.get("texto")) and status in ("aceito", "validar"):
        erros.append(f"{onde}: sem 'escolha' nem 'texto'")
    if not texto_ok(r.get("quem")):
        erros.append(f"{onde}: 'quem' vazio")
    if r.get("origem") not in ORIGENS:
        erros.append(f"{onde}: origem '{r.get('origem')}' inválida")
    if not texto_ok(r.get("data")):
        erros.append(f"{onde}: 'data' vazia")
    if r.get("origem") == "delegacao" and not texto_ok(r.get("obs")):
        erros.append(f"{onde}: origem 'delegacao' exige 'obs' com as palavras da delegação")
    if r.get("origem") == "registro":
        fontes = r.get("fontes")
        if not isinstance(fontes, list) or not fontes:
            erros.append(f"{onde}: origem 'registro' exige 'fontes'")
        else:
            conferir_lista_fontes(fontes, raiz, cache, f"{onde}.fontes", erros, conferir_arquivos)


def tem_ciclo(grafo):
    estado = {}

    def visita(n):
        estado[n] = 1
        for d in grafo.get(n, ()):
            if estado.get(d) == 1 or (d not in estado and d in grafo and visita(d)):
                return True
        estado[n] = 2
        return False

    return any(n not in estado and visita(n) for n in grafo)


def validar(dados, raiz=None, conferir_arquivos=True):
    erros, avisos, cache = [], [], {}
    if not isinstance(dados, dict):
        return ["a raiz do JSON precisa ser objeto"], avisos
    if dados.get("versao") != VERSAO:
        erros.append(f"'versao' precisa ser {VERSAO}")
    meta = dados.get("meta")
    if not isinstance(meta, dict):
        erros.append("'meta' ausente")
        meta = {}
    if not isinstance(meta.get("id"), str) or not ID_SEGURO.match(meta.get("id")):
        erros.append("meta.id ausente ou inseguro (use minúsculas, dígitos e hífen, até 63)")
    if not texto_ok(meta.get("raiz")):
        erros.append("meta.raiz ausente")
    raiz = raiz or meta.get("raiz") or os.getcwd()

    camadas = dados.get("camadas")
    ids_camadas = None
    if camadas is not None:
        if not isinstance(camadas, list):
            erros.append("'camadas' precisa ser lista")
        else:
            ids_camadas = [c.get("id") for c in camadas if isinstance(c, dict) and texto_ok(c.get("id"))]
            if len(ids_camadas) != len(camadas):
                erros.append("camada sem id de texto")
            if len(ids_camadas) != len(set(ids_camadas)):
                erros.append("camadas com id duplicado")

    pontos = dados.get("pontos")
    resolvidos = dados.get("resolvidos", [])
    if not isinstance(pontos, list):
        erros.append("'pontos' precisa ser lista")
        pontos = []
    if not isinstance(resolvidos, list):
        erros.append("'resolvidos' precisa ser lista")
        resolvidos = []
    if not pontos and not resolvidos:
        erros.append("nenhum ponto nem resolvido")

    ids = [p.get("id") for p in pontos if isinstance(p, dict) and texto_ok(p.get("id"))]
    ids_resolvidos = [r.get("id") for r in resolvidos if isinstance(r, dict) and texto_ok(r.get("id"))]
    vistos = set()
    grafo = {}
    for p in pontos:
        if not isinstance(p, dict):
            erros.append("ponto que não é objeto")
            continue
        pid = p.get("id")
        onde = f"[{pid}]"
        if not texto_ok(pid) or "\n" in pid:
            erros.append(f"{onde}: id vazio ou inválido")
        elif pid in vistos:
            erros.append(f"{onde}: id duplicado")
        else:
            vistos.add(pid)
        for campo in ("titulo", "pergunta", "contexto", "sem"):
            if not texto_ok(p.get(campo)):
                erros.append(f"{onde}: '{campo}' vazio")
        if texto_ok(p.get("pergunta")) and not p["pergunta"].strip().endswith("?"):
            avisos.append(f"{onde}: pergunta não termina em '?'")
        if ids_camadas is not None and p.get("camada") not in ids_camadas:
            erros.append(f"{onde}: camada '{p.get('camada')}' não existe em 'camadas'")
        situacao = p.get("situacao")
        if situacao not in SITUACOES:
            erros.append(f"{onde}: situacao '{situacao}' inválida")
        if p.get("tipo") not in (1, 2) or isinstance(p.get("tipo"), bool):
            erros.append(f"{onde}: tipo precisa ser 1 ou 2")
        registrado = isinstance(p.get("registro"), dict)
        ref_erros = []
        fontes = conferir_lista_fontes(p.get("fontes", []), raiz, cache, f"{onde} fontes", ref_erros, conferir_arquivos)
        if not fontes:
            avisos.append(f"{onde}: sem fonte; o contexto deve dizer 'sem fonte' ou tratar de preferência")
        opcoes = p.get("opcoes")
        if not isinstance(opcoes, list) or not 2 <= len(opcoes) <= 4:
            erros.append(f"{onde}: precisa de 2 a 4 opções")
            opcoes = opcoes if isinstance(opcoes, list) else []
        nomes = []
        for i, o in enumerate(opcoes):
            for campo in ("nome", "favor", "contra"):
                if not isinstance(o, dict) or not texto_ok(o.get(campo)):
                    erros.append(f"{onde} opcoes[{i}]: '{campo}' vazio")
            if isinstance(o, dict) and texto_ok(o.get("nome")):
                nomes.append(normalizar(o["nome"]))
        if len(nomes) != len(set(nomes)):
            erros.append(f"{onde}: opções com nome repetido")
        rec = p.get("rec")
        if rec is not None:
            if not isinstance(rec, dict):
                erros.append(f"{onde}: 'rec' precisa ser objeto ou null")
            else:
                ok_idx = inteiro(rec.get("opcao")) and 0 <= rec["opcao"] < len(opcoes)
                if not ok_idx:
                    erros.append(f"{onde}: rec.opcao fora das opções")
                if not texto_ok(rec.get("porque")):
                    erros.append(f"{onde}: rec.porque vazio")
                rf = rec.get("fontes")
                if not isinstance(rf, list) or not rf:
                    erros.append(f"{onde}: recomendação sem fonte; use rec null")
                else:
                    conferir_lista_fontes(rf, raiz, cache, f"{onde} rec.fontes", ref_erros, conferir_arquivos)
                if ok_idx and isinstance(opcoes[rec["opcao"]], dict) and opcoes[rec["opcao"]].get("origem") == "proposta":
                    avisos.append(f"{onde}: recomendação aponta para opção 'proposta' sem base na fonte")
        aprov = p.get("aprovador")
        if aprov is not None:
            if not isinstance(aprov, dict) or not texto_ok(aprov.get("quem")):
                erros.append(f"{onde}: aprovador precisa de 'quem'")
            elif not isinstance(aprov.get("fontes"), list) or not aprov["fontes"]:
                erros.append(f"{onde}: aprovador sem fonte; sem exigência concreta no projeto, remova 'aprovador'")
            else:
                conferir_lista_fontes(aprov["fontes"], raiz, cache, f"{onde} aprovador.fontes", ref_erros, conferir_arquivos)
        for e in ref_erros:
            if registrado and any(k in e for k in FONTE_MUDOU):
                avisos.append(f"{e} (ponto já registrado: fonte mudou, a escolha não é reaberta)")
            else:
                erros.append(e)
        deps = p.get("depende_de") or []
        if not isinstance(deps, list):
            erros.append(f"{onde}: depende_de precisa ser lista")
            deps = []
        for dep in deps:
            if dep == pid:
                erros.append(f"{onde}: depende de si mesmo")
            elif dep not in ids:
                erros.append(f"{onde}: depende_de '{dep}' não existe")
        if texto_ok(pid):
            grafo[pid] = [d for d in deps if d in ids and d != pid]
        reg = p.get("registro")
        if reg is not None:
            conferir_registro(reg, opcoes, f"{onde} registro", erros, raiz, cache, conferir_arquivos)
            if (isinstance(reg, dict) and isinstance(aprov, dict) and reg.get("status") == "aceito"
                    and reg.get("origem") != "registro"):
                erros.append(f"{onde}: o projeto exige aprovador ({aprov.get('quem')}); sem o registro dele, "
                             "a escolha fica com status 'validar'")
    if tem_ciclo(grafo):
        erros.append("depende_de forma ciclo")

    for r in resolvidos:
        if not isinstance(r, dict) or not texto_ok(r.get("id")):
            erros.append("resolvido sem id")
            continue
        onde = f"[{r['id']}] resolvido"
        if r["id"] in ids:
            erros.append(f"{onde}: id também está em 'pontos'")
        if ids_resolvidos.count(r["id"]) > 1:
            erros.append(f"{onde}: id duplicado")
        for campo in ("titulo", "resposta"):
            if not texto_ok(r.get(campo)):
                erros.append(f"{onde}: '{campo}' vazio")
        if not isinstance(r.get("fontes"), list) or not r["fontes"]:
            erros.append(f"{onde}: resolvido pelo código exige fonte")
        else:
            conferir_lista_fontes(r["fontes"], raiz, cache, f"{onde} fontes", erros, conferir_arquivos)

    historico = dados.get("historico", [])
    if not isinstance(historico, list):
        erros.append("'historico' precisa ser lista")
        historico = []
    por_id = {p["id"]: p for p in pontos if isinstance(p, dict) and texto_ok(p.get("id"))}
    for i, h in enumerate(historico):
        onde = f"historico[{i}]"
        if not isinstance(h, dict):
            erros.append(f"{onde}: precisa ser objeto")
            continue
        alvo = h.get("ponto")
        if not isinstance(alvo, str):
            alvo = None
            erros.append(f"{onde}: 'ponto' precisa ser texto (histórico órfão)")
        elif alvo != "*" and alvo not in por_id and alvo not in ids_resolvidos:
            erros.append(f"{onde}: ponto '{alvo}' não existe (histórico órfão)")
        if not texto_ok(h.get("evento")):
            erros.append(f"{onde}: 'evento' vazio")
        if not texto_ok(h.get("data")):
            erros.append(f"{onde}: 'data' vazia")
        ant = h.get("anterior")
        if ant is not None:
            if not isinstance(ant, dict) or ant.get("status") != "superado":
                erros.append(f"{onde}: 'anterior' precisa ser registro com status 'superado'")
            elif alvo is not None and alvo in por_id:
                ops = por_id[alvo].get("opcoes") if isinstance(por_id[alvo].get("opcoes"), list) else []
                conferir_registro(ant, ops, f"{onde}.anterior", erros, raiz, cache, False, anterior=True)
    return erros, avisos


def cobertura(dados):
    c = {"pendente": 0, "aceito": 0, "validar": 0, "adiado": 0, "fora_do_escopo": 0}
    for p in dados.get("pontos") or []:
        if not isinstance(p, dict):
            continue
        r = p.get("registro")
        st = r.get("status") if isinstance(r, dict) else None
        c[st if st in c else "pendente"] += 1
    c["resolvido_pelo_codigo"] = len(dados.get("resolvidos") or [])
    return c


# ---------- subcomandos ----------

def cmd_local(a):
    raiz = canonico(a.raiz) if a.raiz else canonico(achar_raiz(os.getcwd()))
    ident = slug(a.id, 63, "")
    if not ident:
        print("ERRO id vazio depois de normalizado; use letras ou dígitos")
        return 1
    base = os.path.abspath(a.base or base_padrao())
    proprio = os.path.join(base, nome_pasta_projeto(raiz), ident)
    exatos, outros, ilegiveis = [], [], []
    try:
        nomes = sorted(os.listdir(base)) if os.path.isdir(base) else []
    except OSError:
        nomes = []
        ilegiveis.append(base)
    if nomes:
        for nome in nomes:
            arq = os.path.join(base, nome, ident, NOME_ESTADO)
            if not os.path.isfile(arq):
                continue
            try:
                r = (ler_json(arq).get("meta") or {}).get("raiz")
            except (OSError, ValueError, AttributeError):
                ilegiveis.append(arq)
                continue
            if isinstance(r, str) and canonico(r) == raiz:
                exatos.append(arq)
            else:
                mesma_pasta = isinstance(r, str) and slug(os.path.basename(r.rstrip("/\\"))) == slug(os.path.basename(raiz))
                existe = isinstance(r, str) and os.path.isdir(r)
                if mesma_pasta or not existe:
                    outros.append({"raiz": r, "arquivo": arq, "raiz_existe": existe})
    arquivo = os.path.join(proprio, NOME_ESTADO)
    if not exatos and os.path.exists(arquivo):
        # pasta-rótulo ocupada por outro projeto (colisão de hash curto): nunca reutilizar
        proprio = os.path.join(base, nome_pasta_projeto(raiz, 64), ident)
        arquivo = os.path.join(proprio, NOME_ESTADO)
    if exatos:
        arquivo = os.path.join(proprio, NOME_ESTADO) if os.path.join(proprio, NOME_ESTADO) in exatos else exatos[0]
    saida = {
        "raiz": raiz,
        "id": ident,
        "pasta_estado": os.path.dirname(arquivo),
        "arquivo": arquivo,
        "existe": bool(exatos),
        "outros_caminhos": outros,
    }
    if len(exatos) > 1:
        saida["duplicados"] = [x for x in exatos if x != arquivo]
    if ilegiveis:
        saida["ilegiveis"] = ilegiveis
    if exatos:
        try:
            saida["cobertura"] = cobertura(ler_json(arquivo))
        except (OSError, ValueError) as e:
            saida["erro_leitura"] = str(e)
    codigo = 0
    if a.criar:
        try:
            os.makedirs(saida["pasta_estado"], exist_ok=True)
            fd, sonda = tempfile.mkstemp(prefix=".sonda-", dir=saida["pasta_estado"])
            os.close(fd)
            os.remove(sonda)
            saida["gravavel"] = True
        except OSError as e:
            saida["gravavel"] = False
            saida["motivo"] = f"{type(e).__name__}: {e}"
            codigo = 3
    print(json.dumps(saida, ensure_ascii=False, indent=2))
    return codigo


def carregar(arquivo):
    try:
        return ler_json(arquivo), None
    except (OSError, ValueError) as e:
        return None, f"ERRO não foi possível ler {arquivo}: {e}"


def cmd_validar(a):
    dados, falha = carregar(a.arquivo)
    if falha:
        print(falha)
        return 2
    erros, avisos = validar(dados, a.raiz, not a.sem_arquivos)
    for e in erros:
        print(f"ERRO {e}")
    for w in avisos:
        print(f"AVISO {w}")
    pts = dados.get("pontos") if isinstance(dados, dict) and isinstance(dados.get("pontos"), list) else []
    com_rec = sum(1 for p in pts if isinstance(p, dict) and p.get("rec"))
    cob = cobertura(dados) if isinstance(dados, dict) else {}
    print(f"pontos={len(pts)} com_recomendacao={com_rec} erros={len(erros)} avisos={len(avisos)} "
          + " ".join(f"{k}={v}" for k, v in cob.items()))
    print("Conferência confirma que as fontes citadas existem e contêm o trecho; não prova que as afirmações estão corretas.")
    return 1 if erros else 0


def cmd_registrar(a):
    dados, falha = carregar(a.arquivo)
    if falha:
        print(falha)
        return 2
    mtime = os.stat(a.arquivo).st_mtime_ns
    erros_antes, _ = validar(dados, a.raiz, False)
    pontos = dados.get("pontos") if isinstance(dados, dict) else None
    ponto = next((p for p in pontos or [] if isinstance(p, dict) and p.get("id") == a.ponto), None)
    if ponto is None:
        print(f"ERRO ponto '{a.ponto}' não existe")
        return 1
    opcoes = ponto.get("opcoes") or []
    if (a.opcao is None) == (a.texto is None) and a.status in ("aceito", "validar"):
        print("ERRO informe --opcao ou --texto (um dos dois)")
        return 1
    escolha = None
    if a.opcao is not None:
        if not 1 <= a.opcao <= len(opcoes):
            print(f"ERRO opção {a.opcao} não existe (o ponto tem {len(opcoes)}; numeração começa em 1)")
            return 1
        escolha = a.opcao - 1
    reg = {"escolha": escolha, "texto": a.texto, "obs": a.obs, "quem": a.quem,
           "origem": a.origem, "data": a.data or agora(), "status": a.status}
    if a.fonte_ref:
        reg["fontes"] = [{"ref": a.fonte_ref, "trecho": a.fonte_trecho}]
    rotulo = opcoes[escolha]["nome"] if escolha is not None else (a.texto or a.status)
    entrada = {"data": reg["data"], "ponto": a.ponto, "evento": f"registrado: {rotulo} ({a.status})"}
    antigo = ponto.get("registro")
    if isinstance(antigo, dict):
        ant = dict(antigo)
        ant["status"] = "superado"
        entrada["anterior"] = ant
    ponto["registro"] = reg
    dados.setdefault("historico", []).append(entrada)
    dados.setdefault("meta", {})["atualizado"] = reg["data"]
    erros_depois, _ = validar(dados, a.raiz, False)
    conf = []
    if a.origem == "registro":
        conferir_lista_fontes(reg.get("fontes") or [], a.raiz or dados["meta"].get("raiz") or os.getcwd(),
                              {}, "registro.fontes", conf, True)
    novos = [e for e in erros_depois + conf if e not in erros_antes]
    if novos:
        for e in novos:
            print(f"ERRO {e}")
        print("Nada gravado.")
        return 1
    try:
        gravar_atomico(a.arquivo, dump(dados), mtime)
    except RuntimeError as e:
        print(f"ERRO {e}")
        return 1
    except OSError as e:
        print(f"ERRO escrita negada: {e}. Siga com o estado na conversa.")
        return 3
    print(f"{a.ponto}: registrado '{rotulo}' · status {a.status} · origem {a.origem}"
          + (" · anterior marcado como superado" if "anterior" in entrada else ""))
    return 0


def cmd_painel(a):
    dados, falha = carregar(a.arquivo)
    if falha:
        print(falha)
        return 2
    erros, _ = validar(dados, None, False)
    if erros:
        for e in erros:
            print(f"ERRO {e}")
        print("Painel não gerado: corrija o decisoes.json.")
        return 1
    molde = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "assets", "painel.html")
    with open(molde, encoding="utf-8") as f:
        html = f.read()
    if html.count(MARCA_DADOS) != 1:
        print("ERRO molde do painel sem marcador único de dados")
        return 1
    js = json.dumps(dados, ensure_ascii=False)
    js = js.replace("&", "\\u0026").replace("<", "\\u003c").replace(">", "\\u003e")
    js = js.replace("\u2028", "\\u2028").replace("\u2029", "\\u2029")
    saida = a.saida or os.path.join(os.path.dirname(os.path.abspath(a.arquivo)), "painel.html")
    try:
        gravar_atomico(saida, html.replace(MARCA_DADOS, js))
    except OSError as e:
        print(f"ERRO escrita negada: {e}. Siga no modo conversa.")
        return 3
    print(saida)
    return 0


def main(argv=None):
    for s in (sys.stdout, sys.stderr):
        if hasattr(s, "reconfigure"):
            s.reconfigure(encoding="utf-8", errors="replace")
    ap = argparse.ArgumentParser(prog="fechar_decisoes.py", description="Auxiliar opcional do fechar-decisoes.")
    sub = ap.add_subparsers(dest="cmd", required=True)

    p = sub.add_parser("local", help="resolve raiz e pasta de estado")
    p.add_argument("--id", required=True)
    p.add_argument("--raiz", help="raiz do projeto; padrão: topo do git ou pasta atual")
    p.add_argument("--base", help="pasta base do estado; padrão: $FECHAR_DECISOES_HOME ou ~/.fechar-decisoes")
    p.add_argument("--criar", action="store_true", help="cria a pasta de estado e testa a escrita")
    p.set_defaults(f=cmd_local)

    p = sub.add_parser("validar", help="confere o decisoes.json")
    p.add_argument("arquivo")
    p.add_argument("--raiz", help="padrão: meta.raiz")
    p.add_argument("--sem-arquivos", action="store_true", help="não abre os arquivos citados")
    p.set_defaults(f=cmd_validar)

    p = sub.add_parser("registrar", help="grava a resposta de um ponto")
    p.add_argument("arquivo")
    p.add_argument("--ponto", required=True)
    p.add_argument("--opcao", type=int, help="número mostrado ao usuário (1 = primeira opção)")
    p.add_argument("--texto", help="resposta livre, quando não é uma das opções")
    p.add_argument("--status", default="aceito", choices=sorted(STATUS))
    p.add_argument("--quem", default="interlocutor")
    p.add_argument("--origem", default="interlocutor", choices=sorted(ORIGENS))
    p.add_argument("--obs")
    p.add_argument("--fonte-ref")
    p.add_argument("--fonte-trecho")
    p.add_argument("--data")
    p.add_argument("--raiz")
    p.set_defaults(f=cmd_registrar)

    p = sub.add_parser("painel", help="gera painel.html autocontido")
    p.add_argument("arquivo")
    p.add_argument("--saida")
    p.set_defaults(f=cmd_painel)

    a = ap.parse_args(argv)
    return a.f(a)


if __name__ == "__main__":
    sys.exit(main())
