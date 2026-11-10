# Copyright 2026 Scalizer (https://www.scalizer.fr)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import models


class PurchaseOrderLine(models.Model):
    _inherit = "purchase.order.line"

    def _prepare_purchase_order_line_from_procurement(
        self,
        product_id,
        product_qty,
        product_uom,
        location_dest_id,
        name,
        origin,
        company_id,
        values,
        po,
    ):
        """Set the analytic distribution of the procurement on the new line.

        The distribution is set in the procurement values by ``stock_analytic``
        from the stock move at the origin of the need.

        :return: the values of the purchase order line to create
        :rtype: dict
        """
        res = super()._prepare_purchase_order_line_from_procurement(
            product_id,
            product_qty,
            product_uom,
            location_dest_id,
            name,
            origin,
            company_id,
            values,
            po,
        )
        analytic_distribution = values.get("analytic_distribution")
        if analytic_distribution:
            res["analytic_distribution"] = analytic_distribution
        return res

    def _find_candidate(
        self,
        product_id,
        product_qty,
        product_uom,
        location_id,
        name,
        origin,
        company_id,
        values,
    ):
        """Merge a procurement only in a line having the same analytic.

        When the procurement carries an analytic distribution, only the lines
        with the same distribution are candidates, so the analytic of a need is
        never lost in a line of another one.

        :return: the line where the procurement can be merged, if any
        :rtype: recordset
        """
        analytic_distribution = values.get("analytic_distribution")
        lines = self
        if analytic_distribution:
            lines = self.filtered(
                lambda line: line.analytic_distribution == analytic_distribution
            )
        return super(PurchaseOrderLine, lines)._find_candidate(
            product_id,
            product_qty,
            product_uom,
            location_id,
            name,
            origin,
            company_id,
            values,
        )
