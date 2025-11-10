# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import UserError

class MarketplaceMassConfirmWizard(models.TransientModel):
    """Wizard for batch order confirmation"""
    _name = 'marketplace.mass.confirm.wizard'
    _description = 'Mass Order Confirmation Wizard'

    order_ids = fields.Many2many(
        'marketplace.order',
        string='Orders to Confirm',
        domain="[('state', '=', 'draft')]"
    )
    
    check_stock = fields.Boolean(
        string='Check Stock Availability',
        default=True,
        help="Verify stock before confirming orders"
    )
    
    send_emails = fields.Boolean(
        string='Send Confirmation Emails',
        default=True
    )

    @api.model
    def default_get(self, fields_list):
        """Get default values from context"""
        res = super(MarketplaceMassConfirmWizard, self).default_get(fields_list)
        
        if self.env.context.get('active_ids'):
            orders = self.env['marketplace.order'].browse(
                self.env.context.get('active_ids')
            ).filtered(lambda o: o.state == 'draft')
            res['order_ids'] = [(6, 0, orders.ids)]
        
        return res

    def action_confirm_orders(self):
        """Confirm selected orders"""
        self.ensure_one()
        
        if not self.order_ids:
            raise UserError(_('Please select at least one order to confirm'))
        
        confirmed_count = 0
        failed_orders = []
        
        for order in self.order_ids:
            try:
                # Check stock if required
                if self.check_stock:
                    for line in order.order_line_ids:
                        if line.product_id.qty_available < line.quantity:
                            failed_orders.append(
                                f"{order.name}: Insufficient stock for {line.product_id.name}"
                            )
                            continue
                
                # Confirm order
                order.action_confirm()
                confirmed_count += 1
                
            except Exception as e:
                failed_orders.append(f"{order.name}: {str(e)}")
        
        # Prepare result message
        message = f"Successfully confirmed {confirmed_count} order(s)."
        if failed_orders:
            message += f"\n\nFailed orders:\n" + "\n".join(failed_orders)
        
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Mass Confirmation Complete'),
                'message': message,
                'type': 'success' if not failed_orders else 'warning',
                'sticky': True if failed_orders else False,
            }
        }