# -*- coding: utf-8 -*-
from odoo import models, fields, api

class MarketProductListing(models.Model):
    _name = 'market.product.listing'
    description = fields.Html(string='Description')
    name = fields.Char(string='Listing Name', required=True)
    vendor_id = fields.Many2one('market.vendor', string='Vendor', required=True)
    product_tmpl_id = fields.Many2one('product.template', string='Product Template')
    price = fields.Float(string='Price', required=True)
    qty_available = fields.Float(string='Quantity Available', default=0.0)
    state = fields.Selection([
        ('draft','Draft'),
        ('published','Published'),
        ('archived','Archived')
    ], default='draft')
    image = fields.Binary(string='Image')  # pour logo / image du produit
