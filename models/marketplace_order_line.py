from odoo import models, fields, api

class MarketOrderLine(models.Model):
    _name = 'market.order.line'
    _description = 'Order line for marketplace'

    order_id = fields.Many2one('market.order', string='Order', required=True, ondelete='cascade')
    listing_id = fields.Many2one('market.product.listing', string='Listing', required=True)
    vendor_id = fields.Many2one('market.vendor', string='Vendor', related='listing_id.vendor_id', store=True)
    
    product_name = fields.Char(
        string='Product Name',
        required=True,
        compute='_compute_product_name',
        store=True
    )
    
    product_qty = fields.Float(string='Quantity', default=1.0)
    price_unit = fields.Float(string='Unit Price', required=True)
    price_subtotal = fields.Float(string='Subtotal', compute='_compute_price_subtotal', store=True)

    @api.depends('listing_id')
    def _compute_product_name(self):
        for line in self:
            line.product_name = line.listing_id.name if line.listing_id else 'Undefined Product'

    @api.depends('product_qty', 'price_unit')
    def _compute_price_subtotal(self):
        for line in self:
            line.price_subtotal = (line.product_qty or 0.0) * (line.price_unit or 0.0)
  
    @api.onchange('listing_id')
    def _onchange_listing(self):
        for line in self:
            if line.listing_id:
               line.product_name = line.listing_id.name
