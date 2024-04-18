from dateutil.utils import today

from odoo import api, fields, models, exceptions, _
from odoo.exceptions import ValidationError, UserError
from odoo.tools import date_utils
from odoo.tools import float_compare, float_is_zero


class EstateProperty(models.Model):
    _name = "estate.property"
    _description = "Estate Property"
    _order = "id desc"
    _sql_constraints = [
        ("check_expected_price", "CHECK(expected_price > 0)", "Expected price must be strictly positive."),
        ("check_selling_price", "CHECK(selling_price >= 0)", "Selling price must be positive."),
    ]

    name = fields.Char("Title", required=True)
    description = fields.Text("Description")
    postcode = fields.Char("Postcode")
    date_availability = fields.Date("Available From", default=date_utils.add(today(), months=3), copy=False)
    expected_price = fields.Float("Expected Price", required=True)
    selling_price = fields.Float("Selling Price", readonly=True, copy=False)
    bedrooms = fields.Integer("Bedrooms", default=2)
    living_area = fields.Integer("Living Area (sqm)")
    facades = fields.Integer("Facades")
    garage = fields.Boolean("Garage")
    garden = fields.Boolean("Garden")
    garden_area = fields.Integer("Garden Area (sqm)")
    garden_orientation = fields.Selection(
        selection=[
            ("north", "North"),
            ("south", "South"),
            ("east", "East"),
            ("west", "West")
        ],
        string="Garden Orientation"
    )

    active = fields.Boolean("Active", default=True)
    state = fields.Selection(
        selection=[
            ("new", "New"),
            ("offer_received", "Offer Received"),
            ("offer_accepted", "Offer Accepted"),
            ("sold", "Sold"),
            ("canceled", "Canceled")
        ],
        string="Status",
        required=True,
        copy=False,
        default="new"
    )

    company_id = fields.Many2one("res.company", required=True, default=lambda self: self.env.company)
    property_type_id = fields.Many2one("estate.property.type", string="Property Type")
    buyer_id = fields.Many2one("res.partner", string="Buyer", readonly=True, copy=False)
    salesperson_id = fields.Many2one("res.users", string="Salesperson")
    tag_ids = fields.Many2many("estate.property.tag", string="Tags")
    offer_ids = fields.One2many("estate.property.offer", "property_id", string="Offers")

    total_area = fields.Float("Total Area (sqm)", compute="_compute_total_area")
    best_price = fields.Float("Best Offer", compute="_compute_best_price")

    @api.depends("living_area", "garden_area")
    def _compute_total_area(self):
        for record in self:
            record.total_area = record.living_area + record.garden_area

    @api.depends("offer_ids.price")
    def _compute_best_price(self):
        for record in self:
            if record.offer_ids:
                record.best_price = max(record.offer_ids.mapped("price"))
            else:
                record.best_price = 0

    @api.constrains("selling_price", "expected_price")
    def _check_price_difference(self):
        for record in self:
            if (
                    not float_is_zero(record.selling_price, precision_rounding=0.01)
                    and float_compare(record.selling_price, record.expected_price * 90.0 / 100.0,
                                      precision_rounding=0.01) < 0
            ):
                raise ValidationError(_("Selling price cannot be lower than 90% of the expected price"))

    @api.onchange("garden")
    def _onchange_garden(self):
        if self.garden:
            self.garden_area = 10
            self.garden_orientation = "north"
        else:
            self.garden_area = 0
            self.garden_orientation = False

    def action_sold(self):
        if self.state != "canceled":
            self.state = "sold"
        else:
            raise UserError("Canceled properties cannot be sold.")

    def action_cancel(self):
        if self.state != "sold":
            self.state = "canceled"
        else:
            raise UserError("Sold properties cannot be canceled.")

    def set_offer_received(self):
        if self.state == "new":
            self.state = "offer_received"

    @api.ondelete(at_uninstall=False)
    def _unlink_if_status_is_new_or_canceled(self):
        if self.state != "new" or self.state != "canceled":
            raise UserError(_("Only new and canceled properties can be deleted!"))
