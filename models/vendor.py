# -*- coding: utf-8 -*-
from odoo import models, fields, api

class MarketVendor(models.Model):
    _name = 'market.vendor'
    # AJOUTE CETTE LIGNE D'HÉRITAGE :
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description = 'Marketplace Vendor'

    name = fields.Char(string='Vendor Name', required=True, tracking=True) # Tu peux ajouter tracking=True pour suivre les changements
    active = fields.Boolean(string="Active", default=True)
    user_id = fields.Many2one('res.users', string='Account Manager')
    partner_id = fields.Many2one('res.partner', string='Partner')
    state = fields.Selection([
        ('draft','Draft'),
        ('validated','Validated'),
        ('suspended','Suspended')
    ], default='draft', string='Status', tracking=True) # Utile de tracker le statut aussi
    rating = fields.Float(string='Rating', digits=(3,2))
    note = fields.Text(string='Notes')