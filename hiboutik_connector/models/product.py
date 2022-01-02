# Copyright 2021 Zuher Elmas
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).

import logging

from odoo import fields, models

logger = logging.getLogger(__name__)


class ProductTemplate(models.Model):
    _inherit = "product.template"

    hiboutik_product_id = fields.Integer(string='Hiboutik product Id')
    hiboutik_product_category_id = fields.Integer(string='Hiboutik product Category Id')
    hiboutik_product_supplier_reference = fields.Char(string='Hiboutik Supplier Ref')
    hiboutik_sync = fields.Boolean(string='Hiboutik Sync')
    hiboutik_active = fields.Boolean(string='Hiboutik product active')
    hb_font_color = fields.Char(
        "Font Color Code", default="#333333", help="Use Hex Code only Ex:-#FFFFFF"
    )
    hb_bck_color = fields.Char(
        "Background Color Code", default="#FFFFFF", help="Use Hex Code only Ex:-#FFFFFF"
    )
