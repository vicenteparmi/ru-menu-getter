# Coleta da UFRGS

O CampusDine coleta os cardápios do RU01 ao RU06 na [página da PRAE](https://www.ufrgs.br/prae/cardapio-restaurante-universitario/). O coletor valida as datas pelo cabeçalho da tabela e exclui o RU01 Anexo, que possui cardápio próprio e não está no catálogo.

Para coletar sem gravar, execute `ruby UFRGS/UFRGS.rb --dry-run` a partir da raiz do repositório. A execução com `BASE_URL` e `FIREBASE_KEY` configuradas grava os menus e relê cada registro para conferir o resultado.

A tarefa `ufrgs-menu-scraper` roda no Cloud Run em `southamerica-east1`. O Cloud Scheduler dispara a coleta nas segundas e terças às 8h, no horário de Brasília. O coletor usa esse ambiente porque o portal da PRAE encerrou conexões vindas dos runners hospedados do GitHub Actions.
