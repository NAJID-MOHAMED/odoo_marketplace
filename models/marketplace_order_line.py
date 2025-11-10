from odoo import models, fields, api


class MarketOrderLine(models.Model):
    _name = 'market.order.line'
    _description = 'Order line for marketplace'

    order_id = fields.Many2one('market.order', string='Order', required=True, ondelete='cascade')
    listing_id = fields.Many2one('market.product.listing', string='Listing', required=True)
    vendor_id = fields.Many2one('market.vendor', string='Vendor', related='listing_id.vendor_id', store=True)
    product_qty = fields.Float(string='Quantity', default=1.0)
    price_unit = fields.Float(string='Unit Price', required=True)
    price_subtotal = fields.Float(string='Subtotal', compute='_compute_price_subtotal', store=True)

    @api.depends('product_qty', 'price_unit')
    def _compute_price_subtotal(self):
        for line in self:
            try:
                line.price_subtotal = (line.product_qty or 0.0) * (line.price_unit or 0.0)
            except Exception:
                line.price_subtotal = 0.0
