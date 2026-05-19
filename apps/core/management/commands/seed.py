"""
Cria dados mínimos de demonstração para testar o sistema:
- 1 Empresa (Polpa do Nordeste)
- 2 Filiais (Matriz Natal + Filial Mossoró)
- 3 Perfis de acesso (Admin, Gerente, Operador)
- 1 Superusuário admin@inoovated.com / admin123
- 3 Categorias, 3 Unidades de Medida

Uso:
    python manage.py seed
"""
from django.core.management.base import BaseCommand
from django.db import transaction

from apps.core.models import Empresa, Filial, PerfilAcesso, Permissao, Usuario


class Command(BaseCommand):
    help = 'Cria dados iniciais de demonstração'

    @transaction.atomic
    def handle(self, *args, **options):
        self.stdout.write(self.style.NOTICE('Criando dados de demonstração...'))

        # Empresa
        empresa, created = Empresa.objects.get_or_create(
            cnpj='12345678000199',
            defaults={
                'razao_social': 'POLPA DO NORDESTE INDÚSTRIA LTDA',
                'nome_fantasia': 'Polpa do Nordeste',
                'regime_tributario': Empresa.RegimeTributario.SIMPLES_NACIONAL,
                'codigo_regime_tributario': 1,
                'endereco': 'Av. Industrial',
                'numero': '1000',
                'bairro': 'Distrito Industrial',
                'cidade': 'Natal',
                'uf': 'RN',
                'cep': '59100000',
                'codigo_municipio_ibge': '2408102',
                'email': 'contato@polpanordeste.com.br',
            },
        )
        self.stdout.write(f'  Empresa: {empresa} ({"criada" if created else "já existia"})')

        # Filiais
        matriz, _ = Filial.objects.get_or_create(
            cnpj='12345678000199',
            defaults={
                'empresa': empresa,
                'razao_social': empresa.razao_social,
                'nome_fantasia': 'Polpa do Nordeste — Matriz Natal',
                'is_matriz': True,
                'endereco': 'Av. Industrial', 'numero': '1000',
                'bairro': 'Distrito Industrial', 'cidade': 'Natal', 'uf': 'RN',
                'cep': '59100000', 'codigo_municipio_ibge': '2408102',
            },
        )
        filial_mossoro, _ = Filial.objects.get_or_create(
            cnpj='12345678000270',
            defaults={
                'empresa': empresa,
                'razao_social': empresa.razao_social,
                'nome_fantasia': 'Polpa do Nordeste — Mossoró',
                'is_matriz': False,
                'endereco': 'BR-304', 'numero': 'km 5',
                'bairro': 'Zona Rural', 'cidade': 'Mossoró', 'uf': 'RN',
                'cep': '59600000', 'codigo_municipio_ibge': '2408003',
            },
        )
        self.stdout.write(f'  Filiais: {matriz} / {filial_mossoro}')

        # Perfis
        admin_perfil, _ = PerfilAcesso.objects.get_or_create(
            empresa=empresa, nome='Administrador',
            defaults={'is_admin': True, 'descricao': 'Acesso total ao sistema.'},
        )
        gerente, _ = PerfilAcesso.objects.get_or_create(
            empresa=empresa, nome='Gerente',
            defaults={'descricao': 'Gerencia operação da filial, sem acesso a config.'},
        )
        operador, _ = PerfilAcesso.objects.get_or_create(
            empresa=empresa, nome='Operador',
            defaults={'descricao': 'Operador de PDV e estoque.'},
        )

        # Permissões do Gerente
        for mod in ['vendas', 'estoque', 'compras', 'producao', 'cadastros', 'produtos', 'relatorios']:
            Permissao.objects.get_or_create(
                perfil=gerente, modulo=mod,
                defaults={
                    'pode_ver': True, 'pode_criar': True, 'pode_editar': True,
                    'pode_cancelar': True, 'pode_aprovar': True, 'pode_exportar': True,
                },
            )
        # Permissões do Operador
        for mod in ['vendas', 'estoque', 'pdv']:
            Permissao.objects.get_or_create(
                perfil=operador, modulo=mod,
                defaults={'pode_ver': True, 'pode_criar': True},
            )

        # Superusuário
        email = 'admin@inoovated.com'
        if not Usuario.objects.filter(email=email).exists():
            Usuario.objects.create_superuser(
                email=email, nome='Admin do Sistema', password='admin123',
                empresa=empresa, filial=matriz, perfil=admin_perfil,
            )
            self.stdout.write(self.style.SUCCESS(f'  Superusuário criado: {email} / admin123'))
        else:
            self.stdout.write(f'  Superusuário já existia: {email}')

        # Seed de produtos (chamado se apps.produtos estiver disponível)
        self._seed_produtos(empresa, matriz)

        self.stdout.write(self.style.SUCCESS('\n✓ Seed concluído.'))
        self.stdout.write('  Acesse: http://localhost:8000/auth/login/')
        self.stdout.write('  Login: admin@inoovated.com / admin123')

    def _seed_produtos(self, empresa, matriz):
        try:
            from apps.produtos.models import CategoriaProduto, UnidadeMedida
        except ImportError:
            return

        CategoriaProduto.objects.get_or_create(
            empresa=empresa, filial=matriz, nome='Polpa de Fruta',
            defaults={
                'descricao': 'Polpas produzidas internamente',
                'id_externo': 'seed:categoria:polpa-de-fruta',
            },
        )
        CategoriaProduto.objects.get_or_create(
            empresa=empresa, filial=matriz, nome='Matéria-Prima',
            defaults={
                'descricao': 'Frutas frescas e insumos',
                'id_externo': 'seed:categoria:materia-prima',
            },
        )
        CategoriaProduto.objects.get_or_create(
            empresa=empresa, filial=matriz, nome='Embalagem',
            defaults={
                'descricao': 'Sacos, caixas, rotulos',
                'id_externo': 'seed:categoria:embalagem',
            },
        )

        for sigla, desc, tipo in [
            ('KG', 'Quilograma', 'peso'),
            ('UN', 'Unidade', 'unidade'),
            ('L', 'Litro', 'volume'),
            ('CX', 'Caixa', 'unidade'),
        ]:
            UnidadeMedida.objects.get_or_create(
                empresa=empresa, sigla=sigla,
                defaults={'descricao': desc, 'tipo': tipo},
            )
        self.stdout.write('  Categorias e unidades base criadas.')
