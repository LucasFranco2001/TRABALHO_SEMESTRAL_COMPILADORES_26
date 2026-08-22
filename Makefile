# Trabalho semestral de Compiladores — MPL
#
#   make verificar E=1     confere a Entrega 1
#   make verificar E=4     confere a Entrega 4 (e as anteriores)
#   make verificar         confere as quatro
#   make evidencias E=1    grava evidencias/verificacao-1.txt para entregar
#   make exemplo           compila e roda um programa de exemplo
#   make limpar            apaga os .mplb gerados

PY := python3
E  :=

.PHONY: verificar evidencias exemplo limpar autoteste ajuda

ajuda:
	@sed -n '/^# Trabalho/,/^$$/p' Makefile | sed 's/^# \{0,1\}//'

verificar:
	@$(PY) verificar.py $(if $(E),$(E),todas)

evidencias:
	@if [ -z "$(E)" ]; then echo "diga qual: make evidencias E=1"; exit 1; fi
	@mkdir -p evidencias
	@$(PY) verificar.py $(E) > evidencias/verificacao-$(E).txt 2>&1; \
	  estado=$$?; \
	  echo "gravado em evidencias/verificacao-$(E).txt"; \
	  if [ $$estado -ne 0 ]; then \
	    echo "ATENCAO: a verificacao falhou. A evidencia registra a falha —"; \
	    echo "e isso e melhor do que entregar sem evidencia nenhuma."; \
	  fi

exemplo:
	@./compilar exemplos/ola.mpl && ./executar exemplos/ola.mplb

limpar:
	@find . -name '*.mplb' -delete
	@echo "os .mplb foram apagados"

autoteste:
	@./autoteste.sh
