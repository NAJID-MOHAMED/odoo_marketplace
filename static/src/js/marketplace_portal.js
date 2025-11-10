/** @odoo-module **/

odoo.define('marketplace.portal', function (require) {
    'use strict';

    var publicWidget = require('web.public.widget');
    var core = require('web.core');
    var ajax = require('web.ajax');

    var _t = core._t;

    /**
     * Product Filter Widget
     */
    publicWidget.registry.MarketplaceProductFilter = publicWidget.Widget.extend({
        selector: '.o_marketplace_product_filter',
        events: {
            'change select[name="category"]': '_onCategoryChange',
            'change select[name="sort"]': '_onSortChange',
            'input input[name="search"]': '_onSearchChange',
        },

        _onCategoryChange: function (ev) {
            var category = $(ev.currentTarget).val();
            this._updateProducts({category: category});
        },

        _onSortChange: function (ev) {
            var sort = $(ev.currentTarget).val();
            this._updateProducts({sort: sort});
        },

        _onSearchChange: function (ev) {
            clearTimeout(this.searchTimeout);
            var search = $(ev.currentTarget).val();
            
            this.searchTimeout = setTimeout(() => {
                this._updateProducts({search: search});
            }, 500);
        },

        _updateProducts: function (params) {
            var currentUrl = new URL(window.location.href);
            Object.keys(params).forEach(key => {
                if (params[key]) {
                    currentUrl.searchParams.set(key, params[key]);
                } else {
                    currentUrl.searchParams.delete(key);
                }
            });
            window.location.href = currentUrl.toString();
        },
    });

    /**
     * Add to Cart Widget
     */
    publicWidget.registry.MarketplaceAddToCart = publicWidget.Widget.extend({
        selector: '.o_marketplace_add_to_cart',
        events: {
            'click': '_onAddToCart',
        },

        _onAddToCart: function (ev) {
            ev.preventDefault();
            var $btn = $(ev.currentTarget);
            var productId = $btn.data('product-id');
            var quantity = $btn.closest('.o_product_card').find('input[name="quantity"]').val() || 1;

            $btn.prop('disabled', true).text(_t('Adding...'));

            ajax.jsonRpc('/shop/cart/update_json', 'call', {
                product_id: productId,
                add_qty: quantity,
            }).then(function (data) {
                if (data.cart_quantity) {
                    $('.o_cart_quantity').text(data.cart_quantity);
                    $btn.text(_t('Added!')).addClass('btn-success');
                    
                    setTimeout(function () {
                        $btn.text(_t('Add to Cart')).removeClass('btn-success').prop('disabled', false);
                    }, 2000);
                }
            }).catch(function (error) {
                console.error('Error adding to cart:', error);
                $btn.text(_t('Error')).addClass('btn-danger');
                setTimeout(function () {
                    $btn.text(_t('Add to Cart')).removeClass('btn-danger').prop('disabled', false);
                }, 2000);
            });
        },
    });

    /**
     * Product Rating Widget
     */
    publicWidget.registry.MarketplaceProductRating = publicWidget.Widget.extend({
        selector: '.o_marketplace_rating',
        events: {
            'click .o_rating_star': '_onStarClick',
        },

        start: function () {
            this._super.apply(this, arguments);
            this._updateStars();
        },

        _onStarClick: function (ev) {
            var $star = $(ev.currentTarget);
            var rating = $star.data('rating');
            this.$('input[name="rating"]').val(rating);
            this._updateStars(rating);
        },

        _updateStars: function (rating) {
            rating = rating || this.$('input[name="rating"]').val() || 0;
            this.$('.o_rating_star').each(function (index) {
                $(this).toggleClass('fa-star', index < rating)
                       .toggleClass('fa-star-o', index >= rating);
            });
        },
    });

    /**
     * Order Tracking Widget
     */
    publicWidget.registry.MarketplaceOrderTracking = publicWidget.Widget.extend({
        selector: '.o_marketplace_order_tracking',

        start: function () {
            this._super.apply(this, arguments);
            this._updateTrackingStatus();
        },

        _updateTrackingStatus: function () {
            var state = this.$el.data('order-state');
            var states = ['draft', 'confirmed', 'processing', 'shipped', 'delivered', 'done'];
            var currentIndex = states.indexOf(state);

            this.$('.o_tracking_step').each(function (index) {
                $(this).toggleClass('active', index <= currentIndex)
                       .toggleClass('completed', index < currentIndex);
            });
        },
    });

    return {
        MarketplaceProductFilter: publicWidget.registry.MarketplaceProductFilter,
        MarketplaceAddToCart: publicWidget.registry.MarketplaceAddToCart,
        MarketplaceProductRating: publicWidget.registry.MarketplaceProductRating,
        MarketplaceOrderTracking: publicWidget.registry.MarketplaceOrderTracking,
    };
});