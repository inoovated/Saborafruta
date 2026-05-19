from django.db import models


class TipoAnalise(models.TextChoices):
    MATERIA_PRIMA = "materia_prima", "Matéria-prima"
    PRODUTO_ACABADO = "produto_acabado", "Produto Acabado"
    PROCESSO = "processo", "Processo"
    EMBALAGEM = "embalagem", "Embalagem"


class ResultadoAnalise(models.TextChoices):
    PENDENTE = "pendente", "Pendente"
    APROVADO = "aprovado", "Aprovado"
    REPROVADO = "reprovado", "Reprovado"
    APROVADO_COM_RESSALVA = "aprovado_com_ressalva", "Aprovado com ressalva"


class AcaoReprovacao(models.TextChoices):
    BLOQUEIO = "bloqueio", "Bloqueio"
    DESCARTE = "descarte", "Descarte"
    REPROCESSAMENTO = "reprocessamento", "Reprocessamento"
    DEVOLUCAO_FORNECEDOR = "devolucao_fornecedor", "Devolução ao fornecedor"
