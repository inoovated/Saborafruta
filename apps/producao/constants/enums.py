from django.db import models


class StatusOP(models.TextChoices):
    RASCUNHO = "rascunho", "Rascunho"
    PLANEJADA = "planejada", "Planejada"
    ABERTA = "aberta", "Aberta"
    EM_PRODUCAO = "em_producao", "Em produção"
    PAUSADA = "pausada", "Pausada"
    ENCERRADA = "encerrada", "Encerrada"
    CANCELADA = "cancelada", "Cancelada"


class TurnoProducao(models.TextChoices):
    MATUTINO = "matutino", "Matutino"
    VESPERTINO = "vespertino", "Vespertino"
    NOTURNO = "noturno", "Noturno"
    INTEGRAL = "integral", "Integral"


class EtapaProducao(models.TextChoices):
    PREPARACAO = "preparacao", "Preparação"
    MISTURA = "mistura", "Mistura"
    PROCESSAMENTO = "processamento", "Processamento"
    ENVASE = "envase", "Envase"
    CONGELAMENTO = "congelamento", "Congelamento"
    SECAGEM = "secagem", "Secagem"
    EXTRUSAO = "extrusao", "Extrusão"
    SOPRO = "sopro", "Sopro"
    CORTE = "corte", "Corte"
    SOLDA = "solda", "Solda"
    IMPRESSAO = "impressao", "Impressão"
    ACABAMENTO = "acabamento", "Acabamento"
    EMBALAGEM = "embalagem", "Embalagem"


class TipoPerda(models.TextChoices):
    PROCESSO = "processo", "Processo"
    QUEBRAS = "quebras", "Quebras"
    QUALIDADE = "qualidade", "Qualidade"
    VENCIMENTO = "vencimento", "Vencimento"
    STARTUP = "startup", "Setup/Startup"
    TRANSPORTE = "transporte", "Transporte"
    ARMAZENAMENTO = "armazenamento", "Armazenamento"
