from odoo import models, Command


class EstateProperty(models.Model):
    _inherit = "estate.property"

    def action_sold(self):
        self.check_access_rights('read')
        self.check_access_rule('read')
        self.check_access_rights('write')
        self.check_access_rule('write')
        res = super().action_sold()
        journal = self.env["account.journal"].sudo().search([("type", "=", "sale")], limit=1)
        for record in self:
            self.env["account.move"].sudo().create(
                {
                    "partner_id": record.buyer_id.id,
                    "move_type": "out_invoice",
                    "journal_id": journal.id,
                    "invoice_line_ids": [
                        Command.create({
                            "name": record.name,
                            "quantity": 1.0,
                            "price_unit": record.selling_price * 6.0 / 100.0,
                        }),
                        Command.create({
                            "name": "Administrative fees",
                            "quantity": 1.0,
                            "price_unit": 100.0,
                        }),
                    ],
                }
            )
        return res
