# Copyright 2021 Zuher Elmas
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).

import logging

from odoo import fields, models

logger = logging.getLogger(__name__)


class PosCategory(models.Model):
    _inherit = 'pos.category'

    hiboutik_id = fields.Integer(string="Hiboutik category ID", )
    hiboutik_parent_id = fields.Integer(string="Hiboutik parent category ID", )
    hiboutik_sync = fields.Boolean(string='Sync With Hiboutik')


class PosPaymentMode(models.Model):
    _inherit = 'pos.payment.method'

    hiboutik_equivalent = fields.Char(
        string="Hiboutik payment type",
        help="Indiquate payment equivalent in Hiboutik.",
    )


class PosConfig(models.Model):
    _inherit = 'pos.config'

    hiboutik_sync = fields.Boolean(string='Hiboutik_sync')
    hiboutik_store_id = fields.Integer(string='Hiboutik store Id')


class PosOrder(models.Model):
    _inherit = 'pos.order'

    hiboutik_order_id = fields.Integer(string='Hiboutik order Id')
    # hiboutik_unique_sale_id = fields.Char(string='Hiboutik Unique Sale Id')


class PosOrderLine(models.Model):
    _inherit = 'pos.order.line'

    hiboutik_order_line_id = fields.Integer(string='Hiboutik order line Id')


class PosPayment(models.Model):
    _inherit = 'pos.payment'

    hiboutik_payment_detail_id = fields.Integer(
        string='Hiboutik payment detail Id')


class PosSession(models.Model):
    _inherit = 'pos.session'

    def _post_statement_difference(self, amount):
        return {}
