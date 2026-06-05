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

## Railway Deploy (API)

Após cada push, acionar redeploy via API GraphQL:

```bash
curl -s -X POST https://backboard.railway.com/graphql/v2 \
  -H "Authorization: Bearer c1c560e5-ff97-4f28-82b9-5df157ec6811" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "mutation serviceInstanceRedeploy($environmentId: String!, $serviceId: String!) { serviceInstanceRedeploy(environmentId: $environmentId, serviceId: $serviceId) }",
    "variables": {
      "environmentId": "168e0342-5cc5-4a53-978f-493feb55cac8",
      "serviceId": "a49870de-e2b3-4090-a0fa-0ad5ddcf0862"
    }
  }'
```

- **Project ID:** `220ad93c-5fb9-4750-bbc5-5cf38acb6fc7`
- **Service ID:** `a49870de-e2b3-4090-a0fa-0ad5ddcf0862`
- **Environment ID:** `168e0342-5cc5-4a53-978f-493feb55cac8`
