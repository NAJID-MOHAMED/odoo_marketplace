# -*- coding: utf-8 -*-

from odoo import http, _
from odoo.http import request
from odoo.addons.portal.controllers.portal import CustomerPortal, pager as portal_pager
from odoo.exceptions import AccessError, MissingError

class MarketplacePortal(CustomerPortal):
    """Portal controller for marketplace vendors and customers"""

    def _prepare_home_portal_values(self, counters):
        """Add marketplace counters to portal home"""
        values = super()._prepare_home_portal_values(counters)
        
        partner = request.env.user.partner_id
        
        # Vendor counters
        if 'vendor_product_count' in counters:
            vendor = request.env['marketplace.vendor'].search([
                ('partner_id', '=', partner.id)
            ], limit=1)
            if vendor:
                values['vendor_product_count'] = request.env['marketplace.product'].search_count([
                    ('vendor_id', '=', vendor.id)
                ])
                values['vendor_order_count'] = request.env['marketplace.order'].search_count([
                    ('vendor_id', '=', vendor.id)
                ])
        
        # Customer counters
        if 'customer_order_count' in counters:
            values['customer_order_count'] = request.env['marketplace.order'].search_count([
                ('customer_id', '=', partner.id)
            ])
        
        return values

    # Vendor Portal Routes
    @http.route(['/my/vendor', '/my/vendor/page/<int:page>'], type='http', auth="user", website=True)
    def portal_my_vendor_dashboard(self, page=1, **kw):
        """Vendor dashboard"""
        vendor = request.env['marketplace.vendor'].search([
            ('user_id', '=', request.env.user.id)
        ], limit=1)
        
        if not vendor:
            return request.render('odoo_marketplace.vendor_not_found')
        
        values = {
            'vendor': vendor,
            'page_name': 'vendor_dashboard',
        }
        
        return request.render('odoo_marketplace.portal_vendor_dashboard', values)

    @http.route(['/my/vendor/products', '/my/vendor/products/page/<int:page>'], 
                type='http', auth="user", website=True)
    def portal_my_vendor_products(self, page=1, sortby=None, filterby=None, search=None, **kw):
        """Vendor products list"""
        vendor = request.env['marketplace.vendor'].search([
            ('user_id', '=', request.env.user.id)
        ], limit=1)
        
        if not vendor:
            return request.render('odoo_marketplace.vendor_not_found')
        
        Product = request.env['marketplace.product']
        domain = [('vendor_id', '=', vendor.id)]
        
        if search:
            domain += [('name', 'ilike', search)]
        
        # Count
        product_count = Product.search_count(domain)
        
        # Pager
        pager = portal_pager(
            url="/my/vendor/products",
            total=product_count,
            page=page,
            step=self._items_per_page,
        )
        
        # Products
        products = Product.search(domain, limit=self._items_per_page, offset=pager['offset'])
        
        values = {
            'vendor': vendor,
            'products': products,
            'pager': pager,
            'page_name': 'vendor_products',
            'default_url': '/my/vendor/products',
            'search': search,
        }
        
        return request.render('odoo_marketplace.portal_vendor_products', values)

    @http.route(['/my/vendor/orders', '/my/vendor/orders/page/<int:page>'], 
                type='http', auth="user", website=True)
    def portal_my_vendor_orders(self, page=1, **kw):
        """Vendor orders list"""
        vendor = request.env['marketplace.vendor'].search([
            ('user_id', '=', request.env.user.id)
        ], limit=1)
        
        if not vendor:
            return request.render('odoo_marketplace.vendor_not_found')
        
        Order = request.env['marketplace.order']
        domain = [('vendor_id', '=', vendor.id)]
        
        order_count = Order.search_count(domain)
        
        pager = portal_pager(
            url="/my/vendor/orders",
            total=order_count,
            page=page,
            step=self._items_per_page,
        )
        
        orders = Order.search(domain, limit=self._items_per_page, offset=pager['offset'])
        
        values = {
            'vendor': vendor,
            'orders': orders,
            'pager': pager,
            'page_name': 'vendor_orders',
        }
        
        return request.render('odoo_marketplace.portal_vendor_orders', values)

    # Customer Portal Routes
    @http.route(['/my/orders', '/my/orders/page/<int:page>'], 
                type='http', auth="user", website=True)
    def portal_my_customer_orders(self, page=1, **kw):
        """Customer orders list"""
        partner = request.env.user.partner_id
        Order = request.env['marketplace.order']
        
        domain = [('customer_id', '=', partner.id)]
        order_count = Order.search_count(domain)
        
        pager = portal_pager(
            url="/my/orders",
            total=order_count,
            page=page,
            step=self._items_per_page,
        )
        
        orders = Order.search(domain, limit=self._items_per_page, offset=pager['offset'], 
                             order='create_date desc')
        
        values = {
            'orders': orders,
            'pager': pager,
            'page_name': 'customer_orders',
        }
        
        return request.render('odoo_marketplace.portal_customer_orders', values)

    @http.route(['/my/orders/<int:order_id>'], type='http', auth="user", website=True)
    def portal_order_page(self, order_id, access_token=None, **kw):
        """Single order details"""
        try:
            order_sudo = self._document_check_access('marketplace.order', order_id, access_token)
        except (AccessError, MissingError):
            return request.redirect('/my')
        
        values = {
            'order': order_sudo,
            'page_name': 'order',
        }
        
        return request.render('odoo_marketplace.portal_order_details', values)


class MarketplaceAPI(http.Controller):
    """REST API endpoints for marketplace"""

    @http.route('/api/marketplace/products', type='json', auth='public', methods=['GET'], csrf=False)
    def api_get_products(self, **kw):
        """Get published products"""
        try:
            domain = [('state', '=', 'published')]
            
            # Filters
            if kw.get('category_id'):
                domain.append(('category_id', '=', int(kw['category_id'])))
            if kw.get('vendor_id'):
                domain.append(('vendor_id', '=', int(kw['vendor_id'])))
            if kw.get('search'):
                domain.append(('name', 'ilike', kw['search']))
            
            # Pagination
            limit = int(kw.get('limit', 20))
            offset = int(kw.get('offset', 0))
            
            products = request.env['marketplace.product'].sudo().search(
                domain, limit=limit, offset=offset, order='create_date desc'
            )
            
            return {
                'success': True,
                'data': [{
                    'id': p.id,
                    'name': p.name,
                    'code': p.code,
                    'vendor': p.vendor_id.name,
                    'category': p.category_id.name,
                    'price': p.list_price,
                    'discount_price': p.discount_price if p.has_discount else None,
                    'rating': p.average_rating,
                    'stock_status': p.stock_status,
                } for p in products],
                'total': request.env['marketplace.product'].sudo().search_count(domain)
            }
        except Exception as e:
            return {'success': False, 'error': str(e)}

    @http.route('/api/marketplace/products/<int:product_id>', type='json', auth='public', methods=['GET'], csrf=False)
    def api_get_product_details(self, product_id, **kw):
        """Get product details"""
        try:
            product = request.env['marketplace.product'].sudo().browse(product_id)
            
            if not product.exists() or product.state != 'published':
                return {'success': False, 'error': 'Product not found'}
            
            return {
                'success': True,
                'data': {
                    'id': product.id,
                    'name': product.name,
                    'code': product.code,
                    'description': product.description,
                    'short_description': product.short_description,
                    'vendor': {
                        'id': product.vendor_id.id,
                        'name': product.vendor_id.name,
                        'rating': product.vendor_id.average_rating,
                    },
                    'category': product.category_id.name,
                    'price': product.list_price,
                    'discount_price': product.discount_price if product.has_discount else None,
                    'rating': product.average_rating,
                    'review_count': product.review_count,
                    'stock_status': product.stock_status,
                    'qty_available': product.qty_available,
                }
            }
        except Exception as e:
            return {'success': False, 'error': str(e)}

    @http.route('/api/marketplace/vendors', type='json', auth='public', methods=['GET'], csrf=False)
    def api_get_vendors(self, **kw):
        """Get approved vendors"""
        try:
            domain = [('state', '=', 'approved')]
            
            limit = int(kw.get('limit', 20))
            offset = int(kw.get('offset', 0))
            
            vendors = request.env['marketplace.vendor'].sudo().search(
                domain, limit=limit, offset=offset
            )
            
            return {
                'success': True,
                'data': [{
                    'id': v.id,
                    'name': v.name,
                    'code': v.code,
                    'rating': v.average_rating,
                    'product_count': v.product_count,
                } for v in vendors],
                'total': request.env['marketplace.vendor'].sudo().search_count(domain)
            }
        except Exception as e:
            return {'success': False, 'error': str(e)}

    @http.route('/api/marketplace/categories', type='json', auth='public', methods=['GET'], csrf=False)
    def api_get_categories(self, **kw):
        """Get categories"""
        try:
            categories = request.env['marketplace.category'].sudo().search([('active', '=', True)])
            
            return {
                'success': True,
                'data': [{
                    'id': c.id,
                    'name': c.name,
                    'complete_name': c.complete_name,
                    'product_count': c.product_count,
                } for c in categories]
            }
        except Exception as e:
            return {'success': False, 'error': str(e)}

    @http.route('/api/marketplace/orders/create', type='json', auth='user', methods=['POST'], csrf=False)
    def api_create_order(self, **kw):
        """Create new order (requires authentication)"""
        try:
            order_lines = kw.get('order_lines', [])
            if not order_lines:
                return {'success': False, 'error': 'No order lines provided'}
            
            # Validate products
            product_ids = [line['product_id'] for line in order_lines]
            products = request.env['marketplace.product'].sudo().browse(product_ids)
            
            if len(products) != len(product_ids):
                return {'success': False, 'error': 'Invalid product(s)'}
            
            # Group by vendor
            vendor_orders = {}
            for line in order_lines:
                product = products.filtered(lambda p: p.id == line['product_id'])
                vendor_id = product.vendor_id.id
                
                if vendor_id not in vendor_orders:
                    vendor_orders[vendor_id] = []
                vendor_orders[vendor_id].append({
                    'product_id': product.id,
                    'product_name': product.name,
                    'quantity': line['quantity'],
                    'price_unit': product.discount_price or product.list_price,
                })
            
            # Create orders per vendor
            created_orders = []
            for vendor_id, lines in vendor_orders.items():
                order_vals = {
                    'customer_id': request.env.user.partner_id.id,
                    'vendor_id': vendor_id,
                    'order_line_ids': [(0, 0, line) for line in lines],
                    'shipping_address_id': kw.get('shipping_address_id'),
                    'payment_method': kw.get('payment_method', 'card'),
                }
                
                order = request.env['marketplace.order'].sudo().create(order_vals)
                created_orders.append(order.id)
            
            return {
                'success': True,
                'order_ids': created_orders,
                'message': f'{len(created_orders)} order(s) created successfully'
            }
        except Exception as e:
            return {'success': False, 'error': str(e)}