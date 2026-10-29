"""
Entrega 3 — analise semantica.

Tabela de simbolos, escopos aninhados e verificacao de tipos.

Tres coisas que costumam ser esquecidas e valem nota:
  - o corpo de uma funcao abre DOIS escopos (o dos parametros e o do bloco);
  - uma funcao pode ser chamada antes de aparecer no arquivo, entao a
    primeira passada so coleta assinaturas;
  - funcao com retorno declarado precisa garantir o retorno em TODOS os
    caminhos.

Leiam antes: LINGUAGEM.md secoes 3 a 5, e CONTRATOS.md secao 4.

Representacao dos escopos: cada Escopo guarda um dicionario com os seus
proprios simbolos e uma referencia ao escopo pai (dicionario encadeado).
Procurar um nome e subir a cadeia de pais. Todos os escopos tambem ficam
numa lista, na ordem em que foram abertos, que e a ordem do --tabela.
"""
from mplc.erros import ErroMPL

NUMERICOS = ('inteiro', 'real')


class Simbolo:
    """Um nome conhecido: variavel, parametro ou funcao."""

    def __init__(self, nome, categoria, tipo, linha, parametros=None):
        self.nome = nome
        self.categoria = categoria          # 'variavel', 'parametro' ou 'funcao'
        self.tipo = tipo                    # tipo da variavel, ou tipo de retorno
        self.linha = linha
        self.parametros = parametros or []  # funcao: lista de tipos dos parametros
        self.escopo = None                  # escopo onde foi declarado (preenchido ao declarar)

    def descricao(self):
        if self.categoria == 'funcao':
            return f"{self.nome}|funcao|{self.tipo}({','.join(self.parametros)})|{self.linha}"
        return f"{self.nome}|{self.categoria}|{self.tipo}|{self.linha}"


class Escopo:
    """Um escopo: seus simbolos (em ordem de declaracao) e o escopo que o contem."""

    def __init__(self, numero, descricao, pai):
        self.numero = numero
        self.descricao = descricao
        self.pai = pai
        self.simbolos = {}                  # dict mantem a ordem de insercao

    def declarar(self, simbolo):
        simbolo.escopo = self
        self.simbolos[simbolo.nome] = simbolo

    def procurar(self, nome):
        """Sobe a cadeia de pais; o primeiro que tiver o nome esconde os de fora."""
        escopo = self
        while escopo is not None:
            if nome in escopo.simbolos:
                return escopo.simbolos[nome]
            escopo = escopo.pai
        return None


class Tabela:
    """Todos os escopos do programa, na ordem em que foram abertos."""

    def __init__(self):
        self.escopos = []
        self.global_ = self.abrir('global', None)

    def abrir(self, descricao, pai):
        escopo = Escopo(len(self.escopos), descricao, pai)
        self.escopos.append(escopo)
        return escopo


def _erro(no, mensagem):
    return ErroMPL('semantico', no.linha, no.coluna, mensagem)


def _cabe(destino, origem):
    """3.1: so existe uma conversao implicita, inteiro -> real."""
    return origem == destino or (destino == 'real' and origem == 'inteiro')


class Analisador:
    def __init__(self):
        self.tabela = Tabela()
        self.escopo = self.tabela.global_    # escopo corrente
        self.funcao = None                   # Simbolo da funcao que esta sendo analisada

    # ------------------------------------------------------- primeira passada

    def coletar(self, raiz):
        """So assinaturas: assim uma funcao pode ser chamada antes de aparecer."""
        for f in raiz.filhos:
            nome, tipo = f.extra['nome'], f.extra['tipo']
            params = f.filhos[0].filhos
            if nome in self.tabela.global_.simbolos:
                raise _erro(f, f"a funcao '{nome}' ja foi declarada")
            simbolo = Simbolo(nome, 'funcao', tipo, f.linha, [p.extra['tipo'] for p in params])
            self.tabela.global_.declarar(simbolo)
            f.extra['simbolo'] = simbolo
        principal = self.tabela.global_.simbolos.get('principal')
        if principal is None:
            raise ErroMPL('semantico', raiz.linha or 1, raiz.coluna or 1,
                          "falta a funcao 'principal'")
        if principal.parametros or principal.tipo != 'vazio':
            f = next(x for x in raiz.filhos if x.extra['nome'] == 'principal')
            raise _erro(f, "'principal' deve ser 'vazio' e nao ter parametros")

    # --------------------------------------------------------- segunda passada

    def programa(self, raiz):
        self.coletar(raiz)
        for f in raiz.filhos:
            self.funcao_corpo(f)

    def funcao_corpo(self, f):
        self.funcao = f.extra['simbolo']
        # primeiro escopo da funcao: os parametros
        escopo = self.tabela.abrir(f"funcao {f.extra['nome']}", self.tabela.global_)
        f.extra['escopo'] = escopo
        self.escopo = escopo
        for p in f.filhos[0].filhos:
            if p.extra['tipo'] == 'vazio':
                raise _erro(p, f"o parametro '{p.extra['nome']}' nao pode ser 'vazio'")
            if p.extra['nome'] in escopo.simbolos:
                raise _erro(p, f"o parametro '{p.extra['nome']}' esta repetido")
            sim = Simbolo(p.extra['nome'], 'parametro', p.extra['tipo'], p.linha)
            escopo.declarar(sim)
            p.extra['simbolo'] = sim
        # segundo escopo da funcao: o bloco, onde moram as variaveis locais
        garante = self.bloco(f.filhos[1])
        self.escopo = self.tabela.global_
        if self.funcao.tipo != 'vazio' and not garante:
            raise _erro(f, f"a funcao '{self.funcao.nome}' nao retorna em todos os caminhos")
        self.funcao = None

    def bloco(self, no):
        """Abre um escopo, analisa os comandos e fecha. Devolve se garante retorno."""
        escopo = self.tabela.abrir('bloco', self.escopo)
        no.extra['escopo'] = escopo
        self.escopo = escopo
        garante = False
        for c in no.filhos:
            if self.comando(c):
                garante = True
        self.escopo = escopo.pai
        return garante

    # ----------------------------------------------------------------- comandos

    def comando(self, no):
        """Analisa um comando. Devolve True se ele garante o retorno."""
        rotulo = no.rotulo.split()[0]
        if rotulo == 'declaracao':
            self.declaracao(no)
        elif rotulo == 'atribuicao':
            self.atribuicao(no)
        elif rotulo == 'se':
            return self.se(no)
        elif rotulo == 'enquanto':
            self.condicao(no.filhos[0], 'enquanto')
            self.bloco(no.filhos[1])
        elif rotulo == 'escreva':
            self.expressao(no.filhos[0])
        elif rotulo == 'retorne':
            return self.retorne(no)
        elif rotulo == 'bloco':
            return self.bloco(no)
        elif rotulo == 'chamada':
            self.chamada(no)         # como comando, a funcao pode ser 'vazio'
        return False

    def declaracao(self, no):
        nome, tipo = no.extra['nome'], no.extra['tipo']
        if tipo == 'vazio':
            raise _erro(no, f"a variavel '{nome}' nao pode ser 'vazio'")
        if no.filhos:
            # o inicializador e analisado ANTES de o nome existir: 'inteiro x = x;'
            # nao enxerga o x que esta nascendo
            valor = self.expressao(no.filhos[0])
            if not _cabe(tipo, valor):
                raise _erro(no, f"nao da para guardar '{valor}' em '{nome}' ({tipo})")
        if nome in self.escopo.simbolos:
            raise _erro(no, f"'{nome}' ja foi declarado neste escopo")
        sim = Simbolo(nome, 'variavel', tipo, no.linha)
        self.escopo.declarar(sim)
        no.extra['simbolo'] = sim

    def atribuicao(self, no):
        nome = no.extra['nome']
        sim = self.escopo.procurar(nome)
        if sim is None:
            raise _erro(no, f"'{nome}' nao foi declarado")
        if sim.categoria == 'funcao':
            raise _erro(no, f"'{nome}' e uma funcao, nao uma variavel")
        valor = self.expressao(no.filhos[0])
        if not _cabe(sim.tipo, valor):
            raise _erro(no, f"nao da para atribuir '{valor}' a '{nome}' ({sim.tipo})")
        no.extra['simbolo'] = sim

    def condicao(self, no, quem):
        tipo = self.expressao(no)
        if tipo != 'logico':
            raise _erro(no, f"a condicao do '{quem}' precisa ser logica, mas e '{tipo}'")

    def se(self, no):
        self.condicao(no.filhos[0], 'se')
        entao = self.bloco(no.filhos[1])
        if len(no.filhos) == 3:
            senao = self.bloco(no.filhos[2])
            return entao and senao       # so o se/senao com retorno nos dois lados garante
        return False                     # se sem senao NUNCA garante retorno

    def retorne(self, no):
        esperado = self.funcao.tipo
        if no.filhos:
            if esperado == 'vazio':
                raise _erro(no, "funcao 'vazio' nao retorna valor")
            valor = self.expressao(no.filhos[0])
            if not _cabe(esperado, valor):
                raise _erro(no, f"retorno '{valor}' nao cabe em '{esperado}'")
        elif esperado != 'vazio':
            raise _erro(no, f"a funcao '{self.funcao.nome}' precisa retornar '{esperado}'")
        return True

    # --------------------------------------------------------------- expressoes

    def expressao(self, no):
        """Devolve o tipo da expressao e o grava em no.extra['tipo']. Nunca devolve 'vazio'."""
        tipo = self._tipo(no)
        if tipo == 'vazio':
            raise _erro(no, "uma funcao 'vazio' nao pode ser usada como valor")
        no.extra['tipo'] = tipo
        return tipo

    def _tipo(self, no):
        rotulo = no.rotulo.split()[0]
        if rotulo == 'literal':
            return no.extra['tipo']
        if rotulo == 'variavel':
            sim = self.escopo.procurar(no.extra['nome'])
            if sim is None:
                raise _erro(no, f"'{no.extra['nome']}' nao foi declarado")
            if sim.categoria == 'funcao':
                raise _erro(no, f"'{sim.nome}' e uma funcao, nao uma variavel")
            no.extra['simbolo'] = sim
            return sim.tipo
        if rotulo == 'chamada':
            return self.chamada(no)
        if rotulo == 'unario':
            return self.unario(no)
        return self.binario(no)

    def chamada(self, no):
        nome = no.extra['nome']
        sim = self.tabela.global_.simbolos.get(nome)
        if sim is None:
            raise _erro(no, f"a funcao '{nome}' nao existe")
        if len(no.filhos) != len(sim.parametros):
            raise _erro(no, f"'{nome}' espera {len(sim.parametros)} argumento(s), "
                            f"mas recebeu {len(no.filhos)}")
        for i, (arg, esperado) in enumerate(zip(no.filhos, sim.parametros), 1):
            tipo = self.expressao(arg)
            if not _cabe(esperado, tipo):
                raise _erro(arg, f"argumento {i} de '{nome}': '{tipo}' nao cabe em '{esperado}'")
        no.extra['simbolo'] = sim
        no.extra['tipo'] = sim.tipo
        return sim.tipo

    def unario(self, no):
        op = no.extra['op']
        tipo = self.expressao(no.filhos[0])
        if op == 'nao':
            if tipo != 'logico':
                raise _erro(no, f"'nao' exige 'logico', mas recebeu '{tipo}'")
            return 'logico'
        if tipo not in NUMERICOS:
            raise _erro(no, f"'-' exige um numero, mas recebeu '{tipo}'")
        return tipo

    def binario(self, no):
        op = no.extra['op']
        # os dois lados sao sempre analisados (e avaliados: nao ha curto-circuito)
        e = self.expressao(no.filhos[0])
        d = self.expressao(no.filhos[1])
        ambos_num = e in NUMERICOS and d in NUMERICOS
        resultado = 'inteiro' if (e == 'inteiro' and d == 'inteiro') else 'real'

        if op == '+':
            if ambos_num:
                return resultado
            if e == 'texto' and d == 'texto':
                return 'texto'
            raise _erro(no, f"'+' nao aceita '{e}' e '{d}'")
        if op in ('-', '*', '/'):
            if ambos_num:
                return resultado
            raise _erro(no, f"'{op}' exige numeros, mas recebeu '{e}' e '{d}'")
        if op == '%':
            if e == 'inteiro' and d == 'inteiro':
                return 'inteiro'
            raise _erro(no, f"'%' exige dois 'inteiro', mas recebeu '{e}' e '{d}'")
        if op in ('==', '!='):
            if ambos_num or e == d:
                return 'logico'
            raise _erro(no, f"'{op}' compara tipos iguais, mas recebeu '{e}' e '{d}'")
        if op in ('<', '<=', '>', '>='):
            if ambos_num:
                return 'logico'
            raise _erro(no, f"'{op}' exige numeros, mas recebeu '{e}' e '{d}'")
        # 'e' e 'ou'
        if e == 'logico' and d == 'logico':
            return 'logico'
        raise _erro(no, f"'{op}' exige dois 'logico', mas recebeu '{e}' e '{d}'")


def analisar(arvore):
    """Percorre a arvore, monta a tabela e confere os tipos. Devolve a tabela."""
    analisador = Analisador()
    analisador.programa(arvore)
    return analisador.tabela


def despejar(tabela):
    """Devolve as linhas do --tabela, no formato da secao 4 do contrato."""
    linhas = []
    for escopo in tabela.escopos:
        if escopo.pai is None:
            linhas.append(f"escopo {escopo.numero} {escopo.descricao}")
        else:
            linhas.append(f"escopo {escopo.numero} {escopo.descricao} pai {escopo.pai.numero}")
        for simbolo in escopo.simbolos.values():
            linhas.append('  ' + simbolo.descricao())
    return linhas
