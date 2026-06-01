from __future__ import annotations

import gzip
import json
from datetime import datetime
from pathlib import Path

from django.apps import apps
from django.core.management.base import BaseCommand, CommandError
from django.core.serializers.json import DjangoJSONEncoder
from django.db import connections


class Command(BaseCommand):
    help = 'Gera backup logico do banco em JSONL gzip, sem depender de pg_dump.'

    def add_arguments(self, parser):
        parser.add_argument(
            '--output-dir',
            default='backups/database',
            help='Diretorio onde o backup sera gravado.',
        )
        parser.add_argument(
            '--database',
            default='default',
            help='Alias de banco Django.',
        )
        parser.add_argument(
            '--include-auth',
            action='store_true',
            help='Inclui tabelas auth/admin/sessions. Por padrao elas entram no backup; flag mantida para clareza.',
        )

    def handle(self, *args, **options):
        alias = options['database']
        if alias not in connections:
            raise CommandError(f'Banco desconhecido: {alias}')

        output_dir = Path(options['output_dir'])
        output_dir.mkdir(parents=True, exist_ok=True)
        timestamp = datetime.utcnow().strftime('%Y%m%dT%H%M%SZ')
        output_path = output_dir / f'erp_inoovated_db_{timestamp}.jsonl.gz'

        total_modelos = 0
        total_registros = 0
        tabelas = set(connections[alias].introspection.table_names())
        with gzip.open(output_path, 'wt', encoding='utf-8') as arquivo:
            for model in apps.get_models():
                opts = model._meta
                if opts.proxy or not opts.managed:
                    continue
                if opts.db_table not in tabelas:
                    continue

                qs = model._default_manager.using(alias).all().order_by(opts.pk.name)
                count = qs.count()
                arquivo.write(json.dumps({
                    'type': 'model',
                    'app_label': opts.app_label,
                    'model': opts.model_name,
                    'db_table': opts.db_table,
                    'count': count,
                }, ensure_ascii=True) + '\n')

                for obj in qs.iterator(chunk_size=1000):
                    fields = {}
                    for field in opts.concrete_fields:
                        value = field.value_from_object(obj)
                        fields[field.name] = value
                    arquivo.write(json.dumps({
                        'type': 'row',
                        'model': f'{opts.app_label}.{opts.model_name}',
                        'pk': obj.pk,
                        'fields': fields,
                    }, ensure_ascii=True, cls=DjangoJSONEncoder) + '\n')

                total_modelos += 1
                total_registros += count

        self.stdout.write(self.style.SUCCESS(
            f'Backup do banco criado: {output_path} '
            f'({total_modelos} modelos, {total_registros} registros).'
        ))
