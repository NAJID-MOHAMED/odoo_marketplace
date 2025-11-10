# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError

class MarketplaceCategory(models.Model):
    """Product categories for marketplace"""
    _name = 'marketplace.category'
    _description = 'Marketplace Category'
    _parent_name = 'parent_id'
    _parent_store = True
    _rec_name = 'complete_name'
    _order = 'complete_name'

    name = fields.Char(string='Category Name', required=True, translate=True, index=True)
    complete_name = fields.Char(
        string='Complete Name',
        compute='_compute_complete_name',
        recursive=True,
        store=True
    )
    parent_id = fields.Many2one(
        'marketplace.category',
        string='Parent Category',
        ondelete='restrict',
        index=True
    )
    parent_path = fields.Char(index=True)
    child_id = fields.One2many('marketplace.category', 'parent_id', string='Child Categories')
    
    description = fields.Text(string='Description', translate=True)
    image = fields.Binary(string='Category Image', attachment=True)
    
    product_ids = fields.One2many('marketplace.product', 'category_id', string='Products')
    product_count = fields.Integer(string='Product Count', compute='_compute_product_count')
    
    # Link to standard product category
    product_categ_id = fields.Many2one('product.category', string='Product Category')
    
    active = fields.Boolean(string='Active', default=True)
    sequence = fields.Integer(string='Sequence', default=10)
    
    # SEO
    meta_title = fields.Char(string='Meta Title')
    meta_description = fields.Text(string='Meta Description')
    
    _sql_constraints = [
        ('name_unique', 'UNIQUE(name, parent_id)', 'Category name must be unique per level!'),
    ]

    @api.depends('name', 'parent_id.complete_name')
    def _compute_complete_name(self):
        for category in self:
            if category.parent_id:
                category.complete_name = f'{category.parent_id.complete_name} / {category.name}'
            else:
                category.complete_name = category.name

    @api.depends('product_ids')
    def _compute_product_count(self):
        for category in self:
            category.product_count = len(category.product_ids)

    @api.constrains('parent_id')
    def _check_parent_id(self):
        if not self._check_recursion():
            raise ValidationError(_('You cannot create recursive categories.'))

    def action_view_products(self):
        self.ensure_one()
        return {
            'name': _('Products'),
            'type': 'ir.actions.act_window',
            'res_model': 'marketplace.product',
            'view_mode': 'tree,form',
            'domain': [('category_id', '=', self.id)],
            'context': {'default_category_id': self.id},
        }