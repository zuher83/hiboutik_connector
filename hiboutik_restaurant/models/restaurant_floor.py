# -*- coding: utf-8 -*-

import logging

from odoo import fields, models

logger = logging.getLogger(__name__)


class RestaurantFloor(models.Model):
    _inherit = "restaurant.floor"

    hiboutik_id = fields.Integer(string='Hiboutik floor Id')
    hiboutik_store_id = fields.Integer(string='Hiboutik store Id')
