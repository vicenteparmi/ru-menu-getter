# UFPR — coleta HTTPS verificada, sem IA

O servidor `p4e.ufpr.br` apresentava o certificado `*.ufpr.br` sem o intermediário
RNP ICPEdu GR46 OV TLS CA 2025. `source_http.rb` completa a cadeia apenas para
essa origem, usando o certificado público oficial em `certs/`. O intermediário
precisa validar contra as raízes confiáveis do sistema operacional. Certificado,
hostname e validade continuam sendo verificados; não há downgrade HTTP ou proxy
público. A origem, fingerprint e validade estão documentadas em `certs/README.md`.

`menu_parser.rb` associa cada cabeçalho de data à tabela seguinte, em vez de
combinar duas listas independentes. Preserva os nomes dos pratos e as opções
veganas, sem acrescentar os rótulos dos ícones (como “Contém glúten”).
Cabeçalhos futuros sem tabela (como o de Toledo em 30/10/2026) não são
tratados como cardápios publicados. Datas atuais/passadas sem tabela continuam
sendo reportadas como erro; datas inválidas ou duplicadas são rejeitadas.

```sh
ruby UFPR/test_source_http.rb
ruby UFPR/test_menu_parser.rb
ruby UFPR.rb --dry-run --output ufpr-menus.json
# Com BASE_URL e FIREBASE_KEY configuradas:
ruby UFPR.rb --output ufpr-menus.json
```

A gravação usa o caminho existente do CampusDine:
`archive/menus/{cidade}/rus/{restaurante}/menus/{YYYY-MM-DD}`. Cada gravação é
relida e comparada com o conteúdo enviado. Datas fora da janela entre sete dias
atrás e quatorze dias à frente não são republicadas. Erros em uma unidade não
interrompem as outras, mas fazem o job terminar com erro e gerar relatório.

O workflow `daily_menu.yml` continua às 00:00 e 12:00 UTC. Para executar somente
UFPR, use `target=ufpr`; `ufpr_dry_run=true` valida a fonte sem escrever no banco.
Não exige autenticação Google Cloud, somente os segredos Firebase já existentes.
