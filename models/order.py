# -*- coding: utf-8 -*-
from odoo import models, fields, api


class MarketOrder(models.Model):
    _name = 'market.order'
    _inherit = ['mail.thread']
    _description = 'Marketplace Order'

    name = fields.Char(string='Order Reference', required=True, copy=False, readonly=True, default='New')
    partner_id = fields.Many2one('res.partner', string='Customer', required=True)
    date_order = fields.Datetime(string='Order Date', default=fields.Datetime.now)
    state = fields.Selection([
        ('draft','Draft'),
        ('sale','Confirmed'),
        ('done','Done'),
        ('cancel','Cancelled')
    ], default='draft')
    order_line_ids = fields.One2many('market.order.line', 'order_id', string='Order Lines')
    amount_total = fields.Float(string='Total', compute='_compute_amount_total', store=True)

    @api.depends('order_line_ids.price_subtotal')
    def _compute_amount_total(self):
        for order in self:
            total = 0.0
            for line in order.order_line_ids:
                total += (line.price_subtotal or 0.0)
            order.amount_total = total
            
    def action_confirm(self):
        for order in self:
            # Logique de confirmation ici (ex: vérifier le stock)
            order.state = 'sale' # ou 'confirmed' selon ta définition de state
        return True

    def action_cancel(self):
        for order in self:
            # Logique d'annulation ici
            order.state = 'cancel'
        return True
