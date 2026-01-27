# -*- coding: utf-8 -*-

from odoo import _, api, fields, models

class ConciliacionCuentasBancarias(models.Model):
    _name = 'conciliacion_cuadratica.cuentas_bancarias'

    name = fields.Char('Número de cuenta', required=True)
    banco_nombre = fields.Char('Banco', required=True)
    titular_cuenta_nombre = fields.Char('Nombre del titular de la cuenta')
