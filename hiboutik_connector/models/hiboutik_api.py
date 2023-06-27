# Copyright 2021 Zuher Elmas
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).

import logging
import base64
import pytz
import requests
import pandas

from datetime import datetime, time

from odoo import models, tools, _
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


class HiboutikApi(models.AbstractModel):
    _name = 'hiboutik.api'
    _description = 'Hiboutik Api'

    def hb_api(self, url='', method='GET', data=False):
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
            if method == 'PUT':
                auth = requests.put(url, headers=headers, data=data)
            else:
                auth = requests.get(url, headers=headers)

            if auth.status_code == 200:
                response = auth.json()
                return response

        except Exception as err:
            _logger.warning(
                "Failed to connect to Hiboutik API. Please check your settings.",
                exc_info=True)
            raise UserError(_("Connection Hiboutik API failed: %s") %
                            tools.ustr(err))

    def get_category(self):
        base_url = '/categories'

        hb_category = self.hb_api(url=base_url, method='GET')

        for c in hb_category:
            # Check POS product category
            odoo_pos_cat = self.env['pos.category'].search(
                [('hiboutik_id', '=', c.get('category_id'))], limit=1)

            vals = {
                'name': c.get('category_name'),
                'hiboutik_parent_id': c.get('category_id_parent'),
                'hiboutik_sync': True
            }

            if odoo_pos_cat:
                vals['sequence'] = c.get('category_position')
                odoo_pos_cat.write(vals)

            if not odoo_pos_cat:
                vals['hiboutik_id'] = c.get('category_id')
                vals['sequence'] = c.get('category_position')
                self.env['pos.category'].create(vals)

            # Check product category
            vals_product_cat = {
                'name': c.get('category_name'),
                'hiboutik_parent_id': c.get('category_id_parent'),
                'hiboutik_sync': True
            }
            product_cat = self.env['product.category'].search(
                [('hiboutik_id', '=', c.get('category_id'))], limit=1)

            if product_cat:
                product_cat.write(vals_product_cat)

            if not product_cat:
                vals_product_cat['hiboutik_id'] = c.get('category_id')
                self.env['product.category'].create(vals_product_cat)

        # Check if categories need update
        odoo_pos_cat = self.env['pos.category'].search([])

        for oc in odoo_pos_cat:
            if oc.hiboutik_parent_id:
                odoo_pos_cat = self.env['pos.category'].search(
                    [('hiboutik_id', '=', oc.hiboutik_parent_id)], limit=1)
                oc.write({'parent_id': odoo_pos_cat.id})

        all_products_cat = self.env['product.category'].search([])

        for pc in all_products_cat:
            if pc.hiboutik_parent_id:
                all_products_cat = self.env['product.category'].search(
                    [('hiboutik_id', '=', pc.hiboutik_parent_id)], limit=1)
                pc.write({'parent_id': all_products_cat.id})

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
                [('hiboutik_product_id', '=', p.get('product_id')),
                 '|', ('active', '=', True),
                 ('active', '=', False)],
                limit=1)

            pos_category = ''
            product_category = ''
            if p.get('product_category'):
                pos_category_get = self.env['pos.category'].search(
                    [('hiboutik_id', '=', p.get('product_category'))], limit=1)
                if pos_category_get:
                    pos_category = pos_category_get.id

                category_get = self.env['product.category'].search(
                    [('hiboutik_id', '=', p.get('product_category'))], limit=1)
                if category_get:
                    product_category = category_get.id

            taxes = []
            if p.get('product_vat'):
                taxes_get = self.env['account.tax'].search(
                    [('hiboutik_tax_id', '=', p.get('product_vat'))], limit=1)

                if taxes_get:
                    taxes = [(6, 0, taxes_get.ids)]

            product_type = 'consu'
            if p.get('product_stock_management') == 1:
                product_type = 'product'

            product_active = True
            if p.get('product_arch') == 1:
                product_active = False

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
                    'active': product_active,
                    'hiboutik_active': product_active,
                    'type': product_type, 'hb_font_color': p.get(
                        'product_font_color'),
                    'hb_bck_color': p.get('product_bck_btn_color'),
                    'available_in_pos': p.get('product_display')}
                if taxes:
                    vals['taxes_id'] = taxes
                if pos_category:
                    vals['pos_categ_id'] = pos_category
                if pos_category:
                    vals['categ_id'] = product_category

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
                    'active': product_active,
                    'hiboutik_active': product_active,
                    'type': product_type, 'hb_font_color': p.get(
                        'product_font_color'),
                    'hb_bck_color': p.get('product_bck_btn_color'),
                    'available_in_pos': p.get('product_display')}
                if taxes:
                    vals['taxes_id'] = taxes
                if pos_category:
                    vals['pos_categ_id'] = pos_category
                if pos_category:
                    vals['categ_id'] = product_category

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
        latest_hiboutik_order_id = self.env['pos.order'].search(
            [('hiboutik_order_id', '>', 1)], order='hiboutik_order_id desc', limit=1)

        if latest_hiboutik_order_id:
            latest_hiboutik_order_id_date = latest_hiboutik_order_id.date_order

            if config.company_id.hiboutik_start_sync:
                if latest_hiboutik_order_id_date.date() < self.env.company.hiboutik_start_sync.date():
                    raise UserError(
                        _("The last order in database is older than the start date of the synchronization. Please change the start date of the synchronization in the company settings."))
            start_date = latest_hiboutik_order_id_date
        else:
            start_date = config.company_id.hiboutik_start_sync

        end_date = datetime.now().strftime("%Y-%m-%d")
        dates = pandas.date_range(
            start=start_date, end=end_date, freq='D', tz='Europe/Paris')

        for d in dates:
            base_url = (
                '/closed_sales/%s/%s') % (config.hiboutik_store_id, d.strftime("%Y/%m/%d"))

            start_day = pytz.timezone(self.env.user.tz).localize(
                datetime.combine(d, time(0, 0, 0))).astimezone(
                pytz.UTC).replace(tzinfo=None)
            end_day = pytz.timezone(self.env.user.tz).localize(
                datetime.combine(d, time(23, 59, 59))).astimezone(
                pytz.UTC).replace(tzinfo=None)

            get_sales_ids = self.hb_api(url=base_url, method='GET')
            if get_sales_ids:
                session_vals = {
                    'start_at': start_day,
                    'stop_at': end_day,
                    'cash_register_balance_start': 0.0
                }

                config.open_ui()
                session = config.current_session_id
                session.write(session_vals)
                session.set_cashbox_pos(0, None)

                for s in get_sales_ids:
                    sale_exist = self.env['pos.order'].search(
                        [('hiboutik_order_id', '=', s.get('sale_id'))], limit=1)
                    _logger.warning('%s' % s.get('sale_id'))
                    if not sale_exist:
                        customer = False
                        if s.get('customer_id') != 0:
                            customer = self.customer_check(
                                s.get('customer_id'))

                        self.get_closed_sale_details(
                            sale_id=s.get('sale_id'),
                            session=session, customer=customer)

                cash_payment_method = session.payment_method_ids.filtered('is_cash_count')[
                    :1]
                total_cash_payment = sum(session.mapped('order_ids.payment_ids').filtered(
                    lambda payment: payment.payment_method_id.id == cash_payment_method.id).mapped('amount'))
                session.post_closing_cash_details(total_cash_payment)
                session.write({'stop_at': end_day})

                orders = session.order_ids.filtered(
                    lambda o: o.state == 'paid' or o.state == 'invoiced')
                total_sales_amount = sum(orders.mapped('amount_total'))
                total_sales_payment_amount = sum(
                    orders.payment_ids.mapped('amount'))

                amount_to_balance = 0
                balancing_account = False

                if total_sales_amount > total_sales_payment_amount:
                    amount_to_balance -= total_sales_amount - total_sales_payment_amount
                    balancing_account = session.company_id.hiboutik_payment_loss_account_id
                if total_sales_amount < total_sales_payment_amount:
                    amount_to_balance += total_sales_payment_amount - total_sales_amount
                    balancing_account = session.company_id.hiboutik_payment_profit_account_id

                session.sudo().with_context(stop_at=end_day).action_pos_session_closing_control(
                    balancing_account=balancing_account, amount_to_balance=amount_to_balance, bank_payment_method_diffs=None)

                all_related_moves = session.bank_payment_ids.mapped('move_id')
                for mv in all_related_moves:
                    name = ('%s - %s %s' % (session.stop_at.strftime("%d/%m/%Y"),
                            session.name, mv.journal_id.name))
                    sql = "UPDATE account_move_line SET name = %s WHERE id = ANY(%s)"
                    self._cr.execute(sql, (name, mv.line_ids.ids,))

                cash_moves = session.statement_line_ids.mapped('move_id')
                if cash_moves:
                    name = _('Combine Cash POS payments from %s - %s') % (
                        end_day.strftime("%d/%m/%Y"), session.name),
                    sql = "UPDATE account_move SET ref = %s WHERE id = ANY(%s)"
                    self._cr.execute(sql, (name, cash_moves.ids,))

    def get_closed_sale_details(self, sale_id, session, customer):
        sale_detail_url = '/sales/%s' % sale_id
        sale_details_list = self.hb_api(url=sale_detail_url, method='GET')

        for sale_details in sale_details_list:
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

            if sale_details.get('ressource_id') != 0:
                table_id = self.env['restaurant.table'].search(
                    [('hiboutik_id', '=', sale_details.get('ressource_id')),
                     '|', ('active', '=', True),
                     ('active', '=', False)], limit=1)
                vals['table_id'] = table_id.id

            if customer != 0:
                vals['partner_id'] = customer

            sale_lines = self.closed_sales_lines_data(
                sale_details.get('line_items'), session, customer)

            payments = []
            amount_paid = 0.0
            if sale_details.get('payment_details'):
                for pay in sale_details.get('payment_details'):
                    _logger.warning('Payment method %s' %
                                    pay.get('payment_type'))
                    payment = self.env['pos.payment.method'].search(
                        [('hiboutik_equivalent', '=', pay.get('payment_type'))], limit=1)
                    payment_vals = {
                        'hiboutik_payment_detail_id': pay.get(
                            'payment_detail_id'),
                        'payment_method_id': payment.id,
                        'name': '%s - %s - %s' % (closed_date_obj.strftime("%d/%m/%Y"), sale_details.get('unique_sale_id'), payment.name),
                        'amount': float(pay.get('payment_amount')),
                        'payment_date': closed_date_obj}
                    amount_paid += float(pay.get('payment_amount'))
                    payments.append((0, 0, payment_vals))
            else:
                payment = self.env['pos.payment.method'].search(
                    [('hiboutik_equivalent', '=', sale_details.get('payment'))], limit=1)

                if not payment and sale_details.get('balance'):
                    payment = self.env['pos.payment.method'].search(
                        [('hiboutik_equivalent', '=', 'ESP')], limit=1)

                if not payment and customer and sale_details.get('balance'):
                    payment = self.env['pos.payment.method'].search(
                        [('hiboutik_equivalent', '=', 'CRED')], limit=1)

                payment_vals = {
                    'name': '%s - %s - %s' % (closed_date_obj.strftime("%d/%m/%Y"), sale_details.get('unique_sale_id'), payment.name),
                    'payment_method_id': payment.id,
                    'amount': sale_details.get('total'),
                    'payment_date': closed_date_obj
                }
                amount_paid += float(sale_details.get('total'))
                payments.append((0, 0, payment_vals))

            vals['payment_ids'] = payments
            vals['amount_tax'] = float(sale_details.get('sale_total_tax'))
            vals['amount_total'] = float(sale_details.get('total'))
            vals['amount_paid'] = amount_paid
            vals['amount_return'] = 0.0

            vals['lines'] = sale_lines

            result = self.env['pos.order'].create(vals)
            result.action_pos_order_paid()

            try:
                log_vals = {
                    'state': 'succes',
                    'hiboutik_sync_model': 'Closed Sale',
                    'hiboutik_id': sale_details.get('sale_id'),
                    'hiboutik_message': 'Succesfull sync'
                }
                self.env['hiboutik.history'].sudo().create(log_vals)

            except Exception as e:
                log_vals_error = {
                    'state': 'error',
                    'hiboutik_sync_model': 'Closed Sale',
                    'hiboutik_id': sale_details.get('sale_id'),
                    'hiboutik_message': '%s' % e
                }
                self.env['hiboutik.history'].sudo().create(log_vals_error)
                _logger.warning('%s - %s' % (sale_details.get('sale_id'), e))
                pass

    def closed_sales_lines_data(self, lines, session, customer):
        # Get sale lines vals
        sale_lines = []
        for sld in lines:
            if sld.get('product_id') == 0:
                product_id = session.config_id.discount_product_id
                if sld.get('tax_value') == 20:
                    tax_get = self.env['account.tax'].search(
                        [('hiboutik_tax_id', '=', 1)])
                if sld.get('tax_value') == 10:
                    tax_get = self.env['account.tax'].search(
                        [('hiboutik_tax_id', '=', 2)])
                if sld.get('tax_value') == 5.5:
                    tax_get = self.env['account.tax'].search(
                        [('hiboutik_tax_id', '=', 3)])
                if sld.get('tax_value') == 2.1:
                    tax_get = self.env['account.tax'].search(
                        [('hiboutik_tax_id', '=', 4)])
                if sld.get('tax_value') == 0:
                    tax_get = self.env['account.tax'].search(
                        [('hiboutik_tax_id', '=', 5)])
            else:
                product_id = self.env['product.template'].search(
                    [('hiboutik_product_id', '=', sld.get('product_id')), '|', ('active', '=', True), ('active', '=', False)], limit=1)
                tax_get = product_id.taxes_id

            default_fiscal_position = self.env['pos.config'].browse(
                1).default_fiscal_position_id

            fiscal_position = self.env['res.partner'].browse(
                customer).property_account_position_id if customer != 0 else default_fiscal_position
            tax_ids = fiscal_position.map_tax(tax_get)
            tax_values = (
                tax_ids.compute_all(
                    float(sld.get('product_price')),
                    session.currency_id, sld.get('quantity'))
                if tax_ids
                else
                {
                    'total_excluded': float(sld.get('product_price')) * float(sld.get('quantity')),
                    'total_included': float(sld.get('product_price')) * float(sld.get('quantity')),
                }
            )

            lines_vals = {
                'hiboutik_order_line_id': sld.get('line_item_id'),
                'product_id': product_id.id,
                'full_product_name': product_id.name,
                'price_unit': float(sld.get('product_price')),
                'price_subtotal': tax_values['total_excluded'],
                'price_subtotal_incl': tax_values['total_included'],
                'qty': sld.get('quantity'),
                'tax_ids': [(6, 0, tax_get.ids)],
            }
            sale_lines.append((0, 0, lines_vals))
        return sale_lines

    def sychronize_datas(self):
        self.get_category()
        self.get_products()

    def sychronize_sales(self):
        pos_config = self.env['pos.config'].search(
            [('hiboutik_store_id', '>', 0), ('hiboutik_sync', '=', True)])
        self.sychronize_datas()
        for config in pos_config:
            self.get_closed_sales(config)
