"""
Entrega 2 — analise sintatica.

Transformar a lista de tokens numa arvore.

Descida recursiva, uma funcao por nivel de precedencia, na ordem da secao 3.3
da especificacao (da mais fraca para a mais forte):

    ou -> e -> igualdade -> relacional -> aditiva -> multiplicativa
       -> unaria -> primaria

Cada nivel binario e um LACO, nao uma recursao a direita: le o operando da
esquerda, e enquanto aparecer um operador do seu nivel, pendura o que ja foi
lido como filho esquerdo de um novo no. E isso que faz `10 - 4 - 3` virar
`(10 - 4) - 3` (associativo a esquerda). O unario, ao contrario, chama a si
mesmo — `nao nao x` e `- - x` sao associativos a direita.

A gramatica completa, em EBNF, esta no README.md.
"""
from mplc.erros import ErroMPL


class No:
    """Um no da arvore. O rotulo e o que sai no --ast."""

    def __init__(self, rotulo, filhos=None, linha=0, coluna=0, **extra):
        self.rotulo = rotulo      # 'binario +', 'literal inteiro 1', 'bloco', ...
        self.filhos = filhos or []
        self.linha = linha
        self.coluna = coluna
        self.extra = extra        # o que a semantica quiser pendurar depois


# token de tipo -> nome do tipo como sai na arvore
TIPOS = {
    'TIPO_INTEIRO': 'inteiro',
    'TIPO_REAL': 'real',
    'TIPO_LOGICO': 'logico',
    'TIPO_TEXTO': 'texto',
    'TIPO_VAZIO': 'vazio',
}

# os niveis binarios, do mais fraco para o mais forte (secao 3.3)
OPS_OU = {'OU'}
OPS_E = {'E'}
OPS_IGUALDADE = {'IGUAL', 'DIFERENTE'}
OPS_RELACIONAL = {'MENOR', 'MENOR_IGUAL', 'MAIOR', 'MAIOR_IGUAL'}
OPS_ADITIVA = {'MAIS', 'MENOS'}
OPS_MULTIPLICATIVA = {'VEZES', 'DIVIDE', 'RESTO'}

# como o token aparece na mensagem de erro
NOMES = {
    'FIM_ARQUIVO': 'fim do arquivo',
    'PONTO_VIRGULA': "';'",
    'ABRE_PAR': "'('",
    'FECHA_PAR': "')'",
    'ABRE_CHAVE': "'{'",
    'FECHA_CHAVE': "'}'",
    'VIRGULA': "','",
    'ATRIBUI': "'='",
    'ID': 'um nome',
    'FUNCAO': "'funcao'",
}


def _descrever(tok):
    if tok.tipo == 'FIM_ARQUIVO':
        return 'o fim do arquivo'
    return repr(tok.lexema)


class Parser:
    def __init__(self, tokens):
        self.tokens = tokens
        self.pos = 0

    # ------------------------------------------------------------ utilitarios

    def atual(self):
        return self.tokens[self.pos]

    def proximo(self):
        """O token depois do atual (para decidir entre atribuicao e chamada)."""
        if self.pos + 1 < len(self.tokens):
            return self.tokens[self.pos + 1]
        return self.tokens[-1]

    def avancar(self):
        tok = self.tokens[self.pos]
        if tok.tipo != 'FIM_ARQUIVO':
            self.pos += 1
        return tok

    def ve(self, *tipos):
        return self.atual().tipo in tipos

    def erro(self, esperado):
        """O erro fica no token que APARECEU, nunca no fim do anterior."""
        tok = self.atual()
        raise ErroMPL('sintatico', tok.linha, tok.coluna,
                      f'esperava {esperado}, mas veio {_descrever(tok)}')

    def exigir(self, tipo, esperado=None):
        if self.atual().tipo != tipo:
            self.erro(esperado or NOMES.get(tipo, tipo))
        return self.avancar()

    def tipo(self):
        if not self.ve(*TIPOS):
            self.erro('um tipo (inteiro, real, logico, texto ou vazio)')
        return TIPOS[self.avancar().tipo]

    # --------------------------------------------------------------- programa

    def programa(self):
        # programa = { funcao } FIM_ARQUIVO
        inicio = self.atual()
        funcoes = []
        while not self.ve('FIM_ARQUIVO'):
            funcoes.append(self.funcao())
        return No('programa', funcoes, inicio.linha, inicio.coluna)

    def funcao(self):
        # funcao = 'funcao' tipo ID '(' [ parametros ] ')' bloco
        inicio = self.exigir('FUNCAO', "'funcao'")
        tipo = self.tipo()
        nome = self.exigir('ID', 'o nome da funcao')
        self.exigir('ABRE_PAR')
        params = self.parametros()
        self.exigir('FECHA_PAR')
        corpo = self.bloco()
        return No(f'funcao {nome.lexema} {tipo}', [params, corpo],
                  inicio.linha, inicio.coluna, nome=nome.lexema, tipo=tipo)

    def parametros(self):
        # parametros = parametro { ',' parametro }
        inicio = self.atual()
        lista = []
        if not self.ve('FECHA_PAR'):
            lista.append(self.parametro())
            while self.ve('VIRGULA'):
                self.avancar()
                lista.append(self.parametro())
        return No('parametros', lista, inicio.linha, inicio.coluna)

    def parametro(self):
        # parametro = tipo ID
        inicio = self.atual()
        tipo = self.tipo()
        nome = self.exigir('ID', 'o nome do parametro')
        return No(f'parametro {nome.lexema} {tipo}', [], inicio.linha, inicio.coluna,
                  nome=nome.lexema, tipo=tipo)

    # --------------------------------------------------------------- comandos

    def bloco(self):
        # bloco = '{' { comando } '}'
        inicio = self.exigir('ABRE_CHAVE')
        comandos = []
        while not self.ve('FECHA_CHAVE'):
            comandos.append(self.comando())
        self.avancar()
        return No('bloco', comandos, inicio.linha, inicio.coluna)

    def comando(self):
        tok = self.atual()
        if tok.tipo in TIPOS:
            return self.declaracao()
        if tok.tipo == 'SE':
            return self.se()
        if tok.tipo == 'ENQUANTO':
            return self.enquanto()
        if tok.tipo == 'ESCREVA':
            return self.escreva()
        if tok.tipo == 'RETORNE':
            return self.retorne()
        if tok.tipo == 'ABRE_CHAVE':
            return self.bloco()        # bloco solto: abre um escopo novo (4.7)
        if tok.tipo == 'ID':
            if self.proximo().tipo == 'ATRIBUI':
                return self.atribuicao()
            if self.proximo().tipo == 'ABRE_PAR':
                chamada = self.chamada()
                self.exigir('PONTO_VIRGULA')
                return chamada
            self.avancar()
            self.erro("'=' ou '(' depois do nome")
        if tok.tipo == 'FIM_ARQUIVO':
            self.erro("'}' para fechar o bloco")
        self.erro('um comando')

    def declaracao(self):
        # declaracao = tipo ID [ '=' expressao ] ';'
        inicio = self.atual()
        tipo = self.tipo()
        nome = self.exigir('ID', 'o nome da variavel')
        filhos = []
        if self.ve('ATRIBUI'):
            self.avancar()
            filhos.append(self.expressao())
        self.exigir('PONTO_VIRGULA')
        return No(f'declaracao {nome.lexema} {tipo}', filhos, inicio.linha, inicio.coluna,
                  nome=nome.lexema, tipo=tipo)

    def atribuicao(self):
        # atribuicao = ID '=' expressao ';'
        nome = self.exigir('ID')
        self.exigir('ATRIBUI')
        valor = self.expressao()
        self.exigir('PONTO_VIRGULA')
        return No(f'atribuicao {nome.lexema}', [valor], nome.linha, nome.coluna,
                  nome=nome.lexema)

    def se(self):
        # se = 'se' '(' expressao ')' bloco [ 'senao' bloco ]
        inicio = self.exigir('SE')
        self.exigir('ABRE_PAR')
        condicao = self.expressao()
        self.exigir('FECHA_PAR')
        filhos = [condicao, self.bloco()]
        if self.ve('SENAO'):
            self.avancar()
            filhos.append(self.bloco())
        return No('se', filhos, inicio.linha, inicio.coluna)

    def enquanto(self):
        # enquanto = 'enquanto' '(' expressao ')' bloco
        inicio = self.exigir('ENQUANTO')
        self.exigir('ABRE_PAR')
        condicao = self.expressao()
        self.exigir('FECHA_PAR')
        corpo = self.bloco()
        return No('enquanto', [condicao, corpo], inicio.linha, inicio.coluna)

    def escreva(self):
        # escreva = 'escreva' '(' expressao ')' ';'
        inicio = self.exigir('ESCREVA')
        self.exigir('ABRE_PAR')
        valor = self.expressao()
        self.exigir('FECHA_PAR')
        self.exigir('PONTO_VIRGULA')
        return No('escreva', [valor], inicio.linha, inicio.coluna)

    def retorne(self):
        # retorne = 'retorne' [ expressao ] ';'
        inicio = self.exigir('RETORNE')
        filhos = []
        if not self.ve('PONTO_VIRGULA'):
            filhos.append(self.expressao())
        self.exigir('PONTO_VIRGULA')
        return No('retorne', filhos, inicio.linha, inicio.coluna)

    # ------------------------------------------------------------- expressoes

    def expressao(self):
        return self.ou()

    def _binario(self, operadores, proximo_nivel):
        """
        Um nivel binario associativo a esquerda:
            nivel = proximo { op proximo }
        O laco (e nao a recursao a direita) e o que garante (a - b) - c.
        """
        esquerda = proximo_nivel()
        while self.ve(*operadores):
            op = self.avancar()
            direita = proximo_nivel()
            esquerda = No(f'binario {op.lexema}', [esquerda, direita], op.linha, op.coluna,
                          op=op.lexema)
        return esquerda

    def ou(self):              # 1. ou
        return self._binario(OPS_OU, self.e)

    def e(self):               # 2. e
        return self._binario(OPS_E, self.igualdade)

    def igualdade(self):       # 3. == !=
        return self._binario(OPS_IGUALDADE, self.relacional)

    def relacional(self):      # 4. < <= > >=
        return self._binario(OPS_RELACIONAL, self.aditiva)

    def aditiva(self):         # 5. + -
        return self._binario(OPS_ADITIVA, self.multiplicativa)

    def multiplicativa(self):  # 6. * / %
        return self._binario(OPS_MULTIPLICATIVA, self.unaria)

    def unaria(self):          # 7. nao, - unario (associativos a direita)
        if self.ve('NAO', 'MENOS'):
            op = self.avancar()
            operando = self.unaria()
            return No(f'unario {op.lexema}', [operando], op.linha, op.coluna, op=op.lexema)
        return self.primaria()

    def primaria(self):        # 8. chamada, ( ), literais e variaveis
        tok = self.atual()
        if tok.tipo == 'INTEIRO':
            self.avancar()
            return No(f'literal inteiro {int(tok.lexema)}', [], tok.linha, tok.coluna,
                      tipo='inteiro', valor=int(tok.lexema))
        if tok.tipo == 'REAL':
            self.avancar()
            return No(f'literal real {float(tok.lexema):.6f}', [], tok.linha, tok.coluna,
                      tipo='real', valor=float(tok.lexema))
        if tok.tipo == 'LOGICO':
            self.avancar()
            return No(f'literal logico {tok.lexema}', [], tok.linha, tok.coluna,
                      tipo='logico', valor=tok.lexema == 'verdadeiro')
        if tok.tipo == 'TEXTO':
            self.avancar()
            return No(f'literal texto {tok.lexema}', [], tok.linha, tok.coluna,
                      tipo='texto', valor=tok.lexema)
        if tok.tipo == 'ID':
            if self.proximo().tipo == 'ABRE_PAR':
                return self.chamada()
            self.avancar()
            return No(f'variavel {tok.lexema}', [], tok.linha, tok.coluna, nome=tok.lexema)
        if tok.tipo == 'ABRE_PAR':
            self.avancar()
            dentro = self.expressao()
            self.exigir('FECHA_PAR')
            return dentro          # o parentese nao vira no: a forma da arvore ja diz tudo
        self.erro('uma expressao')

    def chamada(self):
        # chamada = ID '(' [ expressao { ',' expressao } ] ')'
        nome = self.exigir('ID')
        self.exigir('ABRE_PAR')
        args = []
        if not self.ve('FECHA_PAR'):
            args.append(self.expressao())
            while self.ve('VIRGULA'):
                self.avancar()
                args.append(self.expressao())
        self.exigir('FECHA_PAR')
        return No(f'chamada {nome.lexema}', args, nome.linha, nome.coluna, nome=nome.lexema)


def analisar(tokens):
    """Recebe a lista de Token. Devolve a raiz da arvore (um No 'programa')."""
    return Parser(tokens).programa()


def despejar(no, nivel=0, saida=None):
    """Imprime a arvore no formato do --ast. Ja esta pronto: dois espacos por nivel."""
    saida = saida if saida is not None else []
    saida.append('  ' * nivel + no.rotulo)
    for f in no.filhos:
        despejar(f, nivel + 1, saida)
    return saida
