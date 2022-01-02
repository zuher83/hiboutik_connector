# Copyright 2021 Zuher Elmas
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).

import logging

from odoo import fields, models

logger = logging.getLogger(__name__)

class AccountTax(models.Model):
    _inherit = 'account.tax'

    hiboutik_tax_id = fields.Integer(string='Hiboutik tax Id')
