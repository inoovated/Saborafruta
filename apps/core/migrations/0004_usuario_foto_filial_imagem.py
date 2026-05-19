from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0003_permissao_qualidade'),
    ]

    operations = [
        migrations.AddField(
            model_name='filial',
            name='imagem',
            field=models.ImageField(blank=True, null=True, upload_to='filiais/imagens/'),
        ),
        migrations.AddField(
            model_name='usuario',
            name='foto',
            field=models.ImageField(blank=True, null=True, upload_to='usuarios/fotos/'),
        ),
    ]
