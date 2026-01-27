# -*- coding: utf-8 -*-

from odoo import _, api, fields, models
from odoo.exceptions import ValidationError

class AccountBankStatementLine(models.Model):
    _inherit = 'account.bank.statement.line'

    tipo_conciliacion_cuadratica = fields.Selection([
            ('CXC Interempresa', 'CXC Interempresa'), 
            ('CXC Socios', 'CXC Socios'),
            ('CXC Empleados', 'CXC Empleados'),
            ('Anticipo a Clientes', 'Anticipo a Clientes'),
            ('Intereses Ganados', 'Intereses Ganados'),
            ('Transferencias Interempresa', 'Transferencias Interempresa'),
            ('Otros Ingresos', 'Otros Ingresos'),
        ],string="Tipo de conciliación cuadrática")
    tipo_conciliacion_cuadratica_pago = fields.Selection([
            ('Gastos Operativos', 'Gastos Operativos'),
            ('Anticipos', 'Anticipos'),
            ('Prestamos', 'Prestamos'),
            ('Dividendos', 'Dividendos'),
            ('CXP Socios', 'CXP Socio'),
            ('CXP Relacionadas Locales', 'CXP Relacionadas Locales'),
            ('Transferencias Interempresa', 'Transferencias Interempresa'),
            ('Otros Egresos', 'Otros Egresos'),
        ],string="Tipo de conciliación cuadrática de pago")
    cuenta_origen_conciliacion_cuadratica = fields.Many2one('conciliacion_cuadratica.cuentas_bancarias', string='Cuenta de origen')
    banco_origen_conciliacion_cuadratica = fields.Char(string='Banco de origen', related='cuenta_origen_conciliacion_cuadratica.banco_nombre')
    date_conciliado = fields.Date(string='Fecha de conciliación')

    @api.constrains('tipo_conciliacion_cuadratica', 'cuenta_origen_conciliacion_cuadratica', 'tipo_conciliacion_cuadratica_pago')
    def _check_interempresa_fields(self):
        for rec in self:
            if rec.tipo_conciliacion_cuadratica or rec.tipo_conciliacion_cuadratica_pago:
                if not rec.cuenta_origen_conciliacion_cuadratica:
                    raise ValidationError(_("Debe seleccionar una Cuenta de Origen para pagos con el tipo de conciliación cuadrática seleccionado."))

    def write(self, vals):
        recs_actualizandose = self.filtered(lambda l: not l.is_reconciled)
        res = super().write(vals)
        if vals.get('is_reconciled'):
            for line in recs_actualizandose:
                if line.is_reconciled:
                    line.date_conciliado = fields.Date.today()
        return res

