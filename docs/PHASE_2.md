# Fase 2 — Autenticação e autorização

## Fatia implementada

O backend disponibiliza `POST /api/v1/auth/login` com email e senha em JSON e
`GET /api/v1/auth/me`. O token de acesso é um JWT assinado com HS256, contém o UUID
do usuário em `sub` e possui expiração configurável.

As variáveis `JWT_SECRET_KEY`, `JWT_EXPIRATION_MINUTES` e `JWT_ALGORITHM` configuram
o token. O valor presente em `.env.example` e no fallback do Docker Compose é apenas
para desenvolvimento e deve ser substituído em qualquer ambiente compartilhado ou
de produção.

## Política de acesso

- `ADMIN` lista, cria e altera usuários e cria ou altera estações e carregadores;
- `ADMIN` consulta globalmente usuários, veículos e sessões, mas não executa as
  operações de motorista sobre veículos e sessões;
- `USER` consulta e altera seu próprio usuário, mas não pode alterar `role`.
- `USER` cria, consulta, altera e exclui somente os próprios veículos;
- `USER` consulta estações e carregadores necessários ao início da recarga, sem
  permissão para alterá-los;
- `USER` inicia, consulta e encerra somente as próprias sessões;
- veículos e sessões de um `USER` são filtrados pelo usuário autenticado;
- recursos pertencentes a outro usuário respondem `404`, evitando confirmar sua
  existência;
- uma operação administrativa feita por `USER` responde `403`;
- credenciais inválidas e contas inativas respondem igualmente `401`, sem revelar
  se a conta existe ou está desativada;
- operações autenticadas derivam `user_id` do JWT; em particular, a criação de
  veículo e o início de sessão não confiam em proprietário enviado pelo cliente.

Tokens ausentes, inválidos ou expirados respondem `401` com o desafio Bearer. Nenhuma
resposta pública inclui `password_hash`.

## OpenAPI

Todos os endpoints desta fase, exceto `POST /api/v1/auth/login`, declaram o esquema
`HTTPBearer` no OpenAPI. O endpoint de health também permanece público.

## Estado da fase

A política de autenticação e autorização da Fase 2 está implementada. Os testes
automatizados cobrem autenticação, expiração e desativação, papéis, propriedade,
tentativas de IDOR, respostas `401`/`403`/`404` e o vínculo das operações ao usuário
autenticado.
