"""Processamento de imagens de filial."""
from io import BytesIO
from pathlib import Path

from django.core.files.base import ContentFile
from PIL import Image


def preparar_imagem_filial(arquivo, max_width=900, max_height=360):
    """Redimensiona a imagem da filial preservando proporcao e sem cortar."""
    arquivo.seek(0)
    imagem = Image.open(arquivo)
    tem_alpha = imagem.mode in ('RGBA', 'LA') or (
        imagem.mode == 'P' and 'transparency' in imagem.info
    )
    imagem = imagem.convert('RGBA' if tem_alpha else 'RGB')
    imagem.thumbnail((max_width, max_height), Image.Resampling.LANCZOS)

    buffer = BytesIO()
    nome_base = Path(getattr(arquivo, 'name', '') or 'filial').stem or 'filial'
    if tem_alpha:
        imagem.save(buffer, format='PNG', optimize=True)
        nome = f'{nome_base}.png'
    else:
        imagem.save(buffer, format='JPEG', quality=92, optimize=True, progressive=True)
        nome = f'{nome_base}.jpg'
    return ContentFile(buffer.getvalue(), name=nome)
