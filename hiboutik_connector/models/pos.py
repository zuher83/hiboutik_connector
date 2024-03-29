# Copyright 2023 Zuher Elmas
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).

import logging

from odoo import fields, models, api, _
from odoo.tools import float_is_zero, float_compare
# from odoo.exceptions import UserError

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


class PosOrderLine(models.Model):
    _inherit = 'pos.order.line'

    hiboutik_order_line_id = fields.Integer(string='Hiboutik order line Id')


class PosPayment(models.Model):
    _inherit = 'pos.payment'

    hiboutik_payment_detail_id = fields.Integer(
        string='Hiboutik payment detail Id')


class PosSession(models.Model):
    _inherit = 'pos.session'

    session_sales_untaxed_total = fields.Monetary(
        compute='_compute_sales_total',
        string='Total Untaxed',
        readonly=True)

    session_sales_taxed_total = fields.Monetary(
        compute='_compute_sales_total',
        string='Total Taxed',
        readonly=True)

    @api.depends('order_ids')
    def _compute_sales_total(self):
        for session in self:
            if session.order_ids:
                session.session_sales_taxed_total = sum(
                    session.order_ids.mapped('amount_total'))
                session.session_sales_untaxed_total = session.session_sales_taxed_total - sum(session.order_ids.mapped(
                    'amount_tax'))
            else:
                session.session_sales_taxed_total = 0.0
                session.session_sales_untaxed_total = 0.0

    @api.depends('payment_method_ids', 'order_ids', 'cash_register_balance_start')
    def _compute_cash_balance(self):
        for session in self:
            cash_payment_method = session.payment_method_ids.filtered('is_cash_count')[
                :1]
            if cash_payment_method:
                total_cash_payment = 0.0
                # last_session = session.search( [('config_id', '=', session.config_id.id), ('id', '!=', session.id)], limit=1)
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
        result = super(PosSession, self).action_pos_session_closing_control(balancing_account,
                                                                            amount_to_balance, bank_payment_method_diffs)
        if self._context.get('stop_at'):
            self.write({'stop_at': self._context.get('stop_at')})
        return result

    def _create_account_move(self, balancing_account=False, amount_to_balance=0, bank_payment_method_diffs=None):
        """ Create account.move and account.move.line records for this session.

        Side-effects include:
            - setting self.move_id to the created account.move record
            - reconciling cash receivable lines, invoice receivable lines and stock output lines
        """
        if self._context.get('stop_at'):
            ref = _('POS Sales of %s - %s') % (
                self._context.get('stop_at').strftime("%d/%m/%Y"), self.name)
        else:
            ref = _('POS Session %s') % (self.name)
        account_move = self.env['account.move'].create({
            'journal_id': self.config_id.journal_id.id,
            'date': self._context.get('stop_at'),
            'ref': _('POS Sales of %s') % (ref),
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

    def _create_combine_account_payment(self, payment_method, amounts, diff_amount):
        outstanding_account = payment_method.outstanding_account_id or self.company_id.account_journal_payment_debit_account_id
        destination_account = self._get_receivable_account(payment_method)

        if float_compare(amounts['amount'], 0, precision_rounding=self.currency_id.rounding) < 0:
            # revert the accounts because account.payment doesn't accept negative amount.
            outstanding_account, destination_account = destination_account, outstanding_account

        account_payment = self.env['account.payment'].create({
            'amount': abs(amounts['amount']),
            'journal_id': payment_method.journal_id.id,
            'force_outstanding_account_id': outstanding_account.id,
            'destination_account_id':  destination_account.id,
            'ref': _('Combine %s POS payments from %s %s') % (payment_method.name, self._context.get(
                'stop_at').strftime("%d/%m/%Y"), self.name),
            'pos_payment_method_id': payment_method.id,
            'pos_session_id': self.id,
        })

        diff_amount_compare_to_zero = self.currency_id.compare_amounts(
            diff_amount, 0)
        if diff_amount_compare_to_zero != 0:
            self._apply_diff_on_account_payment_move(
                account_payment, payment_method, diff_amount)

        account_payment.action_post()
        return account_payment.move_id.line_ids.filtered(lambda line: line.account_id == account_payment.destination_account_id)

    def _create_diff_account_move_for_split_payment_method(self, payment_method, diff_amount):
        diff_move = super()._create_diff_account_move_for_split_payment_method(
            payment_method=payment_method, diff_amount=diff_amount)
        diff_move['date'] = self._context.get('stop_at')
        return diff_move

    def _get_split_receivable_vals(self, payment, amount, amount_converted):
        partial_vals = super()._get_split_receivable_vals(
            payment=payment, amount=amount, amount_converted=amount_converted)
        partial_vals['name'] = '%s - %s %s' % (self._context.get(
            'stop_at').strftime("%d/%m/%Y"), self.name, payment.payment_method_id.name)
        return partial_vals

    def _get_combine_receivable_vals(self, payment_method, amount, amount_converted):
        partial_vals = super()._get_combine_receivable_vals(
            payment_method=payment_method, amount=amount, amount_converted=amount_converted)
        partial_vals['name'] = '%s - %s %s' % (self._context.get(
            'stop_at').strftime("%d/%m/%Y"), self.name, payment_method.name)
        return partial_vals

    def _get_sale_vals(self, key, amount, amount_converted):
        partial_vals = super()._get_sale_vals(
            key=key, amount=amount, amount_converted=amount_converted)
        account_id, sign, tax_keys, base_tag_ids = key
        tax_ids = set(tax[0] for tax in tax_keys)
        applied_taxes = self.env['account.tax'].browse(tax_ids)
        title = _('Sales') if sign == 1 else _('Refund')
        untaxed = _('untaxed')
        name = '%s %s' % (title, untaxed)
        if applied_taxes:
            name = '%s - %s %s %s' % (self._context.get('stop_at').strftime(
                "%d/%m/%Y"), self.name, title, ', '.join([tax.name for tax in applied_taxes]))

        partial_vals['name'] = name

        return partial_vals

    def _get_tax_vals(self, key, amount, amount_converted, base_amount_converted):
        partial_args = super()._get_tax_vals(
            key=key, amount=amount, amount_converted=amount_converted, base_amount_converted=base_amount_converted)
        account_id, repartition_line_id, tax_id, tag_ids = key
        tax = self.env['account.tax'].browse(tax_id)
        name = '%s - %s %s' % (self._context.get(
            'stop_at').strftime("%d/%m/%Y"), self.name, tax.name)
        partial_args['name'] = name

        return partial_args

    def _get_split_statement_line_vals(self, journal_id, amount, payment):
        result = super()._get_split_statement_line_vals(
            journal_id=journal_id, amount=amount, payment=payment)
        result['date'] = self._context.get('stop_at')
        return result

    def _get_combine_statement_line_vals(self, journal_id, amount, payment_method):
        result = super()._get_combine_statement_line_vals(
            journal_id, amount, payment_method)
        result['payment_ref'] = '%s - %s %s' % (self._context.get(
            'stop_at').strftime("%d/%m/%Y"), self.name, payment_method.name)
        result['date'] = self._context.get('stop_at')
        return result
