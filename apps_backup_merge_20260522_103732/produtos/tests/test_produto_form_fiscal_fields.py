from django.test import TestCase

from apps.produtos.forms import ProdutoForm


class ProdutoFormFiscalFieldsTests(TestCase):
    def test_formulario_expõe_campos_fiscais_complementares(self):
        form = ProdutoForm()

        expected_fields = {
            'codigo_beneficio_fiscal_icms',
            'modalidade_bc_icms',
            'aliquota_icms',
            'reducao_bc_icms',
            'aliquota_fcp',
            'modalidade_bc_icms_st',
            'mva_icms_st',
            'reducao_bc_icms_st',
            'aliquota_icms_st',
            'aliquota_fcp_st',
            'aliquota_pis',
            'aliquota_cofins',
            'natureza_receita_pis_cofins',
            'ex_tipi',
            'cst_cbs',
            'classificacao_tributaria_cbs',
            'aliquota_cbs',
            'reducao_cbs',
            'cst_ibs',
            'classificacao_tributaria_ibs',
            'aliquota_ibs_uf',
            'aliquota_ibs_municipal',
            'reducao_ibs',
            'cst_is',
            'classificacao_tributaria_is',
            'aliquota_is',
        }

        self.assertTrue(expected_fields.issubset(form.fields.keys()))
