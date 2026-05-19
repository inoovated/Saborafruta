from __future__ import annotations

import tarfile
from datetime import datetime
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError


class Command(BaseCommand):
    help = 'Compacta MEDIA_ROOT em um arquivo tar.gz para contingencia.'

    def add_arguments(self, parser):
        parser.add_argument(
            '--output-dir',
            default='backups/media',
            help='Diretorio onde o backup sera gravado.',
        )
        parser.add_argument(
            '--media-root',
            default='',
            help='Sobrescreve o MEDIA_ROOT usado no backup.',
        )

    def handle(self, *args, **options):
        media_root = Path(options['media_root'] or settings.MEDIA_ROOT).resolve()
        if not media_root.exists() or not media_root.is_dir():
            raise CommandError(f'MEDIA_ROOT inexistente ou invalido: {media_root}')

        output_dir = Path(options['output_dir'])
        output_dir.mkdir(parents=True, exist_ok=True)
        timestamp = datetime.utcnow().strftime('%Y%m%dT%H%M%SZ')
        output_path = output_dir / f'erp_inoovated_media_{timestamp}.tar.gz'

        total_arquivos = 0
        total_bytes = 0
        with tarfile.open(output_path, 'w:gz') as tar:
            for path in media_root.rglob('*'):
                if not path.is_file():
                    continue
                arcname = Path('media') / path.relative_to(media_root)
                tar.add(path, arcname=str(arcname))
                total_arquivos += 1
                total_bytes += path.stat().st_size

        self.stdout.write(self.style.SUCCESS(
            f'Backup de media criado: {output_path} '
            f'({total_arquivos} arquivos, {total_bytes} bytes).'
        ))
