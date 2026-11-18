// Laboratorio de numeros: recursao direta e mutua, divisao inteira, resto,
// reais, texto e logica, tudo no mesmo programa.

funcao inteiro mdc(inteiro a, inteiro b) {
  se (b == 0) {
    retorne a;
  }
  retorne mdc(b, a % b);
}

funcao logico ehPrimo(inteiro n) {
  se (n < 2) {
    retorne falso;
  }
  inteiro d = 2;
  enquanto (d * d <= n) {
    se (n % d == 0) {
      retorne falso;
    }
    d = d + 1;
  }
  retorne verdadeiro;
}

funcao inteiro somaDivisores(inteiro n) {
  inteiro soma = 0;
  inteiro d = 1;
  enquanto (d < n) {
    se (n % d == 0) {
      soma = soma + d;
    }
    d = d + 1;
  }
  retorne soma;
}

funcao inteiro passosCollatz(inteiro n) {
  inteiro passos = 0;
  enquanto (n != 1) {
    se (n % 2 == 0) {
      n = n / 2;
    } senao {
      n = 3 * n + 1;
    }
    passos = passos + 1;
  }
  retorne passos;
}

// Metodo de Newton: cada volta melhora a estimativa da raiz.
funcao real raiz(real x) {
  real r = x;
  inteiro volta = 0;
  enquanto (volta < 20) {
    r = (r + x / r) / 2.0;
    volta = volta + 1;
  }
  retorne r;
}

funcao inteiro fib(inteiro n) {
  se (n < 2) {
    retorne n;
  }
  retorne fib(n - 1) + fib(n - 2);
}

funcao inteiro fatorial(inteiro n) {
  se (n <= 1) {
    retorne 1;
  }
  retorne n * fatorial(n - 1);
}

// Recursao mutua: uma chama a outra, e nenhuma delas e a primeira do arquivo.
funcao logico ehPar(inteiro n) {
  se (n == 0) {
    retorne verdadeiro;
  }
  retorne ehImpar(n - 1);
}

funcao logico ehImpar(inteiro n) {
  se (n == 0) {
    retorne falso;
  }
  retorne ehPar(n - 1);
}

funcao vazio principal() {
  escreva("== mdc ==");
  escreva(mdc(1071, 462));

  escreva("== primos ate 40 ==");
  inteiro n = 2;
  enquanto (n <= 40) {
    se (ehPrimo(n)) {
      escreva(n);
    }
    n = n + 1;
  }

  escreva("== numeros perfeitos ate 500 ==");
  inteiro p = 2;
  enquanto (p <= 500) {
    se (somaDivisores(p) == p) {
      escreva(p);
    }
    p = p + 1;
  }

  escreva("== Collatz de 27 (passos ate chegar a 1) ==");
  escreva(passosCollatz(27));

  escreva("== raiz de 2 por Newton ==");
  escreva(raiz(2.0));

  escreva("== fibonacci(20) e fatorial(12) ==");
  escreva(fib(20));
  escreva(fatorial(12));

  escreva("== recursao mutua ==");
  escreva(ehPar(10));
  escreva(ehImpar(7));
  escreva(ehPar(7));

  escreva("== divisao inteira e resto ==");
  real metade = 7 / 2;
  escreva(metade);
  escreva(-7 / 2);
  escreva(-7 % 3);
}
