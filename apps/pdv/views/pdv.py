import json
from decimal import Decimal

from django.db import transaction
from django.db.models import Q, Sum
from django.http import JsonResponse
from django.shortcuts import render
from django.core.paginator import Paginator
from django.utils import timezone
from django.views.decorators.http import require_GET, require_POST

from apps.core.services.exceptions import DadosInvalidosError, EstoqueInsuficienteError
from apps.core.services.permissions import requer_permissao
from apps.financeiro.models import FormaPagamento
from apps.pdv.models import (
    Caixa, ItemVendaPDV, MovimentacaoCaixa, PagamentoVendaPDV, SessaoPDV, VendaPDV,
)
from apps.pdv.services.produto_vendavel_service import ProdutoVendavelService
from apps.pdv.services.venda_pdv_service import VendaPDVService
from apps.produtos.models import LinhaProducao, Produto


# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------

def _sessao_aberta(request):
    return SessaoPDV.objects.for_filial(request.filial_ativa).filter(
        usuario=request.user, status="aberto"
    ).first()


def _proximo_numero_venda(filial):
    ultimo_num = (
        VendaPDV.objects.filter(filial=filial)
        .order_by("-numero_venda")
        .values_list("numero_venda", flat=True)
        .first()
    )
    return (ultimo_num or 0) + 1


# ---------------------------------------------------------------------------
# Tela principal
# ---------------------------------------------------------------------------

@requer_permissao('pdv', 'ver')
def pdv_home(request):
    caixas = list(
        Caixa.objects.for_filial(request.filial_ativa)
        .filter(ativo=True)
        .values('id', 'numero', 'descricao')
    )
    linhas = list(
        LinhaProducao.objects.filter(ativo=True)
        .values('id', 'nome', 'icone', 'cor_identificacao')
    )
    return render(request, "pdv/home.html", {
        "title": "PDV",
        "caixas_json": json.dumps(caixas),
        "linhas_json": json.dumps(linhas),
    })


# ---------------------------------------------------------------------------
# Lista de vendas
# ---------------------------------------------------------------------------

@requer_permissao('pdv', 'ver')
def vendas_list(request):
    qs = VendaPDV.objects.for_filial(request.filial_ativa).select_related(
        "cliente", "sessao_pdv", "usuario"
    ).order_by("-data_venda")
    paginator = Paginator(qs, 25)
    page = paginator.get_page(request.GET.get("page", 1))
    return render(request, "pdv/vendas_list.html", {"title": "Vendas PDV", "page": page})


# ---------------------------------------------------------------------------
# API — Busca de produtos e clientes (existentes, mantidos)
# ---------------------------------------------------------------------------

@requer_permissao('pdv', 'ver')
def buscar_produto(request):
    q = request.GET.get("q", "").strip()
    linha_id = request.GET.get("linha")
    qs = Produto.objects.for_filial(request.filial_ativa).filter(ativo=True)
    if q:
        filtro = Q(descricao__icontains=q) | Q(codigo__icontains=q) | Q(codigo_barras__icontains=q)
        if q.isdigit():
            filtro |= Q(pk=int(q))
        qs = qs.filter(filtro)
    if linha_id:
        qs = qs.filter(linha_producao_id=linha_id)
    produtos = list(qs.select_related("linha_producao")[:20])
    data = []
    for p in produtos:
        contrato = ProdutoVendavelService.consultar(
            produto=p,
            filial=request.filial_ativa,
            quantidade=Decimal("1"),
        )
        data.append({
            "id": p.id, "descricao": p.descricao_pdv or p.descricao,
            "codigo_barras": p.codigo_barras,
            "preco": float(contrato["preco_aplicado"]),
            "preco_base": float(p.preco_venda or 0),
            "preco_origem": contrato["preco_origem"],
            "preco_origem_tipo": contrato["preco_origem_tipo"],
            "preco_origem_detalhe": contrato["preco_origem_detalhe"],
            "estoque_disponivel": float(contrato["saldo_disponivel"]),
            "custo_atual": float(contrato["custo_atual"]),
            "margem_percentual": float(contrato["margem_percentual"]),
            "status_comercial": contrato["status_comercial"],
            "status_comercial_label": contrato["status_comercial_label"],
            "lote_obrigatorio": contrato["lote_obrigatorio"],
            "promocoes_aplicaveis": contrato["promocoes_aplicaveis"],
            "bloqueios": contrato["bloqueios"],
            "alertas": contrato["alertas"],
            "pode_vender": contrato["pode_vender"],
            "permite_venda_sem_estoque": p.permite_venda_sem_estoque,
            "linha": p.linha_producao.nome if p.linha_producao else None,
            "icone": p.linha_producao.icone if p.linha_producao else None,
            "cor": p.linha_producao.cor_identificacao if p.linha_producao else None,
        })
    return JsonResponse({"produtos": data})


@requer_permissao('pdv', 'ver')
def buscar_cliente(request):
    from apps.cadastros.models import Cliente
    q = request.GET.get("q", "").strip()
    qs = Cliente.objects.for_filial(request.filial_ativa).filter(ativo=True)
    if q:
        qs = qs.filter(razao_social__icontains=q) | qs.filter(cpf_cnpj__icontains=q)
    qs = qs[:20]
    return JsonResponse({"clientes": [{
        "id": c.id, "razao_social": c.razao_social, "cpf_cnpj": c.cpf_cnpj,
        "linhas_interesse": c.linhas_interesse,
        "saldo_devedor": float(c.saldo_devedor or 0),
    } for c in qs]})


# ---------------------------------------------------------------------------
# API — Estado inicial do PDV
# ---------------------------------------------------------------------------

def _serializa_produto(p, filial):
    contrato = ProdutoVendavelService.consultar(
        produto=p,
        filial=filial,
        quantidade=Decimal("1"),
    )
    return {
        "id": p.id,
        "descricao": p.descricao_pdv or p.descricao,
        "codigo_barras": p.codigo_barras,
        "preco": float(contrato["preco_aplicado"]),
        "preco_base": float(p.preco_venda or 0),
        "preco_origem": contrato["preco_origem"],
        "preco_origem_tipo": contrato["preco_origem_tipo"],
        "preco_origem_detalhe": contrato["preco_origem_detalhe"],
        "estoque_disponivel": float(contrato["saldo_disponivel"]),
        "custo_atual": float(contrato["custo_atual"]),
        "margem_percentual": float(contrato["margem_percentual"]),
        "status_comercial": contrato["status_comercial"],
        "status_comercial_label": contrato["status_comercial_label"],
        "lote_obrigatorio": contrato["lote_obrigatorio"],
        "promocoes_aplicaveis": contrato["promocoes_aplicaveis"],
        "bloqueios": contrato["bloqueios"],
        "alertas": contrato["alertas"],
        "pode_vender": contrato["pode_vender"],
        "linha": p.linha_producao.nome if p.linha_producao else None,
        "icone": p.linha_producao.icone if p.linha_producao else None,
        "cor": p.linha_producao.cor_identificacao if p.linha_producao else None,
    }


@requer_permissao('pdv', 'ver')
@require_GET
def api_estado(request):
    sessao = _sessao_aberta(request)

    try:
        formas = list(
            FormaPagamento.objects.filter(
                empresa=request.filial_ativa.empresa, ativo=True
            ).values('id', 'descricao', 'tipo', 'requer_tef')
        )
    except Exception:
        formas = []

    # Top 10 — mais vendidos por quantidade em vendas finalizadas
    top_produtos = []
    try:
        ranking = (
            ItemVendaPDV.objects
            .filter(venda_pdv__filial=request.filial_ativa,
                    venda_pdv__status="finalizada")
            .values('produto_id')
            .annotate(qtd=Sum('quantidade'))
            .order_by('-qtd')[:10]
        )
        ids_ordenados = [r['produto_id'] for r in ranking]
        if ids_ordenados:
            produtos = {
                p.id: p for p in Produto.objects.filter(id__in=ids_ordenados)
                .select_related('linha_producao')
            }
            for pid in ids_ordenados:
                p = produtos.get(pid)
                if p and p.ativo:
                    top_produtos.append(_serializa_produto(p, request.filial_ativa))

        # Sem histórico de vendas: mostra produtos cadastrados
        if not top_produtos:
            fallback = (
                Produto.objects.for_filial(request.filial_ativa)
                .filter(ativo=True)
                .select_related('linha_producao')
                .order_by('descricao')[:10]
            )
            top_produtos = [_serializa_produto(p, request.filial_ativa) for p in fallback]
    except Exception:
        top_produtos = []

    return JsonResponse({
        "sessao": {
            "id": sessao.id,
            "caixa_id": sessao.caixa_id,
            "data_abertura": sessao.data_abertura.isoformat(),
        } if sessao else None,
        "formas_pagamento": formas,
        "top_produtos": top_produtos,
    })


# ---------------------------------------------------------------------------
# API — Abertura de caixa
# ---------------------------------------------------------------------------

@requer_permissao('pdv', 'ver')
@require_POST
def api_caixa_abrir(request):
    try:
        body = json.loads(request.body)
        caixa_id = int(body.get("caixa_id", 0))
        valor_abertura = Decimal(str(body.get("valor_abertura", "0")))
    except (ValueError, KeyError):
        return JsonResponse({"erro": "Dados inválidos."}, status=400)

    if _sessao_aberta(request):
        return JsonResponse({"erro": "Já existe uma sessão aberta para este usuário."}, status=400)

    try:
        caixa = Caixa.objects.for_filial(request.filial_ativa).get(id=caixa_id, ativo=True)
    except Caixa.DoesNotExist:
        return JsonResponse({"erro": "Caixa não encontrado."}, status=404)

    sessao = SessaoPDV.objects.create(
        filial=request.filial_ativa,
        caixa=caixa,
        usuario=request.user,
        valor_abertura=valor_abertura,
        data_abertura=timezone.now(),
        status="aberto",
    )
    return JsonResponse({
        "ok": True,
        "sessao_id": sessao.id,
        "caixa": {"id": caixa.id, "numero": caixa.numero, "descricao": caixa.descricao},
    })


# ---------------------------------------------------------------------------
# API — Criar caixa
# ---------------------------------------------------------------------------

@requer_permissao('pdv', 'ver')
@require_POST
def api_caixa_criar(request):
    """Cria um novo Caixa para a filial e o retorna pronto para seleção."""
    try:
        body = json.loads(request.body)
        descricao = str(body.get("descricao", "")).strip()[:60]
    except (ValueError, KeyError):
        return JsonResponse({"erro": "Dados inválidos."}, status=400)

    # próximo número disponível para a filial
    ultimo = Caixa.objects.for_filial(request.filial_ativa).order_by('-numero').first()
    proximo_numero = (ultimo.numero + 1) if ultimo else 1

    try:
        caixa = Caixa.objects.create(
            filial=request.filial_ativa,
            numero=proximo_numero,
            descricao=descricao,
            ativo=True,
        )
    except Exception as exc:
        return JsonResponse({"erro": f"Erro ao criar caixa: {exc}"}, status=400)

    return JsonResponse({
        "ok": True,
        "caixa": {"id": caixa.id, "numero": caixa.numero, "descricao": caixa.descricao},
    })


# ---------------------------------------------------------------------------
# API — Finalizar venda
# ---------------------------------------------------------------------------

@requer_permissao('pdv', 'ver')
@require_POST
def api_venda_finalizar(request):
    try:
        body = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({"erro": "JSON inválido."}, status=400)

    sessao = _sessao_aberta(request)
    if not sessao:
        return JsonResponse({"erro": "Nenhuma sessão de caixa aberta."}, status=400)

    itens = body.get("itens", [])
    pagamentos = body.get("pagamentos", [])
    if not itens:
        return JsonResponse({"erro": "Carrinho vazio."}, status=400)
    if not pagamentos:
        return JsonResponse({"erro": "Informe ao menos uma forma de pagamento."}, status=400)

    cliente_id = body.get("cliente_id")
    desconto = Decimal(str(body.get("desconto", "0")))
    acrescimo = Decimal(str(body.get("acrescimo", "0")))
    delivery = bool(body.get("delivery", False))
    endereco_entrega = body.get("endereco_entrega", {})

    try:
        venda = VendaPDVService.finalizar_venda(
            sessao=sessao,
            filial=request.filial_ativa,
            usuario=request.user,
            itens=itens,
            pagamentos=pagamentos,
            cliente_id=cliente_id,
            desconto=desconto,
            acrescimo=acrescimo,
            delivery=delivery,
            endereco_entrega=endereco_entrega,
        )
    except (DadosInvalidosError, EstoqueInsuficienteError) as exc:
        return JsonResponse({"erro": str(exc)}, status=400)
    except Exception as exc:
        return JsonResponse({"erro": str(exc)}, status=500)

    return JsonResponse({"ok": True, "numero_venda": venda.numero_venda, "venda_id": venda.id})

# ---------------------------------------------------------------------------
# API — Salvar como pendente
# ---------------------------------------------------------------------------

@requer_permissao('pdv', 'ver')
@require_POST
def api_venda_pendente(request):
    try:
        body = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({"erro": "JSON inválido."}, status=400)

    sessao = _sessao_aberta(request)
    if not sessao:
        return JsonResponse({"erro": "Nenhuma sessão de caixa aberta."}, status=400)

    itens = body.get("itens", [])
    if not itens:
        return JsonResponse({"erro": "Carrinho vazio."}, status=400)

    cliente_id = body.get("cliente_id")
    desconto = Decimal(str(body.get("desconto", "0")))
    acrescimo = Decimal(str(body.get("acrescimo", "0")))
    delivery = bool(body.get("delivery", False))
    endereco_entrega = body.get("endereco_entrega", {})

    try:
        with transaction.atomic():
            numero = _proximo_numero_venda(request.filial_ativa)

            venda = VendaPDV.objects.create(
                sessao_pdv=sessao,
                filial=request.filial_ativa,
                numero_venda=numero,
                cliente_id=cliente_id or None,
                status="aberta",
                delivery=delivery,
                endereco_entrega=endereco_entrega,
                valor_desconto=desconto,
                valor_acrescimo=acrescimo,
                usuario=request.user,
                data_venda=timezone.now(),
            )

            subtotal = Decimal("0")
            for idx, item in enumerate(itens, start=1):
                produto = Produto.objects.select_related("unidade_medida").get(id=int(item["produto_id"]))
                quantidade = Decimal(str(item["quantidade"]))
                valor_unitario = Decimal(str(item["valor_unitario"]))
                valor_total_item = quantidade * valor_unitario
                um_sigla = produto.unidade_medida.sigla if produto.unidade_medida_id else "UN"
                ItemVendaPDV.objects.create(
                    venda_pdv=venda,
                    produto=produto,
                    numero_item=idx,
                    quantidade=quantidade,
                    unidade_medida=um_sigla,
                    valor_unitario=valor_unitario,
                    valor_total=valor_total_item,
                )
                subtotal += valor_total_item

            venda.valor_subtotal = subtotal
            venda.valor_total = subtotal - desconto + acrescimo
            venda.save(update_fields=["valor_subtotal", "valor_total"])

    except Produto.DoesNotExist:
        return JsonResponse({"erro": "Produto não encontrado."}, status=404)
    except Exception as exc:
        return JsonResponse({"erro": str(exc)}, status=500)

    return JsonResponse({"ok": True, "numero_venda": venda.numero_venda, "venda_id": venda.id})


# ---------------------------------------------------------------------------
# API — Listar pendentes
# ---------------------------------------------------------------------------

@requer_permissao('pdv', 'ver')
@require_GET
def api_pendentes(request):
    sessao = _sessao_aberta(request)
    qs = VendaPDV.objects.for_filial(request.filial_ativa).filter(
        status="aberta"
    ).select_related("cliente").order_by("-data_venda")[:50]

    pendentes = []
    for v in qs:
        pendentes.append({
            "id": v.id,
            "numero_venda": v.numero_venda,
            "cliente": v.cliente.razao_social if v.cliente else "Consumidor",
            "valor_total": float(v.valor_total),
            "data_venda": v.data_venda.isoformat(),
            "delivery": v.delivery,
        })

    return JsonResponse({"pendentes": pendentes, "sessao_ativa": sessao is not None})


# ---------------------------------------------------------------------------
# API — Detalhe de uma venda pendente (itens + cabeçalho)
# ---------------------------------------------------------------------------

@requer_permissao('pdv', 'ver')
@require_GET
def api_pendente_detalhe(request, pk):
    try:
        venda = (
            VendaPDV.objects
            .for_filial(request.filial_ativa)
            .prefetch_related("itens__produto__linha_producao", "cliente")
            .get(pk=pk, status="aberta")
        )
    except VendaPDV.DoesNotExist:
        return JsonResponse({"erro": "Venda pendente não encontrada."}, status=404)

    itens = []
    for item in venda.itens.select_related("produto__linha_producao"):
        p = item.produto
        itens.append({
            "produto_id": p.pk,
            "descricao": p.descricao_pdv or p.descricao,
            "codigo_barras": p.codigo_barras or "",
            "icone": p.linha_producao.icone if p.linha_producao else "📦",
            "cor": p.linha_producao.cor_identificacao if p.linha_producao else None,
            "linha": p.linha_producao.nome if p.linha_producao else None,
            "quantidade": float(item.quantidade),
            "valor_unitario": float(item.valor_unitario),
            "valor_total": float(item.valor_total),
            "desconto_percentual": float(item.desconto_percentual or 0),
        })

    return JsonResponse({
        "ok": True,
        "venda_id": venda.pk,
        "numero_venda": venda.numero_venda,
        "cliente_id": venda.cliente_id,
        "cliente_nome": venda.cliente.razao_social if venda.cliente else "Consumidor Final",
        "cliente_cpf_cnpj": venda.cliente.cpf_cnpj if venda.cliente else "",
        "desconto": float(venda.valor_desconto),
        "acrescimo": float(venda.valor_acrescimo),
        "delivery": venda.delivery,
        "endereco_entrega": venda.endereco_entrega or {},
        "itens": itens,
    })


# ---------------------------------------------------------------------------
# API — Cancelar venda pendente
# ---------------------------------------------------------------------------

@requer_permissao('pdv', 'ver')
@require_POST
def api_pendente_cancelar(request, pk):
    try:
        venda = VendaPDV.objects.for_filial(request.filial_ativa).get(pk=pk, status="aberta")
    except VendaPDV.DoesNotExist:
        return JsonResponse({"erro": "Venda pendente não encontrada."}, status=404)

    venda.delete()
    return JsonResponse({"ok": True})


# ---------------------------------------------------------------------------
# API — Histórico de compras (vendas finalizadas)
# ---------------------------------------------------------------------------

@requer_permissao('pdv', 'ver')
@require_GET
def api_historico(request):
    qs = (
        VendaPDV.objects.for_filial(request.filial_ativa)
        .filter(status="finalizada")
        .select_related("cliente")
        .prefetch_related("itens")
        .order_by("-data_venda")[:30]
    )
    vendas = []
    for v in qs:
        vendas.append({
            "id": v.id,
            "numero_venda": v.numero_venda,
            "cliente": v.cliente.razao_social if v.cliente else "Consumidor Final",
            "valor_total": float(v.valor_total),
            "data_venda": v.data_venda.isoformat(),
            "delivery": v.delivery,
            "qtd_itens": v.itens.count(),
        })
    return JsonResponse({"vendas": vendas})


# ---------------------------------------------------------------------------
# API — Criar cliente rápido no PDV
# ---------------------------------------------------------------------------

@requer_permissao('pdv', 'ver')
@require_POST
def api_cliente_criar(request):
    from apps.cadastros.models import Cliente, ClienteFilial
    try:
        body = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({"erro": "JSON inválido."}, status=400)

    razao_social = body.get("razao_social", "").strip()
    if not razao_social:
        return JsonResponse({"erro": "Nome / Razão Social é obrigatório."}, status=400)

    tipo_pessoa = body.get("tipo_pessoa", "F")
    cpf_cnpj = (body.get("cpf_cnpj") or "").replace(".", "").replace("-", "").replace("/", "").strip()

    try:
        with transaction.atomic():
            cliente = Cliente.objects.create(
                filial=request.filial_ativa,
                tipo_pessoa=tipo_pessoa,
                razao_social=razao_social,
                nome_fantasia=body.get("nome_fantasia", ""),
                cpf_cnpj=cpf_cnpj,
                telefone=body.get("telefone", ""),
                celular=body.get("celular", ""),
                email=body.get("email", ""),
                cep=(body.get("cep") or "").replace("-", ""),
                endereco=body.get("endereco", ""),
                numero=body.get("numero", ""),
                complemento=body.get("complemento", ""),
                bairro=body.get("bairro", ""),
                cidade=body.get("cidade", ""),
                uf=body.get("uf", ""),
                consumidor_final=True,
                ativo=True,
            )
            ClienteFilial.objects.create(
                cliente=cliente,
                filial=request.filial_ativa,
                ativo=True,
            )
    except Exception as exc:
        return JsonResponse({"erro": str(exc)}, status=500)

    return JsonResponse({
        "ok": True,
        "cliente": {
            "id": cliente.id,
            "razao_social": cliente.razao_social,
            "cpf_cnpj": cliente.cpf_cnpj,
            "celular": cliente.celular,
        },
    })


# ---------------------------------------------------------------------------
# API — Gerar orçamento
# ---------------------------------------------------------------------------

@requer_permissao('pdv', 'ver')
@require_POST
def api_venda_orcamento(request):
    try:
        body = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({"erro": "JSON inválido."}, status=400)

    sessao = _sessao_aberta(request)
    if not sessao:
        return JsonResponse({"erro": "Nenhuma sessão de caixa aberta."}, status=400)

    itens = body.get("itens", [])
    if not itens:
        return JsonResponse({"erro": "Carrinho vazio."}, status=400)

    cliente_id = body.get("cliente_id")
    desconto = Decimal(str(body.get("desconto", "0")))
    acrescimo = Decimal(str(body.get("acrescimo", "0")))
    delivery = bool(body.get("delivery", False))
    endereco_entrega = body.get("endereco_entrega", {})

    try:
        with transaction.atomic():
            numero = _proximo_numero_venda(request.filial_ativa)

            venda = VendaPDV.objects.create(
                sessao_pdv=sessao,
                filial=request.filial_ativa,
                numero_venda=numero,
                cliente_id=cliente_id or None,
                status="orcamento",
                origem="pdv",
                delivery=delivery,
                endereco_entrega=endereco_entrega,
                valor_desconto=desconto,
                valor_acrescimo=acrescimo,
                usuario=request.user,
                data_venda=timezone.now(),
            )

            subtotal = Decimal("0")
            for idx, item in enumerate(itens, start=1):
                produto = Produto.objects.select_related("unidade_medida").get(id=int(item["produto_id"]))
                quantidade = Decimal(str(item["quantidade"]))
                valor_unitario = Decimal(str(item["valor_unitario"]))
                valor_total_item = quantidade * valor_unitario
                um_sigla = produto.unidade_medida.sigla if produto.unidade_medida_id else "UN"
                ItemVendaPDV.objects.create(
                    venda_pdv=venda,
                    produto=produto,
                    numero_item=idx,
                    quantidade=quantidade,
                    unidade_medida=um_sigla,
                    valor_unitario=valor_unitario,
                    valor_total=valor_total_item,
                )
                subtotal += valor_total_item

            venda.valor_subtotal = subtotal
            venda.valor_total = subtotal - desconto + acrescimo
            venda.save(update_fields=["valor_subtotal", "valor_total"])

    except Produto.DoesNotExist:
        return JsonResponse({"erro": "Produto não encontrado."}, status=404)
    except Exception as exc:
        return JsonResponse({"erro": str(exc)}, status=500)

    return JsonResponse({"ok": True, "numero_venda": venda.numero_venda, "venda_id": venda.id})


# ---------------------------------------------------------------------------
# Helper — Resumo de fechamento de caixa
# ---------------------------------------------------------------------------

def _resumo_sessao(sessao):
    """Monta o resumo completo de uma sessão de caixa para relatório."""
    vendas = (
        VendaPDV.objects.filter(sessao_pdv=sessao, status="finalizada")
        .select_related("cliente")
        .prefetch_related("pagamentos__forma_pagamento", "itens")
        .order_by("numero_venda")
    )

    total_balcao = Decimal("0")
    total_delivery = Decimal("0")
    qtd_balcao = 0
    qtd_delivery = 0
    qtd_itens = Decimal("0")
    desconto_total = Decimal("0")
    troco_dinheiro = Decimal("0")
    dinheiro_bruto = Decimal("0")

    formas_acc = {}   # forma_id -> {descricao, tipo, valor, qtd}
    vendas_list = []

    for v in vendas:
        if v.delivery:
            total_delivery += v.valor_total
            qtd_delivery += 1
        else:
            total_balcao += v.valor_total
            qtd_balcao += 1
        desconto_total += v.valor_desconto or Decimal("0")

        for it in v.itens.all():
            qtd_itens += it.quantidade

        for pg in v.pagamentos.all():
            fp = pg.forma_pagamento
            acc = formas_acc.setdefault(fp.id, {
                "descricao": fp.descricao, "tipo": fp.tipo,
                "valor": Decimal("0"), "qtd": 0,
            })
            acc["valor"] += pg.valor
            acc["qtd"] += 1
            if fp.tipo == "dinheiro":
                dinheiro_bruto += pg.valor
                troco_dinheiro += pg.troco

        vendas_list.append({
            "id": v.id,
            "numero_venda": v.numero_venda,
            "cliente": v.cliente.razao_social if v.cliente else "Consumidor Final",
            "valor_total": float(v.valor_total),
            "delivery": v.delivery,
            "tipo": "Delivery" if v.delivery else "Balcão",
            "data_venda": v.data_venda.isoformat(),
            "qtd_itens": v.itens.count(),
        })

    movs = list(MovimentacaoCaixa.objects.filter(sessao_pdv=sessao))
    total_sangrias = sum((m.valor for m in movs if m.tipo == "sangria"), Decimal("0"))
    total_suprimentos = sum((m.valor for m in movs if m.tipo == "suprimento"), Decimal("0"))
    movimentacoes = [{
        "tipo": m.tipo,
        "valor": float(m.valor),
        "observacao": m.observacao,
        "data": m.data_movimentacao.isoformat(),
    } for m in movs if m.tipo in ("sangria", "suprimento")]

    # Dinheiro físico esperado na gaveta
    esperado_dinheiro = (
        sessao.valor_abertura + dinheiro_bruto - troco_dinheiro
        + total_suprimentos - total_sangrias
    )

    total_geral = total_balcao + total_delivery

    return {
        "sessao": {
            "id": sessao.id,
            "caixa_numero": sessao.caixa.numero,
            "caixa_descricao": sessao.caixa.descricao,
            "operador": sessao.usuario.nome or sessao.usuario.email,
            "data_abertura": sessao.data_abertura.isoformat(),
            "valor_abertura": float(sessao.valor_abertura),
            "status": sessao.status,
            "data_fechamento": sessao.data_fechamento.isoformat() if sessao.data_fechamento else None,
        },
        "resumo": {
            "total_geral": float(total_geral),
            "qtd_vendas": qtd_balcao + qtd_delivery,
            "qtd_itens": float(qtd_itens),
            "desconto_total": float(desconto_total),
            "total_balcao": float(total_balcao),
            "qtd_balcao": qtd_balcao,
            "total_delivery": float(total_delivery),
            "qtd_delivery": qtd_delivery,
        },
        "formas_pagamento": sorted([
            {"descricao": f["descricao"], "tipo": f["tipo"],
             "valor": float(f["valor"]), "qtd": f["qtd"]}
            for f in formas_acc.values()
        ], key=lambda x: -x["valor"]),
        "caixa": {
            "valor_abertura": float(sessao.valor_abertura),
            "dinheiro_vendas": float(dinheiro_bruto),
            "troco": float(troco_dinheiro),
            "suprimentos": float(total_suprimentos),
            "sangrias": float(total_sangrias),
            "esperado_dinheiro": float(esperado_dinheiro),
        },
        "movimentacoes": movimentacoes,
        "vendas": vendas_list,
    }


# ---------------------------------------------------------------------------
# API — Resumo do caixa (relatório de fechamento)
# ---------------------------------------------------------------------------

@requer_permissao('pdv', 'ver')
@require_GET
def api_caixa_resumo(request):
    sessao = _sessao_aberta(request)
    if not sessao:
        return JsonResponse({"erro": "Nenhuma sessão de caixa aberta."}, status=400)
    return JsonResponse(_resumo_sessao(sessao))


# ---------------------------------------------------------------------------
# API — Registrar sangria / suprimento
# ---------------------------------------------------------------------------

@requer_permissao('pdv', 'ver')
@require_POST
def api_caixa_movimentacao(request):
    try:
        body = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({"erro": "JSON inválido."}, status=400)

    sessao = _sessao_aberta(request)
    if not sessao:
        return JsonResponse({"erro": "Nenhuma sessão de caixa aberta."}, status=400)

    tipo = body.get("tipo")
    if tipo not in ("sangria", "suprimento"):
        return JsonResponse({"erro": "Tipo inválido. Use sangria ou suprimento."}, status=400)

    try:
        valor = Decimal(str(body.get("valor", "0")))
    except (ValueError, TypeError):
        return JsonResponse({"erro": "Valor inválido."}, status=400)
    if valor <= 0:
        return JsonResponse({"erro": "O valor deve ser maior que zero."}, status=400)

    with transaction.atomic():
        MovimentacaoCaixa.objects.create(
            sessao_pdv=sessao,
            filial=request.filial_ativa,
            tipo=tipo,
            valor=valor,
            observacao=body.get("observacao", "")[:200],
            usuario=request.user,
            data_movimentacao=timezone.now(),
        )
        if tipo == "sangria":
            sessao.total_sangrias = (sessao.total_sangrias or Decimal("0")) + valor
            sessao.save(update_fields=["total_sangrias"])
        else:
            sessao.total_suprimentos = (sessao.total_suprimentos or Decimal("0")) + valor
            sessao.save(update_fields=["total_suprimentos"])

    return JsonResponse({"ok": True})


# ---------------------------------------------------------------------------
# API — Fechar caixa (com conferência)
# ---------------------------------------------------------------------------

@requer_permissao('pdv', 'ver')
@require_POST
def api_caixa_fechar(request):
    try:
        body = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({"erro": "JSON inválido."}, status=400)

    sessao = _sessao_aberta(request)
    if not sessao:
        return JsonResponse({"erro": "Nenhuma sessão de caixa aberta."}, status=400)

    try:
        valor_contado = Decimal(str(body.get("valor_contado", "0")))
    except (ValueError, TypeError):
        return JsonResponse({"erro": "Valor contado inválido."}, status=400)

    resumo = _resumo_sessao(sessao)
    esperado = Decimal(str(resumo["caixa"]["esperado_dinheiro"]))
    diferenca = valor_contado - esperado

    with transaction.atomic():
        sessao.status = "fechado"
        sessao.data_fechamento = timezone.now()
        sessao.valor_fechamento_informado = valor_contado
        sessao.valor_fechamento_sistema = esperado
        sessao.diferenca_caixa = diferenca
        sessao.conferido_por = request.user
        sessao.conferido_em = timezone.now()
        sessao.observacao_conferencia = body.get("observacao", "")
        sessao.save(update_fields=[
            "status", "data_fechamento", "valor_fechamento_informado",
            "valor_fechamento_sistema", "diferenca_caixa",
            "conferido_por", "conferido_em", "observacao_conferencia",
        ])
        MovimentacaoCaixa.objects.create(
            sessao_pdv=sessao,
            filial=request.filial_ativa,
            tipo="fechamento",
            valor=valor_contado,
            observacao=body.get("observacao", "")[:200],
            usuario=request.user,
            data_movimentacao=timezone.now(),
        )

    return JsonResponse({
        "ok": True,
        "esperado_dinheiro": float(esperado),
        "valor_contado": float(valor_contado),
        "diferenca": float(diferenca),
    })


# ---------------------------------------------------------------------------
# Delivery Kanban
# ---------------------------------------------------------------------------

DELIVERY_COLUNAS = [
    ('novo', 'Novo Pedido', '#3b82f6'),
    ('preparando', 'Em Preparo', '#f59e0b'),
    ('em_entrega', 'Saiu para Entrega', '#8b5cf6'),
    ('entregue', 'Entregue', '#10b981'),
]

DELIVERY_STATUS_VALIDOS = {c[0] for c in DELIVERY_COLUNAS} | {'cancelado'}


@requer_permissao('pdv', 'ver')
def delivery_kanban(request):
    qs = (
        VendaPDV.objects
        .for_filial(request.filial_ativa)
        .filter(delivery=True)
        .exclude(status='cancelada')
        .exclude(status_delivery='cancelado')
        .select_related('cliente', 'usuario')
        .prefetch_related('itens__produto')
        .order_by('data_venda')
    )

    colunas = []
    for status_key, label, cor in DELIVERY_COLUNAS:
        pedidos = [v for v in qs if v.status_delivery == status_key]
        colunas.append({
            'key': status_key,
            'label': label,
            'cor': cor,
            'pedidos': pedidos,
        })

    return render(request, 'pdv/delivery_kanban.html', {
        'colunas': colunas,
        'total': qs.count(),
    })


@require_POST
@requer_permissao('pdv', 'editar')
def delivery_mover(request, pk):
    try:
        body = json.loads(request.body or b'{}')
    except ValueError:
        return JsonResponse({'erro': 'JSON invalido'}, status=400)

    novo_status = body.get('status', '').strip()
    if novo_status not in DELIVERY_STATUS_VALIDOS:
        return JsonResponse({'erro': 'Status invalido'}, status=400)

    venda = VendaPDV.objects.for_filial(request.filial_ativa).filter(pk=pk, delivery=True).first()
    if not venda:
        return JsonResponse({'erro': 'Pedido nao encontrado'}, status=404)

    campos = ['status_delivery']
    venda.status_delivery = novo_status

    observacao = body.get('observacao', '').strip()
    if observacao:
        venda.observacao_delivery = observacao
        campos.append('observacao_delivery')

    entregador = body.get('entregador', '').strip()
    if entregador:
        venda.entregador = entregador[:100]
        campos.append('entregador')

    venda.save(update_fields=campos)
    return JsonResponse({
        'ok': True,
        'status': venda.status_delivery,
        'status_label': venda.get_status_delivery_display(),
    })


@require_POST
@requer_permissao('pdv', 'editar')
def delivery_atualizar(request, pk):
    try:
        body = json.loads(request.body or b'{}')
    except ValueError:
        return JsonResponse({'erro': 'JSON invalido'}, status=400)

    venda = VendaPDV.objects.for_filial(request.filial_ativa).filter(pk=pk, delivery=True).first()
    if not venda:
        return JsonResponse({'erro': 'Pedido nao encontrado'}, status=404)

    campos = []
    if 'entregador' in body:
        venda.entregador = str(body['entregador'])[:100]
        campos.append('entregador')
    if 'observacao_delivery' in body:
        venda.observacao_delivery = str(body['observacao_delivery'])
        campos.append('observacao_delivery')

    if campos:
        venda.save(update_fields=campos)

    return JsonResponse({'ok': True})
