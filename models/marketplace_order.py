# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError, UserError
import logging

_logger = logging.getLogger(__name__)

class MarketplaceOrder(models.Model):
    """Customer orders in marketplace"""
    _name = 'marketplace.order'
    _description = 'Marketplace Order'
    _inherit = ['mail.thread', 'mail.activity.mixin', 'portal.mixin']
    _order = 'create_date desc'

    name = fields.Char(string='Order Reference', required=True, readonly=True, 
                       copy=False, default='/', index=True)
    
    # Parties
    customer_id = fields.Many2one('res.partner', string='Customer', required=True, 
                                  tracking=True, ondelete='restrict')
    vendor_id = fields.Many2one('marketplace.vendor', string='Vendor', required=True,
                                tracking=True, ondelete='restrict', index=True)
    
    # Order Details
    order_line_ids = fields.One2many('marketplace.order.line', 'order_id', 
                                     string='Order Lines')
    
    # Dates
    order_date = fields.Datetime(string='Order Date', required=True, 
                                 default=fields.Datetime.now, tracking=True)
    confirmed_date = fields.Datetime(string='Confirmed Date', readonly=True)
    delivered_date = fields.Datetime(string='Delivered Date', readonly=True)
    cancelled_date = fields.Datetime(string='Cancelled Date', readonly=True)
    
    # Status
    state = fields.Selection([
        ('draft', 'Draft'),
        ('confirmed', 'Confirmed'),
        ('processing', 'Processing'),
        ('shipped', 'Shipped'),
        ('delivered', 'Delivered'),
        ('done', 'Done'),
        ('cancelled', 'Cancelled'),
    ], string='Status', default='draft', required=True, tracking=True)
    
    # Amounts
    currency_id = fields.Many2one('res.currency', string='Currency',
                                  default=lambda self: self.env.company.currency_id)
    amount_untaxed = fields.Monetary(string='Untaxed Amount', 
                                     compute='_compute_amounts', store=True)
    amount_tax = fields.Monetary(string='Taxes', compute='_compute_amounts', store=True)
    amount_total = fields.Monetary(string='Total', compute='_compute_amounts', store=True)
    
    # Shipping
    shipping_address_id = fields.Many2one('res.partner', string='Shipping Address')
    shipping_method = fields.Selection([
        ('standard', 'Standard'),
        ('express', 'Express'),
        ('overnight', 'Overnight'),
    ], string='Shipping Method', default='standard')
    shipping_cost = fields.Monetary(string='Shipping Cost', currency_field='currency_id')
    tracking_number = fields.Char(string='Tracking Number')
    
    # Payment
    payment_method = fields.Selection([
        ('cash', 'Cash on Delivery'),
        ('card', 'Credit/Debit Card'),
        ('bank', 'Bank Transfer'),
        ('wallet', 'Digital Wallet'),
    ], string='Payment Method')
    payment_status = fields.Selection([
        ('unpaid', 'Unpaid'),
        ('partial', 'Partially Paid'),
        ('paid', 'Paid'),
        ('refunded', 'Refunded'),
    ], string='Payment Status', default='unpaid', tracking=True)
    
    # Invoice
    invoice_id = fields.Many2one('account.move', string='Invoice', readonly=True)
    
    # Commission
    commission_id = fields.Many2one('marketplace.commission', string='Commission')
    
    # Notes
    customer_note = fields.Text(string='Customer Note')
    internal_note = fields.Text(string='Internal Note')
    
    _sql_constraints = [
        ('name_unique', 'UNIQUE(name)', 'Order reference must be unique!'),
    ]

    @api.model
    def create(self, vals):
        if vals.get('name', '/') == '/':
            vals['name'] = self.env['ir.sequence'].next_by_code('marketplace.order') or '/'
        
        order = super(MarketplaceOrder, self).create(vals)
        _logger.info(f'New order created: {order.name}')
        return order

    @api.depends('order_line_ids.subtotal', 'order_line_ids.tax_amount', 'shipping_cost')
    def _compute_amounts(self):
        for order in self:
            order.amount_untaxed = sum(order.order_line_ids.mapped('subtotal'))
            order.amount_tax = sum(order.order_line_ids.mapped('tax_amount'))
            order.amount_total = order.amount_untaxed + order.amount_tax + order.shipping_cost

    def action_confirm(self):
        self.ensure_one()
        if self.state != 'draft':
            raise UserError(_('Only draft orders can be confirmed'))
        
        # Check stock availability
        for line in self.order_line_ids:
            if line.product_id.qty_available < line.quantity:
                raise UserError(_('Insufficient stock for %s') % line.product_id.name)
        
        # Update stock
        for line in self.order_line_ids:
            line.product_id.update_stock(line.quantity, 'subtract')
        
        self.write({
            'state': 'confirmed',
            'confirmed_date': fields.Datetime.now(),
        })
        
        self._send_confirmation_email()
        self._create_commission()
        self.message_post(body=_('Order confirmed'))

    def action_process(self):
        self.ensure_one()
        self.write({'state': 'processing'})
        self.message_post(body=_('Order is being processed'))

    def action_ship(self):
        self.ensure_one()
        self.write({'state': 'shipped'})
        self._send_shipping_email()
        self.message_post(body=_('Order shipped'))

    def action_deliver(self):
        self.ensure_one()
        self.write({
            'state': 'delivered',
            'delivered_date': fields.Datetime.now(),
        })
        self.message_post(body=_('Order delivered'))

    def action_done(self):
        self.ensure_one()
        self.write({'state': 'done'})
        self._create_invoice()
        self.message_post(body=_('Order completed'))

    def action_cancel(self):
        self.ensure_one()
        if self.state in ['done', 'cancelled']:
            raise UserError(_('Cannot cancel completed or cancelled orders'))
        
        # Restore stock
        if self.state in ['confirmed', 'processing']:
            for line in self.order_line_ids:
                line.product_id.update_stock(line.quantity, 'add')
        
        self.write({
            'state': 'cancelled',
            'cancelled_date': fields.Datetime.now(),
        })
        self.message_post(body=_('Order cancelled'))

    def _create_commission(self):
        """Create commission record"""
        self.ensure_one()
        if not self.commission_id and self.vendor_id:
            vals = {
                'order_id': self.id,
                'vendor_id': self.vendor_id.id,
                'order_amount': self.amount_total,
            }
            commission = self.env['marketplace.commission'].create(vals)
            self.commission_id = commission.id

    def _create_invoice(self):
        """Create invoice"""
        # Implementation would create account.move
        pass

    def _send_confirmation_email(self):
        template = self.env.ref('marketplace.email_template_order_confirmation', 
                                raise_if_not_found=False)
        if template:
            template.send_mail(self.id, force_send=True)

    def _send_shipping_email(self):
        template = self.env.ref('marketplace.email_template_order_shipped',
                                raise_if_not_found=False)
        if template:
            template.send_mail(self.id, force_send=True)


class MarketplaceOrderLine(models.Model):
    """Order line items"""
    _name = 'marketplace.order.line'
    _description = 'Marketplace Order Line'
    _order = 'order_id, sequence, id'

    order_id = fields.Many2one('marketplace.order', string='Order', required=True, 
                               ondelete='cascade', index=True)
    sequence = fields.Integer(string='Sequence', default=10)
    
    product_id = fields.Many2one('marketplace.product', string='Product', 
                                 required=True, ondelete='restrict')
    product_name = fields.Char(string='Description', required=True)
    
    quantity = fields.Float(string='Quantity', required=True, default=1.0, 
                           digits='Product Unit of Measure')
    price_unit = fields.Monetary(string='Unit Price', required=True, 
                                 currency_field='currency_id')
    
    discount = fields.Float(string='Discount (%)', default=0.0, digits=(3, 2))
    
    tax_ids = fields.Many2many('account.tax', string='Taxes')
    tax_amount = fields.Monetary(string='Tax Amount', compute='_compute_amounts', 
                                 store=True, currency_field='currency_id')
    
    subtotal = fields.Monetary(string='Subtotal', compute='_compute_amounts', 
                               store=True, currency_field='currency_id')
    
    currency_id = fields.Many2one(related='order_id.currency_id', store=True)
    
    @api.depends('quantity', 'price_unit', 'discount')
    def _compute_amounts(self):
        for line in self:
            price = line.price_unit * (1 - line.discount / 100.0)
            line.subtotal = price * line.quantity
            # Tax calculation would go here
            line.tax_amount = 0.0

    @api.onchange('product_id')
    def _onchange_product_id(self):
        if self.product_id:
            self.product_name = self.product_id.name
            self.price_unit = self.product_id.discount_price or self.product_id.list_price