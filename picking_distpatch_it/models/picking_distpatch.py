# -*- coding: utf-8 -*-

from odoo import models, fields, api
from odoo import _


class pickingDistpatchIT(models.Model):
    _name = 'picking.distpatch.it'
    _inherit = 'mail.thread'
    _description = 'Proceso de Despacho de Mercadería'

    @api.depends('related_picking_ids')
    def _amount_all(self):
        """
        Compute the total amounts of the SO.
        """
        for order in self:
            peso_total = 0.0
            for line in order.related_picking_ids:
                peso_total += line.peso_picking_it
            order.update({
                'peso_total': peso_total
            })

    @api.model
    def _default_note(self):
        return self.env['ir.config_parameter'].sudo().get_param('account.use_invoice_terms') and self.env.company.invoice_terms or ''

    name = fields.Char(
        string="Nombre", 
        readonly=True, 
        required=True, 
        copy=False, 
        default=lambda self: _('New'))

    state = fields.Selection(
        [
            ('draft', 'Borrador'),
            ('finalized', 'Finalizado'),
        ], 'Estado',
        readonly=True, select=True, copy=False,
        default='draft',
        help='the state of the picking. '
        'Workflow is draft -> assigned -> progress -> done or cancel',
        track_visibility="onchange")

    date_order = fields.Date(
        'Fecha Creación',
        required=True, readonly=True, select=True,
        states={'draft': [('readonly', False)]},
        default=fields.Date.context_today,
        help='date on which the picking dispatched is to be processed')

    picker_id = fields.Many2one(
        'res.users', 'Usuario de Creación',
        readonly=True, select=True,
        states={'draft': [('readonly', False)]},
        help='the user to which the pickings are assigned',
        default=lambda self: self.env.user and self.env.user.id or False)

    related_picking_ids = fields.One2many(
        'stock.picking','picking_distpatch_id',
        string='Albaranes',
        track_visibility="onchange",
        readonly=True
       )

    fleet_vehicle_id = fields.Many2one('fleet.vehicle','Vehiculo Flete',track_visibility="onchange")

    _sql_constraints = [
        ('name_uniq', 'unique(name,company_id)', 'Ya existe este correlativo!'),
    ]
    company_id = fields.Many2one('res.company', 
        'Compañia', 
        required=True, 
        index=True, 
        default=lambda self: self.env.company)

    total_albaranes = fields.Float("Peso Total Albaranes(kg)",compute="calcular_peso")
    peso_total = fields.Float("Peso Total (kg)",related="fleet_vehicle_id.weight_vehicle")
    cambiar = fields.Boolean("Cambiar estado")    
    note = fields.Text('Terms and conditions', default=_default_note)

    @api.model
    def create(self, vals):
        if vals.get('name', _('New')) == _('New'):
            seq_date = None
            if 'date_order' in vals:
                seq_date = fields.Datetime.context_timestamp(self, fields.Datetime.to_datetime(vals['date_order']))
            if 'company_id' in vals:
                vals['name'] = self.env['ir.sequence'].with_context(force_company=vals['company_id']).next_by_code(
                    'picking.distpatch.it', sequence_date=seq_date) or _('New')
            else:
                vals['name'] = self.env['ir.sequence'].next_by_code('picking.distpatch.it', sequence_date=seq_date) or _('New')

        result = super(pickingDistpatchIT, self).create(vals)
        return result        

    def button_finalized(self):
        for albaran in self:
            if albaran.state in 'draft':
                self.state = 'finalized'

    @api.onchange('related_picking_ids')
    def calcular_peso(self):
        for albaran in self:
            total_albaranes = 0.0
            for linea in albaran.related_picking_ids:
                total_albaranes += float(linea.peso_picking_it)
            albaran.total_albaranes = float(total_albaranes)

    def button_restore(self):
        for albaran in self:
            if albaran.state in 'finalized':
                albaran.state = 'draft'

    def add_detalles(self):
	    return {
            'name': "Albaranes",
            'res_model': 'picking.distpatch.line',
            'view_mode': 'form',
            'type': 'ir.actions.act_window',
            'target': 'new',
	    }



class stockPickingDistpatchIT(models.Model):
    _inherit = 'stock.picking'

    peso_picking_it = fields.Float('Peso Albaran (kg)', compute="_compute_peso_albaran")
    picking_distpatch_id = fields.Many2one('picking.distpatch.it','Doc. Cierre')

    ruta = fields.Many2one('res.users','Ruta',related="partner_id.user_id",store=True)
    ciudad = fields.Many2one('res.country.state','Ciudad',related="partner_id.state_id",store=True)
    provincia =fields.Many2one('res.country.state','Provincia',related="partner_id.province_id",store=True)       
    distrito =fields.Many2one('res.country.state','Distrito',related="partner_id.district_id",store=True)

    es_venta = fields.Boolean('Es venta',compute="get_es_venta")

    def ver_picking(self):
        return {
            'name': 'Picking',
            'type': 'ir.actions.act_window',
            'res_model': 'picking.distpatch.it',
            'view_mode': 'form',
            'res_id': self.picking_distpatch_id.id,
        }

    def get_es_venta(self):
        for i in self:
            flag = False
            for elem in i.move_ids_without_package:
                if elem.sale_line_id.id:
                    flag = True
            i.es_venta = flag

    def create_factura(self):
        for i in self:
            id_sale = False
            for elem in i.move_ids_without_package:
                if elem.sale_line_id.id:
                    id_sale = elem.sale_line_id.order_id.id
            create = self.env['sale.advance.payment.inv'].create({'advance_payment_method':'delivered','picking_ids':[self.id]})
            create.with_context({'active_id':id_sale,'active_ids':[id_sale]}).create_invoices()


    def create_picking_distpatch(self):
        data = {
            'name':_('New'),
            'state':'draft',
        }
        pick = self.env['picking.distpatch.it'].create(data)
        for i in self:
            i.picking_distpatch_id = pick.id

    @api.onchange('name')
    def _compute_peso_albaran(self):
        for alabaranes in self:
            peso = 0
            for linea in alabaranes.move_ids_without_package:
                peso += (linea.product_id.weight * linea.product_uom_qty)
            alabaranes.peso_picking_it = peso

    def quitar(self):
        for i in self:
            i.picking_distpatch_id.message_post(body=u"<b>Se elimino el albaran(ID): </b>" + str(i.id) + "<br/><b>Usuario: </b>" + str(self.env.user.name_get()[0][1] ) )
            i.picking_distpatch_id = False

    def entrar(self):
        return {
            'name': 'Albaran',
            'type': 'ir.actions.act_window',
            'res_model': 'stock.picking',
            'view_mode': 'form',
            'res_id': self.id,
        }

class pickingDistpatchLineIT(models.TransientModel):
	_name ='picking.distpatch.line'

	detalle_id = fields.Many2many('stock.picking','albaranes_despacho_rel','te_id','co','Albaranes')

	def agregar(self):
		for i in self:
			for elem in i.detalle_id:
				elem.picking_distpatch_id = self.env.context['active_id']
				elem.refresh()
				elem.picking_distpatch_id.message_post(body=u"<b>Se agrego el albaran(ID): </b>" + str(elem.id) + "<br/><b>Usuario: </b>" + str(self.env.user.name_get()[0][1] ) )
