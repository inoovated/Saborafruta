# ERP iNoovaTed — Instruções para Claude

## Regra de Deploy (IMPORTANTE)

**Sempre que fizer `git push`, enviar para AMBAS as branches:**

```bash
git push origin main
git push origin thiago/dashboard
```

O Railway pode estar configurado para fazer deploy de qualquer uma dessas branches. Enviar para as duas garante que as atualizações cheguem ao ambiente de produção.

## Branches

- `main` — branch principal
- `thiago/dashboard` — branch de deploy (Railway pode usar esta)

## Stack

- Django (Python) + Alpine.js + Tailwind CSS
- PostgreSQL (via Railway)
- Deploy: Railway (Docker)
