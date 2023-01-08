# Copyright 2021 Zuher Elmas
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).

from odoo import models


class HiboutikApi(models.AbstractModel):
    _inherit = 'hiboutik.api'

    def get_rooms(self):
        base_url = '/rooms'

        hb_rooms = self.hb_api(url=base_url, method='GET')

        for c in hb_rooms:

            odoo_room_id = self.env['restaurant.floor'].search(
                [('hiboutik_id', '=', c.get('room_id'))], limit=1)

            odoo_pos_config_id = self.env['pos.config'].search(
                [('hiboutik_id', '=', c.get('store_id'))], limit=1)

            if not odoo_room_id:
                vals = {
                    'hiboutik_id': c.get('room_id'),
                    'name': c.get('room_name'),
                    'sequence': c.get('room_position'),
                    'hiboutik_store_id': c.get('store_id'),
                    'active': c.get('room_enabled'),
                    'pos_config_id': odoo_pos_config_id.id
                }
                self.env['restaurant.floor'].create(vals)

            if odoo_room_id:
                vals = {
                    'name': c.get('room_name'),
                    'sequence': c.get('room_position'),
                    'hiboutik_store_id': c.get('store_id'),
                    'pos_config_id': odoo_pos_config_id.id,
                    'active': c.get('room_enabled'),
                }
                odoo_room_id.write(vals)

def get_ressources(self):
        base_url = '/ressources'

        hb_ressources = self.hb_api(url=base_url, method='GET')

        for c in hb_ressources:

            odoo_ressource_id = self.env['restaurant.table'].search(
                [('hiboutik_id', '=', c.get('ressource_id'))], limit=1)

            odoo_pos_config_id = self.env['pos.config'].search(
                [('hiboutik_id', '=', c.get('store_id'))], limit=1)

            if not odoo_ressource_id:
                vals = {
                    'hiboutik_id': c.get('room_id'),
                    'name': c.get('room_name'),
                    'sequence': c.get('room_position'),
                    'hiboutik_store_id': c.get('store_id'),
                    'active': c.get('room_enabled'),
                    'pos_config_id': odoo_pos_config_id.id
                }
                self.env['restaurant.floor'].create(vals)

            if odoo_ressource_id:
                vals = {
                    'name': c.get('room_name'),
                    'sequence': c.get('room_position'),
                    'hiboutik_store_id': c.get('store_id'),
                    'pos_config_id': odoo_pos_config_id.id,
                    'active': c.get('room_enabled'),
                }
                odoo_ressource_id.write(vals)
