from django.db import migrations


class Migration(migrations.Migration):
    """Concilia as branches que criavam ParametrosSistema em paralelo.

    ParametrosSistema e ParametroDocumentoFiscal já são criados em
    core.0010_parametros_sistema. Esta migration passa a somente unir a
    branch fiscal iniciada em core.0012 com a branch já existente.
    """

    dependencies = [
        ('core', '0013_filial_regime_tributario'),
        ('core', '0011_certificado_digital'),
    ]

    operations = []
