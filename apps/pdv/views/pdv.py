import json
from decimal import Decimal

from django.db import transaction
from django.db.models import Q
from django.http import JsonResponse
from django.shortcuts import render
from django.core.paginator import Paginator
from django.utils import timezone
from django.views.decorators.http import require_GET, require_POST

from apps.core.services.permissions import requer_permissao
from apps.financeiro.models import FormaPagamento
from apps.pdv.models import (
    Caixa, ItemVendaPDV, PagamentoVendaPDV, SessaoPDV, VendaPDV,
)
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
    qs = qs.select_related("linha_producao")[:20]
    data = [{
        "id": p.id, "descricao": p.descricao_pdv or p.descricao,
        "codigo_barras": p.codigo_barras,
        "preco": float(p.preco_atual),
        "linha": p.linha_producao.nome if p.linha_producao else None,
        "icone": p.linha_producao.icone if p.linha_producao else None,
        "cor": p.linha_producao.cor_identificacao if p.linha_producao else None,
    } for p in qs]
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

@requer_permissao('pdv', 'ver')
@require_GET
def api_estado(request):
    sessao = _sessao_aberta(request)

    formas = list(
        FormaPagamento.objects.filter(
            empresa=request.filial_ativa.empresa, ativo=True
        ).values('id', 'descricao', 'tipo', 'requer_tef')
    )

    top_produtos_qs = (
        Produto.objects.for_filial(request.filial_ativa)
        .filter(ativo=True)
        .select_related('linha_producao')
        .order_by('descricao')[:12]
    )
    top_produtos = []
    for p in top_produtos_qs:
        top_produtos.append({
            "id": p.id,
            "descricao": p.descricao_pdv or p.descricao,
            "codigo_barras": p.codigo_barras,
            "preco": float(p.preco_atual or 0),
            "linha": p.linha_producao.nome if p.linha_producao else None,
            "icone": p.linha_producao.icone if p.linha_producao else None,
            "cor": p.linha_producao.cor_identificacao if p.linha_producao else None,
        })

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
        with transaction.atomic():
            numero = _proximo_numero_venda(request.filial_ativa)

            venda = VendaPDV.objects.create(
                sessao_pdv=sessao,
                filial=request.filial_ativa,
                numero_venda=numero,
                cliente_id=cliente_id or None,
                status="finalizada",
                delivery=delivery,
                endereco_entrega=endereco_entrega,
                valor_desconto=desconto,
                valor_acrescimo=acrescimo,
                usuario=request.user,
                data_venda=timezone.now(),
            )

            subtotal = Decimal("0")
            for idx, item in enumerate(itens, start=1):
                produto_id = int(item["produto_id"])
                quantidade = Decimal(str(item["quantidade"]))
                valor_unitario = Decimal(str(item["valor_unitario"]))
                valor_total_item = quantidade * valor_unitario

                produto = Produto.objects.select_related("unidade_medida").get(id=produto_id)
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

            valor_total = subtotal - desconto + acrescimo
            valor_pago = Decimal("0")
            troco_total = Decimal("0")

            for pgto in pagamentos:
                forma = FormaPagamento.objects.get(
                    id=int(pgto["forma_id"]), empresa=request.filial_ativa.empresa
                )
                valor_pgto = Decimal(str(pgto["valor"]))
                troco = max(Decimal("0"), valor_pgto - (valor_total - valor_pago))
                PagamentoVendaPDV.objects.create(
                    venda_pdv=venda,
                    forma_pagamento=forma,
                    valor=valor_pgto,
                    troco=troco,
                )
                valor_pago += valor_pgto
                troco_total += troco

            venda.valor_subtotal = subtotal
            venda.valor_total = valor_total
            venda.valor_pago = valor_pago
            venda.troco = troco_total
            venda.save(update_fields=[
                "valor_subtotal", "valor_total", "valor_pago", "troco"
            ])

            sessao.total_vendas = (sessao.total_vendas or Decimal("0")) + valor_total
            sessao.save(update_fields=["total_vendas"])

    except Produto.DoesNotExist:
        return JsonResponse({"erro": "Produto não encontrado."}, status=404)
    except FormaPagamento.DoesNotExist:
        return JsonResponse({"erro": "Forma de pagamento não encontrada."}, status=404)
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
