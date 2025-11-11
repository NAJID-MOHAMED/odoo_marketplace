# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import UserError

class MarketplaceVendorPayoutWizard(models.TransientModel):
	"""Wizard for creating vendor payouts"""
	_name = 'marketplace.vendor.payout.wizard'
	_description = 'Vendor Payout Wizard'

	vendor_id = fields.Many2one(
		'marketplace.vendor',
		string='Vendor',
		required=True
	)
    
	commission_ids = fields.Many2many(
		'marketplace.commission',
		string='Commissions',
		domain="[('vendor_id', '=', vendor_id), ('state', '=', 'confirmed'), ('payout_id', '=', False)]"
	)
    
	total_amount = fields.Monetary(
		string='Total Amount',
		compute='_compute_total_amount',
		currency_field='currency_id'
	)
    
	currency_id = fields.Many2one(
		'res.currency',
		string='Currency',
		default=lambda self: self.env.company.currency_id
	)
    
	payout_date = fields.Date(
		string='Payout Date',
		default=fields.Date.context_today,
		required=True
	)
    
	payment_method = fields.Selection([
		('bank', 'Bank Transfer'),
		('check', 'Check'),
		('cash', 'Cash'),
	], string='Payment Method', default='bank', required=True)
    
	notes = fields.Text(string='Notes')

	@api.depends('commission_ids')
	def _compute_total_amount(self):
		for wizard in self:
			wizard.total_amount = sum(wizard.commission_ids.mapped('vendor_amount'))

	@api.onchange('vendor_id')
	def _onchange_vendor_id(self):
		"""Load unpaid commissions for vendor"""
		if self.vendor_id:
			unpaid_commissions = self.env['marketplace.commission'].search([
				('vendor_id', '=', self.vendor_id.id),
				('state', '=', 'confirmed'),
				('payout_id', '=', False)
			])
			self.commission_ids = [(6, 0, unpaid_commissions.ids)]

	def action_create_payout(self):
		"""Create payout record"""
		self.ensure_one()
        
		if not self.commission_ids:
			raise UserError(_('Please select at least one commission to include in the payout'))
        
		# Create payout
		payout_vals = {
			'vendor_id': self.vendor_id.id,
			'payout_date': self.payout_date,
			'payment_method': self.payment_method,
			'notes': self.notes,
		}
        
		payout = self.env['marketplace.payout'].create(payout_vals)
        
		# Link commissions to payout
		self.commission_ids.write({'payout_id': payout.id})
        
		return {
			'type': 'ir.actions.act_window',
			'res_model': 'marketplace.payout',
			'res_id': payout.id,
			'view_mode': 'form',
			'target': 'current',
		}

