# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError, UserError
import logging

_logger = logging.getLogger(__name__)


class MarketplaceVendor(models.Model):
    """
    Vendor model representing sellers on the marketplace platform.
    Manages vendor registration, approval, and performance metrics.
    """
    _name = 'marketplace.vendor'
    _description = 'Marketplace Vendor'
    _inherit = ['mail.thread', 'mail.activity.mixin', 'portal.mixin']
    _order = 'create_date desc'
    _rec_name = 'display_name'

    # Basic Information
    name = fields.Char(
        string='Vendor Name',
        required=True,
        tracking=True,
        index=True,
        help="Legal name of the vendor"
    )
    code = fields.Char(
        string='Vendor Code',
        required=True,
        readonly=True,
        copy=False,
        default='/',
        index=True,
        help="Unique vendor identification code"
    )
    partner_id = fields.Many2one(
        'res.partner',
        string='Related Partner',
        required=True,
        ondelete='restrict',
        tracking=True,
        help="Contact information for the vendor"
    )
    user_id = fields.Many2one(
        'res.users',
        string='Vendor User',
        tracking=True,
        help="User account for vendor portal access"
    )
    
    # Contact Details (Related fields)
    email = fields.Char(related='partner_id.email', string='Email', store=True)
    phone = fields.Char(related='partner_id.phone', string='Phone', store=True)
    mobile = fields.Char(related='partner_id.mobile', string='Mobile', store=True)
    website = fields.Char(related='partner_id.website', string='Website', store=True)
    street = fields.Char(related='partner_id.street', string='Street')
    city = fields.Char(related='partner_id.city', string='City')
    state_id = fields.Many2one(related='partner_id.state_id', string='State')
    country_id = fields.Many2one(related='partner_id.country_id', string='Country')
    zip = fields.Char(related='partner_id.zip', string='Zip')
    
    # Vendor Details
    business_type = fields.Selection([
        ('individual', 'Individual'),
        ('company', 'Company'),
        ('partnership', 'Partnership'),
    ], string='Business Type', required=True, default='company', tracking=True)
    
    tax_id = fields.Char(string='Tax ID', tracking=True, help="Tax identification number")
    registration_number = fields.Char(string='Registration Number', tracking=True)
    
    description = fields.Html(
        string='Description',
        help="Detailed description of the vendor's business"
    )
    
    # Images
    logo = fields.Binary(string='Logo', attachment=True)
    logo_filename = fields.Char(string='Logo Filename')
    banner_image = fields.Binary(string='Banner Image', attachment=True)
    banner_filename = fields.Char(string='Banner Filename')
    
    # Status and Workflow
    state = fields.Selection([
        ('draft', 'Draft'),
        ('pending', 'Pending Approval'),
        ('approved', 'Approved'),
        ('suspended', 'Suspended'),
        ('rejected', 'Rejected'),
    ], string='Status', default='draft', required=True, tracking=True, 
       help="Current vendor registration status")
    
    active = fields.Boolean(string='Active', default=True, tracking=True)
    
    # Commission Settings
    commission_type = fields.Selection([
        ('percentage', 'Percentage'),
        ('fixed', 'Fixed Amount'),
    ], string='Commission Type', default='percentage', required=True)
    
    commission_rate = fields.Float(
        string='Commission Rate (%)',
        digits='Product Price',
        default=10.0,
        help="Commission percentage on sales"
    )
    
    fixed_commission = fields.Monetary(
        string='Fixed Commission',
        currency_field='currency_id',
        help="Fixed commission amount per sale"
    )
    
    currency_id = fields.Many2one(
        'res.currency',
        string='Currency',
        default=lambda self: self.env.company.currency_id
    )
    
    # Dates
    registration_date = fields.Date(
        string='Registration Date',
        default=fields.Date.context_today,
        tracking=True
    )
    approved_date = fields.Date(string='Approved Date', readonly=True, tracking=True)
    approved_by = fields.Many2one('res.users', string='Approved By', readonly=True)
    
    # Relations
    product_ids = fields.One2many(
        'marketplace.product',
        'vendor_id',
        string='Products'
    )
    order_ids = fields.One2many(
        'marketplace.order',
        'vendor_id',
        string='Orders'
    )
    commission_ids = fields.One2many(
        'marketplace.commission',
        'vendor_id',
        string='Commissions'
    )
    payout_ids = fields.One2many(
        'marketplace.payout',
        'vendor_id',
        string='Payouts'
    )
    review_ids = fields.One2many(
        'marketplace.review',
        'vendor_id',
        string='Reviews'
    )
    
    # Computed Fields - Statistics
    product_count = fields.Integer(
        string='Product Count',
        compute='_compute_statistics',
        store=True
    )
    order_count = fields.Integer(
        string='Order Count',
        compute='_compute_statistics',
        store=True
    )
    total_sales = fields.Monetary(
        string='Total Sales',
        compute='_compute_statistics',
        store=True,
        currency_field='currency_id'
    )
    total_commission = fields.Monetary(
        string='Total Commission',
        compute='_compute_statistics',
        store=True,
        currency_field='currency_id'
    )
    pending_payout = fields.Monetary(
        string='Pending Payout',
        compute='_compute_payout_amounts',
        currency_field='currency_id'
    )
    paid_amount = fields.Monetary(
        string='Paid Amount',
        compute='_compute_payout_amounts',
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
    
    # Display name
    display_name = fields.Char(
        string='Display Name',
        compute='_compute_display_name',
        store=True
    )
    
    # Bank Details
    bank_name = fields.Char(string='Bank Name')
    bank_account_number = fields.Char(string='Account Number')
    bank_account_name = fields.Char(string='Account Name')
    bank_swift_code = fields.Char(string='SWIFT/BIC Code')
    
    # Notes
    notes = fields.Text(string='Internal Notes')
    rejection_reason = fields.Text(string='Rejection Reason', tracking=True)
    
    # SQL Constraints
    _sql_constraints = [
        ('code_unique', 'UNIQUE(code)', 'Vendor code must be unique!'),
        ('commission_rate_positive', 'CHECK(commission_rate >= 0)', 
         'Commission rate must be positive!'),
    ]

    @api.model
    def create(self, vals):
        """Override create to generate sequence code"""
        if vals.get('code', '/') == '/':
            vals['code'] = self.env['ir.sequence'].next_by_code('marketplace.vendor') or '/'
        
        vendor = super(MarketplaceVendor, self).create(vals)
        
        # Send registration email
        if vendor.state == 'draft':
            vendor._send_registration_email()
        
        _logger.info(f'New vendor created: {vendor.code} - {vendor.name}')
        return vendor

    def write(self, vals):
        """Override write to track state changes"""
        old_state = self.state
        res = super(MarketplaceVendor, self).write(vals)
        
        if 'state' in vals and vals['state'] != old_state:
            self._handle_state_change(old_state, vals['state'])
        
        return res

    def unlink(self):
        """Prevent deletion of vendors with orders"""
        for vendor in self:
            if vendor.order_count > 0:
                raise UserError(_(
                    'Cannot delete vendor %s because they have %d orders. '
                    'Please archive instead.'
                ) % (vendor.name, vendor.order_count))
        return super(MarketplaceVendor, self).unlink()

    @api.depends('name', 'code')
    def _compute_display_name(self):
        """Compute display name"""
        for vendor in self:
            vendor.display_name = f'[{vendor.code}] {vendor.name}'

    @api.depends('product_ids', 'order_ids', 'commission_ids')
    def _compute_statistics(self):
        """Compute vendor statistics"""
        for vendor in self:
            vendor.product_count = len(vendor.product_ids)
            vendor.order_count = len(vendor.order_ids.filtered(
                lambda o: o.state in ['confirmed', 'processing', 'delivered', 'done']
            ))
            
            completed_orders = vendor.order_ids.filtered(lambda o: o.state == 'done')
            vendor.total_sales = sum(completed_orders.mapped('amount_total'))
            vendor.total_commission = sum(vendor.commission_ids.filtered(
                lambda c: c.state == 'paid'
            ).mapped('commission_amount'))

    @api.depends('commission_ids.state', 'commission_ids.commission_amount')
    def _compute_payout_amounts(self):
        """Compute pending and paid payout amounts"""
        for vendor in self:
            vendor.pending_payout = sum(vendor.commission_ids.filtered(
                lambda c: c.state in ['draft', 'confirmed']
            ).mapped('vendor_amount'))
            
            vendor.paid_amount = sum(vendor.commission_ids.filtered(
                lambda c: c.state == 'paid'
            ).mapped('vendor_amount'))

    @api.depends('review_ids.rating')
    def _compute_rating(self):
        """Compute average rating"""
        for vendor in self:
            published_reviews = vendor.review_ids.filtered(lambda r: r.state == 'published')
            vendor.review_count = len(published_reviews)
            
            if published_reviews:
                vendor.average_rating = sum(published_reviews.mapped('rating')) / len(published_reviews)
            else:
                vendor.average_rating = 0.0

    @api.constrains('commission_rate')
    def _check_commission_rate(self):
        """Validate commission rate"""
        for vendor in self:
            if vendor.commission_type == 'percentage' and (
                vendor.commission_rate < 0 or vendor.commission_rate > 100
            ):
                raise ValidationError(_('Commission rate must be between 0 and 100%'))

    @api.onchange('partner_id')
    def _onchange_partner_id(self):
        """Update fields when partner changes"""
        if self.partner_id:
            self.name = self.partner_id.name
            if not self.user_id and self.partner_id.user_ids:
                self.user_id = self.partner_id.user_ids[0]

    # Action Methods
    def action_submit_approval(self):
        """Submit vendor for approval"""
        self.ensure_one()
        if self.state != 'draft':
            raise UserError(_('Only draft vendors can be submitted for approval'))
        
        self.write({'state': 'pending'})
        self._send_approval_request_email()
        
        self.message_post(
            body=_('Vendor submitted for approval'),
            subject=_('Vendor Registration Submitted')
        )

    def action_approve(self):
        """Approve vendor"""
        self.ensure_one()
        if self.state != 'pending':
            raise UserError(_('Only pending vendors can be approved'))
        
        self.write({
            'state': 'approved',
            'approved_date': fields.Date.context_today(self),
            'approved_by': self.env.user.id,
        })
        
        self._send_approval_notification()
        self._create_vendor_portal_user()
        
        self.message_post(
            body=_('Vendor approved by %s') % self.env.user.name,
            subject=_('Vendor Approved')
        )

    def action_reject(self):
        """Reject vendor"""
        self.ensure_one()
        if self.state != 'pending':
            raise UserError(_('Only pending vendors can be rejected'))
        
        self.write({'state': 'rejected'})
        self._send_rejection_notification()
        
        self.message_post(
            body=_('Vendor rejected: %s') % (self.rejection_reason or 'No reason provided'),
            subject=_('Vendor Rejected')
        )

    def action_suspend(self):
        """Suspend vendor"""
        self.ensure_one()
        self.write({'state': 'suspended', 'active': False})
        self.message_post(body=_('Vendor suspended'))

    def action_reactivate(self):
        """Reactivate suspended vendor"""
        self.ensure_one()
        self.write({'state': 'approved', 'active': True})
        self.message_post(body=_('Vendor reactivated'))

    def action_view_products(self):
        """Open vendor products"""
        self.ensure_one()
        return {
            'name': _('Products'),
            'type': 'ir.actions.act_window',
            'res_model': 'marketplace.product',
            'view_mode': 'tree,form',
            'domain': [('vendor_id', '=', self.id)],
            'context': {'default_vendor_id': self.id},
        }

    def action_view_orders(self):
        """Open vendor orders"""
        self.ensure_one()
        return {
            'name': _('Orders'),
            'type': 'ir.actions.act_window',
            'res_model': 'marketplace.order',
            'view_mode': 'tree,form',
            'domain': [('vendor_id', '=', self.id)],
            'context': {'default_vendor_id': self.id},
        }

    def action_view_commissions(self):
        """Open vendor commissions"""
        self.ensure_one()
        return {
            'name': _('Commissions'),
            'type': 'ir.actions.act_window',
            'res_model': 'marketplace.commission',
            'view_mode': 'tree,form',
            'domain': [('vendor_id', '=', self.id)],
        }

    # Private Methods
    def _handle_state_change(self, old_state, new_state):
        """Handle state change actions"""
        for vendor in self:
            _logger.info(f'Vendor {vendor.code} state changed: {old_state} -> {new_state}')

    def _send_registration_email(self):
        """Send registration confirmation email"""
        template = self.env.ref('marketplace.email_template_vendor_registration', 
                                raise_if_not_found=False)
        if template:
            template.send_mail(self.id, force_send=True)

    def _send_approval_request_email(self):
        """Send approval request to admin"""
        template = self.env.ref('marketplace.email_template_vendor_approval_request',
                                raise_if_not_found=False)
        if template:
            template.send_mail(self.id, force_send=True)

    def _send_approval_notification(self):
        """Send approval notification to vendor"""
        template = self.env.ref('marketplace.email_template_vendor_approved',
                                raise_if_not_found=False)
        if template:
            template.send_mail(self.id, force_send=True)

    def _send_rejection_notification(self):
        """Send rejection notification to vendor"""
        template = self.env.ref('marketplace.email_template_vendor_rejected',
                                raise_if_not_found=False)
        if template:
            template.send_mail(self.id, force_send=True)

    def _create_vendor_portal_user(self):
        """Create portal user for vendor if not exists"""
        self.ensure_one()
        if not self.user_id and self.partner_id:
            # Create portal user
            portal_group = self.env.ref('base.group_portal')
            vendor_group = self.env.ref('marketplace.group_marketplace_vendor')
            
            user_vals = {
                'login': self.email,
                'partner_id': self.partner_id.id,
                'groups_id': [(6, 0, [portal_group.id, vendor_group.id])],
            }
            
            try:
                user = self.env['res.users'].create(user_vals)
                self.user_id = user.id
                _logger.info(f'Portal user created for vendor: {self.code}')
            except Exception as e:
                _logger.error(f'Error creating portal user for vendor {self.code}: {str(e)}')

    def _compute_access_url(self):
        """Compute portal access URL"""
        super(MarketplaceVendor, self)._compute_access_url()
        for vendor in self:
            vendor.access_url = f'/my/vendor/{vendor.id}'