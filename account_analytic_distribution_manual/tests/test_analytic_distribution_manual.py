# Copyright 2024 Tecnativa - Carlos Lopez
# Copyright 2024 Tecnativa - Víctor Martínez
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl)
from psycopg2.errors import UniqueViolation

from odoo.tests import Form, tagged
from odoo.tools import mute_logger

from odoo.addons.account_analytic_distribution_manual.tests.common import (
    DistributionManualCommon,
)


@tagged("post_install", "-at_install")
class TestAnalyticDistributionManual(DistributionManualCommon):
    @mute_logger("odoo.sql_db")
    def test_copy_manual_distribution(self):
        distribution = self.distribution_1.copy()
        self.assertEqual(distribution.name, "Manual Distribution 1 (Copy)")
        distribution2 = self.distribution_1.copy({"name": "New name"})
        self.assertEqual(distribution2.name, "New name")
        with self.assertRaises(UniqueViolation):
            self.ManualDistribution.create(
                {
                    "name": "Manual Distribution 1",
                }
            )

    def test_manual_distribution_analytic_distribution_process_01(self):
        invoice_form = Form(
            self.env["account.move"].with_context(default_move_type="out_invoice")
        )
        invoice_form.partner_id = self.partner_a
        with invoice_form.invoice_line_ids.new() as line_form:
            line_form.product_id = self.product_a
            line_form.manual_distribution_id = self.distribution_1
        invoice = invoice_form.save()
        invoice_line = invoice.invoice_line_ids
        invoice_line.analytic_distribution = self.distribution_1.analytic_distribution
        invoice.action_post()
        self.assertTrue(len(invoice_line.analytic_line_ids), 2)
        self.assertEqual(
            invoice_line.analytic_line_ids.mapped("manual_distribution_id"),
            self.distribution_1,
        )

    def test_manual_distribution_analytic_distribution_process_02(self):
        invoice_form = Form(
            self.env["account.move"].with_context(default_move_type="out_invoice")
        )
        invoice_form.partner_id = self.partner_a
        with invoice_form.invoice_line_ids.new() as line_form:
            line_form.product_id = self.product_a
        invoice = invoice_form.save()
        invoice_line = invoice.invoice_line_ids
        invoice_line.manual_distribution_id = self.distribution_1
        self.analytic_account_a1.name = "test-1"
        aa_1 = self.analytic_account_a1
        self.analytic_account_a2.name = "test-2"
        aa_2 = self.analytic_account_a2
        invoice_line.analytic_distribution_import = {
            "test-1": 20.0,
            "test-2": 80.0,
        }
        self.assertEqual(
            invoice_line.analytic_distribution,
            {str(aa_1.id): 20.0, str(aa_2.id): 80.0},
        )
        invoice.action_post()
        self.assertTrue(len(invoice_line.analytic_line_ids), 2)
        self.assertEqual(
            invoice_line.analytic_line_ids.mapped("manual_distribution_id"),
            self.distribution_1,
        )
        # In this case, the analytic account ID is stored in
        # the field x_plan{self.plan_a.id}_id,
        # not in the account_id field. The account_id field
        # only contains the ID of the analytic
        # account from the first plan (Projects),
        # or the plan with ID = 1.
        account_by_plan = invoice_line.analytic_line_ids.mapped(
            f"x_plan{self.plan_a.id}_id"
        )
        self.assertIn(aa_1, account_by_plan)
        self.assertIn(aa_2, account_by_plan)

    def test_manual_distribution_analytic_distribution_text(self):
        self.analytic_account_a1.name = "test-1"
        aa_1 = self.analytic_account_a1
        self.analytic_account_a2.name = "test-2"
        aa_2 = self.analytic_account_a2
        self.assertEqual(
            self.distribution_1.analytic_distribution_import,
            {"test-1": 40.0, "test-2": 60.0},
        )
        # Set analytic_distribution_import field
        self.distribution_1.analytic_distribution_import = {
            "test-1": 20.0,
            "test-2": 80.0,
        }
        self.assertEqual(
            self.distribution_1.analytic_distribution,
            {str(aa_1.id): 20.0, str(aa_2.id): 80.0},
        )
        # Remove aa_2
        self.distribution_1.analytic_distribution_import = {"test-1": 40.0}
        self.assertEqual(
            self.distribution_1.analytic_distribution, {str(aa_1.id): 40.0}
        )
        # Create aa_2 again
        self.distribution_1.analytic_distribution_import = {
            "test-1": 40.0,
            "test-2": 60.0,
        }
        self.assertEqual(
            self.distribution_1.analytic_distribution,
            {str(aa_1.id): 40.0, str(aa_2.id): 60.0},
        )
        # Update with an "incorrect name"
        self.distribution_1.analytic_distribution_import = {
            "test-1": 40.0,
            "test-3": 60.0,
        }
        self.assertEqual(
            self.distribution_1.analytic_distribution, {str(aa_1.id): 40.0}
        )

    def test_manual_distribution_analytic_distribution_multi_plan(self):
        plan_b = self.env["account.analytic.plan"].create({"name": "Plan B"})
        aa_1 = self.analytic_account_a1
        aa_b1 = self.env["account.analytic.account"].create(
            {"name": "analytic_account_b1", "plan_id": plan_b.id}
        )
        # A key holds one analytic account per plan, their ids joined by a comma
        self.distribution_1.analytic_distribution = {f"{aa_1.id},{aa_b1.id}": 100.0}
        self.assertEqual(
            self.distribution_1.analytic_distribution_import,
            {f"{aa_1.name},{aa_b1.name}": 100.0},
        )
        # Set the same distribution back from the account names
        self.distribution_1.analytic_distribution_import = {
            f"{aa_1.name},{aa_b1.name}": 100.0
        }
        self.assertEqual(
            self.distribution_1.analytic_distribution,
            {f"{aa_1.id},{aa_b1.id}": 100.0},
        )
        # An unknown name in the key discards the whole key
        self.distribution_1.analytic_distribution_import = {
            f"{aa_1.name},analytic_account_b2": 100.0
        }
        self.assertFalse(self.distribution_1.analytic_distribution)

    def test_manual_distribution_analytic_distribution_name_with_separator(self):
        aa_1 = self.analytic_account_a1
        aa_1.name = "analytic,account"
        self.distribution_1.analytic_distribution_import = {aa_1.name: 100.0}
        self.assertEqual(
            self.distribution_1.analytic_distribution, {str(aa_1.id): 100.0}
        )

    def test_manual_distribution_analytic_distribution_deleted_account(self):
        aa_2 = self.analytic_account_a2
        self.analytic_account_a1.unlink()
        self.distribution_1.invalidate_recordset(["analytic_distribution_import"])
        self.assertEqual(
            self.distribution_1.analytic_distribution_import, {aa_2.name: 60}
        )
