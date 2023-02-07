# Copyright 2021 Zuher Elmas
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).

import logging

from odoo import fields, models, _
from odoo.exceptions import AccessError, UserError, ValidationError

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

    def _create_payment_moves(self):
        result = self.env['account.move']
        for payment in self:
            order = payment.pos_order_id
            payment_method = payment.payment_method_id
            if payment_method.type == 'pay_later' or float_is_zero(payment.amount, precision_rounding=order.currency_id.rounding):
                continue
            accounting_partner = self.env["res.partner"]._find_accounting_partner(
                payment.partner_id)
            pos_session = order.session_id
            journal = pos_session.config_id.journal_id
            payment_move = self.env['account.move'].with_context(default_journal_id=journal.id).create({
                'journal_id': journal.id,
                'date': payment.pos_order_id.date_order.date(),
                'ref': _('Invoice payment for %s (%s) using %s - %s') % (order.name, order.account_move.name, payment_method.name, payment.payment_date.date()),
                'pos_payment_ids': payment.ids,
            })
            result |= payment_move
            payment.write({'account_move_id': payment_move.id})
            amounts = pos_session._update_amounts({'amount': 0, 'amount_converted': 0}, {
                                                  'amount': payment.amount}, payment.payment_date)
            credit_line_vals = pos_session._credit_amounts({
                # The field being company dependant, we need to make sure the right value is received.
                'account_id': accounting_partner.with_company(order.company_id).property_account_receivable_id.id,
                'partner_id': accounting_partner.id,
                'move_id': payment_move.id,
                'name': ('%s - test') % payment.payment_date.date()
            }, amounts['amount'], amounts['amount_converted'])
            debit_line_vals = pos_session._debit_amounts({
                'account_id': pos_session.company_id.account_default_pos_receivable_account_id.id,
                'move_id': payment_move.id,
                'name': ('%s - test') % payment.payment_date.date()
            }, amounts['amount'], amounts['amount_converted'])
            self.env['account.move.line'].with_context(check_move_validity=False).create([
                credit_line_vals, debit_line_vals])
            payment_move._post()
        return result


class PosSession(models.Model):
    _inherit = 'pos.session'

    # def _post_statement_difference(self, amount):
    #     return {}

    def action_pos_session_closing_control(self, balancing_account=False, amount_to_balance=0, bank_payment_method_diffs=None):
        result = super(PosSession, self).action_pos_session_closing_control(balancing_account=balancing_account, amount_to_balance=amount_to_balance, bank_payment_method_diffs=bank_payment_method_diffs)
        # for session in self:
        self.write({'stop_at': self._context.get('stop_at')})
        return result

    def _create_account_move(self, balancing_account=False, amount_to_balance=0, bank_payment_method_diffs=None):
        """ Create account.move and account.move.line records for this session.

        Side-effects include:
            - setting self.move_id to the created account.move record
            - reconciling cash receivable lines, invoice receivable lines and stock output lines
        """
        _logger.warning('Move %s' % self._context)
        account_move = self.env['account.move'].create({
            'journal_id': self.config_id.journal_id.id,
            'date': self._context.get('stop_at'),
            'ref': _(('%s - %s') % (self.name, self._context.get('stop_at').date())),
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

    def _get_split_receivable_vals(self, payment, amount, amount_converted):
        accounting_partner = self.env["res.partner"]._find_accounting_partner(
            payment.partner_id)
        if not accounting_partner:
            raise UserError(_("You have enabled the \"Identify Customer\" option for %s payment method,"
                              "but the order %s does not contain a customer.") % (payment.payment_method_id.name,
                                                                                  payment.pos_order_id.name))
        partial_vals = {
            'account_id': accounting_partner.property_account_receivable_id.id,
            'move_id': self.move_id.id,
            'partner_id': accounting_partner.id,
            'name': '%s - %s %s' % (self.name, self._context.get('stop_at').date(), payment.payment_method_id.name),
        }
        return self._debit_amounts(partial_vals, amount, amount_converted)

    def _get_combine_receivable_vals(self, payment_method, amount, amount_converted):
        partial_vals = {
            'account_id': self._get_receivable_account(payment_method).id,
            'move_id': self.move_id.id,
            'name': '%s - %s %s' % (self.name, self._context.get('stop_at').date(), payment_method.name)
        }
        return self._debit_amounts(partial_vals, amount, amount_converted)
