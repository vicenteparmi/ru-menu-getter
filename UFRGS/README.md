# Coleta da UFRGS

O CampusDine coleta os cardápios do RU01 ao RU06 na [página da PRAE](https://www.ufrgs.br/prae/cardapio-restaurante-universitario/). O coletor valida as datas pelo cabeçalho da tabela e exclui o RU01 Anexo, que possui cardápio próprio e não está no catálogo.

Para coletar sem gravar, execute `ruby UFRGS/UFRGS.rb --dry-run` a partir da raiz do repositório. A execução com `BASE_URL` e `FIREBASE_KEY` configuradas grava os menus e relê cada registro para conferir o resultado.

O workflow **UFSC and UFRGS menu update** publica automaticamente de segunda a sábado. A execução manual começa em modo de leitura e permite ativar a publicação pelo campo `upload`.
