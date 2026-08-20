# Hub de Ferramentas · Netz Asset

Abre as automações da mesa numa única janela do navegador, em abas, sem
precisar de um `.bat` por ferramenta.

Hoje o hub reúne duas:

| Aba | O que faz | Repositório |
|---|---|---|
| **Recompra FIDC · Leve Saúde** | Concilia o estoque da Vórtx com os boletos da Grafeno, apura o Termo de Recompra e gera a planilha da rodada | [recompra-leve-saude](https://github.com/calilprime/recompra-leve-saude) |
| **Extração FIDC · FNET** | Baixa os informes mensais do FNET e preenche a planilha de análise | [Extracao-Fundos-NET](https://github.com/calilprime/Extracao-Fundos-NET) |

---

## Instalar numa máquina nova

Precisa de [Python 3.8+](https://www.python.org/downloads/) (marque **"Add
python.exe to PATH"** no instalador) e [Git](https://git-scm.com/download/win).

```
git clone https://github.com/calilprime/netz-projetos-calil.git
cd netz-projetos-calil
py preparar.py
```

O `preparar.py` clona as duas automações nas pastas que o hub procura e
instala as dependências. Quem preferir clicar: **`Preparar ferramentas.bat`**.

Falta então, **só para a Recompra**:

1. copiar `.env.exemplo` para `.env` e preencher as credenciais do banco da
   Vórtx (peça ao responsável — credenciais não vão para repositório);
2. colocar o template oficial em `templates/Leve_Saude_Recompra_TEMPLATE.xlsx`;
3. na primeira execução, clicar em **"Popular o histórico pelas rodadas
   anteriores"** — sem isso a numeração da rodada e a trava contra recompra
   em duplicidade não funcionam.

## Abrir

**Duplo clique em `Abrir Ferramentas Netz.bat`.** O navegador abre sozinho.

Cada ferramenta continua funcionando sozinha também: o `.bat` de dentro da
pasta dela abre só ela, como sempre.

---

## Como funciona

O hub **não contém** o código das automações — ele as executa.

Ao subir, ele:

1. inicia cada ferramenta como um **processo próprio**, na pasta dela, com
   `NETZ_HUB=1` no ambiente. É essa variável que faz `recompra_app.py` e
   `fnet_app.py` não abrirem uma janela de navegador por conta própria;
2. lê o `stdout` de cada processo até achar a linha
   `Servidor rodando em: http://127.0.0.1:<porta>` — as duas já imprimiam
   isso, então a porta não precisa ser combinada de antemão;
3. serve uma página com uma aba por ferramenta, cada uma num `<iframe>`
   apontado para a porta que aquela ferramenta escolheu.

Consequência prática: **uma ferramenta que quebra não derruba a outra**, e o
console de cada uma continua aparecendo, prefixado, no terminal do hub.

### Onde o hub procura cada ferramenta

Não há caminho fixo. Para cada uma, o hub testa uma lista de lugares e usa o
primeiro em que o script existir — dentro da pasta do hub (o layout de um
clone) antes das pastas irmãs (o layout da máquina de origem):

```
<hub>/Recompra - Leve Saude/Código VS CODE/recompra_app.py
<hub>/recompra-leve-saude/recompra_app.py
<hub>/../Recompra - Leve Saude/Código VS CODE/recompra_app.py
<hub>/../recompra-leve-saude/recompra_app.py
```

Se a sua organização for outra, crie um `ferramentas.json` ao lado do
`hub_app.py` — ele tem prioridade sobre a busca automática:

```json
{
  "recompra": "D:\\Netz\\recompra",
  "fnet": "D:\\Netz\\fnet"
}
```

### Adicionar uma terceira ferramenta

Acrescente uma entrada em `FERRAMENTAS`, no topo do `hub_app.py`. A
ferramenta só precisa cumprir duas condições:

* imprimir `Servidor rodando em: http://127.0.0.1:<porta>` ao subir;
* não abrir o navegador quando `NETZ_HUB` estiver no ambiente.

---

## Arquivos

```
hub_app.py                    # servidor do hub: sobe os processos e serve as abas
Abrir Ferramentas Netz.bat    # duplo clique
preparar.py                   # clona as automações e instala dependências
Preparar ferramentas.bat      # duplo clique do preparar.py
```

As pastas das automações e a pasta `Compartilhar/` ficam fora do
versionamento (veja `.gitignore`): cada automação tem o seu repositório, e
versionar uma cópia aqui significaria três cópias para manter em sincronia —
com a de dentro do hub envelhecendo em silêncio.
