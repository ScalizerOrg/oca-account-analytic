# Copyright 2026 Scalizer (https://www.scalizer.fr)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import fields
from odoo.tests import TransactionCase, tagged


@tagged("post_install", "-at_install")
class TestPurchaseStockAnalyticProcurement(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.warehouse = cls.env["stock.warehouse"].search(
            [("company_id", "=", cls.env.company.id)], limit=1
        )
        cls.buy_route = cls.warehouse.buy_pull_id.route_id
        cls.buy_route.product_selectable = True
        cls.vendor = cls.env["res.partner"].create({"name": "Vendor"})
        cls.product = cls.env["product.product"].create(
            {
                "name": "Product",
                "is_storable": True,
                "route_ids": [(6, 0, [cls.buy_route.id])],
                "seller_ids": [(0, 0, {"partner_id": cls.vendor.id, "price": 10})],
            }
        )
        plan = cls.env["account.analytic.plan"].create({"name": "Plan"})
        cls.analytic_1 = cls.env["account.analytic.account"].create(
            {"name": "Analytic 1", "plan_id": plan.id}
        )
        cls.analytic_2 = cls.env["account.analytic.account"].create(
            {"name": "Analytic 2", "plan_id": plan.id}
        )

    def _run_procurement(self, analytic_distribution=None):
        values = {
            "warehouse_id": self.warehouse,
            "date_planned": fields.Datetime.now(),
        }
        if analytic_distribution:
            values["analytic_distribution"] = analytic_distribution
        self.env["stock.rule"].run(
            [
                self.env["stock.rule"].Procurement(
                    self.product,
                    1,
                    self.product.uom_id,
                    self.warehouse.lot_stock_id,
                    "Need",
                    "Origin",
                    self.env.company,
                    values,
                )
            ]
        )

    def _get_lines(self):
        return self.env["purchase.order.line"].search(
            [("product_id", "=", self.product.id)]
        )

    def test_analytic_distribution_is_propagated(self):
        distribution = {str(self.analytic_1.id): 100}
        self._run_procurement(distribution)
        line = self._get_lines()
        self.assertEqual(len(line), 1)
        self.assertEqual(line.analytic_distribution, distribution)

    def test_same_distribution_is_merged(self):
        distribution = {str(self.analytic_1.id): 100}
        self._run_procurement(distribution)
        self._run_procurement(distribution)
        line = self._get_lines()
        self.assertEqual(len(line), 1)
        self.assertEqual(line.product_qty, 2)

    def test_different_distribution_is_not_merged(self):
        self._run_procurement({str(self.analytic_1.id): 100})
        self._run_procurement({str(self.analytic_2.id): 100})
        lines = self._get_lines()
        self.assertEqual(len(lines), 2)
        self.assertEqual(
            set(lines.mapped(lambda line: tuple(line.analytic_distribution))),
            {(str(self.analytic_1.id),), (str(self.analytic_2.id),)},
        )

    def test_without_distribution_is_unchanged(self):
        self._run_procurement()
        self._run_procurement()
        line = self._get_lines()
        self.assertEqual(len(line), 1)
        self.assertEqual(line.product_qty, 2)
