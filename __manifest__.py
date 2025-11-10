# -*- coding: utf-8 -*-
{
    'name': 'Marketplace - Commerce Platform',
    'version': '17.0.1.0.0',
    'category': 'Sales/eCommerce',
    'summary': 'Online marketplace connecting vendors and customers',
    'description': """
        Marketplace Platform for Odoo 17
        ================================
        
        Features:
        * Vendor management with approval workflow
        * Product catalog with categories
        * Customer orders and checkout
        * Commission management
        * Multi-vendor analytics
        * Portal access for vendors and customers
        * Email notifications
        * PDF reports
        * REST API endpoints
        * Payment integration ready
        * Product reviews and ratings
    """,
    'author': 'Your Company',
    'website': 'https://www.yourcompany.com',
    'license': 'LGPL-3',
    'depends': [
        'base',
        'mail',
        'portal',
        'website',
        'sale_management',
        'stock',
        'account',
        'contacts',
        'product',
        'web',
    ],
    'data': [
        # Security
        'security/marketplace_security.xml',
        'security/ir.model.access.csv',
        
        # Data
        'data/marketplace_sequence.xml',
        'data/marketplace_email_template.xml',
        'data/marketplace_demo.xml',
        
        # Views
        'views/marketplace_vendor_views.xml',
        'views/marketplace_product_views.xml',
        'views/marketplace_order_views.xml',
        'views/marketplace_category_views.xml',
        'views/marketplace_commission_views.xml',
        'views/marketplace_review_views.xml',
        'views/marketplace_dashboard_views.xml',
        'views/marketplace_menus.xml',
        
        # Portal
        'views/portal_vendor_templates.xml',
        'views/portal_customer_templates.xml',
        
        # Reports
        'report/marketplace_report_templates.xml',
        'report/marketplace_reports.xml',
        
        # Wizards
        'wizard/marketplace_mass_confirm_wizard_views.xml',
        'wizard/marketplace_vendor_payout_wizard_views.xml',
    ],
    # 'demo': [
    #     'data/marketplace_demo.xml',
    # ],
    'assets': {
        'web.assets_backend': [
            'marketplace/static/src/css/marketplace_backend.css',
            'marketplace/static/src/js/marketplace_dashboard.js',
        ],
        'web.assets_frontend': [
            'marketplace/static/src/css/marketplace_portal.css',
            'marketplace/static/src/js/marketplace_portal.js',
        ],
    },
    'images': ['static/description/banner.png'],
    'installable': True,
    'application': True,
    'auto_install': False,
    'post_init_hook': 'post_init_hook',
}