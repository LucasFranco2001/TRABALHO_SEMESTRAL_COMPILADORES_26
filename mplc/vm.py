"""
Entrega 4, terceira metade (sim, sao tres) — a maquina virtual.

Le o .mplb e executa. Precisa de:
  - uma pilha de operandos;
  - um registro de ativacao por chamada, com os locais e o ponto de volta;
  - deteccao de divisao por zero e de estouro de pilha, com codigo de saida 2.

Essa e a materia da aula 11 virando codigo: sem registro de ativacao, a
recursao nao funciona.

Desenho: UMA pilha de operandos compartilhada por todas as chamadas e, para
cada chamada, um Quadro (registro de ativacao) com os SEUS locais e o ponto
de volta (a funcao e o pc de quem chamou). CHAMA cria um quadro novo; RETORNA
descarta o quadro e volta para o pc guardado. Por isso fatorial(5) tem cinco
quadros vivos ao mesmo tempo, cada um com o seu n.
"""
import json

from mplc.erros import ErroMPL

LIMITE_QUADROS = 10000          # mais fundo que isso e estouro de pilha
LIMITE_OPERANDOS = 1000000


class Codigo:
    """Uma funcao ja lida: instrucoes, rotulos resolvidos e tamanho dos locais."""

    def __init__(self, nome, nparams, nlocais):
        self.nome = nome
        self.nparams = nparams
        self.nlocais = nlocais
        self.insts = []             # (opcode, argumento, linha, coluna)
        self.rotulos = {}           # nome do rotulo -> indice em insts


class Quadro:
    """Registro de ativacao: os locais DESTA chamada e para onde voltar."""
    __slots__ = ('codigo', 'locais', 'pc', 'volta')

    def __init__(self, codigo, locais, volta):
        self.codigo = codigo
        self.locais = locais
        self.pc = 0
        self.volta = volta          # o quadro de quem chamou (o pc dele ja esta guardado)


def _invalido(n, motivo):
    return ErroMPL('execucao', 1, 1, f'arquivo .mplb invalido (linha {n}): {motivo}')


def carregar(texto):
    linhas = texto.split('\n')
    if not linhas or linhas[0].strip() != 'mplb 1':
        raise _invalido(1, "falta o cabecalho 'mplb 1'")
    funcoes, atual = {}, None
    for n, bruta in enumerate(linhas[1:], 2):
        linha = bruta.strip()
        if not linha:
            continue
        if linha.startswith('funcao '):
            partes = linha.split()
            atual = Codigo(partes[1], int(partes[3]), int(partes[5]))
            funcoes[atual.nome] = atual
            continue
        if linha == 'fim':
            atual = None
            continue
        if atual is None:
            raise _invalido(n, 'instrucao fora de funcao')
        if linha.endswith(':') and ' ' not in linha:
            atual.rotulos[linha[:-1]] = len(atual.insts)
            continue
        # o sufixo ' @linha:coluna' e sempre o ultimo pedaco da linha
        corpo, _, pos = linha.rpartition(' @')
        if not _:
            corpo, pos = linha, '1:1'
        l, _, c = pos.partition(':')
        opcode, _, resto = corpo.partition(' ')
        if opcode != 'EMPILHA' and ';' in resto:     # comentario (nome da variavel)
            resto = resto.partition(';')[0]
        arg = resto.strip()
        if opcode == 'EMPILHA':
            arg = _constante(arg)
        elif opcode in ('CARREGA', 'GUARDA'):
            arg = int(arg)
        elif opcode == 'CHAMA':
            nome, nargs = arg.split()
            arg = (nome, int(nargs))
        atual.insts.append((opcode, arg, int(l), int(c)))
    return funcoes


def _constante(texto):
    if texto == 'verdadeiro':
        return True
    if texto == 'falso':
        return False
    if texto.startswith('"'):
        return json.loads(texto)
    if '.' in texto:
        return float(texto)
    return int(texto)


def formatar(v):
    """4.5: como cada tipo sai."""
    if type(v) is bool:
        return 'verdadeiro' if v else 'falso'
    if type(v) is float:
        return f'{v:.6f}'
    return str(v)


def _dividir(a, b, linha, coluna):
    if b == 0:
        raise ErroMPL('execucao', linha, coluna, 'divisao por zero')
    if type(a) is int and type(b) is int:
        q = abs(a) // abs(b)                    # trunca em direcao a zero: 7/2 = 3, -7/2 = -3
        return -q if (a < 0) != (b < 0) else q
    return a / b


def _resto(a, b, linha, coluna):
    if b == 0:
        raise ErroMPL('execucao', linha, coluna, 'resto por zero')
    r = abs(a) % abs(b)                         # o sinal e o do DIVIDENDO: -7 % 3 = -1
    return -r if a < 0 else r


def executar(texto_mplb, saida):
    """Executa o bytecode. Escreve o que o programa imprimir em `saida`."""
    try:
        saida.reconfigure(encoding='utf-8', newline='\n')   # UTF-8, sem BOM
    except (AttributeError, ValueError):
        pass
    funcoes = carregar(texto_mplb)
    if 'principal' not in funcoes:
        raise ErroMPL('execucao', 1, 1, "o programa nao tem a funcao 'principal'")

    pilha = []                                  # pilha de operandos
    principal = funcoes['principal']
    quadro = Quadro(principal, [None] * principal.nlocais, None)
    profundidade = 1

    while quadro is not None:
        cod = quadro.codigo
        if quadro.pc >= len(cod.insts):         # caiu pelo fim da funcao: e um RETORNA
            quadro, profundidade = quadro.volta, profundidade - 1
            continue
        opcode, arg, linha, coluna = cod.insts[quadro.pc]
        quadro.pc += 1

        if opcode == 'CARREGA':
            pilha.append(quadro.locais[arg])
        elif opcode == 'GUARDA':
            quadro.locais[arg] = pilha.pop()
        elif opcode == 'EMPILHA':
            pilha.append(arg)
        elif opcode == 'SOMA':
            b = pilha.pop(); pilha.append(pilha.pop() + b)
        elif opcode == 'SUB':
            b = pilha.pop(); pilha.append(pilha.pop() - b)
        elif opcode == 'MULT':
            b = pilha.pop(); pilha.append(pilha.pop() * b)
        elif opcode == 'DIV':
            b = pilha.pop(); pilha.append(_dividir(pilha.pop(), b, linha, coluna))
        elif opcode == 'RESTO':
            b = pilha.pop(); pilha.append(_resto(pilha.pop(), b, linha, coluna))
        elif opcode == 'IGUAL':
            b = pilha.pop(); pilha.append(pilha.pop() == b)
        elif opcode == 'DIFERENTE':
            b = pilha.pop(); pilha.append(pilha.pop() != b)
        elif opcode == 'MENOR':
            b = pilha.pop(); pilha.append(pilha.pop() < b)
        elif opcode == 'MENORIGUAL':
            b = pilha.pop(); pilha.append(pilha.pop() <= b)
        elif opcode == 'MAIOR':
            b = pilha.pop(); pilha.append(pilha.pop() > b)
        elif opcode == 'MAIORIGUAL':
            b = pilha.pop(); pilha.append(pilha.pop() >= b)
        elif opcode == 'E':
            b = pilha.pop(); pilha.append(pilha.pop() and b)     # os dois lados ja foram avaliados
        elif opcode == 'OU':
            b = pilha.pop(); pilha.append(pilha.pop() or b)
        elif opcode == 'NAO':
            pilha.append(not pilha.pop())
        elif opcode == 'NEG':
            pilha.append(-pilha.pop())
        elif opcode == 'PARAREAL':
            pilha.append(float(pilha.pop()))
        elif opcode == 'DESVIA':
            quadro.pc = cod.rotulos[arg]
        elif opcode == 'DESVIAFALSO':
            if not pilha.pop():
                quadro.pc = cod.rotulos[arg]
        elif opcode == 'ESCREVE':
            saida.write(formatar(pilha.pop()) + '\n')
        elif opcode == 'CHAMA':
            nome, nargs = arg
            if profundidade >= LIMITE_QUADROS or len(pilha) > LIMITE_OPERANDOS:
                raise ErroMPL('execucao', linha, coluna, 'estouro de pilha')
            alvo = funcoes[nome]
            locais = [None] * alvo.nlocais
            for k in range(nargs - 1, -1, -1):  # o ultimo argumento esta no topo
                locais[k] = pilha.pop()
            quadro = Quadro(alvo, locais, quadro)    # quadro NOVO: locais proprios
            profundidade += 1
        elif opcode in ('RETORNA', 'RETORNAVAL'):
            # RETORNAVAL deixa o valor no topo da pilha de operandos, para quem chamou
            quadro, profundidade = quadro.volta, profundidade - 1
        else:
            raise ErroMPL('execucao', linha, coluna, f'instrucao desconhecida: {opcode}')
