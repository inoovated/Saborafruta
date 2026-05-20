# Deploy log

Registro simples de disparos de deploy quando o Railway precisa receber um
commit novo pelo webhook do GitHub.

## 2026-05-20

- Motivo: Railway voltou apos outage parcial e o app publico ainda respondia
  `/health/` com 404, indicando deploy antigo.
- Base enviada: `488d653 Aprimora cadastro XML com lote e validade`.
- Escopo: consolidado do Thiago + estoque, entrada XML, fiscal/manifesto,
  resiliencia e preparacao Supabase/Cloudflare.
- Observacao: migrations e `ensure_quality_schema` rodam no `CMD` do Dockerfile.
