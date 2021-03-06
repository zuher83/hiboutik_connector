# Copyright 2021 Zuher Elmas
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).

import logging
import base64

import hashlib
import urllib
import keyword
import time
import json

import requests
from requests import status_codes

try:
    from urllib import urlencode
except ImportError: # pragma: no cover
    # Python 3
    from urllib.parse import urlencode


from odoo import fields, models
from odoo import tools, api, _
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)

class HiboutikApi(models.AbstractModel):
    _name = 'hiboutik.api'
    _description = 'Hiboutik Api'

    def hb_api(self, url='', method='GET'):
        # self.ensure_one()

        _hb_endpoint = '%s' % self.env['res.company'].browse(self.env.company.id).hiboutik_api_url
        _username = self.env['res.company'].browse(self.env.company.id).hiboutik_username
        _key = self.env['res.company'].browse(self.env.company.id).hiboutik_apikey

        if _username and _key:
            login = "{}:{}".format(_username, _key)
            login = base64.b64encode(login.encode("UTF-8")).decode("UTF-8")
            headers = {
                "Content-Type": "application/x-www-form-urlencoded",
                "Accept": "application/json",
                "Authorization": "Basic %s" % login,
            }

        try:
            url = '%s%s' % (_hb_endpoint,url)
            auth = requests.get(url, headers=headers)

            if auth.status_code == 200:
                response = auth.json()
                return response

        except Exception as err:
            _logger.info(
                "Failed to connect to Hiboutik API. Please check your settings.", exc_info=True)
            raise UserError(_("Connection Hiboutik API failed: %s") %
                            tools.ustr(err))

    def get_category(self):
        base_url = '/categories'

        hb_category = self.hb_api(url=base_url, method='GET')

        for c in hb_category:

            odoo_cat = self.env['pos.category'].search([('hiboutik_id','=', c.get('category_id'))], limit=1)

            if not odoo_cat:
                vals = {
                    'hiboutik_id': c.get('category_id'),
                    'name': c.get('category_name'),
                    'sequence': c.get('category_position'),
                    'hiboutik_parent_id': c.get('category_id_parent'),
                    'hiboutik_sync': True
                }
                self.env['pos.category'].create(vals)

            if odoo_cat:
                vals = {
                    'name': c.get('category_name'),
                    'sequence': c.get('category_position'),
                    'hiboutik_parent_id': c.get('category_id_parent'),
                    'hiboutik_sync': True
                }
                odoo_cat.write(vals)

        #Check update
        odoo_cat = self.env['pos.category'].search([])

        for oc in odoo_cat:
            if oc.hiboutik_parent_id:
                odoo_cat = self.env['pos.category'].search([('hiboutik_id','=', oc.hiboutik_parent_id)], limit=1)
                oc.write({'parent_id': odoo_cat.id})

    def get_products(self):
        base_url = '/products'

        hb_products = self.hb_api(url=base_url, method='GET')

        for p in hb_products:
            odoo_product = self.env['product.template'].search([('hiboutik_product_id','=', p.get('product_id'))], limit=1)

            category = ''
            if p.get('product_category'):
                category_get = self.env['pos.category'].search([('hiboutik_id','=', p.get('product_category'))], limit=1)
                if category_get:
                    category = category_get.id

            taxes = []
            if p.get('product_vat'):
                taxes_get = self.env['account.tax'].search([('hiboutik_tax_id','=', p.get('product_vat'))], limit=1)

                if taxes_get:
                    taxes = [(6, 0, taxes_get.ids)]


            product_type = 'consu'
            if p.get('product_stock_management') == 1:
                product_type = 'product'

            if not odoo_product:
                vals = {
                    'hiboutik_product_id': p.get('product_id'),
                    'hiboutik_product_supplier_reference': p.get('product_supplier_reference'),
                    'hiboutik_sync': True,
                    'hiboutik_product_category_id': p.get('product_category'),
                    'name': p.get('product_model'),
                    'list_price': p.get('product_price'),
                    'sequence': p.get('product_order'),
                    'barcode': p.get('product_barcode'),
                    'active': p.get('product_display'),
                    'hiboutik_active': p.get('product_display'),
                    'type': product_type,
                    'hb_font_color': p.get('product_font_color'),
                    'hb_bck_color': p.get('product_bck_btn_color'),
                    'available_in_pos': True
                }
                if taxes:
                    vals['taxes_id'] = taxes
                if category:
                    vals['pos_categ_id'] = category

                self.env['product.template'].create(vals)

            if odoo_product:
                vals = {
                    'name': p.get('product_model'),
                    'hiboutik_product_supplier_reference': p.get('product_supplier_reference'),
                    'hiboutik_sync': True,
                    'list_price': p.get('product_price'),
                    'sequence': p.get('product_order'),
                    'barcode': p.get('product_barcode'),
                    'active': p.get('product_display'),
                    'hiboutik_active': p.get('product_display'),
                    'type': product_type,
                    'hb_font_color': p.get('product_font_color'),
                    'hb_bck_color': p.get('product_bck_btn_color'),
                    'available_in_pos': True
                }
                if taxes:
                    vals['taxes_id'] = taxes
                if category:
                    vals['pos_categ_id'] = category

                odoo_product.write(vals)

    def sychronize_datas(self):
        self.get_category()
        self.get_products()
