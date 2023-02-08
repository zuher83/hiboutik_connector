# Copyright 2021 Zuher Elmas
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).

import logging

from odoo import fields, models, api, _
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


class PosCategory(models.Model):
    _inherit = 'pos.category'

    hiboutik_id = fields.Integer(string="Hiboutik category ID", )
    hiboutik_parent_id = fields.Integer(string="Hiboutik parent category ID", )
    hiboutik_sync = fields.Boolean(string='Sync With Hiboutik')


class PosPaymentMode(models.Model):
    _inherit = 'pos.payment.method'

    hiboutik_equivalent = fields.Char(
        string="Hiboutik payment type",
        help="Indiquate payment equivalent in Hiboutik.",
    )


class PosConfig(models.Model):
    _inherit = 'pos.config'

    hiboutik_sync = fields.Boolean(string='Hiboutik_sync')
    hiboutik_store_id = fields.Integer(string='Hiboutik store Id')


class PosOrder(models.Model):
    _inherit = 'pos.order'

    hiboutik_order_id = fields.Integer(string='Hiboutik order Id')
    # hiboutik_unique_sale_id = fields.Char(string='Hiboutik Unique Sale Id')


class PosOrderLine(models.Model):
    _inherit = 'pos.order.line'

    hiboutik_order_line_id = fields.Integer(string='Hiboutik order line Id')


class PosPayment(models.Model):
    _inherit = 'pos.payment'

    hiboutik_payment_detail_id = fields.Integer(
        string='Hiboutik payment detail Id')


class PosSession(models.Model):
    _inherit = 'pos.session'

    # def _post_statement_difference(self, amount):
    #     return {}
    # @api.depends('payment_method_ids', 'order_ids', 'cash_register_balance_start')
    # def _compute_cash_balance(self):
    #     result = super(PosSession, self)._compute_cash_balance()
    #     for session in self:
    #         # session.cash_register_balance_end = session.cash_register_total_entry_encoding
    #         session.cash_register_balance_end = 0.0
    #         cash_payment_method = session.payment_method_ids.filtered('is_cash_count')[
    #             :1]
    #         # session.cash_register_total_entry_encoding = sum(session.mapped('order_ids.payment_ids').filtered(
    #             # lambda payment: payment.payment_method_id.id == cash_payment_method.id).mapped('amount'))

    #     return result

    @api.depends('payment_method_ids', 'order_ids', 'cash_register_balance_start')
    def _compute_cash_balance(self):
        for session in self:
            cash_payment_method = session.payment_method_ids.filtered('is_cash_count')[
                :1]
            if cash_payment_method:
                total_cash_payment = 0.0
                last_session = session.search(
                    [('config_id', '=', session.config_id.id), ('id', '!=', session.id)], limit=1)
                result = self.env['pos.payment']._read_group([('session_id', '=', session.id), (
                    'payment_method_id', '=', cash_payment_method.id)], ['amount'], ['session_id'])
                if result:
                    total_cash_payment = result[0]['amount']
                session.cash_register_total_entry_encoding = sum(session.statement_line_ids.mapped('amount')) + (
                    0.0 if session.state == 'closed' else total_cash_payment
                )
                session.cash_register_balance_end = session.cash_register_total_entry_encoding
                session.cash_register_difference = session.cash_register_balance_end_real - \
                    session.cash_register_balance_end
            else:
                session.cash_register_total_entry_encoding = 0.0
                session.cash_register_balance_end = 0.0
                session.cash_register_difference = 0.0

    def action_pos_session_closing_control(self, balancing_account=False, amount_to_balance=0, bank_payment_method_diffs=None):
        result = super(PosSession, self).action_pos_session_closing_control(balancing_account=balancing_account,
                                                                            amount_to_balance=amount_to_balance, bank_payment_method_diffs=bank_payment_method_diffs)
        # for session in self:
        self.write({'stop_at': self._context.get('stop_at')})
        return result

    def _create_account_move(self, balancing_account=False, amount_to_balance=0, bank_payment_method_diffs=None):
        """ Create account.move and account.move.line records for this session.

        Side-effects include:
            - setting self.move_id to the created account.move record
            - reconciling cash receivable lines, invoice receivable lines and stock output lines
        """
        account_move = self.env['account.move'].create({
            'journal_id': self.config_id.journal_id.id,
            'date': self._context.get('stop_at'),
            'ref': '%s - %s' % (self.name, self._context.get('stop_at').date()),
        })
        self.write({'move_id': account_move.id})

        data = {'bank_payment_method_diffs': bank_payment_method_diffs or {}}
        data = self._accumulate_amounts(data)
        data = self._create_non_reconciliable_move_lines(data)
        data = self._create_bank_payment_moves(data)
        data = self._create_pay_later_receivable_lines(data)
        data = self._create_cash_statement_lines_and_cash_move_lines(data)
        data = self._create_invoice_receivable_lines(data)
        data = self._create_stock_output_lines(data)
        if balancing_account and amount_to_balance:
            data = self._create_balancing_line(
                data, balancing_account, amount_to_balance)

        return data

    # def _get_split_receivable_vals(self, payment, amount, amount_converted):
    #     accounting_partner = self.env["res.partner"]._find_accounting_partner(
    #         payment.partner_id)
    #     if not accounting_partner:
    #         raise UserError(_("You have enabled the \"Identify Customer\" option for %s payment method,"
    #                           "but the order %s does not contain a customer.") % (payment.payment_method_id.name,
    #                                                                               payment.pos_order_id.name))
    #     partial_vals = {
    #         'account_id': accounting_partner.property_account_receivable_id.id,
    #         'move_id': self.move_id.id,
    #         'partner_id': accounting_partner.id,
    #         'name': '%s - %s %s' % (self.name, self._context.get('stop_at').strftime("%d/%m/%Y"), payment.payment_method_id.name),
    #     }
    #     return self._debit_amounts(partial_vals, amount, amount_converted)

    def _get_split_receivable_vals(self, payment, amount, amount_converted):
        partial_vals = super()._get_split_receivable_vals(
            payment, amount, amount_converted)
        partial_vals['name'] = '%s - %s %s' % (self.name, self._context.get(
            'stop_at').strftime("%d/%m/%Y"), payment.payment_method_id.name)
        return partial_vals

    # def _get_combine_receivable_vals(self, payment_method, amount, amount_converted):
    #     partial_vals = {
    #         'account_id': self._get_receivable_account(payment_method).id,
    #         'move_id': self.move_id.id,
    #         'name': '%s - %s %s' % (self.name, self._context.get('stop_at').strftime("%d/%m/%Y"), payment_method.name)
    #     }
    #     return self._debit_amounts(partial_vals, amount, amount_converted)

    def _get_combine_receivable_vals(self, payment_method, amount, amount_converted):
        partial_vals = super()._get_combine_receivable_vals(
            payment_method, amount, amount_converted)
        partial_vals['name'] = '%s - %s %s' % (self.name, self._context.get(
            'stop_at').strftime("%d/%m/%Y"), payment_method.name)
        return partial_vals

    # def _get_sale_vals(self, key, amount, amount_converted):
    #     account_id, sign, tax_keys, base_tag_ids = key
    #     tax_ids = set(tax[0] for tax in tax_keys)
    #     applied_taxes = self.env['account.tax'].browse(tax_ids)
    #     title = 'Sales' if sign == 1 else 'Refund'
    #     name = '%s untaxed' % title
    #     if applied_taxes:
    #         name = _('%s - %s %s with %s' % (self.name, self._context.get('stop_at').strftime(
    #             "%d/%m/%Y"), title, ', '.join([tax.name for tax in applied_taxes])))
    #     partial_vals = {
    #         'name': name,
    #         'account_id': account_id,
    #         'move_id': self.move_id.id,
    #         'tax_ids': [(6, 0, tax_ids)],
    #         'tax_tag_ids': [(6, 0, base_tag_ids)],
    #     }
    #     return self._credit_amounts(partial_vals, amount, amount_converted)

    def _get_sale_vals(self, key, amount, amount_converted):
        partial_vals = super()._get_sale_vals(key, amount, amount_converted)
        account_id, sign, tax_keys, base_tag_ids = key
        tax_ids = set(tax[0] for tax in tax_keys)
        applied_taxes = self.env['account.tax'].browse(tax_ids)
        title = _('Sales') if sign == 1 else _('Refund')
        untaxed = _('untaxed')
        name = '%s %s' % (title, untaxed)
        if applied_taxes:
            name = '%s - %s %s %s' % (self.name, self._context.get('stop_at').strftime(
                "%d/%m/%Y"), title, ', '.join([tax.name for tax in applied_taxes]))

        partial_vals['name'] = name

        return partial_vals

    # def _get_tax_vals(self, key, amount, amount_converted, base_amount_converted):
    #     account_id, repartition_line_id, tax_id, tag_ids = key
    #     tax = self.env['account.tax'].browse(tax_id)
    #     name = _('%s - %s %s' % (self.name,
    #              self._context.get('stop_at').strftime("%d/%m/%Y"), tax.name))
    #     partial_args = {
    #         'name': name,
    #         'account_id': account_id,
    #         'move_id': self.move_id.id,
    #         'tax_base_amount': abs(base_amount_converted),
    #         'tax_repartition_line_id': repartition_line_id,
    #         'tax_tag_ids': [(6, 0, tag_ids)],
    #     }
    #     return self._debit_amounts(partial_args, amount, amount_converted)

    def _get_tax_vals(self, key, amount, amount_converted, base_amount_converted):
        partial_args = super()._get_tax_vals(
            key, amount, amount_converted, base_amount_converted)
        account_id, repartition_line_id, tax_id, tag_ids = key
        tax = self.env['account.tax'].browse(tax_id)
        name = '%s - %s %s' % (self.name,
                               self._context.get('stop_at').strftime("%d/%m/%Y"), tax.name)
        partial_args['name'] = name

        return partial_args
