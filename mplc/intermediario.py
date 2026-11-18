"""
Entrega 4, primeira metade — codigo de tres enderecos.

A propriedade que define a representacao, e a unica que o verificador mede:
cada linha de operacao tem NO MAXIMO UM OPERADOR. Uma expressao como
a + b * c vira duas linhas, com um temporario no meio.

O formato do despejo e de voces. A propriedade nao e.

Leiam antes: CONTRATOS.md secao 5.

Como e o nosso formato (um exemplo em README.md):

    funcao fatorial inteiro (n inteiro)
      t0 = n <= 1
      seFalso t0 desvie L0
      retorne 1
    L0:
      t1 = n - 1
      t2 = chama fatorial t1
      t3 = n * t2
      retorne t3
      retorne
    fim

  - t0, t1, ... sao temporarios (um por resultado intermediario);
  - variaveis do fonte mantem o nome; se o mesmo nome aparece em dois
    escopos da mesma funcao, o segundo vira nome@escopo (sombreamento);
  - a conversao inteiro -> real e uma instrucao explicita, paraReal;
  - cada instrucao guarda a linha e a coluna do fonte, para o erro de
    execucao apontar o comando certo (o despejo nao as mostra).
"""
import json
import re
from decimal import Decimal


# --------------------------------------------------------------- operandos

class Operando:
    """Um endereco: temporario, variavel ou constante."""

    def __init__(self, tipo_op, valor, tipo=None):
        self.tipo_op = tipo_op      # 'tmp', 'var' ou 'const'
        self.valor = valor          # nome (tmp/var) ou o valor Python (const)
        self.tipo = tipo            # so para const: inteiro, real, logico, texto

    def __str__(self):
        if self.tipo_op != 'const':
            return self.valor
        return texto_constante(self.tipo, self.valor)


def texto_constante(tipo, valor):
    """Escreve uma constante em texto, do jeito que o .mplb tambem vai usar."""
    if tipo == 'inteiro':
        return str(valor)
    if tipo == 'real':
        # sem notacao cientifica (1e-07 teria um '-' que parece operador) e sem
        # perder precisao: float() de volta devolve exatamente o mesmo numero
        s = format(Decimal(repr(valor)), 'f')
        return s if '.' in s else s + '.0'
    if tipo == 'logico':
        return 'verdadeiro' if valor else 'falso'
    return json.dumps(valor, ensure_ascii=False)


def decodificar_texto(lexema):
    """O lexema vem com aspas e escapes (\\n, \\t, \\\", \\\\); devolve o texto de verdade."""
    corpo, saida, i = lexema[1:-1], [], 0
    while i < len(corpo):
        c = corpo[i]
        if c == '\\' and i + 1 < len(corpo):
            saida.append({'n': '\n', 't': '\t', '"': '"', '\\': '\\'}.get(corpo[i + 1], corpo[i + 1]))
            i += 2
        else:
            saida.append(c)
            i += 1
    return ''.join(saida)


# ------------------------------------------------------------- instrucoes

class Inst:
    """Uma linha do codigo de tres enderecos."""

    def __init__(self, op, dest=None, args=(), sub=None, nome=None, linha=0, coluna=0):
        self.op = op          # copia, bin, un, conv, chama, escreva, retorne,
                              # desvia, seFalso, rotulo
        self.dest = dest      # Operando que recebe o resultado (ou None)
        self.args = list(args)
        self.sub = sub        # o operador, em bin e un
        self.nome = nome      # funcao chamada ou rotulo
        self.linha = linha
        self.coluna = coluna

    def __str__(self):
        a = self.args
        if self.op == 'rotulo':
            return f'{self.nome}:'
        if self.op == 'copia':
            return f'  {self.dest} = {a[0]}'
        if self.op == 'bin':
            return f'  {self.dest} = {a[0]} {self.sub} {a[1]}'
        if self.op == 'un':
            return f'  {self.dest} = {self.sub} {a[0]}'
        if self.op == 'conv':
            return f'  {self.dest} = paraReal {a[0]}'
        if self.op == 'chama':
            chamada = ' '.join(['chama', self.nome] + [str(x) for x in a])
            return f'  {self.dest} = {chamada}' if self.dest else f'  {chamada}'
        if self.op == 'escreva':
            return f'  escreva {a[0]}'
        if self.op == 'retorne':
            return f'  retorne {a[0]}' if a else '  retorne'
        if self.op == 'desvia':
            return f'  desvie {self.nome}'
        if self.op == 'seFalso':
            return f'  seFalso {a[0]} desvie {self.nome}'
        raise ValueError(self.op)


class Funcao:
    def __init__(self, nome, tipo, params):
        self.nome = nome
        self.tipo = tipo
        self.params = params        # lista de (nome_no_ir, tipo)
        self.insts = []


class Programa:
    def __init__(self):
        self.funcoes = []


# ------------------------------------------------------------- tradutor

ARITMETICOS = ('+', '-', '*', '/', '%')
RELACIONAIS = ('==', '!=', '<', '<=', '>', '>=')
PADRAO = {'inteiro': (0, 'inteiro'), 'real': (0.0, 'real'),
          'logico': (False, 'logico'), 'texto': ('', 'texto')}


class Tradutor:
    def __init__(self):
        self.programa = Programa()
        self.rotulos = 0            # global: nenhum rotulo se repete no programa
        self.f = None               # Funcao em construcao
        self.temporarios = 0
        self.nomes = {}             # id(Simbolo) -> nome no IR
        self.em_uso = set()

    # ---- infraestrutura
    def emitir(self, op, no=None, **campos):
        inst = Inst(op, linha=no.linha if no else 0, coluna=no.coluna if no else 0, **campos)
        self.f.insts.append(inst)
        return inst

    def novo_tmp(self):
        t = Operando('tmp', f't{self.temporarios}')
        self.temporarios += 1
        return t

    def novo_rotulo(self):
        r = f'L{self.rotulos}'
        self.rotulos += 1
        return r

    def nome_ir(self, simbolo):
        """Nome da variavel no IR. O sombreamento nao pode virar confusao de nomes."""
        if id(simbolo) not in self.nomes:
            nome = simbolo.nome
            if nome in self.em_uso or re.fullmatch(r't\d+', nome):   # t0 do usuario nao pode ser o t0 do IR
                nome = f'{simbolo.nome}@{simbolo.escopo.numero}'
            self.em_uso.add(nome)
            self.nomes[id(simbolo)] = nome
        return self.nomes[id(simbolo)]

    def variavel(self, simbolo):
        return Operando('var', self.nome_ir(simbolo))

    def converter(self, op, de, para, no):
        """3.1: a unica conversao e inteiro -> real."""
        if de == 'inteiro' and para == 'real':
            if op.tipo_op == 'const':
                return Operando('const', float(op.valor), 'real')
            t = self.novo_tmp()
            self.emitir('conv', no, dest=t, args=[op])
            return t
        return op

    # ---- programa e funcoes
    def programa_(self, raiz):
        for f in raiz.filhos:
            self.funcao(f)
        return self.programa

    def funcao(self, no):
        self.temporarios = 0
        self.nomes, self.em_uso = {}, set()
        params = []
        for p in no.filhos[0].filhos:
            params.append((self.nome_ir(p.extra['simbolo']), p.extra['tipo']))
        self.f = Funcao(no.extra['nome'], no.extra['tipo'], params)
        self.programa.funcoes.append(self.f)
        self.bloco(no.filhos[1])
        self.emitir('retorne', no)          # sair pelo fim do corpo (funcao vazio)
        self.f = None

    # ---- comandos
    def bloco(self, no):
        for c in no.filhos:
            self.comando(c)

    def comando(self, no):
        rotulo = no.rotulo.split()[0]
        if rotulo == 'declaracao':
            alvo = self.variavel(no.extra['simbolo'])
            tipo = no.extra['tipo']
            if no.filhos:
                valor = self.expressao(no.filhos[0])
                valor = self.converter(valor, no.filhos[0].extra['tipo'], tipo, no)
            else:
                v, t = PADRAO[tipo]
                valor = Operando('const', v, t)
            self.emitir('copia', no, dest=alvo, args=[valor])
        elif rotulo == 'atribuicao':
            sim = no.extra['simbolo']
            valor = self.expressao(no.filhos[0])
            valor = self.converter(valor, no.filhos[0].extra['tipo'], sim.tipo, no)
            self.emitir('copia', no, dest=self.variavel(sim), args=[valor])
        elif rotulo == 'se':
            self.se(no)
        elif rotulo == 'enquanto':
            inicio, fim = self.novo_rotulo(), self.novo_rotulo()
            self.emitir('rotulo', nome=inicio)
            cond = self.expressao(no.filhos[0])
            self.emitir('seFalso', no, args=[cond], nome=fim)
            self.bloco(no.filhos[1])
            self.emitir('desvia', no, nome=inicio)
            self.emitir('rotulo', nome=fim)
        elif rotulo == 'escreva':
            valor = self.expressao(no.filhos[0])
            self.emitir('escreva', no, args=[valor])
        elif rotulo == 'retorne':
            if no.filhos:
                valor = self.expressao(no.filhos[0])
                valor = self.converter(valor, no.filhos[0].extra['tipo'], self.f.tipo, no)
                self.emitir('retorne', no, args=[valor])
            else:
                self.emitir('retorne', no)
        elif rotulo == 'bloco':
            self.bloco(no)
        elif rotulo == 'chamada':
            self.chamada(no)

    def se(self, no):
        cond = self.expressao(no.filhos[0])
        if len(no.filhos) == 3:
            senao, fim = self.novo_rotulo(), self.novo_rotulo()
            self.emitir('seFalso', no, args=[cond], nome=senao)
            self.bloco(no.filhos[1])
            self.emitir('desvia', no, nome=fim)
            self.emitir('rotulo', nome=senao)
            self.bloco(no.filhos[2])
            self.emitir('rotulo', nome=fim)
        else:
            fim = self.novo_rotulo()
            self.emitir('seFalso', no, args=[cond], nome=fim)
            self.bloco(no.filhos[1])
            self.emitir('rotulo', nome=fim)

    # ---- expressoes: cada uma devolve o Operando onde o valor vai estar
    def expressao(self, no):
        rotulo = no.rotulo.split()[0]
        if rotulo == 'literal':
            tipo = no.extra['tipo']
            valor = decodificar_texto(no.extra['valor']) if tipo == 'texto' else no.extra['valor']
            return Operando('const', valor, tipo)
        if rotulo == 'variavel':
            return self.variavel(no.extra['simbolo'])
        if rotulo == 'chamada':
            return self.chamada(no)
        if rotulo == 'unario':
            a = self.expressao(no.filhos[0])
            t = self.novo_tmp()
            self.emitir('un', no, dest=t, args=[a], sub=no.extra['op'])
            return t
        return self.binario(no)

    def binario(self, no):
        op = no.extra['op']
        esq, dir_ = no.filhos
        # esquerda primeiro, depois direita: a ordem importa quando ha chamadas
        a = self.expressao(esq)
        b = self.expressao(dir_)
        te, td = esq.extra['tipo'], dir_.extra['tipo']
        if op in ARITMETICOS or op in RELACIONAIS:
            if te == 'real' or td == 'real':           # promove SO o lado inteiro
                a = self.converter(a, te, 'real', no)
                b = self.converter(b, td, 'real', no)
        t = self.novo_tmp()
        self.emitir('bin', no, dest=t, args=[a, b], sub=op)
        return t

    def chamada(self, no):
        sim = no.extra['simbolo']
        args = []
        for arg, tipo_param in zip(no.filhos, sim.parametros):
            valor = self.expressao(arg)
            args.append(self.converter(valor, arg.extra['tipo'], tipo_param, no))
        # chamada de funcao nao-vazio como comando tambem produz um valor: vai
        # para um temporario que ninguem le, e a pilha da VM fica equilibrada
        dest = self.novo_tmp() if sim.tipo != 'vazio' else None
        self.emitir('chama', no, dest=dest, args=args, nome=sim.nome)
        return dest


def gerar(arvore, tabela):
    """Devolve o codigo de tres enderecos."""
    return Tradutor().programa_(arvore)


def despejar(codigo):
    """Devolve as linhas do --ir."""
    linhas = []
    for f in codigo.funcoes:
        params = ', '.join(f'{n} {t}' for n, t in f.params)
        linhas.append(f'funcao {f.nome} {f.tipo} ({params})')
        linhas.extend(str(i) for i in f.insts)
        linhas.append('fim')
    return linhas
