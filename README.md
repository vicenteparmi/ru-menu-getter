# RU Menu Getter and Data Analysis

Este projeto automatiza o processo de obtenção de cardápios diários de vários restaurantes universitários (RUs) e realiza análise de dados sobre os dados coletados. Os dados são então enviados para o Firebase para serem utilizados no aplicativo CampusDine.

Mais informações sobre o aplicativo podem ser encontradas na [página oficial do CampusDine](https://vicx.dev.br/campusdine/).

## Recursos

- **Obtenção de Cardápios Diários**: O script busca cardápios diários de várias universidades, incluindo UFABC e UFPR.
- **Arquivamento de Dados**: Os dados dos cardápios obtidos são arquivados no Firebase Realtime Database e no Google Cloud Firestore.
- **Análise de Dados**: Fluxos de trabalho automatizados realizam análise de dados sobre os cardápios arquivados.
- **Integração com GitHub Actions**: Todo o processo é automatizado usando GitHub Actions, garantindo que os dados sejam atualizados duas vezes ao dia.

## Fluxos de Trabalho

### Atualização de Cardápio Diário

Este fluxo de trabalho é executado duas vezes ao dia (00:00 e 12:00 UTC) para buscar e arquivar os cardápios diários.

- **Configuração**: [`.github/workflows/daily_menu.yml`](.github/workflows/daily_menu.yml)
- **Scripts**:
  - [`UFABC.rb`](UFABC.rb): Busca o cardápio diário da UFABC.
  - [`UFPR.rb`](UFPR.rb): Busca o cardápio diário da UFPR.
  - [`movedata.rb`](movedata.rb): Arquiva os dados dos cardápios antigos.
  - [`movedata_today.rb`](movedata_today.rb): Arquiva o cardápio do dia atual no Firebase Realtime Database e Firestore para ser usado pela Amazon Alexa.

### UFRGS (Containerizado)

Os scripts para a UFRGS estão disponíveis em um container Docker separado:

- **Configuração**: [`UFRGS/docker-compose.yml`](UFRGS/docker-compose.yml)
- **Script**: [`UFRGS/UFRGS.rb`](UFRGS/UFRGS.rb)

### Unicamp (Campinas, Limeira e Piracicaba)

[`UNICAMP.rb`](UNICAMP.rb) lê as páginas oficiais sem IA. O workflow independente
[`unicamp_menu.yml`](.github/workflows/unicamp_menu.yml) executa domingo às 12h,
segunda às 9h e 11h, terça e quinta às 9h (America/Sao_Paulo), ou manualmente
com `gh workflow run unicamp_menu.yml`. Reaproveita `BASE_URI` e `SECRET`;
o workflow legado pode permanecer desativado.

```sh
ruby test_unicamp.rb
ruby UNICAMP.rb --dry-run --campus campinas --output campinas.json
ruby UNICAMP.rb --dry-run --campus regional --output regional.json
# Com BASE_URL e FIREBASE_KEY configuradas: grava e relê cada cardápio.
ruby UNICAMP.rb --campus campinas
```

Campinas e os campi regionais rodam em jobs independentes. Falhas de uma data
são registradas sem impedir outras datas válidas; após gravar os dados válidos,
a execução retorna erro se houve qualquer falha parcial, mantendo o alerta
visível no Actions. Não se substituem cardápios de datas com falha de coleta.

Em Campinas, se uma indicação de restaurantes faltar em um dos cartões
padrão/vegano, usa-se a indicação explícita do cartão par para a mesma refeição
e data. Indicações divergentes, desconhecidas ou ausentes nos dois cartões
continuam sendo rejeitadas. Os testes incluem o HTML real de 28/10/2026 que
provocava a interrupção. Nenhuma alteração no CampusDine é necessária.

### Análise de Dados

Este fluxo de trabalho pode ser acionado manualmente para realizar análise de dados nos cardápios arquivados.

- **Configuração**: [`.github/workflows/data_analysis.yml`](.github/workflows/data_analysis.yml)
- **Script**: [`data_analysis.py`](data_analysis.py)

## Uso

### Fluxos de Trabalho do GitHub Actions

- **Atualização de Cardápio Diário**: Este fluxo de trabalho é executado duas vezes por dia (00:00 e 12:00 UTC) para buscar e arquivar os cardápios diários.
  - Configuração: [`.github/workflows/daily_menu.yml`](.github/workflows/daily_menu.yml)

- **Análise de Dados**: Este fluxo de trabalho pode ser acionado manualmente para realizar análise de dados.
  - Configuração: [`.github/workflows/data_analysis.yml`](.github/workflows/data_analysis.yml)

## Requisitos

### UFV — Viçosa, sem IA

[`UFV.py`](UFV.py) consulta o JSON usado pelo calendário público da UFV,
sem Gemini, navegador ou dependências externas (Python 3.11+).

```sh
# Somente coleta/validação; gravação é sempre explícita.
python UFV.py --start 2026-10-29 --days 14 --output ufv-menus.json
BASE_URL=https://seu-firebase.firebaseio.com FIREBASE_KEY=... python UFV.py --upload
python -m unittest discover -s tests -p 'test_ufv.py' -v
```

O workflow independente [`ufv_menu.yml`](.github/workflows/ufv_menu.yml) executa
a UFV duas vezes por dia (00:00 e 12:00 UTC), ou manualmente com
`gh workflow run ufv_menu.yml`, reaproveitando `BASE_URI` e `SECRET`.
Em pushes e pull requests, somente os testes locais são executados.
A coleta começa no dia atual em America/Sao_Paulo e busca 14 dias.
O portal responde por **HTTP**; HTTPS retorna 403. Envia-se apenas a data
ao portal, sem credenciais. O Firebase é acessado exclusivamente por HTTPS.

O catálogo fica em `menus/ufv-vicosa/rus/{ru-i,ru-ii,ru-iii}`; somente unidades
com refeições publicadas no intervalo são cadastradas. Inicialmente a fonte
publica RU II e RU III/Multiuso; não há cardápio do RU I no intervalo validado.
Uma refeição com rótulo compartilhado é distribuída somente às unidades
explicitamente indicadas, em cada data. Refeitórios ou refeições desconhecidos
interrompem a coleta antes de qualquer escrita.

Cada dia usa `[café, almoço, jantar]`, `weekday` em português e `timestamp`
em segundos, no caminho `archive/menus/ufv-vicosa/rus/{ru}/menus/{data}` que
o CampusDine (`vicenteparmi/ru`) já lê. Períodos sem serviço usam
`Sem refeições disponíveis`. Datas sem publicação são ignoradas; em datas
publicadas, a ausência de uma unidade conhecida é representada sem refeições.
Itens mantêm categorias, observações e indicações de alergênicos da fonte.

Uma atualização atômica e restrita a UFV grava catálogo e cardápios. Metadados
existentes e outras universidades/datas são preservados. Cada cardápio gravado
é relido para verificação. Novas unidades entram como `beta` e `isNew`.
Não é necessária alteração nem nova versão do CampusDine para listar a UFV.

- Ruby 3.4.1
- Gems: nokogiri, firebase, google-cloud-firestore
- Python (para análise de dados)
- Docker (para o container UFRGS)

## Variáveis de Ambiente

As seguintes variáveis de ambiente são necessárias para os scripts e fluxos de trabalho:

- `FIREBASE_KEY`: Chave secreta do Firebase.
- `BASE_URL`: URL base do Firebase.
- `GCLOUD_PROJECT_ID`: ID do projeto Google Cloud.
- `GCLOUD_ADMIN`: Credenciais de administrador do Google Cloud.
- `SERVICE_ACCOUNT_CREDENTIALS`: Credenciais de conta de serviço para o Google Cloud.

## Contribuindo

Contribuições são bem-vindas! Por favor, abra uma issue ou envie um pull request para quaisquer alterações.

## Licença

A licença deste projeto está disponível no arquivo [LICENSE](LICENSE).

### Proteções dos coletores legados

UFPR e UFABC executam em jobs independentes no workflow diário. A tentativa por
proxies públicos da UFABC é limitada a dois candidatos com timeout; uma fonte inacessível
não deve prender a atualização da outra universidade. Ausência de datas ou
quantidade divergente de datas/tabelas interrompe a gravação, evitando deslocar
os cardápios entre dias. Falhas deixam de ser mascaradas por `continue-on-error`.

UFSC e UFRGS continuam sob execução do servidor próprio. As correções publicadas
para eles precisam ser carregadas nesse servidor; o workflow de regressão no
GitHub executa somente testes. Veja [UFSC](RU-AI-GETTER/README.md) e
[UFRGS](UFRGS/README.md) para os comandos e limites dos parsers.

### UFPR: cadeia TLS corrigida

A UFPR usa agora um cliente com a cadeia de certificados completa e validada,
sem proxies públicos. Cada data fica associada à sua própria tabela e todo
upload é verificado por releitura. Veja [UFPR/README.md](UFPR/README.md) para
a origem do certificado intermediário e os comandos de validação/execução.
