# Copyright 2021 Zuher Elmas
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).
from PIL import ImageColor
from odoo import models
import logging

_logger = logging.getLogger(__name__)


class HiboutikApi(models.AbstractModel):
    _inherit = 'hiboutik.api'

    def get_rooms(self):
        base_url = '/rooms'

        hb_rooms = self.hb_api(url=base_url, method='GET')

        for c in hb_rooms:

            odoo_room_id = self.env['restaurant.floor'].search(
                [('hiboutik_id', '=', c.get('room_id'))], limit=1)

            odoo_pos_config_id = self.env['pos.config'].search(
                [('hiboutik_store_id', '=', c.get('store_id'))], limit=1)

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
                [('hiboutik_id', '=', c.get('ressource_id')),
                 '|', ('active', '=', True),
                 ('active', '=', False)],
                limit=1)

            odoo_floor_id = self.env['restaurant.floor'].search(
                [('hiboutik_id', '=', c.get('room_id')), '|', ('active', '=', True),
                 ('active', '=', False)], limit=1)

            # color_hex_splited = '%s' % c.get('color')
            # _logger.warning('%s' % color_hex_splited)
            # color_rgb = ImageColor.getcolor(color_hex_splited, "RGB")
            # _logger.warning('%s' % color_rgb)

            # color = ('rgb%s' % color_rgb)

            if not odoo_ressource_id:
                vals = {
                    'hiboutik_id': c.get('ressource_id'),
                    'name': c.get('ressource_name'),
                    # 'sequence': c.get('room_position'),
                    'hiboutik_room_id': c.get('room_id'),
                    'active': c.get('ressource_enabled'),
                    'floor_id': odoo_floor_id.id,
                    'height': float(c.get('height')),
                    'width': float(c.get('width')),
                    'position_h': float(c.get('left_position')),
                    'position_v': float(c.get('top_position')),
                    # 'color': color,

                }
                self.env['restaurant.table'].create(vals)

            if odoo_ressource_id:
                vals = {
                    'name': c.get('ressource_name'),
                    # 'sequence': c.get('room_position'),
                    'hiboutik_room_id': c.get('room_id'),
                    'active': c.get('ressource_enabled'),
                    'floor_id': odoo_floor_id.id,
                    'height': float(c.get('height')),
                    'width': float(c.get('width')),
                    'position_h': float(c.get('left_position')),
                    'position_v': float(c.get('top_position')),
                    # 'color': color,
                }
                odoo_ressource_id.write(vals)

    def sychronize_datas(self):
        res = super(HiboutikApi, self).sychronize_datas()
        self.get_rooms()
        self.get_ressources()
        return res
