# -*- coding: utf-8 -*-

import logging

from odoo import fields, models

logger = logging.getLogger(__name__)


class RestaurantTable(models.Model):
    _inherit = "restaurant.table"

    hiboutik_id = fields.Integer(string='Hiboutik table Id')
    hiboutik_room_id = fields.Integer(string='Hiboutik room Id')
