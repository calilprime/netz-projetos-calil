# -*- coding: utf-8 -*-
"""
Hub de Ferramentas — Netz Asset
================================

Junta as automações que hoje vivem em pastas e `.bat` separados numa única
janela do navegador, com abas. Cada ferramenta continua sendo o mesmo
programa de sempre — o hub só sobe cada uma como um processo próprio (na sua
própria pasta, com seu próprio `py <script>.py`), descobre em qual porta ela
ficou disponível e mostra as duas dentro de uma aba (`<iframe>`), sem que
elas abram janelas de navegador por conta própria.

Como usar
---------
    Duplo clique em  "Abrir Ferramentas Netz.bat"
    ou, no terminal:  py hub_app.py

Para adicionar uma nova ferramenta, edite a lista ``FERRAMENTAS`` abaixo.

Onde o hub procura cada ferramenta
----------------------------------
Não há caminho fixo: para cada ferramenta o hub testa uma lista de lugares
prováveis e usa o primeiro em que o script existir. Isso faz o mesmo arquivo
funcionar tanto na organização de pastas da máquina do Calil (as automações
como pastas *irmãs* do hub) quanto num clone do repositório (as automações
como pastas *dentro* da pasta do hub, com o nome que o `git clone` dá).

Se a sua organização for outra, crie um ``ferramentas.json`` ao lado deste
arquivo apontando as pastas — ele tem prioridade sobre a busca automática:

    { "recompra": "D:\\\\Netz\\\\recompra", "fnet": "D:\\\\Netz\\\\fnet" }
"""

import http.server
import json
import os
import re
import socket
import subprocess
import sys
import threading
import webbrowser
from pathlib import Path

AQUI = Path(__file__).resolve().parent
ACIMA = AQUI.parent

# ============================================================================
#  As ferramentas que o hub sobe. Cada uma continua no seu próprio código,
#  na sua própria pasta — o hub não mexe em nada além de abrir o processo.
#
#  "candidatos" vale como ordem de preferência: dentro da pasta do hub (o
#  layout de um clone) antes das pastas irmãs (o layout da máquina de origem).
# ============================================================================
FERRAMENTAS = [
    {
        "id": "recompra",
        "rotulo": "Recompra FIDC · Leve Saúde",
        "script": "recompra_app.py",
        "repositorio": "https://github.com/calilprime/recompra-leve-saude.git",
        "candidatos": [
            AQUI / "Recompra - Leve Saude" / "Código VS CODE",
            AQUI / "recompra-leve-saude",
            ACIMA / "Recompra - Leve Saude" / "Código VS CODE",
            ACIMA / "recompra-leve-saude",
        ],
    },
    {
        "id": "fnet",
        "rotulo": "Extração FIDC · FNET",
        "script": "fnet_app.py",
        "repositorio": "https://github.com/calilprime/Extracao-Fundos-NET.git",
        "candidatos": [
            AQUI / "Extração Fundos.NET" / "Cód" / "Atual",
            AQUI / "Extracao-Fundos-NET",
            ACIMA / "Extração Fundos.NET" / "Cód" / "Atual",
            ACIMA / "Extracao-Fundos-NET",
        ],
    },
]


def _pasta_configurada(item):
    """Lê ``ferramentas.json``, se existir. Erro no arquivo não derruba o hub."""
    arquivo = AQUI / "ferramentas.json"
    if not arquivo.exists():
        return None
    try:
        escolhas = json.loads(arquivo.read_text(encoding="utf-8"))
    except (OSError, ValueError) as erro:
        print(f"[hub] ferramentas.json ignorado ({erro}).")
        return None
    caminho = escolhas.get(item["id"])
    return Path(caminho).expanduser() if caminho else None


def resolver_pasta(item):
    """A pasta onde o script da ferramenta está, ou None se não achou."""
    configurada = _pasta_configurada(item)
    if configurada is not None:
        return configurada if (configurada / item["script"]).exists() else None
    for pasta in item["candidatos"]:
        if (pasta / item["script"]).exists():
            return pasta
    return None

# Regex igual nas duas automações: "Servidor rodando em: http://127.0.0.1:PORTA"
_RE_PORTA = re.compile(r"Servidor rodando em:\s*http://127\.0\.0\.1:(\d+)")

_ESTADO = {f["id"]: {"pronto": False, "url": None, "erro": None} for f in FERRAMENTAS}
_PROCESSOS = []


# ============================================================================
#  1. Sobe cada ferramenta como processo filho, com NETZ_HUB=1 para que ela
#     não tente abrir o navegador sozinha (recompra_app.py e fnet_app.py já
#     checam essa variável antes do webbrowser.open).
# ============================================================================
def _iniciar_ferramenta(item, porta):
    pasta = resolver_pasta(item)
    if pasta is None:
        onde = "; ".join(str(p) for p in item["candidatos"])
        _ESTADO[item["id"]]["erro"] = (
            f"Não encontrei {item['script']}. Procurei em: {onde}. "
            f"Rode 'py preparar.py' para baixar as ferramentas, ou aponte a "
            f"pasta em ferramentas.json."
        )
        print(f"[hub] {item['id']}: {_ESTADO[item['id']]['erro']}")
        return

    python = "py" if _tem_comando("py") else sys.executable
    env = dict(os.environ)
    env["NETZ_HUB"] = "1"
    #  A porta vem daqui, e não do sorteio de cada ferramenta: subindo juntas,
    #  as duas sorteavam a mesma (ambas veem a porta livre no mesmo instante) e
    #  no Windows o allow_reuse_address do HTTPServer deixa as duas ligarem no
    #  mesmo endereço — uma aba acabava mostrando a ferramenta da outra.
    env["NETZ_PORTA"] = str(porta)
    env["PYTHONIOENCODING"] = "utf-8"
    env["PYTHONUNBUFFERED"] = "1"

    try:
        proc = subprocess.Popen(
            [python, "-u", item["script"]],
            cwd=str(pasta),
            env=env,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            encoding="utf-8",
            errors="replace",
            bufsize=1,
        )
    except OSError as erro:
        _ESTADO[item["id"]]["erro"] = f"Não consegui iniciar: {erro}"
        return

    _PROCESSOS.append(proc)
    threading.Thread(target=_ler_saida, args=(item, proc), daemon=True).start()


def _ler_saida(item, proc):
    """Lê o stdout do processo filho, acha a porta e ecoa no console do hub."""
    prefixo = f"[{item['id']}] "
    for linha in proc.stdout:
        linha = linha.rstrip("\n")
        print(prefixo + linha)
        m = _RE_PORTA.search(linha)
        if m and not _ESTADO[item["id"]]["pronto"]:
            _ESTADO[item["id"]]["url"] = f"http://127.0.0.1:{m.group(1)}"
            _ESTADO[item["id"]]["pronto"] = True
    codigo = proc.wait()
    if codigo != 0 and not _ESTADO[item["id"]]["pronto"]:
        _ESTADO[item["id"]]["erro"] = f"O processo encerrou sozinho (código {codigo})."


def _tem_comando(nome):
    from shutil import which
    return which(nome) is not None


def _encerrar_tudo():
    for proc in _PROCESSOS:
        if proc.poll() is None:
            proc.terminate()
    for proc in _PROCESSOS:
        try:
            proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            proc.kill()


# ============================================================================
#  2. A página do hub — abas + iframes, sem framework nenhum.
# ============================================================================
def _pagina_html():
    abas = "".join(
        f'<button class="aba{" ativa" if i == 0 else ""}" data-id="{f["id"]}">{f["rotulo"]}</button>'
        for i, f in enumerate(FERRAMENTAS)
    )
    paineis = "".join(
        f'<div class="painel{" ativo" if i == 0 else ""}" data-id="{f["id"]}">'
        f'<div class="carregando" data-id="{f["id"]}">Abrindo {f["rotulo"]}…</div>'
        f'<iframe data-id="{f["id"]}" title="{f["rotulo"]}"></iframe>'
        f'</div>'
        for i, f in enumerate(FERRAMENTAS)
    )
    return f"""<!doctype html>
<html lang="pt-BR">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Ferramentas · Netz Asset</title>
<style>
  :root{{ --navy:#001B5C; --bg:#eef3fa; --line:#dfe6f1; --muted:#5b6b8c; --erro:#c62828; }}
  *{{box-sizing:border-box}}
  html,body{{height:100%;margin:0;font-family:"IBM Plex Sans","Segoe UI",system-ui,Arial,sans-serif;background:var(--bg)}}
  .topbar{{background:var(--navy);display:flex;align-items:center;gap:4px;padding:0 12px}}
  .aba{{background:transparent;border:0;color:#aebfe0;padding:14px 18px;font-size:14px;font-weight:600;
        cursor:pointer;font-family:inherit;border-bottom:3px solid transparent}}
  .aba.ativa{{color:#fff;border-bottom-color:#FF965A}}
  .aba:hover{{color:#fff}}
  .corpo{{height:calc(100% - 49px)}}
  .painel{{display:none;height:100%;position:relative}}
  .painel.ativo{{display:block}}
  iframe{{width:100%;height:100%;border:0;display:block;background:#fff}}
  .carregando{{position:absolute;inset:0;display:flex;align-items:center;justify-content:center;
               color:var(--muted);font-size:14px;background:var(--bg)}}
  .carregando.oculto{{display:none}}
  .carregando.erro{{color:var(--erro);font-weight:600;padding:0 24px;text-align:center}}
</style>
</head>
<body>
<div class="topbar">{abas}</div>
<div class="corpo">{paineis}</div>
<script>
  const abas = document.querySelectorAll(".aba");
  const paineis = document.querySelectorAll(".painel");
  abas.forEach(a => a.addEventListener("click", () => {{
    abas.forEach(x => x.classList.toggle("ativa", x === a));
    paineis.forEach(p => p.classList.toggle("ativo", p.dataset.id === a.dataset.id));
  }}));

  const carregados = new Set();
  async function atualizar(){{
    try{{
      const estado = await (await fetch("/status")).json();
      for(const id in estado){{
        const e = estado[id];
        const caixa = document.querySelector('.carregando[data-id="' + id + '"]');
        const frame = document.querySelector('iframe[data-id="' + id + '"]');
        if(e.erro){{
          caixa.textContent = "Não foi possível abrir esta ferramenta: " + e.erro;
          caixa.classList.add("erro");
        }} else if(e.pronto && !carregados.has(id)){{
          frame.src = e.url;
          caixa.classList.add("oculto");
          carregados.add(id);
        }}
      }}
    }}catch(err){{ /* servidor do hub ainda subindo — tenta de novo */ }}
    if(carregados.size < {len(FERRAMENTAS)}) setTimeout(atualizar, 700);
  }}
  atualizar();
</script>
</body>
</html>"""


class Handler(http.server.BaseHTTPRequestHandler):
    def log_message(self, formato, *args):
        pass  # o log de cada ferramenta já sai com seu próprio prefixo

    def do_GET(self):
        if self.path == "/" or self.path == "":
            corpo = _pagina_html().encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(corpo)))
            self.end_headers()
            self.wfile.write(corpo)
        elif self.path == "/status":
            corpo = json.dumps(_ESTADO).encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(corpo)))
            self.end_headers()
            self.wfile.write(corpo)
        else:
            self.send_response(404)
            self.end_headers()


def _achar_porta(inicio=8900, fim=8950, ocupadas=()):
    for porta in range(inicio, fim):
        if porta in ocupadas:
            continue
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            if s.connect_ex(("127.0.0.1", porta)) != 0:
                return porta
    return inicio


def main():
    #  O hub distribui as portas para não haver duas ferramentas na mesma.
    reservadas = []
    for item in FERRAMENTAS:
        porta_ferramenta = _achar_porta(8765, 8815, ocupadas=reservadas)
        reservadas.append(porta_ferramenta)
        _iniciar_ferramenta(item, porta_ferramenta)

    porta = _achar_porta(ocupadas=reservadas)
    endereco = f"http://127.0.0.1:{porta}"
    servidor = http.server.ThreadingHTTPServer(("127.0.0.1", porta), Handler)

    print("=" * 64)
    print("  Ferramentas Netz Asset — hub")
    print("=" * 64)
    print(f"  Painel em: {endereco}")
    for item in FERRAMENTAS:
        if _ESTADO[item["id"]]["erro"]:
            print(f"  · {item['rotulo']}: NÃO ENCONTRADA (veja o aviso acima)")
        else:
            print(f"  · {item['rotulo']}: {resolver_pasta(item)}")
    print("  Para encerrar: feche esta janela ou pressione Ctrl+C.")
    print("=" * 64)

    threading.Timer(0.8, lambda: webbrowser.open(endereco)).start()
    try:
        servidor.serve_forever()
    except KeyboardInterrupt:
        print("\nEncerrando…")
    finally:
        servidor.shutdown()
        _encerrar_tudo()


if __name__ == "__main__":
    main()
