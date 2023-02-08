# Copyright 2021 Zuher Elmas
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).

import logging

from odoo import fields, models, _

_logger = logging.getLogger(__name__)


class AccountMove(models.Model):
    _inherit = 'account.move'

    def _post(self, soft=True):
        if self._context.get('stop_at'):
            self.write({'date': self._context.get('stop_at')})
        return super(AccountMove, self)._post(soft=soft)
