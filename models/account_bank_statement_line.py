# -*- coding: utf-8 -*-

from odoo import _, api, fields, models

class AccountBankStatementLine(models.Model):
    _inherit = 'account.bank.statement.line'

    tipo_conciliacion_cuadratica = fields.Selection([
            ('CXC Interempresa', 'CXC Interempresa'),
            ('CXC Socios', 'CXC Socios'),
            ('CXC Empleados', 'CXC Empleados'),
            ('CXC Anticipo a Clientes', 'CXC Anticipo a Clientes'),
            ('CXC Intereses Ganados', 'CXC Intereses Ganados'),
            ('CXC Transferencias Interempresa', 'CXC Transferencias Interempresa'),
            ('CXC Otros Ingresos', 'CXC Otros Ingresos'),
            ('CXP Gastos Operativos', 'CXP Gastos Operativos'),
            ('CXP Anticipos', 'CXP Anticipos'),
            ('CXP Prestamos', 'CXP Prestamos'),
            ('CXP Dividendos', 'CXP Dividendos'),
            ('CXP Socios', 'CXP Socios'),
            ('CXP Relacionadas Locales', 'CXP Relacionadas Locales'),
            ('CXP Transferencias Interempresa', 'CXP Transferencias Interempresa'),
            ('CXP Otros Egresos', 'CXP Otros Egresos'),
        ], string="Tipo de conciliación cuadrática")
    cuenta_origen_conciliacion_cuadratica = fields.Many2one('res.partner.bank', string='Cuenta de origen')
    banco_origen_conciliacion_cuadratica = fields.Many2one('res.bank', string='Banco de origen', related='cuenta_origen_conciliacion_cuadratica.bank_id')
    date_conciliado = fields.Date(string='Fecha de conciliación')

    def write(self, vals):
        recs_actualizandose = self.filtered(lambda l: not l.is_reconciled)
        res = super().write(vals)
        if vals.get('is_reconciled'):
            for line in recs_actualizandose:
                if line.is_reconciled:
                    line.date_conciliado = fields.Date.today()
        return res

