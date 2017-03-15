# -*- coding: utf-8 -*-
# Copyright 2017 KMEE
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import api, fields, models
from ..models.financial_move import (
    FINANCIAL_MOVE,
)


class FinancialMoveCreate(models.TransientModel):

    _name = 'financial.move.create'
    _inherit = ['account.abstract.payment']

    @api.multi
    @api.depends('financial_type')
    def _compute_payment_type(self):
        for record in self:
            if record.financial_type in ('r', 'rr'):
                record.payment_type = 'inbound'
            elif record.financial_type in ('p', 'pp'):
                record.payment_type = 'outbound'

    @api.depends('amount', 'amount_discount')
    def _compute_totals(self):
        for record in self:
            record.amount_total = record.amount - record.amount_discount

    line_ids = fields.One2many(
        comodel_name='financial.move.line.create',
        inverse_name='financial_move_id',
        # readonly=True,
    )
    financial_type = fields.Selection(
        selection=FINANCIAL_MOVE,
        required=True,
    )
    payment_type = fields.Selection(
        compute='_compute_payment_type',
    )
    payment_term_id = fields.Many2one(
        string='Payment Term',
        comodel_name='account.payment.term',
    )
    account_analytic_id = fields.Many2one(
        comodel_name='account.analytic.account',
        string=u'Analytic account',
    )
    account_id = fields.Many2one(
        comodel_name='account.account',
        string=u'Account',
        required=True,
        domain=[('internal_type', 'in', ('receivable', 'payable'))],
        help="The partner account used for this invoice."
    )
    document_number = fields.Char(
        string=u"Document Nº",
        required=True,
    )
    date_issue = fields.Date(
        string=u'Financial date',
        default=fields.Date.context_today,
    )
    amount_total = fields.Monetary(
        string=u'Total',
        readonly=True,
        compute='_compute_totals',
    )
    amount_discount = fields.Monetary(
        string=u'Discount',
    )
    note = fields.Text(
        string="Note",
    )

    @api.onchange('payment_term_id', 'document_number',
                  'date_issue', 'amount')
    def onchange_fields(self):
        res = {}
        if not (self.payment_term_id and self.document_number and
                self.date_issue and self.amount > 0.00):
            return res

        computations = \
            self.payment_term_id.compute(self.amount, self.date_issue)

        payment_ids = []
        for idx, item in enumerate(computations[0]):
            payment = dict(
                document_item=self.document_number + '/' + str(idx + 1),
                date_maturity=item[0],
                amount=item[1],
            )
            payment_ids.append((0, False, payment))
        self.line_ids = payment_ids

    @api.multi
    def compute(self):
        financial_move = self.env['financial.move']
        for record in self:
            res = []
            for move in record.line_ids:
                financial = financial_move.create(dict(
                    journal_id=self.journal_id.id,
                    company_id=self.company_id.id,
                    currency_id=self.currency_id.id,
                    financial_type=self.financial_type,
                    partner_id=self.partner_id.id,
                    document_number=self.document_number,
                    date_issue=self.date_issue,
                    payment_method_id=self.payment_method_id.id,
                    payment_term_id=self.payment_term_id.id,
                    account_analytic_id=self.account_analytic_id.id,
                    account_id=self.account_id.id,
                    document_item=move.document_item,
                    date_maturity=move.date_maturity,
                    amount=move.amount,
                ))
                financial.action_confirm()
                res.append(financial.id)

        if record.financial_type == 'r':
            name = 'Receivable'
        else:
            name = 'Payable'
        action = {
            'name': name,
            'type': 'ir.actions.act_window',
            'res_model': 'financial.move',
            'domain': [('id', 'in', res)],
            'views': [(self.env.ref(
                'financial.financial_move_tree_view').id, 'list')],
            'view_type': 'list',
            'view_mode': 'form,tree',
            'target': 'current'
        }
        return action


class FinancialMoveLineCreate(models.TransientModel):

    _name = 'financial.move.line.create'

    currency_id = fields.Many2one(
        comodel_name='res.currency',
        string=u'Currency',
    )

    document_item = fields.Char(
        string=u"Document item",
    )

    date_issue = fields.Date(
        string=u"Document date",
    )

    date_maturity = fields.Date(
        string=u"Due date",
    )

    amount = fields.Monetary(
        string=u"Document amount",
    )

    financial_move_id = fields.Many2one(
        comodel_name='financial.move.create',
        required=True
    )