# -*- coding: utf-8 -*-
"""
conferir_funcoes.py — acha funcao CHAMADA que nunca foi DEFINIDA no index.html.

Por que existe: em 20/08/2026 um bloco de codigo se perdeu numa edicao (o
comando original foi recusado por tamanho e, ao refazer em partes, uma delas
ficou de fora). O `validar_js.py` passou — a SINTAXE estava correta —, mas a
tela do Mix Minimo abria em branco, porque o render chamava `_mmFonte()` e
`mmSetTipo()`, que nao existiam mais.

Sintaxe correta nao garante codigo completo. Este script cobre esse buraco:
roda junto com o validar e avisa antes de publicar.

Uso:  python3 conferir_funcoes.py
"""
import re, sys, os

PROJ = os.path.dirname(os.path.abspath(__file__))
INDEX = os.path.join(PROJ, "index.html")

# nomes que existem no navegador ou vem de biblioteca — nao sao do projeto
IGNORAR = {
    "if", "for", "while", "switch", "catch", "return", "typeof", "function",
    "String", "Number", "Boolean", "Array", "Object", "Math", "JSON", "Date",
    "Map", "Set", "Promise", "RegExp", "Error", "parseInt", "parseFloat",
    "isNaN", "alert", "confirm", "prompt", "setTimeout", "setInterval",
    "clearTimeout", "clearInterval", "fetch", "encodeURIComponent",
    "decodeURIComponent", "requestAnimationFrame", "structuredClone",
    "XLSX", "Chart", "PptxGenJS", "console", "window", "document", "localStorage",
    "ResizeObserver", "MutationObserver", "IntersectionObserver",
    "resolve", "reject",      # parametros de Promise
    "not", "var", "rgba", "rgb", "url", "calc",   # fragmentos de CSS/seletor
    "TypeError", "RangeError", "async", "await", "new", "delete", "void",
}

# funcoes definidas DENTRO de outra (aninhadas) ou passadas como parametro:
# nao aparecem como "function nome(" no topo, mas existem. Conferidas a mao.
LOCAIS = {"addProfTotal", "fnEmp", "bt", "empilha", "uni", "calc", "valor",
          "ehTotal", "ehDetalhe", "nivel", "analisa_canal"}


def main():
    s = open(INDEX, encoding="utf-8").read()
    # so o JS: tudo dentro de <script>
    js = "\n".join(re.findall(r"<script[^>]*>(.*?)</script>", s, re.S))

    definidas = set(re.findall(r"function\s+([A-Za-z_$][\w$]*)\s*\(", js))
    definidas |= set(re.findall(r"(?:const|let|var)\s+([A-Za-z_$][\w$]*)\s*=\s*"
                                r"(?:async\s*)?(?:function|\()", js))
    definidas |= set(re.findall(r"(?:const|let|var)\s+([A-Za-z_$][\w$]*)\s*=", js))

    # tira COMENTARIOS e STRINGS antes de procurar chamadas: sem isso o
    # detector acusa palavra em portugues dentro de comentario ("Cobertura
    # (dias)") como se fosse funcao inexistente, e o aviso vira ruido.
    # ORDEM IMPORTA: as STRINGS saem primeiro. Tirando comentario antes, um
    # endereco dentro de string ('https://...') era lido como comentario, a
    # linha era cortada no meio, a aspa ficava aberta e o regex seguinte
    # engolia paginas inteiras de codigo — o detector entao dizia "tudo certo"
    # justamente onde havia problema (descoberto ao testar a trava, 20/08).
    limpo = re.sub(r"'(?:\\.|[^'\\\n])*'", "''", js)
    limpo = re.sub(r'"(?:\\.|[^"\\\n])*"', '""', limpo)
    limpo = re.sub(r"`(?:\\.|[^`\\])*`", "``", limpo, flags=re.S)
    limpo = re.sub(r"//[^\n]*", " ", limpo)
    limpo = re.sub(r"/\*.*?\*/", " ", limpo, flags=re.S)
    chamadas = set(re.findall(r"\b([A-Za-z_$][\w$]*)\s*\(", limpo))
    # chamadas dentro de onclick="..." no HTML tambem contam
    for m in re.finditer(r'on\w+="([^"]+)"', s):
        chamadas |= set(re.findall(r"\b([A-Za-z_$][\w$]*)\s*\(", m.group(1)))

    faltando = sorted(n for n in chamadas - definidas - IGNORAR - LOCAIS
                      if not n.startswith(("_0x",)) and len(n) > 2
                      and not re.match(r"^[A-Z][A-Z_0-9]+$", n))   # CONSTANTES

    # metodos (x.foo()) sao falso positivo: so acusa o que aparece "solto"
    reais = []
    for n in faltando:
        if re.search(r"(?<![.\w])" + re.escape(n) + r"\s*\(", limpo):
            reais.append(n)

    if reais:
        print("FUNCOES CHAMADAS MAS NUNCA DEFINIDAS (%d):" % len(reais))
        for n in reais:
            ctx = re.search(r"^.*\b" + re.escape(n) + r"\s*\(.*$", js, re.M)
            print("  ! %-28s %s" % (n, (ctx.group(0).strip()[:70] if ctx else "")))
        print("\nA sintaxe pode estar OK e a tela quebrar mesmo assim.")
        return 1
    print("nenhuma funcao orfa — todas as chamadas tem definicao")
    return 0


if __name__ == "__main__":
    sys.exit(main())
