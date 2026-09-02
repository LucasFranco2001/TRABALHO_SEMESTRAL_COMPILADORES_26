"""
Entrega 1 — analise lexica.

Transformar o texto do programa numa lista de tokens.

O que voces tem que devolver: uma lista de Token. O ultimo elemento e sempre
um token FIM_ARQUIVO. A regra de posicao dele esta em CONTRATOS.md, secao 7.

Leiam antes: LINGUAGEM.md secao 2, e CONTRATOS.md secao 2.
"""
from mplc.erros import ErroMPL


class Token:
    __slots__ = ('tipo', 'lexema', 'linha', 'coluna')

    def __init__(self, tipo, lexema, linha, coluna):
        self.tipo = tipo          # 'ID', 'INTEIRO', 'MAIS', ... (a lista esta no contrato)
        self.lexema = lexema      # o texto exato como apareceu no fonte
        self.linha = linha
        self.coluna = coluna      # a coluna do PRIMEIRO caractere do token

    def __str__(self):
        # esta e a linha que o --tokens imprime; nao mexam no formato
        return f"{self.linha},{self.coluna},{self.tipo},{self.lexema}"


PALAVRAS_RESERVADAS = {
    'funcao': 'FUNCAO',
    'retorne': 'RETORNE',
    'se': 'SE',
    'senao': 'SENAO',
    'enquanto': 'ENQUANTO',
    'escreva': 'ESCREVA',
    'inteiro': 'TIPO_INTEIRO',
    'real': 'TIPO_REAL',
    'logico': 'TIPO_LOGICO',
    'texto': 'TIPO_TEXTO',
    'vazio': 'TIPO_VAZIO',
    'verdadeiro': 'LOGICO',
    'falso': 'LOGICO',
    'e': 'E',
    'ou': 'OU',
    'nao': 'NAO',
}

# Precisam ser testados antes dos operadores de um caractere: '<=' antes de
# '<', e o mesmo para '==', '!=' e '>='. E a armadilha desta entrega.
OPERADORES_DOIS_CHARES = {
    '==': 'IGUAL',
    '!=': 'DIFERENTE',
    '<=': 'MENOR_IGUAL',
    '>=': 'MAIOR_IGUAL',
}

OPERADORES_UM_CHAR = {
    '+': 'MAIS',
    '-': 'MENOS',
    '*': 'VEZES',
    '%': 'RESTO',
    '<': 'MENOR',
    '>': 'MAIOR',
    '=': 'ATRIBUI',
    '(': 'ABRE_PAR',
    ')': 'FECHA_PAR',
    '{': 'ABRE_CHAVE',
    '}': 'FECHA_CHAVE',
    ',': 'VIRGULA',
    ';': 'PONTO_VIRGULA',
}

ESCAPES_VALIDOS = {'n', 't', '"', '\\'}


def _eh_letra(c):
    return ('a' <= c <= 'z') or ('A' <= c <= 'Z') or c == '_'


def _eh_digito(c):
    return '0' <= c <= '9'


def _eh_alfanum(c):
    return _eh_letra(c) or _eh_digito(c)


def analisar(fonte):
    """Recebe o texto do programa. Devolve a lista de Token."""
    tokens = []
    i = 0
    n = len(fonte)
    linha = 1
    coluna = 1

    while i < n:
        c = fonte[i]

        if c == '\n':
            i += 1
            linha += 1
            coluna = 1
            continue

        if c in ' \t\r':
            i += 1
            coluna += 1
            continue

        if c == '/' and i + 1 < n and fonte[i + 1] == '/':
            i += 2
            coluna += 2
            while i < n and fonte[i] != '\n':
                i += 1
                coluna += 1
            continue

        if c == '/' and i + 1 < n and fonte[i + 1] == '*':
            l0, c0 = linha, coluna
            i += 2
            coluna += 2
            fechado = False
            while i < n:
                if fonte[i] == '*' and i + 1 < n and fonte[i + 1] == '/':
                    i += 2
                    coluna += 2
                    fechado = True
                    break
                if fonte[i] == '\n':
                    i += 1
                    linha += 1
                    coluna = 1
                else:
                    i += 1
                    coluna += 1
            if not fechado:
                raise ErroMPL('lexico', l0, c0, 'comentario de bloco nao fechado')
            continue

        if _eh_letra(c):
            l0, c0 = linha, coluna
            j = i
            while j < n and _eh_alfanum(fonte[j]):
                j += 1
            palavra = fonte[i:j]
            coluna += j - i
            i = j
            tipo = PALAVRAS_RESERVADAS.get(palavra, 'ID')
            tokens.append(Token(tipo, palavra, l0, c0))
            continue

        if _eh_digito(c):
            l0, c0 = linha, coluna
            j = i
            while j < n and _eh_digito(fonte[j]):
                j += 1
            if j < n and fonte[j] == '.':
                if j + 1 < n and _eh_digito(fonte[j + 1]):
                    k = j + 1
                    while k < n and _eh_digito(fonte[k]):
                        k += 1
                    lexema = fonte[i:k]
                    coluna += k - i
                    i = k
                    tokens.append(Token('REAL', lexema, l0, c0))
                    continue
                col_ponto = c0 + (j - i)
                raise ErroMPL('lexico', l0, col_ponto,
                               'o ponto do numero real exige digito antes e depois')
            lexema = fonte[i:j]
            coluna += j - i
            i = j
            tokens.append(Token('INTEIRO', lexema, l0, c0))
            continue

        if c == '"':
            l0, c0 = linha, coluna
            j = i + 1
            fechado = False
            while j < n:
                cj = fonte[j]
                if cj == '"':
                    j += 1
                    fechado = True
                    break
                if cj == '\n':
                    break
                if cj == '\\':
                    if j + 1 < n and fonte[j + 1] in ESCAPES_VALIDOS:
                        j += 2
                        continue
                    col_barra = coluna + (j - i)
                    raise ErroMPL('lexico', linha, col_barra,
                                   'escape desconhecido dentro de texto')
                j += 1
            if not fechado:
                raise ErroMPL('lexico', l0, c0, 'texto sem fechar na mesma linha')
            lexema = fonte[i:j]
            coluna += j - i
            i = j
            tokens.append(Token('TEXTO', lexema, l0, c0))
            continue

        dois = fonte[i:i + 2]
        if dois in OPERADORES_DOIS_CHARES:
            tokens.append(Token(OPERADORES_DOIS_CHARES[dois], dois, linha, coluna))
            i += 2
            coluna += 2
            continue

        if c == '/':
            tokens.append(Token('DIVIDE', c, linha, coluna))
            i += 1
            coluna += 1
            continue

        if c in OPERADORES_UM_CHAR:
            tokens.append(Token(OPERADORES_UM_CHAR[c], c, linha, coluna))
            i += 1
            coluna += 1
            continue

        raise ErroMPL('lexico', linha, coluna, f'caractere invalido {c!r}')

    tokens.append(Token('FIM_ARQUIVO', '', linha, coluna))
    return tokens
