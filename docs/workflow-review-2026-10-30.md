# Revisão dos workflows — 30/10/2026

Repositório de coleta que alimenta o CampusDine: `vicenteparmi/ru-menu-getter`.
Foram consultadas as 30 execuções mais recentes e os logs das duas falhas de hoje.

- [Daily 41100240918](https://github.com/vicenteparmi/ru-menu-getter/actions/runs/41100240918): UFPR falhou em Matinhos (nenhum cardápio com data explícita) e Toledo (tabela ausente para 30/10). As outras oito unidades foram coletadas, gravadas e relidas com sucesso. UFABC passou; UTFPR foi ignorada conforme o agendamento.
- [Daily 41000057114](https://github.com/vicenteparmi/ru-menu-getter/actions/runs/41000057114): mesmos dois erros UFPR. UFABC falhou após um ReadTimeout e falhas nos dois proxies públicos utilizados.
- Últimas execuções UFV (41098881744) e Unicamp (40928748105): sucesso.
- `vicenteparmi/ru` não retornou execuções no endpoint Actions.

## Alteração proposta

UFABC passa a tentar a origem até três vezes, com open timeout de 10s e read timeout de 20s, e pausas de 2s/4s. Timeout, erros de transporte, HTTP 429/5xx e respostas sem conteúdo de cardápio permitem nova tentativa. HTTP permanente continua falhando imediatamente. Foram removidos os serviços de descoberta e o fallback por proxies públicos; o proxy configurado pelo ambiente continua sendo respeitado. A exaustão das tentativas mantém o job em falha. O parser e os caminhos Firebase permanecem os mesmos.

## Pendências da fonte UFPR

Não há evidência suficiente para mudar o parser de Matinhos ou classificar Toledo como fechado. A fixture de Toledo de 29/10 já contém um cabeçalho futuro de 30/10 sem tabela. Quando essa data chega, a validação corretamente sinaliza a falta. Não se deve fabricar cardápios nem gravar ausência de refeições como se fosse confirmação de fechamento.

A consulta ao vivo neste ambiente falhou no proxy HTTPS por verificação da cadeia de certificado da origem UFPR. Isso limita a confirmação do HTML atual e não comprova indisponibilidade no GitHub Actions, onde oito unidades foram coletadas. É necessário conferir a publicação de Matinhos/Toledo na origem antes de alterar seu tratamento.

Nenhum workflow de produção foi disparado e nenhum dado Firebase foi alterado durante a revisão. A correção de retentativas precisa ser incorporada e observada nas próximas execuções; ela não garante disponibilidade das fontes externas.
