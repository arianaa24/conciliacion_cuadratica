# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
import io
import xlsxwriter
import base64
import logging

class ReporteConciliacionCuadraticaWizard(models.TransientModel):
    _name = 'conciliacion_cuadratica.reporte_conciliacion_wizard'
    _description = 'Reporte de Conciliación Cuadrática'

    diario_id = fields.Many2one("account.journal", string="Diario", required=True, domain=[('type', '=', 'bank')])
    year = fields.Integer(string="Año", required=True, default=lambda self: fields.Date.today().year)
    otros_ajustes_ids = fields.One2many(
        'conciliacion_cuadratica.reporte_ajuste_wizard',
        'wizard_id',
        string="Otros Ajustes"
    )
    name = fields.Char('Nombre archivo')
    archivo = fields.Binary('Archivo')
    
    def print_report_excel(self):
        for w in self:
            f = io.BytesIO()
            libro = xlsxwriter.Workbook(f)
            hoja = libro.add_worksheet('Conciliacion Cuadrática')
            
            dict = {}
            dict['diario_id'] = w['diario_id']
            dict['year'] = w['year']
            dict['cuenta_id'] = w['diario_id'].default_account_id

            company_id = self.env.company
            base_pagos = self.env['account.payment'].search([
                ('journal_id', '=', dict['diario_id'].id),
                ('state', '=', 'posted'),
                ('date', '>=', f"{dict['year']}-01-01"),
                ('date', '<=', f"{dict['year']}-12-31"),
            ], order='date')
            base_apuntes = self.env['account.bank.statement.line'].search([
                ('journal_id','=',dict['diario_id'].id),
                ('date','<=',f"{dict['year']}-12-31") #('date', '>=', f"{dict['year']}-01-01"),
            ])
            total_ingresos = []
            total_egresos = []
            transitos_ingresos = []
            transitos_egresos = []

            # --- OBTENER DATOS ---
            # -- Cuentas por cobrar: cxc
            saldo_incial_mensual = self.env['report.conciliacion_cuadratica.reporte_conciliacion'].saldo_inicial_por_mes(dict)[0]
            saldo_final_mensual = self.env['report.conciliacion_cuadratica.reporte_conciliacion'].saldo_inicial_por_mes(dict)[1]
            total_ingresos.append(saldo_incial_mensual)
            
            cxc_locales_datos = self.env['report.conciliacion_cuadratica.reporte_conciliacion'].filtrar_movimientos_por_tipo_conciliacion('inbound', pagos=base_pagos, tipo_conciliacion='cxc_local')['pagos']
            cxc_locales_mensual = self.env['report.conciliacion_cuadratica.reporte_conciliacion'].obtener_montos_mensuales(cxc_locales_datos)
            cxc_locales_lines = []
            for dato in cxc_locales_datos:
                cxc_locales_lines.append({
                    'documento': dato.name,
                    'fecha': dato.date,
                    'cliente': dato.partner_id.name,
                    'monto': dato.amount,
                })
            total_ingresos.append(cxc_locales_mensual) 

            cxc_exterior_datos = self.env['report.conciliacion_cuadratica.reporte_conciliacion'].filtrar_movimientos_por_tipo_conciliacion('inbound', pagos=base_pagos, tipo_conciliacion='cxc_exterior')['pagos']
            cxc_exterior_mensual = self.env['report.conciliacion_cuadratica.reporte_conciliacion'].obtener_montos_mensuales(cxc_exterior_datos)
            cxc_exterior_lines = []
            for dato in cxc_exterior_datos:
                cxc_exterior_lines.append({
                    'documento': dato.name,
                    'fecha': dato.date,
                    'cliente': dato.partner_id.name,
                    'monto': dato.amount,
                })
            total_ingresos.append(cxc_exterior_mensual)
            
            cxc_local_exterior_datos = self.env['report.conciliacion_cuadratica.reporte_conciliacion'].filtrar_movimientos_por_tipo_conciliacion('inbound', pagos=base_pagos, tipo_conciliacion='cxc_interempresa')['pagos']
            cxc_local_exterior_mensual = self.env['report.conciliacion_cuadratica.reporte_conciliacion'].obtener_montos_mensuales(cxc_local_exterior_datos)
            cxc_local_exterior_lines = []
            for dato in cxc_local_exterior_datos:
                cxc_local_exterior_lines.append({
                    'empresa': dato.partner_id.name,
                    'banco': dato.banco_origen_conciliacion_cuadratica.name,
                    'cuenta': dato.cuenta_origen_conciliacion_cuadratica.acc_number,
                    'monto': dato.amount,
                    'mes': dato.date.month,
                })
            total_ingresos.append(cxc_local_exterior_mensual)

            cxc_socios_datos = self.env['report.conciliacion_cuadratica.reporte_conciliacion'].filtrar_movimientos_por_tipo_conciliacion('inbound', apuntes=base_apuntes, tipo_conciliacion='cxc_socios')['apuntes']
            cxc_socios_resultado = self.env['report.conciliacion_cuadratica.reporte_conciliacion'].obtener_montos_apuntes_por_mes(cxc_socios_datos, dict['year'])
            cxc_socios_mensual = cxc_socios_resultado['final']
            cxc_socios_transito = cxc_socios_resultado['transito']
            transitos_ingresos.append(cxc_socios_transito)
            cxc_socios_lines = []
            for dato in cxc_socios_datos:
                if dato.date_conciliado and dato.date_conciliado.year == dict['year']:
                    cxc_socios_lines.append({
                        'socio': dato.partner_id.name,
                        'banco': dato.banco_origen_conciliacion_cuadratica.name,
                        'cuenta': dato.cuenta_origen_conciliacion_cuadratica.acc_number,
                        'monto': dato.amount,
                        'mes': dato.date_conciliado.month,
                    })
            total_ingresos.append(cxc_socios_mensual)

            
            cxc_empleados_datos = self.env['report.conciliacion_cuadratica.reporte_conciliacion'].filtrar_movimientos_por_tipo_conciliacion('inbound', pagos=base_pagos, apuntes=base_apuntes, tipo_conciliacion='cxc_empleados')#['pagos']#['apuntes']
            cxc_empleados_pagos = self.env['report.conciliacion_cuadratica.reporte_conciliacion'].obtener_montos_mensuales(cxc_empleados_datos['pagos'])
            cxc_empleados_resultado = self.env['report.conciliacion_cuadratica.reporte_conciliacion'].obtener_montos_apuntes_por_mes(cxc_empleados_datos['apuntes'], dict['year'])
            cxc_empleados_apuntes = cxc_empleados_resultado['final']
            cxc_empleados_mensual = self.env['report.conciliacion_cuadratica.reporte_conciliacion'].sumar_pagos_apuntes(cxc_empleados_pagos,cxc_empleados_apuntes)
            total_ingresos.append(cxc_empleados_mensual)

            anticipo_clientes_datos = self.env['report.conciliacion_cuadratica.reporte_conciliacion'].filtrar_movimientos_por_tipo_conciliacion('inbound', pagos=base_pagos, apuntes=base_apuntes, tipo_conciliacion='anticipo_clientes')#['pagos']#['apuntes']
            anticipo_clientes_pagos = self.env['report.conciliacion_cuadratica.reporte_conciliacion'].obtener_montos_mensuales(anticipo_clientes_datos['pagos'])
            anticipo_clientes_resultado = self.env['report.conciliacion_cuadratica.reporte_conciliacion'].obtener_montos_apuntes_por_mes(anticipo_clientes_datos['apuntes'], dict['year'])
            anticipo_clientes_mensual = self.env['report.conciliacion_cuadratica.reporte_conciliacion'].sumar_pagos_apuntes(anticipo_clientes_pagos,anticipo_clientes_resultado['final'])
            total_ingresos.append(anticipo_clientes_mensual)

            intereses_ganados_datos = self.env['report.conciliacion_cuadratica.reporte_conciliacion'].filtrar_movimientos_por_tipo_conciliacion('inbound', apuntes=base_apuntes, tipo_conciliacion='intereses_ganados')['apuntes']
            intereses_ganados_resultado = self.env['report.conciliacion_cuadratica.reporte_conciliacion'].obtener_montos_apuntes_por_mes(intereses_ganados_datos, dict['year'])
            intereses_ganados_mensual = intereses_ganados_resultado['final']
            intereses_ganados_transito = intereses_ganados_resultado['transito']
            transitos_ingresos.append(intereses_ganados_transito)
            total_ingresos.append(intereses_ganados_mensual)

            transfer_interempresa_datos = self.env['report.conciliacion_cuadratica.reporte_conciliacion'].filtrar_movimientos_por_tipo_conciliacion('inbound', apuntes=base_apuntes, tipo_conciliacion='transfer_interempresa')['apuntes']
            transfer_interempresa_resultado = self.env['report.conciliacion_cuadratica.reporte_conciliacion'].obtener_montos_apuntes_por_mes(transfer_interempresa_datos, dict['year'])
            transfer_interempresa_mensual = transfer_interempresa_resultado['final']
            transfer_interempresa_transito = transfer_interempresa_resultado['transito']
            transitos_ingresos.append(transfer_interempresa_transito)
            transfer_interempresa_lines = []
            for dato in transfer_interempresa_datos:
                if dato.date_conciliado and dato.date_conciliado.year == dict['year']:
                    transfer_interempresa_lines.append({
                        'banco': dato.banco_origen_conciliacion_cuadratica.name,
                        'cuenta': dato.cuenta_origen_conciliacion_cuadratica.acc_number,
                        'monto': dato.amount,
                        'mes': dato.date_conciliado.month,
                    })
            total_ingresos.append(transfer_interempresa_mensual)
            
            otros_ingresos_datos = self.env['report.conciliacion_cuadratica.reporte_conciliacion'].filtrar_movimientos_por_tipo_conciliacion('inbound', pagos=base_pagos, tipo_conciliacion= 'otros_ingresos')['pagos']
            otros_ingresos_mensual = self.env['report.conciliacion_cuadratica.reporte_conciliacion'].obtener_montos_mensuales(otros_ingresos_datos)
            otros_ingresos_lines = []
            for dato in otros_ingresos_datos:
                otros_ingresos_lines.append({
                    'nota': dato.descripcion,
                    'monto': dato.amount,
                    'mes': dato.date.month,
                })
            total_ingresos.append(otros_ingresos_mensual)

            total_ingresos_mensual = self.env['report.conciliacion_cuadratica.reporte_conciliacion'].obtener_totales_mensuales(total_ingresos)
            depositos_transito_mensual = self.env['report.conciliacion_cuadratica.reporte_conciliacion'].obtener_totales_mensuales(transitos_ingresos)
            

            # -- Cuentas por pagar: cxp
            gastos_operativos_datos = self.env['report.conciliacion_cuadratica.reporte_conciliacion'].filtrar_movimientos_por_tipo_conciliacion('outbound', pagos=base_pagos, pago_conciliacion='gastos_operativos')['pagos']
            gastos_operativos_mensual = self.env['report.conciliacion_cuadratica.reporte_conciliacion'].obtener_montos_mensuales(gastos_operativos_datos)
            total_egresos.append(gastos_operativos_mensual)

            anticipos_datos = self.env['report.conciliacion_cuadratica.reporte_conciliacion'].filtrar_movimientos_por_tipo_conciliacion('outbound', pagos=base_pagos, apuntes=base_apuntes, pago_conciliacion='anticipos')#['pagos']#['apuntes']
            anticipos_pagos = self.env['report.conciliacion_cuadratica.reporte_conciliacion'].obtener_montos_mensuales(anticipos_datos['pagos'])
            anticipos_resultado = self.env['report.conciliacion_cuadratica.reporte_conciliacion'].obtener_montos_apuntes_por_mes(anticipos_datos['apuntes'], dict['year'])
            anticipos_mensual = self.env['report.conciliacion_cuadratica.reporte_conciliacion'].sumar_pagos_apuntes(anticipos_pagos, anticipos_resultado['final'])
            total_egresos.append(anticipos_mensual)

            prestamos_datos = self.env['report.conciliacion_cuadratica.reporte_conciliacion'].filtrar_movimientos_por_tipo_conciliacion('outbound', apuntes=base_apuntes, pago_conciliacion='prestamos')['apuntes']
            prestamos_resultado = self.env['report.conciliacion_cuadratica.reporte_conciliacion'].obtener_montos_apuntes_por_mes(prestamos_datos, dict['year'])
            prestamos_mensual = prestamos_resultado['final']
            prestamos_transito = prestamos_resultado['transito']
            transitos_egresos.append(prestamos_transito)
            prestamos_lines = []
            for dato in prestamos_datos:
                if dato.date_conciliado and dato.date_conciliado.year == dict['year']:
                    prestamos_lines.append({
                        'nombre': dato.partner_id.name,
                        'banco': dato.banco_origen_conciliacion_cuadratica.name,
                        'cuenta': dato.cuenta_origen_conciliacion_cuadratica.acc_number,
                        'monto': dato.amount,
                        'mes': dato.date_conciliado.month,
                    })
            total_egresos.append(prestamos_mensual)

            dividendos_datos = self.env['report.conciliacion_cuadratica.reporte_conciliacion'].filtrar_movimientos_por_tipo_conciliacion('outbound', pagos=base_pagos, apuntes=base_apuntes, pago_conciliacion='dividendos')#['pagos']#['apuntes']
            dividendos_pagos = self.env['report.conciliacion_cuadratica.reporte_conciliacion'].obtener_montos_mensuales(dividendos_datos['pagos'])
            dividendos_resultado = self.env['report.conciliacion_cuadratica.reporte_conciliacion'].obtener_montos_apuntes_por_mes(dividendos_datos['apuntes'], dict['year'])
            dividendos_mensual = self.env['report.conciliacion_cuadratica.reporte_conciliacion'].sumar_pagos_apuntes(dividendos_pagos, dividendos_resultado['final'])
            lineas_unificadas = list(dividendos_datos['pagos']) + list(dividendos_datos['apuntes'])
            dividendos_lines = []
            primeros_10_dividendos_lines = lineas_unificadas[:10]
            for dato in primeros_10_dividendos_lines:
                mes = dato.date_conciliado.month if dato._name == 'account.bank.statement.line' else dato.date.month
                dividendos_lines.append({
                    'socio': dato.partner_id.name,
                    'banco': dato.banco_origen_conciliacion_cuadratica.name,
                    'cuenta': dato.cuenta_origen_conciliacion_cuadratica.acc_number,
                    'monto': dato.amount,
                    'mes': mes,
                })
            otras_dividendos_mensual = []
            if lineas_unificadas[10:]:
                resto = lineas_unificadas[10:]
                pagos_resto = [r for r in resto if r._name == 'account.payment']
                apuntes_resto = [r for r in resto if r._name == 'account.bank.statement.line']
                resto_pagos_m = self.env['report.conciliacion_cuadratica.reporte_conciliacion'].obtener_montos_mensuales(pagos_resto)
                resto_apuntes_m = self.env['report.conciliacion_cuadratica.reporte_conciliacion'].obtener_montos_apuntes_por_mes(apuntes_resto, dict['year'])['final']
                otras_dividendos_mensual = self.env['report.conciliacion_cuadratica.reporte_conciliacion'].sumar_pagos_apuntes(resto_pagos_m, resto_apuntes_m)
            total_egresos.append(dividendos_mensual)

            cxp_socios_datos = self.env['report.conciliacion_cuadratica.reporte_conciliacion'].filtrar_movimientos_por_tipo_conciliacion('outbound', apuntes=base_apuntes, pago_conciliacion='cxp_socios')['apuntes']
            cxp_socios_resultado = self.env['report.conciliacion_cuadratica.reporte_conciliacion'].obtener_montos_apuntes_por_mes(cxp_socios_datos, dict['year'])
            cxp_socios_mensual = cxp_socios_resultado['final']
            cxp_socios_transito = cxp_socios_resultado['transito']
            transitos_egresos.append(cxp_socios_transito)
            cxp_socios_lines = []
            for dato in cxp_socios_datos:
                if dato.date_conciliado and dato.date_conciliado.year == dict['year']:
                    cxp_socios_lines.append({
                        'socio': dato.partner_id.name,
                        'banco': dato.banco_origen_conciliacion_cuadratica.name,
                        'cuenta': dato.cuenta_origen_conciliacion_cuadratica.acc_number,
                        'monto': dato.amount,
                        'mes': dato.date_conciliado.month,
                    })
            total_egresos.append(cxp_socios_mensual)

            cxp_relacionadas_locales_datos = self.env['report.conciliacion_cuadratica.reporte_conciliacion'].filtrar_movimientos_por_tipo_conciliacion('outbound', apuntes=base_apuntes, pago_conciliacion='cxp_relacionadas_locales')['apuntes']
            cxp_relacionadas_locales_resultado = self.env['report.conciliacion_cuadratica.reporte_conciliacion'].obtener_montos_apuntes_por_mes(cxp_relacionadas_locales_datos, dict['year'])
            cxp_relacionadas_locales_mensual = cxp_relacionadas_locales_resultado['final']
            cxp_relacionadas_locales_transito = cxp_relacionadas_locales_resultado['transito']
            transitos_egresos.append(cxp_relacionadas_locales_transito)
            cxp_relacionadas_locales_lines = []
            for dato in cxp_relacionadas_locales_datos:
                if dato.date_conciliado and dato.date_conciliado.year == dict['year']:
                    cxp_relacionadas_locales_lines.append({
                        'empresa': dato.partner_id.name,
                        'banco': dato.banco_origen_conciliacion_cuadratica.name,
                        'cuenta': dato.cuenta_origen_conciliacion_cuadratica.acc_number,
                        'monto': dato.amount,
                        'mes': dato.date_conciliado.month,
                    })
            total_egresos.append(cxp_relacionadas_locales_mensual)

            cxp_relacionadas_exterior_datos = self.env['report.conciliacion_cuadratica.reporte_conciliacion'].filtrar_movimientos_por_tipo_conciliacion('outbound', apuntes=base_apuntes, pago_conciliacion='cxp_relacionadas_exterior')['apuntes']
            cxp_relacionadas_exterior_resultado = self.env['report.conciliacion_cuadratica.reporte_conciliacion'].obtener_montos_apuntes_por_mes(cxp_relacionadas_exterior_datos, dict['year'])
            cxp_relacionadas_exterior_mensual = cxp_relacionadas_exterior_resultado['final']
            cxp_relacionadas_exterior_transito = cxp_relacionadas_exterior_resultado['transito']
            transitos_egresos.append(cxp_relacionadas_exterior_transito)
            cxp_relacionadas_exterior_lines = []
            for dato in cxp_relacionadas_exterior_datos:
                if dato.date_conciliado and dato.date_conciliado.year == dict['year']:
                    cxp_relacionadas_exterior_lines.append({
                        'empresa': dato.partner_id.name,
                        'banco': dato.banco_origen_conciliacion_cuadratica .name,
                        'cuenta': dato.cuenta_origen_conciliacion_cuadratica.acc_number,
                        'monto': dato.amount,
                        'mes': dato.date_conciliado.month,
                    })
            total_egresos.append(cxp_relacionadas_exterior_mensual) 

            cxp_transfer_interempresa_datos = self.env['report.conciliacion_cuadratica.reporte_conciliacion'].filtrar_movimientos_por_tipo_conciliacion('outbound', apuntes=base_apuntes, pago_conciliacion='transfer_interempresa')['apuntes']
            cxp_transfer_interempresa_resultado = self.env['report.conciliacion_cuadratica.reporte_conciliacion'].obtener_montos_apuntes_por_mes(cxp_transfer_interempresa_datos, dict['year'])
            cxp_transfer_interempresa_mensual = cxp_transfer_interempresa_resultado['final']
            cxp_transfer_interempresa_transito = cxp_transfer_interempresa_resultado['transito']
            transitos_egresos.append(cxp_transfer_interempresa_transito)
            cxp_transfer_interempresa_lines = []
            for dato in cxp_transfer_interempresa_datos:
                if dato.date_conciliado and dato.date_conciliado.year == dict['year']:
                    cxp_transfer_interempresa_lines.append({
                        'banco': dato.banco_origen_conciliacion_cuadratica.name,
                        'cuenta': dato.cuenta_origen_conciliacion_cuadratica.acc_number,
                        'monto': dato.amount,
                        'mes': dato.date_conciliado.month,
                    })
            total_egresos.append(cxp_transfer_interempresa_mensual) 

            otros_egresos_datos = self.env['report.conciliacion_cuadratica.reporte_conciliacion'].filtrar_movimientos_por_tipo_conciliacion('outbound', pagos=base_pagos, pago_conciliacion= 'otros_egresos')['pagos']
            otros_egresos_mensual = self.env['report.conciliacion_cuadratica.reporte_conciliacion'].obtener_montos_mensuales(otros_egresos_datos)
            otros_egresos_lines = []
            for dato in otros_egresos_datos:
                otros_egresos_lines.append({
                    'nota': dato.descripcion,
                    'monto': dato.amount,
                    'mes': dato.date.month,
                })
            total_egresos.append(otros_egresos_mensual)

            total_egresos_mensual = self.env['report.conciliacion_cuadratica.reporte_conciliacion'].obtener_totales_mensuales(total_egresos)
            cheques_transito_mensual = self.env['report.conciliacion_cuadratica.reporte_conciliacion'].obtener_totales_mensuales(transitos_egresos)

            # -- Ajustes extra
            ajustes = self.otros_ajustes_ids
            otros_ajustes = ajustes.filtered(lambda a: a.tipo == 'otros_ajustes')
            intereses_ganados = ajustes.filtered(lambda a: a.tipo == 'intereses_ganados')
            notas_debito = ajustes.filtered(lambda a: a.tipo == 'notas_debito')
            ajustes_finales = ajustes.filtered(lambda a: a.tipo == 'ajustes_finales')
            otros_ajustes_mensual = self.env['report.conciliacion_cuadratica.reporte_conciliacion'].obtener_montos_mensuales(otros_ajustes)
            intereses_ganados_mensual = self.env['report.conciliacion_cuadratica.reporte_conciliacion'].obtener_montos_mensuales(intereses_ganados)
            notas_debito_mensual = self.env['report.conciliacion_cuadratica.reporte_conciliacion'].obtener_montos_mensuales(notas_debito)
            ajustes_finales_mensual = self.env['report.conciliacion_cuadratica.reporte_conciliacion'].obtener_montos_mensuales(ajustes_finales)


            # --- FORMATO ---
            formats = {}
            formats['fecha'] = libro.add_format({'num_format': 'dd/mm/yy'})
            formats['numero'] = libro.add_format({'num_format': '#,##0.00'})
            formats['bold'] = libro.add_format({'bold': True})
            formats['bold_center'] = libro.add_format({'bold': True, 'align': 'center'})
            formats['center'] = libro.add_format({'align': 'center'})
            formats['table_subtitle_bold'] = libro.add_format({'align': 'center', 'bold': True, 'bg_color': '#203764', 'font_color': 'white'})
            formats['table_subtitle'] = libro.add_format({'align': 'center', 'bg_color': '#203764', 'font_color': 'white'})
            formats['row_totals_bold'] = libro.add_format({'bold': True, 'bg_color': '#BFBFBF'})
            formats['row_totals_number'] = libro.add_format({'bold': True, 'bg_color': '#BFBFBF', 'num_format': '#,##0.00'})

            hoja.set_column(0,0,2)
            hoja.set_column(1,1,4)
            hoja.set_column(2,4,24)
            hoja.set_column(5,30,15)

            # --- Encabezado (Datos) ---
            hoja.merge_range('B4:C4', 'Nombre o Razón Social:', formats['bold'])
            hoja.merge_range('D4:E4', company_id.name)
            hoja.write('F4','NIT:', formats['bold'])
            hoja.write('G4', company_id.vat)
            hoja.merge_range('B5:G5', 'Identificación del Banco donde tiene su cuenta', formats['bold_center'])
            hoja.merge_range('B6:C6', 'Nombre del Banco:', formats['bold'])
            hoja.merge_range('D6:G6', dict['diario_id'].bank_id.name)
            hoja.merge_range('B7:C7', 'País:', formats['bold'])
            hoja.merge_range('D7:G7', company_id.country_id.name)
            hoja.merge_range('B8:C8', 'No. de Cuenta Bancaria:', formats['bold'])
            hoja.write('D8', dict['diario_id'].bank_account_id.acc_number)
            hoja.write('E8','Tipo de Moneda:', formats['bold'])
            hoja.merge_range('F8:G8', dict['diario_id'].currency_id.name)
            hoja.merge_range('B9:C9', 'Tipo de Cuenta:', formats['bold'])
            hoja.merge_range('D9:G9', dict['diario_id'].bank_account_id.account_type)
            hoja.merge_range('B10:G10', 'Datos de la Contabilidad', formats['bold_center'])
            hoja.merge_range('B11:C11', 'Nombre de la Cuenta Contable:', formats['bold'])
            hoja.merge_range('D11:G11', dict['diario_id'].default_account_id.name)
            hoja.merge_range('B12:C12', 'No. de Cuenta Contable:', formats['bold'])
            hoja.merge_range('D12:G12', dict['diario_id'].default_account_id.code)

            # --- Encabezado de tabla ---
            hoja.merge_range('B14:AE14','CONCILIACIÓN CUADRÁTICA MENSUAL (POR CUENTA BANCARIA)', formats['bold_center'])
            hoja.merge_range('B15:AE15','(Valores en Quetzales)', formats['center'])
            hoja.merge_range('C17:E17','CONCILIACIÓN DE SALDOS BANCARIOS', formats['table_subtitle_bold'])
            hoja.merge_range('F17:AE17','PERÍODOS ' + str(dict['year']), formats['table_subtitle_bold'])
            hoja.merge_range('C18:E18','CONCEPTOS', formats['table_subtitle_bold'])
            hoja.merge_range('F18:G18','ENERO', formats['table_subtitle_bold'])
            hoja.merge_range('H18:I18','FEBRERO', formats['table_subtitle_bold'])
            hoja.merge_range('J18:K18','MARZO', formats['table_subtitle_bold'])
            hoja.merge_range('L18:M18','ABRIL', formats['table_subtitle_bold'])
            hoja.merge_range('N18:O18','MAYO', formats['table_subtitle_bold'])
            hoja.merge_range('P18:Q18','JUNIO', formats['table_subtitle_bold'])
            hoja.merge_range('R18:S18','JULIO', formats['table_subtitle_bold'])
            hoja.merge_range('T18:U18','AGOSTO', formats['table_subtitle_bold'])
            hoja.merge_range('V18:W18','SEPTIEMBRE', formats['table_subtitle_bold'])
            hoja.merge_range('X18:Y18','OCTUBRE', formats['table_subtitle_bold'])
            hoja.merge_range('Z18:AA18','NOVIEMBRE', formats['table_subtitle_bold'])
            hoja.merge_range('AB18:AC18','DICIEMBRE', formats['table_subtitle_bold'])
            hoja.merge_range('AD18:AE18','TOTALES', formats['table_subtitle_bold'])


            # --- Saldo inicial ---
            hoja.merge_range('C19:E19','SALDO INICIAL SEGÚN BANCO', formats['bold'])
            col = 6
            for mes in range(0, 12):
                hoja.write(18, col, saldo_incial_mensual[mes], formats['numero'])
                col += 2
            hoja.write(18, col, sum(saldo_incial_mensual), formats['numero'])

            hoja.write('B20', '( + )', formats['bold'])
            hoja.merge_range('C20:E20','DEPÓSITOS', formats['bold'])

            # --- Cuentas por cobrar: Locales ---
            hoja.merge_range('C21:E21','Cuentas por cobrar clientes locales (hoja adjunta)', formats['bold'])
            col = 6
            for mes in range(0, 12):
                hoja.write(20, col, cxc_locales_mensual[mes], formats['numero'])
                col += 2
            hoja.write(20, col, sum(cxc_locales_mensual), formats['numero'])
            # Hoja 2 - lineas
            hoja_2 = libro.add_worksheet('Cuentas por Cobrar Clientes Locales')
            hoja_2.write(0, 0, 'Cuentas por Cobrar Clientes Locales', formats['bold'])
            hoja_2.write(1, 0, 'Documento', formats['table_subtitle_bold'])
            hoja_2.write(1, 1, 'Fecha', formats['table_subtitle_bold'])
            hoja_2.write(1, 2, 'Cliente', formats['table_subtitle_bold'])
            hoja_2.write(1, 3, 'Monto', formats['table_subtitle_bold'])
            fila_2 = 2
            for line in cxc_locales_lines:
                hoja_2.write(fila_2, 0, line['documento'])
                hoja_2.write(fila_2, 1, line['fecha'], formats['fecha'])
                hoja_2.write(fila_2, 2, line['cliente'])
                hoja_2.write(fila_2, 3, line['monto'], formats['numero'])
                fila_2 += 1

            # --- Cuentas por cobrar: Exteriores ---
            hoja.merge_range('C22:E22','Cuentas por cobrar clientes del exterior (hoja adjunta)', formats['bold'])
            col = 6
            for mes in range(0, 12):
                hoja.write(21, col, cxc_exterior_mensual[mes], formats['numero'])
                col += 2
            hoja.write(21, col, sum(cxc_exterior_mensual), formats['numero'])
            # Hoja 3 - lineas
            hoja_3 = libro.add_worksheet('Cuentas por Cobrar Clientes Exterior')
            hoja_3.write(0, 0, 'Cuentas por Cobrar Clientes Exterior', formats['bold'])
            hoja_3.write(1, 0, 'Documento', formats['table_subtitle_bold'])
            hoja_3.write(1, 1, 'Fecha', formats['table_subtitle_bold'])
            hoja_3.write(1, 2, 'Cliente', formats['table_subtitle_bold'])
            hoja_3.write(1, 3, 'Monto', formats['table_subtitle_bold'])
            fila_3 = 2
            for line in cxc_exterior_lines:
                hoja_3.write(fila_3, 0, line['documento'])
                hoja_3.write(fila_3, 1, line['fecha'], formats['fecha'])
                hoja_3.write(fila_3, 2, line['cliente'])
                hoja_3.write(fila_3, 3, line['monto'], formats['numero'])
                fila_3 += 1

            # --- Cuentas por cobrar: Relacionadas Locales y del Exterior ---
            hoja.merge_range('C23:E23','Cuentas y documentos por cobrar relacionadas locales y del exterior', formats['bold'])
            col = 6
            for mes in range(0, 12):
                hoja.write(22, col, cxc_local_exterior_mensual[mes], formats['numero'])
                col += 2
            # lineas
            hoja.write(22, col, sum(cxc_local_exterior_mensual), formats['numero'])
            hoja.write('C24','Empresa', formats['table_subtitle'])
            hoja.write('D24','Banco', formats['table_subtitle'])
            hoja.write('E24','No. Cuenta', formats['table_subtitle'])
            col = 5
            for mes in range(0, 12):
                hoja.write(23, col, "Valor", formats['bold_center'])
                col += 2
            fila = 24
            for line in cxc_local_exterior_lines:
                columna = 5 + (line['mes'] - 1) * 2
                hoja.write(fila, 2, line['empresa'])
                hoja.write(fila, 3, line['banco'])
                hoja.write(fila, 4, line['cuenta'])
                hoja.write(fila, columna, line['monto'], formats['numero'])
                fila += 1
            
            # --- Cuentas por cobrar: Socios ---
            hoja.merge_range(fila, 2, fila, 4,'Cuentas por cobrar a socios', formats['bold'])
            col = 6
            for mes in range(0, 12):
                hoja.write(fila, col, cxc_socios_mensual[mes], formats['numero'])
                col += 2
            hoja.write(fila, col, sum(cxc_socios_mensual), formats['numero'])
            # lineas
            hoja.write(fila+1, 2, 'Nombre del Socio', formats['table_subtitle'])
            hoja.write(fila+1, 3, 'Banco', formats['table_subtitle'])
            hoja.write(fila+1, 4, 'No. Cuenta', formats['table_subtitle'])
            col = 5
            for mes in range(0, 12):
                hoja.write(fila+1, col, "Valor", formats['bold_center'])
                col += 2
            fila += 2
            for line in cxc_socios_lines:
                columna = 5 + (line['mes'] - 1) * 2
                hoja.write(fila, 2, line['socio'])
                hoja.write(fila, 3, line['banco'])
                hoja.write(fila, 4, line['cuenta'])
                hoja.write(fila, columna, line['monto'], formats['numero'])
                fila += 1

            # --- Cuentas por cobrar: Empleados --- 
            hoja.merge_range(fila, 2, fila, 4,'Cuentas por cobrar a empleados', formats['bold'])
            col = 6
            for mes in range(0, 12):
                hoja.write(fila, col, cxc_empleados_mensual[mes], formats['numero'])
                col += 2
            hoja.write(fila, col, sum(cxc_empleados_mensual), formats['numero'])
            fila += 1

            # --- Anticipo a Clientes --- 
            hoja.merge_range(fila, 2, fila, 4,'Anticipo de clientes', formats['bold'])
            col = 6
            for mes in range(0, 12):
                hoja.write(fila, col, anticipo_clientes_mensual[mes], formats['numero'])
                col += 2
            hoja.write(fila, col, sum(anticipo_clientes_mensual), formats['numero'])
            fila += 1

            # --- Intereses Ganados --- 
            hoja.merge_range(fila, 2, fila, 4,'Intereses ganados', formats['bold'])
            col = 6
            for mes in range(0, 12):
                hoja.write(fila, col, intereses_ganados_mensual[mes], formats['numero'])
                col += 2
            hoja.write(fila, col, sum(intereses_ganados_mensual), formats['numero'])
            fila += 1

            # --- CXC Transferencias Interempresa --- 
            hoja.merge_range(fila, 2, fila, 4,'Trasferencia de fondos entre cuentas bancarias', formats['bold'])
            col = 6
            for mes in range(0, 12):
                hoja.write(fila, col, transfer_interempresa_mensual[mes], formats['numero'])
                col += 2
            hoja.write(fila, col, sum(transfer_interempresa_mensual), formats['numero'])
            # lineas
            hoja.write(fila+1, 2, 'Banco', formats['table_subtitle'])
            hoja.merge_range(fila+1, 3, fila+1, 4, 'No. De Cuenta ', formats['table_subtitle'])
            col = 5
            for mes in range(0, 12):
                hoja.write(fila+1, col, "Valor", formats['bold_center'])
                col += 2
            fila += 2
            for line in transfer_interempresa_lines:
                columna = 5 + (line['mes'] - 1) * 2
                hoja.write(fila, 2, line['banco'])
                hoja.merge_range(fila, 3, fila, 4,  line['cuenta'])
                hoja.write(fila, columna, line['monto'], formats['numero'])
                fila += 1
            
            # --- Otros ingresos --- 
            hoja.merge_range(fila, 2, fila, 4,'Otros ingresos', formats['bold'])
            col = 6
            for mes in range(0, 12):
                hoja.write(fila, col, otros_ingresos_mensual[mes], formats['numero'])
                col += 2
            hoja.write(fila, col, sum(otros_ingresos_mensual), formats['numero'])
            # lineas
            fila += 1
            for line in otros_ingresos_lines:
                columna = 5 + (line['mes'] - 1) * 2
                hoja.merge_range(fila, 2, fila, 4,  line['nota'])
                hoja.write(fila, columna, line['monto'], formats['numero'])
                fila += 1
            
            # --- Totales de ingresos --- 
            hoja.write(fila, 1, "A")
            hoja.merge_range(fila, 2, fila, 4,'TOTAL DEPÓSITOS DEL PERÍODO', formats['row_totals_bold'])
            col = 6
            for mes in range(0, 12):
                hoja.write(fila, col, total_ingresos_mensual[mes], formats['row_totals_number'])
                col += 2
            hoja.write(fila, col, sum(total_ingresos_mensual), formats['row_totals_number'])
            fila += 1
            
            
            hoja.write(fila, 1, '( - )', formats['bold'])
            hoja.merge_range(fila, 2, fila, 4,'EGRESOS', formats['bold'])
            fila += 1
            
            # --- Proveedores ---
            hoja.merge_range(fila, 2, fila, 4,'PROVEEDORES', formats['bold'])
            fila += 1

            # --- Gastos Operativos
            hoja.merge_range(fila, 2, fila, 4,'Gastos Operativos', formats['bold'])
            col = 6
            for mes in range(0, 12):
                hoja.write(fila, col, gastos_operativos_mensual[mes], formats['numero'])
                col += 2
            hoja.write(fila, col, sum(gastos_operativos_mensual), formats['numero'])
            fila += 1

            # --- Anticipos
            hoja.merge_range(fila, 2, fila, 4,'Pagos anticipados', formats['bold'])
            col = 6
            for mes in range(0, 12):
                hoja.write(fila, col, anticipos_mensual[mes], formats['numero'])
                col += 2
            hoja.write(fila, col, sum(anticipos_mensual), formats['numero'])
            fila += 1

            # --- Prestamos
            hoja.merge_range(fila, 2, fila, 4,'Pago a Préstamos ', formats['bold'])
            col = 6
            for mes in range(0, 12):
                hoja.write(fila, col, prestamos_mensual[mes], formats['numero'])
                col += 2
            hoja.write(fila, col, sum(prestamos_mensual), formats['numero'])
            # lineas
            hoja.write(fila+1, 2, 'Nombre', formats['table_subtitle'])
            hoja.write(fila+1, 3, 'Banco', formats['table_subtitle'])
            hoja.write(fila+1, 4, 'No. Cuenta', formats['table_subtitle'])
            col = 5
            for mes in range(0, 12):
                hoja.write(fila+1, col, "Valor", formats['bold_center'])
                col += 2
            fila += 2
            for line in prestamos_lines:
                columna = 5 + (line['mes'] - 1) * 2
                hoja.write(fila, 2, line['nombre'])
                hoja.write(fila, 3, line['banco'])
                hoja.write(fila, 4, line['cuenta'])
                hoja.write(fila, columna, line['monto'], formats['numero'])
                fila += 1
            
            # --- Dividendos
            hoja.merge_range(fila, 2, fila, 4,'Pago de dividendos', formats['bold'])
            col = 6
            for mes in range(0, 12):
                hoja.write(fila, col, dividendos_mensual[mes], formats['numero'])
                col += 2
            hoja.write(fila, col, sum(dividendos_mensual), formats['numero'])
            # lineas
            hoja.write(fila+1, 2, 'Nombre del socio', formats['table_subtitle'])
            hoja.write(fila+1, 3, 'Banco', formats['table_subtitle'])
            hoja.write(fila+1, 4, 'No. Cuenta', formats['table_subtitle'])
            col = 5
            for mes in range(0, 12):
                hoja.write(fila+1, col, "Valor", formats['bold_center'])
                col += 2
            fila += 2
            for line in dividendos_lines:
                columna = 5 + (line['mes'] - 1) * 2
                hoja.write(fila, 2, line['socio'])
                hoja.write(fila, 3, line['banco'])
                hoja.write(fila, 4, line['cuenta'])
                hoja.write(fila, columna, line['monto'], formats['numero'])
                fila += 1
            if otras_dividendos_mensual:
                hoja.write(fila, 2, "Agrupación")
                col = 5
                for mes in range(0, 12):
                    hoja.write(fila, col, otras_dividendos_mensual[mes], formats['numero'])
                    col += 2
                fila += 1
            
            # --- Cuentas por pagar: Socios ---
            hoja.merge_range(fila, 2, fila, 4,'Cuentas por pagar socios (hoja adjunta)', formats['bold'])
            col = 6
            for mes in range(0, 12):
                hoja.write(fila, col, cxp_socios_mensual[mes], formats['numero'])
                col += 2
            hoja.write(fila, col, sum(cxp_socios_mensual), formats['numero'])
            # Hoja 4 - lineas
            hoja_4 = libro.add_worksheet('Cuentas por Pagar Socios')
            hoja_4.write(0, 0, 'Cuentas por Pagar Socios', formats['bold'])
            hoja_4.write(1, 0, 'Nombre del socio', formats['table_subtitle_bold'])
            hoja_4.write(1, 1, 'Banco', formats['table_subtitle_bold'])
            hoja_4.write(1, 2, 'No. Cuenta', formats['table_subtitle_bold'])
            hoja_4.write(1, 3, 'Valor', formats['table_subtitle_bold'])
            fila_4 = 2
            for line in cxp_socios_lines:
                hoja_4.write(fila_4, 0, line['socio'])
                hoja_4.write(fila_4, 1, line['banco'])
                hoja_4.write(fila_4, 2, line['cuenta'])
                hoja_4.write(fila_4, 3, line['monto'], formats['numero'])
                fila_4 += 1
            fila += 1
            
            # --- Cuentas por pagar: Relacionadas Locales ---
            hoja.merge_range(fila, 2, fila, 4,'Cuentas por pagar relacionadas locales (hoja adjunta)', formats['bold'])
            col = 6
            for mes in range(0, 12):
                hoja.write(fila, col, cxp_relacionadas_locales_mensual[mes], formats['numero'])
                col += 2
            hoja.write(fila, col, sum(cxp_relacionadas_locales_mensual), formats['numero'])
            # Hoja 5 - lineas
            hoja_5 = libro.add_worksheet('Cuentas por Relacionadas Locales')
            hoja_5.write(0, 0, 'Cuentas por Pagar Relacionadas Locales', formats['bold'])
            hoja_5.write(1, 0, 'Empresa', formats['table_subtitle_bold'])
            hoja_5.write(1, 1, 'Banco', formats['table_subtitle_bold'])
            hoja_5.write(1, 2, 'No. Cuenta', formats['table_subtitle_bold'])
            hoja_5.write(1, 3, 'Valor', formats['table_subtitle_bold'])
            fila_5 = 2
            for line in cxp_relacionadas_locales_lines:
                hoja_5.write(fila_5, 0, line['empresa'])
                hoja_5.write(fila_5, 1, line['banco'])
                hoja_5.write(fila_5, 2, line['cuenta'])
                hoja_5.write(fila_5, 3, line['monto'], formats['numero'])
                fila_5 += 1
            fila += 1

            # --- Cuentas por pagar: Relacionadas del Exterior ---
            hoja.merge_range(fila, 2, fila, 4,'Cuentas por pagar relacionadas del exterior (hoja adjunta)', formats['bold'])
            col = 6
            for mes in range(0, 12):
                hoja.write(fila, col, cxp_relacionadas_exterior_mensual[mes], formats['numero'])
                col += 2
            hoja.write(fila, col, sum(cxp_relacionadas_exterior_mensual), formats['numero'])
            # Hoja 6 - lineas
            hoja_6 = libro.add_worksheet('Cuentas por Relacionadas del Exterior')
            hoja_6.write(0, 0, 'Cuentas por Pagar Relacionadas del Exterior', formats['bold'])
            hoja_6.write(1, 0, 'Empresa', formats['table_subtitle_bold'])
            hoja_6.write(1, 1, 'Banco', formats['table_subtitle_bold'])
            hoja_6.write(1, 2, 'No. Cuenta', formats['table_subtitle_bold'])
            hoja_6.write(1, 3, 'Valor', formats['table_subtitle_bold'])
            fila_6 = 2
            for line in cxp_relacionadas_exterior_lines:
                hoja_6.write(fila_6, 0, line['empresa'])
                hoja_6.write(fila_6, 1, line['banco'])
                hoja_6.write(fila_6, 2, line['cuenta'])
                hoja_6.write(fila_6, 3, line['monto'], formats['numero'])
                fila_6 += 1
            fila += 1
            
            # --- CXP Transferencias Interempresa --- 
            hoja.merge_range(fila, 2, fila, 4,'Egreso por trasferencia de fondos entre cuentas bancarias (hoja adjunta)', formats['bold'])
            col = 6
            for mes in range(0, 12):
                hoja.write(fila, col, cxp_transfer_interempresa_mensual[mes], formats['numero'])
                col += 2
            hoja.write(fila, col, sum(cxp_transfer_interempresa_mensual), formats['numero'])
            # Hoja 7 - lineas
            hoja_7 = libro.add_worksheet('Cuentas por Pagar Transferencias Interempresa')
            hoja_7.write(0, 0, 'Cuentas por Pagar Transferencias Interempresa', formats['bold'])
            hoja_7.write(1, 0, 'Banco', formats['table_subtitle_bold'])
            hoja_7.write(1, 1, 'No. Cuenta', formats['table_subtitle_bold'])
            hoja_7.write(1, 2, 'Valor', formats['table_subtitle_bold'])
            fila_7 = 2
            for line in cxp_transfer_interempresa_lines:
                hoja_7.write(fila_7, 0, line['banco'])
                hoja_7.write(fila_7, 1, line['cuenta'])
                hoja_7.write(fila_7, 2, line['monto'], formats['numero'])
                fila_7 += 1
            fila += 1

            # --- Otros egresos --- 
            hoja.merge_range(fila, 2, fila, 4,'Otros egresos', formats['bold'])
            col = 6
            for mes in range(0, 12):
                hoja.write(fila, col, otros_egresos_mensual[mes], formats['numero'])
                col += 2
            hoja.write(fila, col, sum(otros_egresos_mensual), formats['numero'])
            # lineas
            fila += 1
            for line in otros_egresos_lines:
                columna = 5 + (line['mes'] - 1) * 2
                hoja.merge_range(fila, 2, fila, 4,  line['nota'])
                hoja.write(fila, columna, line['monto'], formats['numero'])
                fila += 1
            
            # --- Totales de egresos --- 
            hoja.write(fila, 1, "B")
            hoja.merge_range(fila, 2, fila, 4,'TOTAL EGRESOS', formats['row_totals_bold'])
            col = 6
            for mes in range(0, 12):
                hoja.write(fila, col, total_egresos_mensual[mes], formats['row_totals_number'])
                col += 2
            hoja.write(fila, col, sum(total_egresos_mensual), formats['row_totals_number'])
            fila += 1

            # --- Ingresos menos egresos --- 
            hoja.merge_range(fila, 2, fila, 4,'SALDO FINAL BANCARIO  ( A - B )', formats['bold'])
            col = 6
            for mes in range(0, 12):
                hoja.write(fila, col, total_ingresos_mensual[mes] - total_egresos_mensual[mes], formats['row_totals_number'])
                col += 2
            fila += 1

            hoja.merge_range(fila, 2, fila, 4,'AJUSTES', formats['bold'])
            fila += 1
            hoja.write(fila, 1, '( + )', formats['bold'])
            hoja.merge_range(fila, 2, fila, 4,'Depósitos en Tránsito', formats['bold'])
            col = 6
            for mes in range(0, 12):
                hoja.write(fila, col, depositos_transito_mensual[mes], formats['numero'])
                col += 2
            hoja.write(fila, col, depositos_transito_mensual[11], formats['numero'])
            fila += 1

            hoja.write(fila, 1, '( - )', formats['bold'])
            hoja.merge_range(fila, 2, fila, 4,'Cheques en circulación', formats['bold'])
            col = 6
            for mes in range(0, 12):
                hoja.write(fila, col, cheques_transito_mensual[mes], formats['numero'])
                col += 2
            hoja.write(fila, col, cheques_transito_mensual[11], formats['numero'])
            fila += 1

            # --- Otros Ajustes --- 
            hoja.merge_range(fila, 2, fila, 4,'Otros ajustes', formats['bold'])
            col = 6
            for mes in range(0, 12):
                hoja.write(fila, col, otros_ajustes_mensual[mes], formats['numero'])
                col += 2
            hoja.write(fila, col, sum(otros_ajustes_mensual), formats['numero'])
            # lineas
            fila += 1
            for line in otros_ajustes:
                columna = 5 + (line.date.month - 1) * 2
                hoja.merge_range(fila, 2, fila, 4,  line.descripcion)
                hoja.write(fila, columna, line.amount, formats['numero'])
                fila += 1
            
            # --- Saldo Conciliado --- 
            hoja.merge_range(fila, 2, fila, 4,'SALDO CONCILIADO', formats['row_totals_bold'])
            col = 6
            for mes in range(0, 12):
                hoja.write(fila, col, total_ingresos_mensual[mes] - total_egresos_mensual[mes] - otros_ajustes_mensual[mes], formats['row_totals_number'])
                col += 2
            fila += 1

            # --- Saldo final segun libros y Ajustes finales --- 
            hoja.merge_range(fila, 2, fila, 4,'SALDO FINAL SEGÚN LIBROS', formats['bold'])
            col = 6
            for mes in range(0, 12):
                hoja.write(fila, col, saldo_final_mensual[mes], formats['numero'])
                col += 2
            hoja.write(fila, col, sum(saldo_final_mensual), formats['numero'])
            fila += 1
            
            hoja.merge_range(fila, 2, fila, 4,'AJUSTES', formats['bold'])
            fila += 1
            hoja.write(fila, 1, '( + )', formats['bold'])
            hoja.merge_range(fila, 2, fila, 4,'Ingresos por intereses ganados', formats['bold'])
            col = 6
            for mes in range(0, 12):
                hoja.write(fila, col, intereses_ganados_mensual[mes], formats['numero'])
                col += 2
            hoja.write(fila, col, sum(intereses_ganados_mensual), formats['numero'])
            fila += 1
            for line in intereses_ganados:
                columna = 5 + (line.date.month - 1) * 2
                hoja.merge_range(fila, 2, fila, 4,  line.descripcion)
                hoja.write(fila, columna, line.amount, formats['numero'])
                fila += 1

            hoja.write(fila, 1, '( - )', formats['bold'])
            hoja.merge_range(fila, 2, fila, 4,'Notas de débito no operadas', formats['bold'])
            col = 6
            for mes in range(0, 12):
                hoja.write(fila, col, notas_debito_mensual[mes], formats['numero'])
                col += 2
            hoja.write(fila, col, sum(notas_debito_mensual), formats['numero'])
            fila += 1
            for line in notas_debito:
                columna = 5 + (line.date.month - 1) * 2
                hoja.merge_range(fila, 2, fila, 4,  line.descripcion)
                hoja.write(fila, columna, line.amount, formats['numero'])
                fila += 1

            hoja.merge_range(fila, 2, fila, 4,'Otros ajustes finales', formats['bold'])
            col = 6
            for mes in range(0, 12):
                hoja.write(fila, col, ajustes_finales_mensual[mes], formats['numero'])
                col += 2
            hoja.write(fila, col, sum(ajustes_finales_mensual), formats['numero'])
            fila += 1
            for line in ajustes_finales:
                columna = 5 + (line.date.month - 1) * 2
                hoja.merge_range(fila, 2, fila, 4,  line.descripcion)
                hoja.write(fila, columna, line.amount, formats['numero'])
                fila += 1

            # --- Saldo Conciliado --- 
            hoja.merge_range(fila, 2, fila, 4,'SALDO CONCILIADO', formats['row_totals_bold'])
            col = 6
            for mes in range(0, 12):
                hoja.write(fila, col, saldo_final_mensual[mes] + intereses_ganados_mensual[mes] - notas_debito_mensual[mes] - ajustes_finales_mensual[mes], formats['row_totals_number'])
                col += 2
            fila += 1

            libro.close()
            datos = base64.b64encode(f.getvalue())
            self.write({'archivo':datos, 'name':'reporte_conciliacion_cuadratica.xlsx'})
        return {
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'conciliacion_cuadratica.reporte_conciliacion_wizard',
            'res_id': self.id,
            'view_id': False,
            'type': 'ir.actions.act_window',
            'target': 'new',
        }


class ReportConciliacionAjusteWizard(models.TransientModel):
    _name = 'conciliacion_cuadratica.reporte_ajuste_wizard'

    wizard_id = fields.Many2one(
        'conciliacion_cuadratica.reporte_conciliacion_wizard',
        string="Conciliación cuadrática wizard",
        required=True,
        ondelete='cascade'
    )
    descripcion = fields.Char("Descripción", required=True)
    amount = fields.Float("Monto", required=True)
    date = fields.Date("Fecha", required=True)
    tipo = fields.Selection([
        ('otros_ajustes', 'Otros Ajustes'),
        ('intereses_ganados', 'Ingresos por Intereses Ganados'),
        ('notas_debito', 'Notas de Débito No Operadas'),
        ('ajustes_finales', 'Ajustes Finales')
    ], string="Tipo de Ajuste", required=True)