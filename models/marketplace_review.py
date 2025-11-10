# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError

class MarketplaceReview(models.Model):
    """Product and vendor reviews"""
    _name = 'marketplace.review'
    _description = 'Marketplace Review'
    _inherit = ['mail.thread']
    _order = 'create_date desc'

    name = fields.Char(string='Title', required=True)
    
    customer_id = fields.Many2one('res.partner', string='Customer', required=True,
                                  ondelete='cascade')
    
    product_id = fields.Many2one('marketplace.product', string='Product',
                                 ondelete='cascade', index=True)
    vendor_id = fields.Many2one('marketplace.vendor', string='Vendor',
                                ondelete='cascade', index=True)
    order_id = fields.Many2one('marketplace.order', string='Order')
    
    rating = fields.Integer(string='Rating', required=True, help='Rating from 1 to 5')
    review_text = fields.Text(string='Review', required=True)
    
    state = fields.Selection([
        ('draft', 'Draft'),
        ('published', 'Published'),
        ('rejected', 'Rejected'),
    ], string='Status', default='draft', tracking=True)
    
    helpful_count = fields.Integer(string='Helpful Votes', default=0)
    verified_purchase = fields.Boolean(string='Verified Purchase', 
                                       compute='_compute_verified_purchase', store=True)
    
    review_date = fields.Datetime(string='Review Date', default=fields.Datetime.now)
    
    _sql_constraints = [
        ('rating_check', 'CHECK(rating >= 1 AND rating <= 5)', 
         'Rating must be between 1 and 5!'),
    ]

    @api.depends('order_id', 'customer_id')
    def _compute_verified_purchase(self):
        for review in self:
            review.verified_purchase = bool(review.order_id and 
                                           review.order_id.state == 'done')

    @api.constrains('product_id', 'vendor_id')
    def _check_review_target(self):
        for review in self:
            if not review.product_id and not review.vendor_id:
                raise ValidationError(_('Review must be for either a product or vendor'))

    def action_publish(self):
        self.write({'state': 'published'})

    def action_reject(self):
        self.write({'state': 'rejected'})

