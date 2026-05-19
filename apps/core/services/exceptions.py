"""Exceções de domínio do sistema."""


class DomainError(Exception):
    """Erro de regra de negócio (mensagem amigável para o usuário)."""


class PermissaoNegadaError(DomainError):
    """Usuário não tem permissão para a operação."""


class EstoqueInsuficienteError(DomainError):
    """Estoque disponível é menor que a quantidade requerida."""


class LoteVencidoError(DomainError):
    """Tentativa de operar com lote vencido."""


class PeriodoBloqueadoError(DomainError):
    """Tentativa de lançamento em período fechado/travado."""


class DadosInvalidosError(DomainError):
    """Dados de entrada inválidos."""
