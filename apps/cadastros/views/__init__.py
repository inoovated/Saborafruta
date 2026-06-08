from .cliente import (
    ClienteListView, ClienteCreateView, ClienteUpdateView,
    ClienteDeleteView, ClienteToggleAtivoView, ClienteInlineEditView, ClienteExportCsvView,
    ClienteExportTodosCsvView, ClienteExportPdfView, consultar_cep_ajax,
)
from .fornecedor import (
    FornecedorListView, FornecedorCreateView, FornecedorUpdateView,
    FornecedorDeleteView, FornecedorToggleAtivoView, FornecedorInlineEditView, FornecedorExportCsvView,
    FornecedorExportTodosCsvView, FornecedorExportPdfView,
)
from .transportadora import (
    TransportadoraListView, TransportadoraCreateView, TransportadoraUpdateView, TransportadoraToggleAtivoView,
    MotoristaListView, MotoristaCreateView, MotoristaUpdateView, MotoristaToggleAtivoView,
    VeiculoListView, VeiculoCreateView, VeiculoUpdateView, VeiculoToggleAtivoView,
    RepresentanteListView, RepresentanteCreateView, RepresentanteUpdateView,
)
from .audit import CadastroLogItemsView, CadastroLogExportCsvView, CadastroLogExportPdfView

__all__ = [
    'ClienteListView', 'ClienteCreateView', 'ClienteUpdateView',
    'ClienteDeleteView', 'ClienteToggleAtivoView', 'ClienteInlineEditView', 'ClienteExportCsvView',
    'ClienteExportTodosCsvView', 'ClienteExportPdfView', 'consultar_cep_ajax',
    'FornecedorListView', 'FornecedorCreateView', 'FornecedorUpdateView',
    'FornecedorDeleteView', 'FornecedorToggleAtivoView', 'FornecedorInlineEditView', 'FornecedorExportCsvView',
    'FornecedorExportTodosCsvView', 'FornecedorExportPdfView',
    'TransportadoraListView', 'TransportadoraCreateView', 'TransportadoraUpdateView', 'TransportadoraToggleAtivoView',
    'MotoristaListView', 'MotoristaCreateView', 'MotoristaUpdateView', 'MotoristaToggleAtivoView',
    'VeiculoListView', 'VeiculoCreateView', 'VeiculoUpdateView', 'VeiculoToggleAtivoView',
    'RepresentanteListView', 'RepresentanteCreateView', 'RepresentanteUpdateView',
    'CadastroLogItemsView', 'CadastroLogExportCsvView', 'CadastroLogExportPdfView',
]
