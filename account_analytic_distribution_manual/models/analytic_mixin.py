# Copyright 2024 Tecnativa - Carlos Lopez
# Copyright 2024 Tecnativa - Víctor Martínez
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).
from odoo import api, fields, models

ACCOUNT_SEPARATOR = ","


class AnalyticMixin(models.AbstractModel):
    _inherit = "analytic.mixin"

    manual_distribution_id = fields.Many2one("account.analytic.distribution.manual")
    analytic_distribution_import = fields.Json(
        compute="_compute_analytic_distribution_import",
        inverse="_inverse_analytic_distribution_import",
        readonly=False,
        string="Analytic distribution (importable)",
        help="Defining this field, it will set the analytical distribution in JSON "
        "format, but using the analytic accounts names as keys of the dictionary, so "
        "it eases the human input.",
    )

    @api.depends("analytic_distribution")
    def _compute_analytic_distribution_import(self):
        """Convert the analytic_distribution to a json using the account names.

        A distribution key references one analytic account per analytic plan,
        their ids being joined by a comma (e.g. "709,11,2"), so the key is
        split and the names are joined back with the same separator.
        """
        aa_model = self.env["account.analytic.account"]
        for item in self:
            data = {}
            distribution = item.analytic_distribution or {}
            for key, percentage in distribution.items():
                account_ids = [
                    int(account_id)
                    for account_id in str(key).split(ACCOUNT_SEPARATOR)
                    if account_id
                ]
                aa_records = aa_model.browse(account_ids).exists()
                if not aa_records:
                    continue
                data[ACCOUNT_SEPARATOR.join(aa_records.mapped("name"))] = percentage
            item.analytic_distribution_import = data

    def _inverse_analytic_distribution_import(self):
        """Convert the json to the appropriate value of analytic_distribution.

        Each key may hold one analytic account name per analytic plan, joined
        by a comma, as rendered by _compute_analytic_distribution_import. Keys
        holding an unknown account name are discarded.
        """
        for item in self:
            company = (
                item.company_id if "company_id" in item._fields else self.env.company
            )
            base_domain = [("company_id", "in", company.ids + [False])]
            data = {}
            new_distribution = item.analytic_distribution_import or {}
            for key, percentage in new_distribution.items():
                aa_ids = self._get_analytic_account_ids_from_names(key, base_domain)
                if aa_ids:
                    data[ACCOUNT_SEPARATOR.join(str(aa_id) for aa_id in aa_ids)] = (
                        percentage
                    )
            item.analytic_distribution = data

    def _get_analytic_account_ids_from_names(self, key, base_domain):
        """Return the analytic account ids matching an importable key.

        The whole key is searched as a single account name first, so account
        names containing the separator keep working. It is only split when no
        account bears that exact name. An empty list is returned as soon as one
        of the names is unknown.
        """
        aa_model = self.env["account.analytic.account"]
        aa_record = aa_model.search(base_domain + [("name", "=", key)], limit=1)
        if aa_record:
            return aa_record.ids
        if ACCOUNT_SEPARATOR not in str(key):
            return []
        aa_ids = []
        for name in str(key).split(ACCOUNT_SEPARATOR):
            aa_record = aa_model.search(
                base_domain + [("name", "=", name.strip())], limit=1
            )
            if not aa_record:
                return []
            aa_ids.append(aa_record.id)
        return aa_ids
