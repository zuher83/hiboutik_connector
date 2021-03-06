# Copyright 2021 Zuher Elmas
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).

import logging

from odoo import fields, models

_logger = logging.getLogger(__name__)


class ResCompany(models.Model):
    _inherit = "res.company"

    hiboutik_username = fields.Char(
        string="Username Api",
        help="Indiquate your username.",
    )
    hiboutik_apikey = fields.Char(
        string="Api Key",
        help="Indiquate Api Key",
    )
    hiboutik_api_url = fields.Char(
        string="Hiboutik Url",
        help="Indiquate Hiboutik Url",
    )

    def sychronize_datas(self):
        response = self.env['hiboutik.api'].sycronise_datas()
        return response
