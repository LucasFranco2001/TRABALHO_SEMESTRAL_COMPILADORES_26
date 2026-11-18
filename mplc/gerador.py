"""
Entrega 4, segunda metade — geracao do codigo executavel.

Traduz o codigo de tres enderecos para o formato que a VM de voces executa.
O formato do .mplb e de voces, com uma exigencia: tem que ser TEXTO legivel.
Na apresentacao a gente vai abrir um .mplb e ler junto.

Leiam antes: CONTRATOS.md secao 6.

O nosso formato (conjunto de instrucoes completo no README.md):

    mplb 1
    funcao fatorial params 1 locais 4
      CARREGA 0 ; n @2:7
      EMPILHA 1 @2:12
      MENORIGUAL @2:9
      ...
    fim

Uma VM de pilha com locais numerados. Cada variavel e cada temporario do
codigo de tres enderecos vira um LOCAL (um slot numerado) da funcao; uma
linha de tres enderecos vira "empilha os operandos, opera, guarda no destino".
O sufixo @linha:coluna e do fonte, e serve ao erro de execucao.
"""
from mplc.intermediario import texto_constante

BINARIOS = {
    '+': 'SOMA', '-': 'SUB', '*': 'MULT', '/': 'DIV', '%': 'RESTO',
    '==': 'IGUAL', '!=': 'DIFERENTE', '<': 'MENOR', '<=': 'MENORIGUAL',
    '>': 'MAIOR', '>=': 'MAIORIGUAL', 'e': 'E', 'ou': 'OU',
}
UNARIOS = {'-': 'NEG', 'nao': 'NAO'}


class _Funcao:
    """Gera o corpo de uma funcao e numera os locais por ordem de aparicao."""

    def __init__(self, f):
        self.f = f
        self.slots = {}
        self.corpo = []
        for nome, _ in f.params:            # os parametros ocupam os primeiros locais
            self.slot(nome)

    def slot(self, nome):
        if nome not in self.slots:
            self.slots[nome] = len(self.slots)
        return self.slots[nome]

    def emitir(self, texto, inst=None):
        if inst is not None and inst.linha:
            texto += f' @{inst.linha}:{inst.coluna}'
        self.corpo.append('  ' + texto if not texto.endswith(':') else texto)

    def empilhar(self, op, inst):
        if op.tipo_op == 'const':
            self.emitir(f'EMPILHA {texto_constante(op.tipo, op.valor)}', inst)
        else:
            self.emitir(f'CARREGA {self.slot(op.valor)} ; {op.valor}', inst)

    def guardar(self, dest, inst):
        self.emitir(f'GUARDA {self.slot(dest.valor)} ; {dest.valor}', inst)

    def traduzir(self, i):
        op = i.op
        if op == 'rotulo':
            self.emitir(f'{i.nome}:')
        elif op == 'copia':
            self.empilhar(i.args[0], i)
            self.guardar(i.dest, i)
        elif op == 'bin':
            self.empilhar(i.args[0], i)
            self.empilhar(i.args[1], i)
            self.emitir(BINARIOS[i.sub], i)
            self.guardar(i.dest, i)
        elif op == 'un':
            self.empilhar(i.args[0], i)
            self.emitir(UNARIOS[i.sub], i)
            self.guardar(i.dest, i)
        elif op == 'conv':
            self.empilhar(i.args[0], i)
            self.emitir('PARAREAL', i)
            self.guardar(i.dest, i)
        elif op == 'chama':
            for a in i.args:
                self.empilhar(a, i)
            self.emitir(f'CHAMA {i.nome} {len(i.args)}', i)
            if i.dest is not None:
                self.guardar(i.dest, i)
        elif op == 'escreva':
            self.empilhar(i.args[0], i)
            self.emitir('ESCREVE', i)
        elif op == 'retorne':
            if i.args:
                self.empilhar(i.args[0], i)
                self.emitir('RETORNAVAL', i)
            else:
                self.emitir('RETORNA', i)
        elif op == 'desvia':
            self.emitir(f'DESVIA {i.nome}', i)
        elif op == 'seFalso':
            self.empilhar(i.args[0], i)
            self.emitir(f'DESVIAFALSO {i.nome}', i)

    def texto(self):
        for i in self.f.insts:
            self.traduzir(i)
        cab = f'funcao {self.f.nome} params {len(self.f.params)} locais {len(self.slots)}'
        return [cab] + self.corpo + ['fim']


def gerar(codigo_intermediario):
    """Devolve as linhas do arquivo .mplb."""
    linhas = ['mplb 1']
    for f in codigo_intermediario.funcoes:
        linhas.extend(_Funcao(f).texto())
    return linhas
