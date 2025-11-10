/** @odoo-module **/

import { registry } from "@web/core/registry";
import { Component, useState, onWillStart } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";

/**
 * Marketplace Dashboard Widget
 */
class MarketplaceDashboard extends Component {
    setup() {
        this.orm = useService("orm");
        this.action = useService("action");
        
        this.state = useState({
            stats: {
                total_vendors: 0,
                active_vendors: 0,
                total_products: 0,
                published_products: 0,
                total_orders: 0,
                total_revenue: 0,
                pending_orders: 0,
                pending_commissions: 0,
            },
            loading: true,
        });

        onWillStart(async () => {
            await this.loadDashboardData();
        });
    }

    async loadDashboardData() {
        try {
            // Load vendor stats
            const vendorStats = await this.orm.searchCount(
                "marketplace.vendor",
                [["state", "=", "approved"]]
            );
            this.state.stats.active_vendors = vendorStats;

            // Load product stats
            const productStats = await this.orm.searchCount(
                "marketplace.product",
                [["state", "=", "published"]]
            );
            this.state.stats.published_products = productStats;

            // Load order stats
            const orderStats = await this.orm.readGroup(
                "marketplace.order",
                [["state", "!=", "cancelled"]],
                ["amount_total:sum"],
                []
            );
            
            if (orderStats.length > 0) {
                this.state.stats.total_revenue = orderStats[0].amount_total;
            }

            // Load pending orders
            const pendingOrders = await this.orm.searchCount(
                "marketplace.order",
                [["state", "=", "confirmed"]]
            );
            this.state.stats.pending_orders = pendingOrders;

            this.state.loading = false;
        } catch (error) {
            console.error("Error loading dashboard data:", error);
            this.state.loading = false;
        }
    }

    openVendors() {
        this.action.doAction({
            type: "ir.actions.act_window",
            res_model: "marketplace.vendor",
            views: [[false, "list"], [false, "form"]],
            domain: [["state", "=", "approved"]],
        });
    }

    openProducts() {
        this.action.doAction({
            type: "ir.actions.act_window",
            res_model: "marketplace.product",
            views: [[false, "kanban"], [false, "list"], [false, "form"]],
            domain: [["state", "=", "published"]],
        });
    }

    openOrders() {
        this.action.doAction({
            type: "ir.actions.act_window",
            res_model: "marketplace.order",
            views: [[false, "list"], [false, "form"]],
        });
    }
}

MarketplaceDashboard.template = "marketplace.Dashboard";

// Register the dashboard
registry.category("actions").add("marketplace_dashboard", MarketplaceDashboard);