# ERP iNoovaTed

Sistema ERP industrial para indústria de polpa de frutas. Multi-filial, com rastreabilidade
completa de lote, FIFO/FEFO automático, controle fiscal preparado para SEFAZ, ordem de
produção com explosão de BOM e dashboards operacionais.

---

## 🚀 Stack

| Camada | Tecnologia |
|---|---|
| Backend | Python 3.12 + Django 5/6 |
| Banco | PostgreSQL 16 (SQLite em dev) |
| PK | `BigAutoField` (INTEGER incremental) |
| Monetário | `DecimalField(14,4)` em tudo — nunca float |
| Auth | JWT (`simplejwt`) + RBAC por módulo × ação |
| Cache | Django cache framework (LocMem em dev, Redis em prod) |
| Tasks | Celery + Redis (alertas diários de vencimento) |
| Frontend | Django Templates + Tailwind (CDN) + Alpine.js |
| PWA | manifest + darkmode nativo via `localStorage` |

---

## 📦 Estrutura de módulos

```
apps/
├── core/         Empresa, Filial, Usuário, Perfil, Permissões, Logs, Auth
├── cadastros/    Cliente (com ViaCEP), Fornecedor, Transportadora, Representante
├── produtos/     Produto, Categoria, Unidade, Classe Fiscal + Alíquotas (vigência),
│                 Natureza de Operação, Tabela de Preço
├── estoque/      Lote, Estoque, Movimentação (FEFO), Alerta Vencimento, Inventário
├── producao/     Ficha Técnica (BOM), Ordem de Produção, Perda
├── vendas/       Pedido de Venda (ciclo completo: rascunho → confirmado → separado →
│                 faturado → devolvido), Separação FEFO, Devolução
└── compras/      Pedido de Compra, Entrada de NF (com rateio de IPI no custo médio),
                  Avaliação automática de Fornecedor por pontualidade
```

Cada app segue a mesma arquitetura:
```
app/
├── models/         (um arquivo por agregado)
├── views/          (CBV + FBV)
├── forms/          (ModelForm + validação de domínio)
├── services/       (regras de negócio — única via autorizada para escrita crítica)
├── constants/      (Enums / TextChoices)
├── tasks/          (Celery, quando aplicável)
├── templates/      (HTML Tailwind com herança de `_base.html`)
├── admin.py
└── urls.py
```

---

## 🏁 Rodar localmente

### 1. Clonar e instalar dependências

```bash
cd erp_inoovated
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### 2. Configurar ambiente

```bash
cp .env.example .env
# Edite .env se quiser usar PostgreSQL real; por padrão usa SQLite em dev.
```

### Uploads de imagens

O sistema usa `ImageField` para fotos de usuarios e imagens de filiais. Em desenvolvimento,
as imagens ficam em `MEDIA_ROOT=media`.

Em producao no Railway, nao salve uploads no disco comum do container. Crie um Volume no
Railway, monte em `/app/media` e configure:

```bash
MEDIA_URL=/media/
MEDIA_ROOT=/app/media
```

Com isso, imagens enviadas pelo painel ficam persistidas no Volume mesmo apos redeploy/restart.
Sem esse Volume, o banco continua guardando o caminho do arquivo, mas o arquivo fisico some
quando o Railway recria o container no deploy. Se isso acontecer, e necessario reenviar as
imagens ou restaurar os arquivos a partir de um backup/volume anterior.
Para uma etapa futura com clientes maiores, o caminho recomendado e migrar uploads para um
storage externo compativel com S3/R2, mantendo o Volume como solucao simples de MVP.

### 3. Migrar e popular dados de demonstração

```bash
python manage.py migrate
python manage.py seed
```

### 4. Subir o servidor

```bash
python manage.py runserver
```

Acesse **http://localhost:8000** e faça login:

- **E-mail:** `admin@inoovated.com`
- **Senha:** `admin123`

O comando `seed` cria:
- 1 Empresa (Polpa do Nordeste)
- 2 Filiais (Matriz Natal + Mossoró)
- 3 Perfis de acesso (Administrador, Gerente, Operador)
- 4 Unidades de medida (KG, UN, L, CX)
- 3 Categorias (Polpa de Fruta, Matéria-Prima, Embalagem)

---

## 🔥 Módulos funcionais

### Cadastros
- CRUD de Clientes com **integração ViaCEP** (preenche endereço ao sair do campo CEP, via endpoint AJAX `/cadastros/cep/`)
- Cliente: CPF/CNPJ, grupo de desconto, limite de crédito, consumidor final (DIFAL), contribuinte ICMS, endereços adicionais
- Fornecedores com **nota de qualidade** e % de entregas no prazo
- Transportadoras com RNTRC (ANTT) e veículos
- Representantes com comissão e meta mensal

### Produtos
- Produto completo: identificação, **fiscal SEFAZ** (NCM, CEST, CFOP, origem), preços em `Decimal(14,4)`, estoque min/max, **granel** (código de balança, tara, variação permitida), físico (peso, dimensões)
- **Classe Fiscal com alíquotas por UF e vigência** (histórico obrigatório para auditoria)
- Suporte **Reforma Tributária**: IBS, CBS, IS (vigência gradual 2026-2033)
- Natureza de Operação obrigatória com CFOP vinculado
- Tabela de Preço com **preço escalonado** por quantidade mínima
- Categorias **hierárquicas** (árvore infinita)

### Estoque (coração do sistema)
- **FEFO automático** (First Expired First Out) com filtro de lotes vencidos/bloqueados
- **SELECT FOR UPDATE** em `MovimentacaoService` para evitar race conditions
- Snapshots `quantidade_anterior` / `quantidade_posterior` em TODA movimentação (auditoria forense)
- **Custo médio ponderado** recalculado a cada entrada
- **Transferência bilateral** atômica: saída na origem + entrada no destino em uma transação
- Celery tasks diárias:
  - `verificar_vencimentos` às 07:00 (gera alertas D-1/D-7/D-30/D-45/D-60)
  - `bloquear_lotes_vencidos` às 00:05 (marca status=`vencido`)
  - `verificar_estoque_minimo` às 08:00
- Inventário com travamento opcional de movimentações durante a contagem
- Ajuste manual exige justificativa (registrada no log de auditoria)

### Produção
- **Ficha Técnica (BOM)** com perda prevista por item
- **Ordem de Produção** com máquina de estados:
  ```
  rascunho → aberta → em_producao → encerrada
                           ↓
                       cancelada
  ```
- `abrir()`: valida disponibilidade de MP (explosão da BOM) — levanta erro se faltar MP
- `encerrar()`: consome MP via FEFO, gera lote de produto acabado, calcula rendimento, custo por lote (MP + MO + CIF), dispara alerta se rendimento < 80%
- Registro de perdas por categoria (processo, qualidade, vencimento, outros)

### Core
- **Multi-filial**: `FilialScopedModel` + `FilialManager` com `.for_filial()` aplicado automaticamente
- **JWT** com refresh token + bloqueio progressivo após 5 tentativas falhas
- **Troca de filial** na sessão sem reload (seletor no header)
- **Permissões granulares** por módulo × ação (ver, criar, editar, excluir, cancelar, aprovar, exportar) + perfil admin bypass
- **Auditoria automática** via signals: toda criação/edição/deleção de modelos decorados gera `LogSistema` com IP, user-agent e snapshots JSONB
- PIN de PDV (6 dígitos) para operações rápidas sem login completo

---

## 🎨 Design System

Filosofia: **Apple HIG** adaptada para operação industrial.

- Tipografia: Inter (Google Fonts)
- Grid 4px
- Cores semânticas:
  - 🟢 Verde: OK
  - 🟡 Âmbar: atenção
  - 🔴 Vermelho: crítico
- **Dark mode nativo** via `localStorage` (toggle no header)
- **Sidebar colapsável** com persistência
- **Seletor global de filial** com troca sem reload
- Responsivo mobile-first
- `_form_generic.html`: template único de formulário, incluído via `{% include %}`

---

## 🧪 Testado e validado

Ao gerar as migrations e rodar `seed`, já foram validados:

```
✓ Login page: 200
✓ Root redirect: 302 → /dashboard/
✓ Dashboard (autenticado): 200
✓ /cadastros/clientes/: 200
✓ /produtos/: 200
✓ /estoque/: 200
✓ /estoque/lotes/: 200
✓ /estoque/alertas/: 200
✓ /producao/: 200
✓ /producao/fichas-tecnicas/: 200
```

Testes de serviço executados:
```
✓ TESTE 1 — Entrada com custo médio ponderado: 5×50 + 6×30 / 80 = 5,375 ✓
✓ TESTE 2 — FEFO: escolheu lote com validade mais próxima ✓
✓ TESTE 3 — Saída FEFO automática ✓
✓ TESTE 4 — Bloqueio automático de lote vencido ✓
✓ TESTE 5 — Transferência bilateral atômica entre filiais ✓
```

---

## 🔨 Próximos módulos (roadmap)

As fases 3 e 4 do prompt original — **Vendas, Compras, PDV, Fiscal (NF-e/NFC-e), Financeiro, DRE e Analytics** — estão modeladas no prompt mas não implementadas neste MVP. A fundação (`core`, `cadastros`, `produtos`, `estoque`, `producao`) já comporta esses módulos sem refactor.

---

## 📄 Licença

MIT
 
