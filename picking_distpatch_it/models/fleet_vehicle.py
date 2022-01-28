# -*- coding: utf-8 -*-

from odoo import models, fields, api
from odoo import _

class FleetVehicle(models.Model):
    _inherit = 'fleet.vehicle'

    weight_vehicle = fields.Float('Carga del vehiculo')