# Preparacao Supabase e Cloudflare com custo zero

Este documento define o caminho para preparar Supabase e Cloudflare sem migrar a
producao agora e sem contratar recurso pago durante o MVP.

## Decisao atual

- O MVP continua na Railway, mantendo o custo alvo de US$ 5/mes.
- Supabase nao entra como banco de producao ainda.
- Cloudflare nao precisa assumir DNS de producao agora, a menos que ja exista
  dominio proprio e a mudanca seja planejada.
- Cloudflare R2 fica para depois. Apesar de ter camada gratuita, uso fora da
  franquia pode gerar cobranca; portanto nao ativar enquanto a regra for custo
  zero garantido.

## O que ja pode ficar pronto no codigo

- O projeto ja usa `DATABASE_URL`, entao a troca futura de Railway Postgres para
  Supabase Postgres nao exige reescrever a aplicacao.
- `config/settings/production.py` aceita:
  - `DATABASE_SSL_REQUIRE=True` para forcar `sslmode=require`;
  - `DATABASE_CONN_MAX_AGE=0` para operar melhor com pooler externo.
- `.env.example` tem placeholders de Supabase sem nenhum segredo real.
- Backups e runbook continuam em `docs/RUNBOOK_PRODUCAO.md`.

## O que nao fazer agora

- Nao colocar dados reais, certificado A1, XML de cliente ou senha em projeto
  Supabase gratuito.
- Nao apontar `DATABASE_URL` da Railway para Supabase antes do MVP fechar.
- Nao usar dois bancos em escrita ao mesmo tempo.
- Nao migrar `MEDIA_ROOT` para R2/S3 sem teste de upload, leitura, backup e
  rollback.
- Nao commitar `DATABASE_URL`, tokens Cloudflare, chaves R2 ou senhas.

## Preparacao Cloudflare sem custo

1. Criar ou separar uma conta Cloudflare da empresa.
2. Ativar MFA para todos os usuarios administradores.
3. Registrar quem tem acesso administrativo.
4. Se ja houver dominio proprio, importar a zona DNS no plano Free, mas nao
   trocar nameservers sem janela planejada.
5. Documentar registros previstos:
   - `app.empresa.com.br` apontando para Railway no MVP;
   - `standby.empresa.com.br` reservado para ambiente alternativo futuro;
   - `static.empresa.com.br` ou `media.empresa.com.br` reservado para R2/S3 no
     futuro.
6. Manter TTL baixo apenas perto da virada. Fora de migracao, TTL pode ser
   normal para reduzir complexidade.

## Preparacao Supabase sem custo

O Supabase Free pode ser usado somente para laboratorio sem dado sensivel. Se a
conta pedir cartao ou se houver risco de cobranca, nao criar recurso agora.

Checklist de laboratorio:

1. Criar projeto de teste, se isso continuar sem custo na conta escolhida.
2. Usar uma regiao proxima do Brasil quando disponivel.
3. Criar banco vazio.
4. Restaurar somente dados fake ou anonimizados.
5. Configurar `DATABASE_URL` local apontando para o Supabase de teste.
6. Rodar:

```powershell
python manage.py migrate --settings=config.settings.production
python manage.py check --settings=config.settings.production
python manage.py check --deploy --settings=config.settings.production
```

7. Testar login, troca de filial, estoque, entrada XML com XML fake, manifesto
   local, produtos e promocoes.
8. Destruir o projeto de teste se nao for mais usado.

## Variaveis futuras para Supabase

Exemplo sem segredo real:

```env
DATABASE_URL=postgres://postgres.PROJECT_REF:SENHA@aws-0-sa-east-1.pooler.supabase.com:6543/postgres?sslmode=require
DATABASE_SSL_REQUIRE=True
DATABASE_CONN_MAX_AGE=0
```

Observacoes:

- Usar URL com `sslmode=require`.
- Preferir pooler para ambiente de aplicacao com muitas conexoes curtas.
- Manter `CONN_MAX_AGE=0` ate medir comportamento com o pooler.
- Para migracao real, gerar senha forte e guardar somente no painel/plataforma.

## Virada real depois do MVP

1. Congelar deploys e lancamentos criticos.
2. Gerar backup completo do banco atual.
3. Gerar backup completo de `MEDIA_ROOT`.
4. Restaurar banco no Supabase pago.
5. Rodar migrations e checagens.
6. Apontar ambiente de homologacao para Supabase.
7. Fazer QA com dados reais e rollback planejado:
   - login;
   - filiais;
   - estoque;
   - lotes;
   - inventario;
   - entrada XML;
   - manifesto;
   - produtos;
   - promocoes;
   - contratos minimos de compras/vendas que encostam no estoque.
8. Trocar `DATABASE_URL` da producao somente depois do QA.
9. Manter o banco antigo em modo somente leitura por uma janela curta.
10. Confirmar que nao houve divergencia de estoque ou fiscal.

## Criterios para contratar Supabase Pro

Contratar apenas quando pelo menos um destes pontos acontecer:

- MVP fechado e pronto para usuarios reais.
- Necessidade de backup automatico confiavel.
- Necessidade de PITR para recuperar ponto no tempo.
- Dados reais relevantes ja entrando no sistema.
- Railway continuar instavel e o banco precisar sair do mesmo provedor.

## Criterios para ativar Cloudflare R2

Ativar apenas quando:

- Uploads estiverem relevantes para a operacao.
- Houver imagens, XMLs, anexos fiscais ou certificados que nao podem sumir em
  restart/deploy.
- O fluxo de backup/restauracao de arquivos estiver testado.
- As chaves R2 puderem ser guardadas em variaveis de ambiente, nunca no Git.

## Fontes oficiais

- Supabase Pricing: https://supabase.com/pricing
- Supabase Backups: https://supabase.com/docs/guides/platform/backups
- Cloudflare DNS: https://developers.cloudflare.com/dns/
- Cloudflare R2 Pricing: https://developers.cloudflare.com/r2/pricing/
- Railway Pricing: https://docs.railway.com/pricing
