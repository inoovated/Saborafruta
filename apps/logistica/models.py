from decimal import Decimal

from django.conf import settings
from django.db import models
from django.db.models import Sum
from django.utils import timezone

from apps.core.models import FilialScopedModel, TimestampedModel


class RomaneioCarga(FilialScopedModel):
    class Status(models.TextChoices):
        RASCUNHO = "rascunho", "Rascunho"
        EM_CARREGAMENTO = "em_carregamento", "Em carregamento"
        EM_ROTA = "em_rota", "Em rota"
        ENTREGUE = "entregue", "Entregue"
        CANCELADO = "cancelado", "Cancelado"

    numero = models.PositiveIntegerField(db_index=True)
    data = models.DateField(default=timezone.localdate, db_index=True)
    status = models.CharField(max_length=30, choices=Status.choices, default=Status.RASCUNHO, db_index=True)
    responsavel = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="romaneios_carga",
    )
    transportadora = models.ForeignKey(
        "cadastros.Transportadora",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="romaneios_carga",
    )
    motorista_nome = models.CharField(max_length=120, blank=True)
    motorista_documento = models.CharField(max_length=30, blank=True)
    veiculo_placa = models.CharField(max_length=10, blank=True)
    veiculo_descricao = models.CharField(max_length=100, blank=True)
    origem = models.CharField(max_length=160, blank=True)
    destino_rota = models.CharField(max_length=160, blank=True)
    observacao = models.TextField(blank=True)
    peso_total_kg = models.DecimalField(max_digits=12, decimal_places=3, default=0)
    volume_total = models.DecimalField(max_digits=12, decimal_places=3, default=0)
    valor_total = models.DecimalField(max_digits=14, decimal_places=2, default=0)

    class Meta:
        db_table = "logistica_romaneios_carga"
        ordering = ["-data", "-numero"]
        unique_together = [("filial", "numero")]
        indexes = [
            models.Index(fields=["filial", "status", "-data"]),
            models.Index(fields=["filial", "-numero"]),
        ]
        verbose_name = "Romaneio de Carga"
        verbose_name_plural = "Romaneios de Carga"

    def __str__(self):
        return f"Romaneio #{self.numero:06d}"

    def recalcular_totais(self):
        totais = self.itens.aggregate(
            peso_total=Sum("peso_kg"),
            volume_total=Sum("volumes"),
            valor_total=Sum("valor"),
        )
        self.peso_total_kg = totais["peso_total"] or Decimal("0")
        self.volume_total = totais["volume_total"] or Decimal("0")
        self.valor_total = totais["valor_total"] or Decimal("0")
        self.save(update_fields=["peso_total_kg", "volume_total", "valor_total", "updated_at"])


class ItemRomaneioCarga(TimestampedModel):
    class StatusEntrega(models.TextChoices):
        PENDENTE = "pendente", "Pendente"
        CARREGADO = "carregado", "Carregado"
        ENTREGUE = "entregue", "Entregue"
        NAO_ENTREGUE = "nao_entregue", "Nao entregue"
        CANCELADO = "cancelado", "Cancelado"

    romaneio = models.ForeignKey(RomaneioCarga, on_delete=models.CASCADE, related_name="itens")
    venda_pdv = models.ForeignKey(
        "pdv.VendaPDV",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="itens_romaneio",
    )
    pedido_venda = models.ForeignKey(
        "vendas.PedidoVenda",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="itens_romaneio",
    )
    ordem = models.PositiveIntegerField(default=0)
    cliente_nome = models.CharField(max_length=180)
    documento = models.CharField(max_length=60, blank=True)
    endereco_entrega = models.JSONField(default=dict, blank=True)
    status_entrega = models.CharField(
        max_length=30,
        choices=StatusEntrega.choices,
        default=StatusEntrega.PENDENTE,
        db_index=True,
    )
    volumes = models.DecimalField(max_digits=12, decimal_places=3, default=0)
    peso_kg = models.DecimalField(max_digits=12, decimal_places=3, default=0)
    valor = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    observacao = models.TextField(blank=True)

    class Meta:
        db_table = "logistica_itens_romaneio_carga"
        ordering = ["ordem", "id"]
        indexes = [
            models.Index(fields=["romaneio", "status_entrega"]),
            models.Index(fields=["venda_pdv"]),
            models.Index(fields=["pedido_venda"]),
        ]
        verbose_name = "Item do Romaneio"
        verbose_name_plural = "Itens do Romaneio"

    def __str__(self):
        return f"{self.cliente_nome} - {self.romaneio}"


class OrdemColeta(FilialScopedModel):
    class Status(models.TextChoices):
        RASCUNHO = "rascunho", "Rascunho"
        SOLICITADA = "solicitada", "Solicitada"
        PROGRAMADA = "programada", "Programada"
        COLETADA = "coletada", "Coletada"
        CANCELADA = "cancelada", "Cancelada"

    class TipoSolicitante(models.TextChoices):
        CLIENTE = "cliente", "Cliente"
        FORNECEDOR = "fornecedor", "Fornecedor"
        FILIAL = "filial", "Filial"
        AVULSO = "avulso", "Avulso"

    numero = models.PositiveIntegerField(db_index=True)
    data_solicitacao = models.DateField(default=timezone.localdate, db_index=True)
    data_coleta_prevista = models.DateField(null=True, blank=True, db_index=True)
    data_coleta_realizada = models.DateField(null=True, blank=True)
    status = models.CharField(max_length=30, choices=Status.choices, default=Status.RASCUNHO, db_index=True)
    tipo_solicitante = models.CharField(
        max_length=20,
        choices=TipoSolicitante.choices,
        default=TipoSolicitante.CLIENTE,
    )
    responsavel = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="ordens_coleta",
    )
    cliente = models.ForeignKey(
        "cadastros.Cliente",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="ordens_coleta",
    )
    fornecedor = models.ForeignKey(
        "cadastros.Fornecedor",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="ordens_coleta",
    )
    transportadora = models.ForeignKey(
        "cadastros.Transportadora",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="ordens_coleta",
    )
    romaneio = models.ForeignKey(
        RomaneioCarga,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="ordens_coleta",
    )
    solicitante_nome = models.CharField(max_length=180, blank=True)
    contato_nome = models.CharField(max_length=120, blank=True)
    contato_telefone = models.CharField(max_length=30, blank=True)
    endereco_coleta = models.JSONField(default=dict, blank=True)
    endereco_entrega = models.JSONField(default=dict, blank=True)
    motorista_nome = models.CharField(max_length=120, blank=True)
    veiculo_placa = models.CharField(max_length=10, blank=True)
    volumes = models.DecimalField(max_digits=12, decimal_places=3, default=0)
    peso_total_kg = models.DecimalField(max_digits=12, decimal_places=3, default=0)
    valor_estimado = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    observacao = models.TextField(blank=True)

    class Meta:
        db_table = "logistica_ordens_coleta"
        ordering = ["-data_solicitacao", "-numero"]
        unique_together = [("filial", "numero")]
        indexes = [
            models.Index(fields=["filial", "status", "-data_solicitacao"]),
            models.Index(fields=["filial", "data_coleta_prevista"]),
            models.Index(fields=["cliente"]),
            models.Index(fields=["fornecedor"]),
        ]
        verbose_name = "Ordem de Coleta"
        verbose_name_plural = "Ordens de Coleta"

    def __str__(self):
        return f"Ordem de Coleta #{self.numero:06d}"

    def recalcular_totais(self):
        totais = self.itens.aggregate(
            volumes=Sum("volumes"),
            peso_total=Sum("peso_kg"),
            valor_total=Sum("valor"),
        )
        self.volumes = totais["volumes"] or Decimal("0")
        self.peso_total_kg = totais["peso_total"] or Decimal("0")
        self.valor_estimado = totais["valor_total"] or Decimal("0")
        self.save(update_fields=["volumes", "peso_total_kg", "valor_estimado", "updated_at"])


class ItemOrdemColeta(TimestampedModel):
    ordem = models.ForeignKey(OrdemColeta, on_delete=models.CASCADE, related_name="itens")
    descricao = models.CharField(max_length=220)
    quantidade = models.DecimalField(max_digits=12, decimal_places=3, default=1)
    unidade = models.CharField(max_length=10, default="UN")
    volumes = models.DecimalField(max_digits=12, decimal_places=3, default=0)
    peso_kg = models.DecimalField(max_digits=12, decimal_places=3, default=0)
    valor = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    observacao = models.TextField(blank=True)

    class Meta:
        db_table = "logistica_itens_ordem_coleta"
        ordering = ["id"]
        indexes = [
            models.Index(fields=["ordem"]),
        ]
        verbose_name = "Item da Ordem de Coleta"
        verbose_name_plural = "Itens da Ordem de Coleta"

    def __str__(self):
        return f"{self.descricao} - {self.ordem}"


class ManifestoCarga(FilialScopedModel):
    class Status(models.TextChoices):
        RASCUNHO = "rascunho", "Rascunho"
        EMITIDO = "emitido", "Emitido"
        EM_TRANSITO = "em_transito", "Em transito"
        ENCERRADO = "encerrado", "Encerrado"
        CANCELADO = "cancelado", "Cancelado"

    class Modal(models.TextChoices):
        RODOVIARIO = "rodoviario", "Rodoviario"
        AEREO = "aereo", "Aereo"
        AQUAVIARIO = "aquaviario", "Aquaviario"
        FERROVIARIO = "ferroviario", "Ferroviario"

    numero = models.PositiveIntegerField(db_index=True)
    data_emissao = models.DateField(default=timezone.localdate, db_index=True)
    data_saida = models.DateField(null=True, blank=True)
    status = models.CharField(max_length=30, choices=Status.choices, default=Status.RASCUNHO, db_index=True)
    modal = models.CharField(max_length=20, choices=Modal.choices, default=Modal.RODOVIARIO)
    responsavel = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="manifestos_carga",
    )
    romaneio = models.ForeignKey(
        RomaneioCarga,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="manifestos_carga",
    )
    transportadora = models.ForeignKey(
        "cadastros.Transportadora",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="manifestos_carga",
    )
    motorista_nome = models.CharField(max_length=120, blank=True)
    motorista_documento = models.CharField(max_length=30, blank=True)
    veiculo_placa = models.CharField(max_length=10, blank=True)
    veiculo_descricao = models.CharField(max_length=100, blank=True)
    cidade_origem = models.CharField(max_length=100, blank=True)
    uf_origem = models.CharField(max_length=2, blank=True)
    cidade_destino = models.CharField(max_length=100, blank=True)
    uf_destino = models.CharField(max_length=2, blank=True)
    percurso = models.TextField(blank=True)
    qtd_documentos = models.PositiveIntegerField(default=0)
    volumes = models.DecimalField(max_digits=12, decimal_places=3, default=0)
    peso_total_kg = models.DecimalField(max_digits=12, decimal_places=3, default=0)
    valor_total = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    observacao = models.TextField(blank=True)

    class Meta:
        db_table = "logistica_manifestos_carga"
        ordering = ["-data_emissao", "-numero"]
        unique_together = [("filial", "numero")]
        indexes = [
            models.Index(fields=["filial", "status", "-data_emissao"]),
            models.Index(fields=["filial", "-numero"]),
            models.Index(fields=["romaneio"]),
        ]
        verbose_name = "Manifesto de Carga"
        verbose_name_plural = "Manifestos de Carga"

    def __str__(self):
        return f"Manifesto #{self.numero:06d}"

    def recalcular_totais(self):
        totais = self.documentos.aggregate(
            volumes=Sum("volumes"),
            peso_total=Sum("peso_kg"),
            valor_total=Sum("valor"),
        )
        self.qtd_documentos = self.documentos.count()
        self.volumes = totais["volumes"] or Decimal("0")
        self.peso_total_kg = totais["peso_total"] or Decimal("0")
        self.valor_total = totais["valor_total"] or Decimal("0")
        self.save(update_fields=["qtd_documentos", "volumes", "peso_total_kg", "valor_total", "updated_at"])


class DocumentoManifestoCarga(TimestampedModel):
    class TipoDocumento(models.TextChoices):
        NFE = "nfe", "NF-e"
        NFCE = "nfce", "NFC-e"
        CTE = "cte", "CT-e"
        NFSE = "nfse", "NFS-e"
        OUTRO = "outro", "Outro"

    manifesto = models.ForeignKey(ManifestoCarga, on_delete=models.CASCADE, related_name="documentos")
    tipo_documento = models.CharField(max_length=20, choices=TipoDocumento.choices, default=TipoDocumento.NFE)
    numero_documento = models.CharField(max_length=60)
    serie = models.CharField(max_length=20, blank=True)
    chave_acesso = models.CharField(max_length=80, blank=True, db_index=True)
    remetente_nome = models.CharField(max_length=180, blank=True)
    destinatario_nome = models.CharField(max_length=180, blank=True)
    cidade_origem = models.CharField(max_length=100, blank=True)
    uf_origem = models.CharField(max_length=2, blank=True)
    cidade_destino = models.CharField(max_length=100, blank=True)
    uf_destino = models.CharField(max_length=2, blank=True)
    volumes = models.DecimalField(max_digits=12, decimal_places=3, default=0)
    peso_kg = models.DecimalField(max_digits=12, decimal_places=3, default=0)
    valor = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    observacao = models.TextField(blank=True)

    class Meta:
        db_table = "logistica_documentos_manifesto_carga"
        ordering = ["id"]
        indexes = [
            models.Index(fields=["manifesto"]),
            models.Index(fields=["tipo_documento", "numero_documento"]),
        ]
        verbose_name = "Documento do Manifesto"
        verbose_name_plural = "Documentos do Manifesto"

    def __str__(self):
        return f"{self.get_tipo_documento_display()} {self.numero_documento}"
