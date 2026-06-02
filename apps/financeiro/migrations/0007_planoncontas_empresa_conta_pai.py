"""Adiciona empresa_id e conta_pai_id a tabela plano_contas."""
import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):
    """
    PlanoContas.empresa e PlanoContas.conta_pai ja existem desde
    financeiro.0002_initial. Usamos SeparateDatabaseAndState para apenas
    atualizar o estado do Django.
    """

    dependencies = [
        ("core", "0001_initial"),
        ("financeiro", "0006_rename_fin_credcli_filial_idx_financeiro__filial__2a5b32_idx"),
    ]

    operations = [
        migrations.SeparateDatabaseAndState(
            database_operations=[],
            state_operations=[
                migrations.AddField(
                    model_name="planocontas",
                    name="empresa",
                    field=models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="plano_contas",
                        to="core.empresa",
                    ),
                ),
                migrations.AddField(
                    model_name="planocontas",
                    name="conta_pai",
                    field=models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="filhas",
                        to="financeiro.planocontas",
                    ),
                ),
            ],
        ),
    ]
