# -*- coding: utf-8 -*-
{
    'name': "Odoo MarketPlace ",
    'version': '1.0.0',
    'category': 'Sales',
    'summary': "Module base d'une marketplace multi-fournisseurs",
    'author': "Ton Nom",
    'website': "http://www.example.com",
    'license': "AGPL-3",
    'depends': ['base', 'mail'],
    'data': [
        'security/marketplace_security.xml',
        'security/ir.model.access.csv',
        'views/vendor_views.xml',
        'views/product_listing_views.xml',
        'views/order_views.xml',
        'views/menu_views.xml',
    ],
    'installable': True,
    'application': True,
    
}
