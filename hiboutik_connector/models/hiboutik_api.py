# Copyright 2021 Zuher Elmas
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).

import logging
import base64

import pandas
# import urllib
# import keyword
# import time
# import json

from datetime import datetime, time

import requests
# from requests import status_codes

# try:
#     from urllib import urlencode
# except ImportError:  # pragma: no cover
#     # Python 3
#     from urllib.parse import urlencode

from odoo import fields, models, tools, api, _
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


class HiboutikApi(models.AbstractModel):
    _name = 'hiboutik.api'
    _description = 'Hiboutik Api'

    def hb_api(self, url='', method='GET'):
        _hb_endpoint = '%s' % self.env['res.company'].browse(
            self.env.company.id).hiboutik_api_url
        _username = self.env['res.company'].browse(
            self.env.company.id).hiboutik_username
        _key = self.env['res.company'].browse(
            self.env.company.id).hiboutik_apikey

        if _username and _key:
            login = "{}:{}".format(_username, _key)
            login = base64.b64encode(login.encode("UTF-8")).decode("UTF-8")
            headers = {
                "Content-Type": "application/x-www-form-urlencoded",
                "Accept": "application/json",
                "Authorization": "Basic %s" % login,
            }

        try:
            url = '%s%s' % (_hb_endpoint, url)
            auth = requests.get(url, headers=headers)

            if auth.status_code == 200:
                response = auth.json()
                return response

        except Exception as err:
            _logger.info(
                "Failed to connect to Hiboutik API. Please check your settings.",
                exc_info=True)
            raise UserError(_("Connection Hiboutik API failed: %s") %
                            tools.ustr(err))

    def get_category(self):
        base_url = '/categories'

        hb_category = self.hb_api(url=base_url, method='GET')

        for c in hb_category:

            odoo_cat = self.env['pos.category'].search(
                [('hiboutik_id', '=', c.get('category_id'))], limit=1)

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

        # Check if need update
        odoo_cat = self.env['pos.category'].search([])

        for oc in odoo_cat:
            if oc.hiboutik_parent_id:
                odoo_cat = self.env['pos.category'].search(
                    [('hiboutik_id', '=', oc.hiboutik_parent_id)], limit=1)
                oc.write({'parent_id': odoo_cat.id})

    def get_products(self):
        pagination = 1

        # Check all products with pagination and stop when return empty
        while pagination != 0:
            base_url = '/products/?p=%s' % pagination
            hb_products = self.hb_api(url=base_url, method='GET')

            # if Hiboutik return datas
            if hb_products:
                pagination += 1
                self.get_products_details(hb_products)
            else:
                pagination = 0

    def get_products_details(self, hb_products):

        for p in hb_products:
            odoo_product = self.env['product.template'].search(
                [('hiboutik_product_id', '=', p.get('product_id'))], limit=1)

            category = ''
            if p.get('product_category'):
                category_get = self.env['pos.category'].search(
                    [('hiboutik_id', '=', p.get('product_category'))], limit=1)
                if category_get:
                    category = category_get.id

            taxes = []
            if p.get('product_vat'):
                taxes_get = self.env['account.tax'].search(
                    [('hiboutik_tax_id', '=', p.get('product_vat'))], limit=1)

                if taxes_get:
                    taxes = [(6, 0, taxes_get.ids)]

            product_type = 'consu'
            if p.get('product_stock_management') == 1:
                product_type = 'product'

            if not odoo_product:
                vals = {
                    'hiboutik_product_id': p.get('product_id'),
                    'hiboutik_product_supplier_reference': p.get(
                        'product_supplier_reference'),
                    'hiboutik_sync': True,
                    'hiboutik_product_category_id': p.get('product_category'),
                    'name': p.get('product_model'),
                    'list_price': p.get('product_price'),
                    'sequence': p.get('product_order'),
                    'barcode': p.get('product_barcode'),
                    'active': p.get('product_display'),
                    'hiboutik_active': p.get('product_display'),
                    'type': product_type, 'hb_font_color': p.get(
                        'product_font_color'),
                    'hb_bck_color': p.get('product_bck_btn_color'),
                    'available_in_pos': True}
                if taxes:
                    vals['taxes_id'] = taxes
                if category:
                    vals['pos_categ_id'] = category

                self.env['product.template'].create(vals)

            if odoo_product:
                vals = {
                    'name': p.get('product_model'),
                    'hiboutik_product_supplier_reference': p.get(
                        'product_supplier_reference'),
                    'hiboutik_sync': True,
                    'list_price': p.get('product_price'),
                    'sequence': p.get('product_order'),
                    'barcode': p.get('product_barcode'),
                    'active': p.get('product_display'),
                    'hiboutik_active': p.get('product_display'),
                    'type': product_type, 'hb_font_color': p.get(
                        'product_font_color'),
                    'hb_bck_color': p.get('product_bck_btn_color'),
                    'available_in_pos': True}
                if taxes:
                    vals['taxes_id'] = taxes
                if category:
                    vals['pos_categ_id'] = category

                odoo_product.write(vals)

    def customer_check(self, customer_id):
        result = False
        src_partner = self.env['res.partner'].search(
            [('hiboutik_customer_id', '=', customer_id)], limit=1)

        if src_partner:
            result = src_partner.id
        else:
            base_url = '/customer/%s' % customer_id
            customer = self.hb_api(url=base_url, method='GET')[0]
            _logger.warning('%s' % customer)
            _logger.warning('Test %s' % customer.get('last_name'))
            if customer:
                vals = {
                    'lastname': customer.get('last_name'),
                    'firstname': customer.get('first_name'),
                    'name': customer.get('company'),
                    'phone': customer.get('phone'),
                    'email': customer.get('email'),
                    'vat': customer.get('vat'),
                    'hiboutik_customer_id': customer.get('customers_id')
                }
                if customer.get('addresses'):
                    for ad in customer.get('addresses'):
                        vals['street'] = ad.get('address')
                        vals['zip'] = ad.get('zip_code')
                        vals['city'] = ad.get('city')

                cr_partner = self.env['res.partner'].create(vals)
                result = cr_partner.id

        return result

    def get_closed_sales(self, config):
        start_date = ('%s') % self.env.company.hiboutik_start_sync
        dates = pandas.date_range(
            start='2022-06-04', end='2022-06-06', freq='D', tz='UTC')

        for d in dates:
            base_url = ('/closed_sales/1/%s') % d.strftime("%Y/%m/%d")
            # base_url = ('/z/customers/1/%s') % d.strftime("%Y/%m/%d")
            start_day = datetime.combine(d, time.min)
            end_day = datetime.combine(d, time.max)

            # _logger.warning(d.time.min)

            get_sales_ids = self.hb_api(url=base_url, method='GET')

            if get_sales_ids:
                session_vals = {
                    'start_at': start_day,
                    'stop_at': end_day,
                    'state': 'opened',
                    'config_id': 1
                }

                session = self.env['pos.session'].sudo().create(session_vals)

                for s in get_sales_ids:
                    sale_exist = self.env['pos.order'].search(
                        [('hiboutik_order_id', '=', s.get('sale_id'))], limit=1)

                    if not sale_exist:
                        # hb_sales_ids.append(s.get('sale_id'))
                        customer = False
                        if s.get('customer_id') != 0:
                            customer = self.customer_check(
                                s.get('customer_id'))

                        self.get_closed_sale_details(
                            sale_id=s.get('sale_id'),
                            session=session, customer=customer)

                session.sudo().action_pos_session_validate()

    def get_closed_sale_details(self, sale_id, session, customer):
        sale_detail_url = '/sales/%s' % sale_id
        sale_details_list = self.hb_api(url=sale_detail_url, method='GET')

        for sale_details in sale_details_list:
            # _logger.warn('%s' % sale_details)
            closed_date_str = ('%s/%s/%s %s:%s:%s') % (
                sale_details.get('completed_at_date_dd'),
                sale_details.get('completed_at_date_mm'),
                sale_details.get('completed_at_date_yyyy'),
                sale_details.get('completed_at_date_hh'),
                sale_details.get('completed_at_date_min'),
                sale_details.get('completed_at_date_ss'))

            closed_date_obj = datetime.strptime(
                closed_date_str, '%d/%m/%Y %H:%M:%S')

            vals = {
                'hiboutik_order_id': sale_details.get('sale_id'),
                'date_order': sale_details.get('created_at'),
                'pos_reference': sale_details.get('unique_sale_id'),
                'customer_count': sale_details.get('guests_number'),
                'session_id': session.id
            }

            if customer != 0:
                vals['partner_id'] = customer

            sale_lines = []
            for sld in sale_details.get('line_items'):
                product_id = self.env['product.template'].search(
                    [('hiboutik_product_id', '=', sld.get('product_id'))], limit=1)
                default_fiscal_position = self.env['pos.config'].browse(
                    1).default_fiscal_position_id
                # default_fiscal_position = self.config.default_fiscal_position_id
                # _logger.warn('%s' % sld.get('product_price'))

                fiscal_position = self.env['res.partner'].browse(
                    customer).property_account_position_id if customer != 0 else default_fiscal_position
                tax_ids = fiscal_position.map_tax(product_id.taxes_id)
                tax_values = (
                    tax_ids.compute_all(
                        float(sld.get('product_price')),
                        session.currency_id, sld.get('quantity'))
                    if tax_ids
                    else
                    {'total_excluded': float(sld.get('product_price')) *
                     float(sld.get('quantity')),
                     'total_included': float(sld.get('product_price')) *
                     float(sld.get('quantity')), })

                lines_vals = {
                    'hiboutik_order_line_id': sld.get('line_item_id'),
                    'product_id': product_id.id,
                    'full_product_name': product_id.name,
                    'price_unit': sld.get('product_price'),
                    'price_subtotal': tax_values['total_excluded'],
                    'price_subtotal_incl': tax_values['total_included'],
                    'qty': sld.get('quantity'),
                    'tax_ids': [(6, 0, product_id.taxes_id.ids)],
                }
                sale_lines.append((0, 0, lines_vals))
                # _logger.warn('%s' % lines_vals)

            vals['lines'] = sale_lines

            payments = []
            amount_paid = 0
            if sale_details.get('payment_details'):
                for pay in sale_details.get('payment_details'):
                    payment = self.env['pos.payment.method'].search(
                        [('hiboutik_equivalent', '=', pay.get('payment_type'))], limit=1)
                    payment_vals = {
                        'hiboutik_payment_detail_id': pay.get(
                            'payment_detail_id'),
                        'payment_method_id': payment.id,
                        'amount': float(pay.get(
                            'payment_amount')),
                        'payment_date': closed_date_obj}
                    amount_paid += float(pay.get('payment_amount'))
                    payments.append((0, 0, payment_vals))
            else:
                payment = self.env['pos.payment.method'].search(
                    [('hiboutik_equivalent', '=', sale_details.get('payment'))], limit=1)
                payment_vals = {
                    # 'hiboutik_payment_detail_id': pay.get('payment'),
                    'payment_method_id': payment.id,
                    'amount': sale_details.get('total'),
                    'payment_date': closed_date_obj
                }
                amount_paid = sale_details.get('total')
                payments.append((0, 0, payment_vals))

            vals['payment_ids'] = payments
            vals['amount_tax'] = sale_details.get('sale_total_tax')
            vals['amount_total'] = sale_details.get('total')
            vals['amount_paid'] = amount_paid
            vals['amount_return'] = 0

            # result = self.env['pos.order'].create(vals)
            # result.action_pos_order_paid()

    def sychronize_datas(self):
        self.get_category()
        self.get_products()

    def sychronize_sales(self):
        pos_config = self.env['pos.config'].search(
            [('hiboutik_store_id', '>', 0), ('hiboutik_sync', '=', True)])
        for config in pos_config:
            self.get_closed_sales(config)
