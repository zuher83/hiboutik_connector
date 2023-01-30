# Copyright 2021 Zuher Elmas
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).

import logging

from odoo import fields, models

_logger = logging.getLogger(__name__)


class ProductTemplate(models.Model):
    _inherit = "product.template"

    hiboutik_product_id = fields.Integer(string='Hiboutik product Id')
    hiboutik_product_category_id = fields.Integer(
        string='Hiboutik product Category Id')
    hiboutik_product_supplier_reference = fields.Char(
        string='Hiboutik Supplier Ref')
    hiboutik_sync = fields.Boolean(string='Hiboutik Sync')
    hiboutik_active = fields.Boolean(string='Hiboutik product active')
    hb_font_color = fields.Char(
        "Font Color Code", default="#333333",
        help="Use Hex Code only Ex:-#FFFFFF")
    hb_bck_color = fields.Char(
        "Background Color Code", default="#FFFFFF",
        help="Use Hex Code only Ex:-#FFFFFF")

    def write(self, vals):
        res = super().write(vals)

        if vals.get('property_account_income_id') or vals.get(
                'property_account_expense_id'):
            base_url = '/product/%s' % self.hiboutik_product_id
            oo_account_get = self.env['account.account'].browse(
                vals.get('property_account_income_id')).code

            accounting_account = {
                'product_attribute': 'accounting_account',
                'new_value': oo_account_get}

            # self.env['hiboutik.api'].hb_api(
            #     url=base_url, method='PUT', data=accounting_account)
            _logger.warning('Condition ok %s', vals)

        return res


class ProductCategory(models.Model):
    _inherit = "product.category"

    hiboutik_id = fields.Integer(string='Hiboutik Category Id')
    hiboutik_parent_id = fields.Integer(string='Hiboutik Parent Category Id')
    hiboutik_sync = fields.Boolean(string='Hiboutik Sync')
