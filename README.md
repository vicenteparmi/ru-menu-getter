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
