# Copyright 2021 Zuher Elmas
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).

import logging

from odoo import fields, models

logger = logging.getLogger(__name__)


class HiboutikHistory(models.Model):
    _name = "hiboutik.history"

    hiboutik_sync = fields.Boolean(string='Hiboutik Sync')
    hiboutik_sync_date = fields.Datetime(
        string='Date', readonly=True, index=True, default=fields.Datetime.now)
    hiboutik_sync_model = fields.Char("Model Sync", help="Model Sync")
