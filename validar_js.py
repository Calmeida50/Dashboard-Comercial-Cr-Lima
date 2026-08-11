#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
validar_js.py — confere a sintaxe de TODO o JavaScript do index.html.

Rodar SEMPRE antes de publicar. Em 11/08 uma alteracao com aspas mal fechadas
derrubou a pagina inteira: como o codigo esta todo num arquivo so, um erro de
sintaxe impede qualquer coisa de renderizar.

Usa o `jsc`, motor JavaScript que ja vem no macOS. `new Function(codigo)` faz
apenas o PARSE — nao executa nada, entao nao da erro por falta de DOM.

Saida 0 = pode publicar | 1 = NAO publicar
"""
import os, re, sys, json, subprocess

JSC = ("/System/Library/Frameworks/JavaScriptCore.framework/"
       "Versions/A/Helpers/jsc")
INDEX = os.path.join(os.path.dirname(os.path.abspath(__file__)), "index.html")


def main():
    s = open(INDEX, encoding="utf-8").read()
    blocos = [b for b in re.findall(r"<script(?:\s[^>]*)?>(.*?)</script>", s, re.S)
              if b.strip()]
    print("blocos de codigo: %d" % len(blocos))

    if not os.path.exists(JSC):
        print("jsc nao encontrado — nao consigo validar")
        return 1

    erros = 0
    for i, b in enumerate(blocos):
        chk = "/tmp/_chk_%d.js" % i
        with open(chk, "w", encoding="utf-8") as f:
            f.write("try { new Function(%s); print('OK'); } "
                    "catch (e) { print('ERRO: ' + e.message); }" % json.dumps(b))
        r = subprocess.run([JSC, chk], capture_output=True, text=True)
        out = (r.stdout or "").strip()
        try:
            os.remove(chk)
        except OSError:
            pass
        if not out.startswith("OK"):
            erros += 1
            print("\n  !! bloco %d: %s" % (i, (out or r.stderr)[:200]))
            print("     comeca com: %s" % b.strip()[:90].replace("\n", " "))

    if erros:
        print("\n%d BLOCO(S) COM ERRO — NAO PUBLICAR" % erros)
        return 1
    print("\nsintaxe OK")
    return 0


if __name__ == "__main__":
    sys.exit(main())
