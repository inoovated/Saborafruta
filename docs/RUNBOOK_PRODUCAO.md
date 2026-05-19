# Runbook de producao e contingencia

Este documento define o procedimento minimo quando o ERP iNoovaTed ficar indisponivel por falha do provedor, deploy, banco ou volume de arquivos.

## Regras de ouro

- Nao reiniciar/deployar em loop durante outage confirmada do provedor.
- Nunca colocar senha, certificado A1, `DATABASE_URL` ou tokens em Git, print publico ou chat.
- Antes de qualquer operacao fiscal real, confirmar ambiente homologacao/producao e risco da acao.
- Estoque continua nao replicavel: qualquer recuperacao deve preservar saldos, lotes e movimentacoes por filial.
- Backups precisam sair da Railway; backup que fica apenas no mesmo provedor nao e plano B.

## Diagnostico rapido

1. Abrir `https://status.railway.com`.
2. Testar o health check publico:

```powershell
curl.exe -I https://inovated.up.railway.app/health/
curl.exe https://inovated.up.railway.app/health/
```

3. Conferir status do servico quando o CLI estiver disponivel:

```powershell
npx.cmd --yes @railway/cli status
npx.cmd --yes @railway/cli deployment list --service erp-inoovated
npx.cmd --yes @railway/cli logs --service erp-inoovated --lines 120
```

4. Classificar:

- `health` 200: aplicacao, banco e media respondem.
- `health` 503: aplicacao respondeu, mas banco ou media falhou.
- `X-Railway-Fallback: true`, 404/502/503 no edge, dashboard instavel: provedor/edge.
- Login abre, mas operacoes falham: investigar banco, migrations, permissao ou regra de negocio.

## Comunicacao durante incidente

Mensagem curta para usuarios:

> Estamos com instabilidade no provedor de hospedagem. Os dados permanecem preservados. Evite lancamentos duplicados e aguarde nova confirmacao antes de repetir operacoes.

Se houver risco de operacao fiscal:

> Nao repita emissao/evento fiscal ate confirmarmos o status da SEFAZ e do ERP.

## Backup manual

Gerar backup logico do banco:

```powershell
python manage.py backup_database --settings=config.settings.production --output-dir backups/database
```

Gerar backup da pasta de arquivos:

```powershell
python manage.py backup_media --settings=config.settings.production --output-dir backups/media
```

No Railway, execute os comandos dentro do container do servico via SSH quando o provedor permitir:

```powershell
npx.cmd --yes @railway/cli ssh --service erp-inoovated "python manage.py backup_database --settings=config.settings.production --output-dir /app/media/backups/database"
npx.cmd --yes @railway/cli ssh --service erp-inoovated "python manage.py backup_media --settings=config.settings.production --output-dir /app/media/backups/media"
```

Nao use `railway run` para esse backup se o banco usa `postgres.railway.internal`: esse comando roda localmente com variaveis remotas e pode nao resolver o host interno do Postgres.

Depois baixe os arquivos para um local fora da Railway. Se o edge estiver fora mas SSH/volume ainda responderem, priorize baixar os backups antes de tentar redeploy.

## Periodicidade recomendada

- Banco: diario no MVP; antes e depois de deploys grandes.
- Media: diario no MVP; imediato quando houver upload de XML, certificado, imagens ou documentos importantes.
- Retencao minima: 7 diarios, 4 semanais e 3 mensais.

## Failover manual para outro host

Pre-requisitos:

- Repositorio Git atualizado.
- Variaveis de ambiente exportadas para cofre seguro.
- Backup recente do banco fora da Railway.
- Backup recente de `MEDIA_ROOT` fora da Railway.
- Dominio proprio com TTL baixo, idealmente 60 a 300 segundos.

Passos:

1. Subir Postgres em provedor alternativo.
2. Restaurar backup do banco.
3. Restaurar pasta `media`.
4. Subir a aplicacao pelo Dockerfile do repositorio.
5. Configurar variaveis: `SECRET_KEY`, `DATABASE_URL`, `ALLOWED_HOSTS`, `MEDIA_ROOT`, flags fiscais e demais integrações.
6. Rodar:

```powershell
python manage.py migrate --fake-initial --noinput
python manage.py ensure_quality_schema
python manage.py check --deploy
```

7. Testar `/health/`, login, troca de filial, telas criticas e consulta de leitura.
8. Trocar DNS para o host standby.

## Checklist pos-retorno da Railway

1. Confirmar `https://status.railway.com` como resolvido.
2. Testar `/health/`.
3. Conferir ultimo deploy e logs.
4. Validar login e dashboard.
5. Conferir ultimas entradas, movimentos de estoque e documentos fiscais.
6. Se houve uso de standby, congelar escrita em um dos lados antes de voltar DNS para evitar divergencia.

## Proximas melhorias

- Monitor externo com alerta para `/health/`.
- Backup automatico para storage externo.
- Dominio proprio em vez de depender de `up.railway.app`.
- Ambiente standby documentado e testado mensalmente.
- Restauracao testada em banco limpo a cada ciclo de entrega.
