from dateutil.relativedelta import relativedelta

from odoo import api, fields, models, exceptions, _


class EstatePropertyOffer(models.Model):
    _name = "estate.property.offer"
    _description = "Estate Property Offer"
    _order = "price desc"
    _sql_constraints = [
        ("check_price", "CHECK(price > 0)", "Price must be strictly positive.")
    ]

    price = fields.Float("Price", required=True)
    status = fields.Selection(
        selection=[
            ("accepted", "Accepted"),
            ("refused", "Refused")
        ],
        string="Status",
        copy=False,
        default=False
    )

    partner_id = fields.Many2one("res.partner", string="Partner", required=True)
    property_id = fields.Many2one("estate.property", string="Property", required=True)
    validity = fields.Integer("Validity (days)", default=7)
    date_deadline = fields.Date("Deadline", compute="_compute_date_deadline", inverse="_inverse_date_deadline")
    property_type_id = fields.Many2one("estate.property.type", related="property_id.property_type_id",
                                       store=True)

    @api.depends("validity", "create_date")
    def _compute_date_deadline(self):
        for offer in self:
            date = offer.create_date.date() if offer.create_date else fields.Date.today()
            offer.date_deadline = date + relativedelta(days=offer.validity)

    def _inverse_date_deadline(self):
        for offer in self:
            date = offer.create_date.date() if offer.create_date else fields.Date.today()
            offer.validity = (offer.date_deadline - date).days

    def accept_offer(self):
        for record in self:
            if record.property_id.state == "sold":
                raise exceptions.UserError(_("This property has already been sold."))
            existing_accepted_offer = self.env["estate.property.offer"].search([
                ("property_id", "=", self.property_id.id),
                ("status", "=", "accepted"),
            ], limit=1)
            if existing_accepted_offer:
                raise exceptions.UserError(_("Another offer has already been accepted for this property."))
            record.status = "accepted"
            record.property_id.buyer_id = record.partner_id
            record.property_id.selling_price = record.price
            record.property_id.state = "offer_accepted"
        return True

    def reject_offer(self):
        for record in self:
            record.status = "refused"
        return True

    @api.model
    def create(self, vals):
        estate_property = self.env["estate.property"].browse(vals["property_id"])
        if any(offer.price > vals["price"] for offer in estate_property.offer_ids):
            raise exceptions.UserError(_("New offers can\'t be lower than existing ones."))
        estate_property.set_offer_received()
        return super().create(vals)
