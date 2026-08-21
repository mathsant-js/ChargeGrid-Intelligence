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

- `ADMIN` lista, cria e altera usuários e cria ou altera estações e carregadores.
- `USER` consulta e altera seu próprio usuário, mas não pode alterar `role`.
- veículos e sessões de um `USER` são filtrados pelo usuário autenticado;
- recursos pertencentes a outro usuário respondem `404`, evitando confirmar sua
  existência;
- uma operação administrativa feita por `USER` responde `403`;
- credenciais inválidas e contas inativas respondem igualmente `401`, sem revelar
  se a conta existe ou está desativada;
- o início de sessão deriva `user_id` do JWT e não confia no valor enviado pelo
  cliente.

Tokens ausentes, inválidos ou expirados respondem `401` com o desafio Bearer. Nenhuma
resposta pública inclui `password_hash`.

## Estado da fase

Esta é uma fatia vertical da Fase 2, não a declaração de conclusão da fase inteira.
Os testes automatizados cobrem autenticação, expiração, papéis, propriedade e o vínculo
da sessão ao usuário autenticado.
