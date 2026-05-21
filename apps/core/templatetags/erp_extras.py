"""Filtros e tags customizados."""
from collections import deque
from decimal import Decimal
from io import BytesIO
import hashlib

from django import template
from django.core.files.base import ContentFile

try:
    from PIL import Image
except Exception:  # pragma: no cover - ambiente sem Pillow
    Image = None

register = template.Library()


@register.filter
def moeda(valor):
    """Formata Decimal como R$ 1.234,56."""
    if valor is None or valor == '':
        return 'R$ 0,00'
    try:
        valor = Decimal(str(valor))
    except Exception:
        return valor
    s = f'{valor:,.2f}'
    # Converte formato EN (1,234.56) para pt-BR (1.234,56)
    s = s.replace(',', 'X').replace('.', ',').replace('X', '.')
    return f'R$ {s}'


@register.filter
def quantidade(valor, casas=3):
    """Formata quantidade sem zeros finais desnecessarios."""
    if valor is None:
        return '0'
    try:
        valor = Decimal(str(valor))
    except Exception:
        return valor
    if valor == valor.to_integral_value():
        casas = 0
    fmt = f'{{:,.{casas}f}}'
    s = fmt.format(valor).replace(',', 'X').replace('.', ',').replace('X', '.')
    if casas:
        s = s.rstrip('0').rstrip(',')
    return s


@register.filter
def quantidade_produto(valor, produto=None):
    """Formata estoque como inteiro para unitarios e decimal para granel/fracionado."""
    if valor is None:
        return '0'
    try:
        valor = Decimal(str(valor))
    except Exception:
        return valor
    usa_decimal = False
    if produto is not None:
        usa_decimal = bool(
            getattr(produto, 'vendido_por_peso_granel', False)
            or getattr(produto, 'fracionavel', False)
            or getattr(produto, 'eh_granel', False)
        )
    casas = 3 if usa_decimal else (2 if valor != valor.to_integral_value() else 0)
    fmt = f'{{:,.{casas}f}}'
    return fmt.format(valor).replace(',', 'X').replace('.', ',').replace('X', '.')


@register.filter
def cpf_cnpj(valor):
    """Formata CPF ou CNPJ."""
    if not valor:
        return ''
    v = ''.join(filter(str.isdigit, str(valor)))
    if len(v) == 11:
        return f'{v[:3]}.{v[3:6]}.{v[6:9]}-{v[9:]}'
    if len(v) == 14:
        return f'{v[:2]}.{v[2:5]}.{v[5:8]}/{v[8:12]}-{v[12:]}'
    return valor


@register.filter
def telefone(valor):
    """Formata telefone brasileiro quando houver DDD."""
    if not valor:
        return ''
    v = ''.join(filter(str.isdigit, str(valor)))
    if len(v) == 11:
        return f'({v[:2]}) {v[2:7]}-{v[7:]}'
    if len(v) == 10:
        return f'({v[:2]}) {v[2:6]}-{v[6:]}'
    return valor


@register.filter
def filial_apelido(filial):
    """Retorna um nome curto e operacional para a filial."""
    if not filial:
        return ''

    nome = (
        getattr(filial, 'nome_fantasia', None)
        or getattr(filial, 'razao_social', None)
        or str(filial)
    ).strip()
    cidade = (getattr(filial, 'cidade', None) or '').strip()

    apelido = nome
    for separador in (' — ', ' – ', ' - ', '—', '–'):
        if separador in apelido:
            apelido = apelido.rsplit(separador, 1)[-1].strip()
            break

    if getattr(filial, 'is_matriz', False) and 'matriz' not in apelido.lower():
        apelido = f'Matriz {cidade}'.strip() if cidade else f'Matriz {apelido}'.strip()

    return apelido or cidade or nome


@register.filter
def cep(valor):
    """Formata CEP."""
    if not valor:
        return ''
    v = ''.join(filter(str.isdigit, str(valor)))
    if len(v) == 8:
        return f'{v[:5]}-{v[5:]}'
    return valor


@register.filter
def semaforo_estoque(item):
    """
    Retorna classe CSS semafórica para nível de estoque.
    Espera um dict/obj com `quantidade` e `minimo`.
    """
    try:
        qtd = float(item.get('quantidade', 0) if isinstance(item, dict) else item.quantidade_disponivel or 0)
        minimo = float(item.get('minimo', 0) if isinstance(item, dict) else item.produto.estoque_minimo or 0)
    except Exception:
        return 'bg-gray-100 text-gray-600'

    if minimo > 0 and qtd <= 0:
        return 'bg-red-100 text-red-700'
    if minimo > 0 and qtd < minimo:
        return 'bg-amber-100 text-amber-700'
    return 'bg-emerald-100 text-emerald-700'


def _pixel_quase_branco(pixel, limite=235):
    r, g, b = pixel[:3]
    return r >= limite and g >= limite and b >= limite and (max(r, g, b) - min(r, g, b) <= 30)


@register.filter
def logo_sem_fundo_url(imagem):
    """Gera uma copia PNG removendo apenas o fundo branco ligado as bordas."""
    if not imagem:
        return ''
    try:
        url_original = imagem.url
    except Exception:
        return ''
    if Image is None:
        return url_original

    nome_original = getattr(imagem, 'name', '') or ''
    storage = getattr(imagem, 'storage', None)
    if not nome_original or storage is None:
        return url_original

    chave = hashlib.sha1(nome_original.encode('utf-8')).hexdigest()[:16]
    nome_cache = f'filiais/imagens/cache/sem-fundo-{chave}.png'
    try:
        if storage.exists(nome_cache):
            return storage.url(nome_cache)

        with storage.open(nome_original, 'rb') as arquivo:
            base = Image.open(arquivo).convert('RGBA')

        base.thumbnail((720, 720), Image.Resampling.LANCZOS)
        largura, altura = base.size
        pixels = base.load()
        fila = deque()
        visitados = set()

        for x in range(largura):
            fila.append((x, 0))
            fila.append((x, altura - 1))
        for y in range(altura):
            fila.append((0, y))
            fila.append((largura - 1, y))

        while fila:
            x, y = fila.popleft()
            if (x, y) in visitados or not (0 <= x < largura and 0 <= y < altura):
                continue
            visitados.add((x, y))
            if not _pixel_quase_branco(pixels[x, y]):
                continue

            r, g, b, _alpha = pixels[x, y]
            pixels[x, y] = (r, g, b, 0)
            fila.extend(((x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1)))

        bbox = base.split()[-1].getbbox()
        if bbox:
            margem = 8
            left = max(0, bbox[0] - margem)
            top = max(0, bbox[1] - margem)
            right = min(largura, bbox[2] + margem)
            bottom = min(altura, bbox[3] + margem)
            base = base.crop((left, top, right, bottom))

        buffer = BytesIO()
        base.save(buffer, format='PNG', optimize=True)
        storage.save(nome_cache, ContentFile(buffer.getvalue()))
        return storage.url(nome_cache)
    except Exception:
        return url_original
