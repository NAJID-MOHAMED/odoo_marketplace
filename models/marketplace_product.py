# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError, UserError
import logging

_logger = logging.getLogger(__name__)


class MarketplaceProduct(models.Model):
    """
    Product model for marketplace items.
    Links to product.template with vendor-specific information.
    """
    _name = 'marketplace.product'
    _description = 'Marketplace Product'
    _inherit = ['mail.thread', 'mail.activity.mixin', 'image.mixin']
    _order = 'create_date desc'

    # Basic Information
    name = fields.Char(string='Product Name', required=True, tracking=True, index=True)
    code = fields.Char(
        string='Product Code',
        required=True,
        readonly=True,
        copy=False,
        default='/',
        index=True
    )
    
    # Vendor
    vendor_id = fields.Many2one(
        'marketplace.vendor',
        string='Vendor',
        required=True,
        ondelete='restrict',
        tracking=True,
        index=True
    )
    
    # Product Template Link
    product_tmpl_id = fields.Many2one(
        'product.template',
        string='Product Template',
        ondelete='restrict',
        help="Link to standard Odoo product"
    )
    
    # Category
    category_id = fields.Many2one(
        'marketplace.category',
        string='Category',
        required=True,
        ondelete='restrict',
        tracking=True
    )
    
    # Description
    description = fields.Html(string='Description', tracking=True)
    short_description = fields.Text(string='Short Description')
    
    # Pricing
    list_price = fields.Monetary(
        string='Sale Price',
        currency_field='currency_id',
        required=True,
        tracking=True,
        digits='Product Price'
    )
    cost_price = fields.Monetary(
        string='Cost Price',
        currency_field='currency_id',
        digits='Product Price'
    )
    currency_id = fields.Many2one(
        'res.currency',
        string='Currency',
        default=lambda self: self.env.company.currency_id
    )
    
    # Discount
    has_discount = fields.Boolean(string='Has Discount', default=False)
    discount_percentage = fields.Float(string='Discount (%)', digits=(3, 2))
    discount_price = fields.Monetary(
        string='Discounted Price',
        compute='_compute_discount_price',
        store=True,
        currency_field='currency_id'
    )
    
    # Stock Management
    qty_available = fields.Float(
        string='Quantity On Hand',
        digits='Product Unit of Measure',
        default=0.0
    )
    stock_management = fields.Selection([
        ('manual', 'Manual'),
        ('automatic', 'Automatic (via Odoo Stock)'),
    ], string='Stock Management', default='manual', required=True)
    
    low_stock_threshold = fields.Float(
        string='Low Stock Alert',
        digits='Product Unit of Measure',
        default=10.0
    )
    is_low_stock = fields.Boolean(
        string='Low Stock',
        compute='_compute_stock_status',
        store=True
    )
    stock_status = fields.Selection([
        ('in_stock', 'In Stock'),
        ('low_stock', 'Low Stock'),
        ('out_of_stock', 'Out of Stock'),
    ], string='Stock Status', compute='_compute_stock_status', store=True)
    
    # Product Specifications
    weight = fields.Float(string='Weight (kg)', digits=(8, 3))
    length = fields.Float(string='Length (cm)', digits=(8, 2))
    width = fields.Float(string='Width (cm)', digits=(8, 2))
    height = fields.Float(string='Height (cm)', digits=(8, 2))
    
    # Product Type
    product_type = fields.Selection([
        ('physical', 'Physical Product'),
        ('digital', 'Digital Product'),
        ('service', 'Service'),
    ], string='Product Type', default='physical', required=True)
    
    digital_file = fields.Binary(string='Digital File', attachment=True)
    digital_filename = fields.Char(string='Digital Filename')
    
    # Status
    state = fields.Selection([
        ('draft', 'Draft'),
        ('pending', 'Pending Approval'),
        ('published', 'Published'),
        ('unpublished', 'Unpublished'),
        ('rejected', 'Rejected'),
    ], string='Status', default='draft', required=True, tracking=True)
    
    active = fields.Boolean(string='Active', default=True)
    featured = fields.Boolean(string='Featured Product', default=False, tracking=True)
    
    # SEO
    meta_title = fields.Char(string='Meta Title')
    meta_description = fields.Text(string='Meta Description')
    meta_keywords = fields.Char(string='Meta Keywords')
    
    # Statistics
    order_line_ids = fields.One2many(
        'marketplace.order.line',
        'product_id',
        string='Order Lines'
    )
    review_ids = fields.One2many(
        'marketplace.review',
        'product_id',
        string='Reviews'
    )
    
    # Computed Statistics
    sales_count = fields.Integer(
        string='Sales Count',
        compute='_compute_sales_stats',
        store=True
    )
    total_sold_qty = fields.Float(
        string='Total Sold Quantity',
        compute='_compute_sales_stats',
        store=True,
        digits='Product Unit of Measure'
    )
    total_revenue = fields.Monetary(
        string='Total Revenue',
        compute='_compute_sales_stats',
        store=True,
        currency_field='currency_id'
    )
    average_rating = fields.Float(
        string='Average Rating',
        compute='_compute_rating',
        store=True,
        digits=(3, 2)
    )
    review_count = fields.Integer(
        string='Review Count',
        compute='_compute_rating',
        store=True
    )
    
    # Dates
    published_date = fields.Datetime(string='Published Date', readonly=True)
    
    # Tags
    tag_ids = fields.Many2many(
        'marketplace.product.tag',
        string='Tags'
    )
    
    # Notes
    internal_notes = fields.Text(string='Internal Notes')
    rejection_reason = fields.Text(string='Rejection Reason')
    
    _sql_constraints = [
        ('code_unique', 'UNIQUE(code)', 'Product code must be unique!'),
        ('list_price_positive', 'CHECK(list_price >= 0)', 'Sale price must be positive!'),
        ('qty_positive', 'CHECK(qty_available >= 0)', 'Quantity cannot be negative!'),
    ]

    @api.model
    def create(self, vals):
        """Generate sequence code"""
        if vals.get('code', '/') == '/':
            vals['code'] = self.env['ir.sequence'].next_by_code('marketplace.product') or '/'
        
        product = super(MarketplaceProduct, self).create(vals)
        _logger.info(f'New product created: {product.code} - {product.name}')
        return product

    def write(self, vals):
        """Track state changes"""
        old_state = self.state
        res = super(MarketplaceProduct, self).write(vals)
        
        if 'state' in vals and vals['state'] != old_state:
            self._handle_state_change(old_state, vals['state'])
        
        return res

    def unlink(self):
        """Prevent deletion if product has orders"""
        for product in self:
            if product.sales_count > 0:
                raise UserError(_(
                    'Cannot delete product %s because it has %d sales. '
                    'Please unpublish instead.'
                ) % (product.name, product.sales_count))
        return super(MarketplaceProduct, self).unlink()

    @api.depends('list_price', 'has_discount', 'discount_percentage')
    def _compute_discount_price(self):
        """Compute discounted price"""
        for product in self:
            if product.has_discount and product.discount_percentage > 0:
                product.discount_price = product.list_price * (1 - product.discount_percentage / 100)
            else:
                product.discount_price = product.list_price

    @api.depends('qty_available', 'low_stock_threshold')
    def _compute_stock_status(self):
        """Compute stock status"""
        for product in self:
            if product.qty_available <= 0:
                product.stock_status = 'out_of_stock'
                product.is_low_stock = False
            elif product.qty_available <= product.low_stock_threshold:
                product.stock_status = 'low_stock'
                product.is_low_stock = True
            else:
                product.stock_status = 'in_stock'
                product.is_low_stock = False

    @api.depends('order_line_ids', 'order_line_ids.order_id.state')
    def _compute_sales_stats(self):
        """Compute sales statistics"""
        for product in self:
            completed_lines = product.order_line_ids.filtered(
                lambda l: l.order_id.state == 'done'
            )
            product.sales_count = len(completed_lines)
            product.total_sold_qty = sum(completed_lines.mapped('quantity'))
            product.total_revenue = sum(completed_lines.mapped('subtotal'))

    @api.depends('review_ids.rating', 'review_ids.state')
    def _compute_rating(self):
        """Compute average rating"""
        for product in self:
            published_reviews = product.review_ids.filtered(lambda r: r.state == 'published')
            product.review_count = len(published_reviews)
            
            if published_reviews:
                product.average_rating = sum(published_reviews.mapped('rating')) / len(published_reviews)
            else:
                product.average_rating = 0.0

    @api.constrains('discount_percentage')
    def _check_discount_percentage(self):
        """Validate discount percentage"""
        for product in self:
            if product.has_discount and (
                product.discount_percentage < 0 or product.discount_percentage > 100
            ):
                raise ValidationError(_('Discount percentage must be between 0 and 100'))

    @api.onchange('has_discount')
    def _onchange_has_discount(self):
        """Reset discount when disabled"""
        if not self.has_discount:
            self.discount_percentage = 0.0

    @api.onchange('vendor_id')
    def _onchange_vendor_id(self):
        """Set default currency from vendor"""
        if self.vendor_id:
            self.currency_id = self.vendor_id.currency_id

    # Action Methods
    def action_submit_approval(self):
        """Submit for approval"""
        self.ensure_one()
        if self.state != 'draft':
            raise UserError(_('Only draft products can be submitted'))
        
        self.write({'state': 'pending'})
        self.message_post(body=_('Product submitted for approval'))

    def action_approve(self):
        """Approve product"""
        self.ensure_one()
        if self.state != 'pending':
            raise UserError(_('Only pending products can be approved'))
        
        self.write({
            'state': 'published',
            'published_date': fields.Datetime.now(),
        })
        
        self._create_product_template()
        self.message_post(body=_('Product approved and published'))

    def action_reject(self):
        """Reject product"""
        self.ensure_one()
        self.write({'state': 'rejected'})
        self.message_post(body=_('Product rejected'))

    def action_publish(self):
        """Publish product"""
        self.ensure_one()
        self.write({
            'state': 'published',
            'published_date': fields.Datetime.now(),
        })
        self.message_post(body=_('Product published'))

    def action_unpublish(self):
        """Unpublish product"""
        self.ensure_one()
        self.write({'state': 'unpublished'})
        self.message_post(body=_('Product unpublished'))

    def action_view_orders(self):
        """View product orders"""
        self.ensure_one()
        return {
            'name': _('Orders'),
            'type': 'ir.actions.act_window',
            'res_model': 'marketplace.order.line',
            'view_mode': 'tree,form',
            'domain': [('product_id', '=', self.id)],
        }

    def action_view_reviews(self):
        """View product reviews"""
        self.ensure_one()
        return {
            'name': _('Reviews'),
            'type': 'ir.actions.act_window',
            'res_model': 'marketplace.review',
            'view_mode': 'tree,form',
            'domain': [('product_id', '=', self.id)],
            'context': {'default_product_id': self.id},
        }

    def update_stock(self, quantity, operation='add'):
        """Update product stock"""
        self.ensure_one()
        if operation == 'add':
            self.qty_available += quantity
        elif operation == 'subtract':
            if self.qty_available < quantity:
                raise UserError(_('Insufficient stock for %s') % self.name)
            self.qty_available -= quantity
        
        self.message_post(body=_('Stock %s: %s units') % (operation, quantity))

    # Private Methods
    def _handle_state_change(self, old_state, new_state):
        """Handle state changes"""
        for product in self:
            _logger.info(f'Product {product.code} state: {old_state} -> {new_state}')

    def _create_product_template(self):
        """Create or link to product.template"""
        self.ensure_one()
        if not self.product_tmpl_id:
            vals = {
                'name': self.name,
                'list_price': self.list_price,
                'standard_price': self.cost_price or 0.0,
                'type': 'product' if self.product_type == 'physical' else 'service',
                'categ_id': self.category_id.product_categ_id.id if self.category_id.product_categ_id else False,
                'description': self.description,
                'weight': self.weight,
            }
            product_tmpl = self.env['product.template'].create(vals)
            self.product_tmpl_id = product_tmpl.id


class MarketplaceProductTag(models.Model):
    """Product tags for categorization"""
    _name = 'marketplace.product.tag'
    _description = 'Product Tag'
    _order = 'name'

    name = fields.Char(string='Tag Name', required=True, translate=True)
    color = fields.Integer(string='Color Index')
    product_ids = fields.Many2many('marketplace.product', string='Products')
    
    _sql_constraints = [
        ('name_unique', 'UNIQUE(name)', 'Tag name must be unique!'),
    ]