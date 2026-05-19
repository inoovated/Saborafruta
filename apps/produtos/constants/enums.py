from django.db import models


class TipoProduto(models.TextChoices):
    MATERIA_PRIMA = "materia_prima", "Matéria-prima"
    INSUMO = "insumo", "Insumo"
    PRODUTO_ACABADO = "produto_acabado", "Produto Acabado"
    EMBALAGEM = "embalagem", "Embalagem"
    SUBPRODUTO = "subproduto", "Subproduto"
    UNITARIO = "unitario", "Unitário"
    FRACIONADO = "fracionado", "Fracionado"
    GRANEL_PESO = "granel_peso", "Granel (peso)"
    GRANEL_VOLUME = "granel_volume", "Granel (volume)"
    SERVICO = "servico", "Serviço"
    KIT = "kit", "Kit"


class TemperaturaArmazenamento(models.TextChoices):
    AMBIENTE = "ambiente", "Ambiente"
    RESFRIADO = "resfriado", "Resfriado"
    ZERO_A_QUATRO = "0_a_4", "0°C a 4°C"
    NEG_18 = "neg_18", "-18°C"
    NEG_25 = "neg_25", "-25°C"


class OrigemProduto(models.IntegerChoices):
    NACIONAL = 0, "0 - Nacional"
    ESTRANGEIRA_DIRETA = 1, "1 - Estrangeira (importação direta)"
    ESTRANGEIRA_MERCADO = 2, "2 - Estrangeira (mercado interno)"


class TipoUnidade(models.TextChoices):
    UNIDADE = "unidade", "Unidade"
    PESO = "peso", "Peso"
    VOLUME = "volume", "Volume"
    COMPRIMENTO = "comprimento", "Comprimento"
    AREA = "area", "Área"
