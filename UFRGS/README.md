# Coletor UFRGS no servidor próprio

A coleta continua no servidor já utilizado pelo projeto. A alteração não cria
agenda ou execução de coleta no GitHub.

A data de um título de cardápio só é aceita se estiver próxima da execução
(até sete dias atrás ou quatorze dias à frente). Anos explícitos são respeitados;
sem ano explícito, usa-se a ocorrência mais próxima, incluindo a virada do ano.
Isso impede que seções antigas de dezembro sejam gravadas como dezembro do ano
atual. Dados históricos existentes não são removidos automaticamente.

A verificação TLS permanece habilitada. Falhas de certificado/conexão na origem
precisam ser corrigidas na origem ou na cadeia de certificados do ambiente.

```sh
ruby test_menu_dates.rb
```

Atualize o checkout no servidor. Se usar a imagem Docker deste diretório,
reconstrua a imagem: o coletor agora inclui também `menu_dates.rb`.
