# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import UserError

class MarketplaceCommission(models.Model):
    """Commission tracking for vendor sales"""
    _name = 'marketplace.commission'
    _description = 'Marketplace Commission'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'create_date desc'

    name = fields.Char(string='Reference', required=True, readonly=True, 
                       copy=False, default='/')
    
    order_id = fields.Many2one('marketplace.order', string='Order', required=True,
                               ondelete='cascade', tracking=True)
    vendor_id = fields.Many2one('marketplace.vendor', string='Vendor', required=True,
                                ondelete='restrict', tracking=True, index=True)
    
    order_amount = fields.Monetary(string='Order Amount', required=True,
                                   currency_field='currency_id')
    
    commission_type = fields.Selection(related='vendor_id.commission_type', store=True)
    commission_rate = fields.Float(related='vendor_id.commission_rate', store=True)
    
    commission_amount = fields.Monetary(string='Commission', 
                                       compute='_compute_commission', store=True,
                                       currency_field='currency_id')
    vendor_amount = fields.Monetary(string='Vendor Amount',
                                    compute='_compute_commission', store=True,
                                    currency_field='currency_id')
    
    currency_id = fields.Many2one('res.currency', string='Currency',
                                  default=lambda self: self.env.company.currency_id)
    
    state = fields.Selection([
        ('draft', 'Draft'),
        ('confirmed', 'Confirmed'),
        ('paid', 'Paid'),
    ], string='Status', default='draft', tracking=True)
    
    payout_id = fields.Many2one('marketplace.payout', string='Payout')
    payment_date = fields.Date(string='Payment Date', readonly=True)

    @api.model
    def create(self, vals):
        if vals.get('name', '/') == '/':
            vals['name'] = self.env['ir.sequence'].next_by_code('marketplace.commission') or '/'
        return super(MarketplaceCommission, self).create(vals)

    @api.depends('order_amount', 'commission_rate', 'commission_type')
    def _compute_commission(self):
        for comm in self:
            if comm.commission_type == 'percentage':
                comm.commission_amount = (comm.order_amount or 0.0) * (comm.commission_rate or 0.0) / 100.0
            else:
                # Use vendor fixed commission if set, otherwise 0.0
                comm.commission_amount = comm.vendor_id.fixed_commission or 0.0

            comm.vendor_amount = (comm.order_amount or 0.0) - (comm.commission_amount or 0.0)

    def action_confirm(self):
        self.write({'state': 'confirmed'})
        self.message_post(body=_('Commission confirmed'))

    def action_mark_paid(self):
        self.write({
            'state': 'paid',
            'payment_date': fields.Date.context_today(self),
        })
        self.message_post(body=_('Commission paid'))


class MarketplacePayout(models.Model):
    """Vendor payouts"""
    _name = 'marketplace.payout'
    _description = 'Marketplace Payout'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'create_date desc'

    name = fields.Char(string='Reference', required=True, readonly=True, 
                       copy=False, default='/')
    vendor_id = fields.Many2one('marketplace.vendor', string='Vendor', required=True,
                                ondelete='restrict', tracking=True)
    
    commission_ids = fields.One2many('marketplace.commission', 'payout_id', 
                                    string='Commissions')
    
    amount = fields.Monetary(string='Payout Amount', compute='_compute_amount', 
                            store=True, currency_field='currency_id')
    currency_id = fields.Many2one('res.currency', string='Currency',
                                  default=lambda self: self.env.company.currency_id)
    
    payout_date = fields.Date(string='Payout Date', default=fields.Date.context_today)
    
    state = fields.Selection([
        ('draft', 'Draft'),
        ('confirmed', 'Confirmed'),
        ('paid', 'Paid'),
    ], string='Status', default='draft', tracking=True)
    
    payment_method = fields.Selection([
        ('bank', 'Bank Transfer'),
        ('check', 'Check'),
        ('cash', 'Cash'),
    ], string='Payment Method')
    
    notes = fields.Text(string='Notes')

    @api.model
    def create(self, vals):
        if vals.get('name', '/') == '/':
            vals['name'] = self.env['ir.sequence'].next_by_code('marketplace.payout') or '/'
        return super(MarketplacePayout, self).create(vals)

    @api.depends('commission_ids.vendor_amount')
    def _compute_amount(self):
        for payout in self:
            payout.amount = sum(payout.commission_ids.mapped('vendor_amount'))

    def action_confirm(self):
        self.write({'state': 'confirmed'})
        self.message_post(body=_('Payout confirmed'))

    def action_mark_paid(self):
        self.write({'state': 'paid'})
        self.commission_ids.action_mark_paid()
        self.message_post(body=_('Payout completed'))