# -*- encoding: utf-8 -*-

from odoo import api, models
from datetime import date
import logging

class ReporteConciliacionCuadratica(models.AbstractModel):
    _name = 'report.conciliacion_cuadratica.reporte_conciliacion'
    _description = 'Reporte de Conciliación Cuadrática'

    def saldo_inicial_por_mes(self, datos):
        cuenta_id = datos['cuenta_id'].id
        year = int(datos['year'])
        year_inicio = f"{year}-01-01"
        next_year_inicio = f"{year+1}-01-01"

        self.env.cr.execute("""
            SELECT
                CASE
                    WHEN date < %s THEN 0
                    ELSE EXTRACT(MONTH FROM date)::int
                END AS mes_index,
                COALESCE(SUM(debit) - SUM(credit), 0) AS monto
            FROM account_move_line
            WHERE account_id = %s
            AND parent_state = 'posted'
            AND date < %s
            GROUP BY mes_index
            ORDER BY mes_index
        """, (year_inicio, cuenta_id, next_year_inicio))
        meses_data = self.env.cr.dictfetchall()
        montos_por_mes = {int(md['mes_index']): float(md['monto']) for md in meses_data}
        balance_acumulado = montos_por_mes.get(0, 0.0)
        
        saldo_incial_mensual = []
        for mes in range(1, 13):
            saldo_incial_mensual.append(balance_acumulado)
            balance_acumulado += montos_por_mes.get(mes, 0.0)

        saldo_final_mensual = []
        for mes in range(1, 13):
            balance_acumulado += montos_por_mes.get(mes, 0.0)
            saldo_final_mensual.append(balance_acumulado)
        resultados = [saldo_incial_mensual, saldo_final_mensual]
        return resultados

    def filtrar_movimientos_por_tipo_conciliacion(self, tipo_pago, pagos=[], apuntes=[], tipo_conciliacion=None, pago_conciliacion=None, origen=None):
        if pagos:
            if tipo_pago == 'inbound':
                pagos = pagos.filtered(lambda p: p.payment_type == 'inbound')
            else:
                pagos = pagos.filtered(lambda p: p.payment_type == 'outbound')

        #filtros de ingresos
        if tipo_conciliacion == 'cxc_local':
            pagos = pagos.filtered(
                lambda p: not p.tipo_conciliacion_cuadratica and 
                        (p.partner_id.country_id.code == 'GT' or not p.partner_id.country_id))
        elif tipo_conciliacion == 'cxc_exterior':
            pagos = pagos.filtered(
                lambda p: not p.tipo_conciliacion_cuadratica and 
                        (p.partner_id.country_id and p.partner_id.country_id.code != 'GT'))
        elif tipo_conciliacion == 'cxc_interempresa':
            pagos = pagos.filtered(lambda p: p.tipo_conciliacion_cuadratica == 'CXC Interempresa')
        elif tipo_conciliacion == 'cxc_socios':
            apuntes = apuntes.filtered(lambda p: p.tipo_conciliacion_cuadratica == 'CXC Socios')
        elif tipo_conciliacion == 'cxc_empleados':
            pagos = pagos.filtered(lambda p: p.tipo_conciliacion_cuadratica == 'CXC Empleados')
            apuntes = apuntes.filtered(lambda p: p.tipo_conciliacion_cuadratica == 'CXC Empleados')
        elif tipo_conciliacion == 'anticipo_clientes':
            pagos = pagos.filtered(lambda p: p.tipo_conciliacion_cuadratica == 'CXC Anticipo a Clientes')
            apuntes = apuntes.filtered(lambda p: p.tipo_conciliacion_cuadratica == 'CXC Anticipo a Clientes')
        elif tipo_conciliacion == 'intereses_ganados':
            apuntes = apuntes.filtered(lambda p: p.tipo_conciliacion_cuadratica == 'CXC Intereses Ganados')
        elif tipo_conciliacion == 'transfer_interempresa':
            apuntes = apuntes.filtered(lambda p: p.tipo_conciliacion_cuadratica == 'CXC Transferencias Interempresa')
        elif tipo_conciliacion == 'otros_ingresos':
            pagos = pagos.filtered(lambda p: p.tipo_conciliacion_cuadratica == 'CXC Otros Ingresos')

        #filtros de egresos
        if pago_conciliacion == 'gastos_operativos':
            pagos = pagos.filtered(lambda p: p.tipo_conciliacion_cuadratica == 'CXP Gastos Operativos')
        elif pago_conciliacion == 'anticipos':
            pagos = pagos.filtered(lambda p: p.tipo_conciliacion_cuadratica == 'CXP Anticipos')
            apuntes = apuntes.filtered(lambda p: p.tipo_conciliacion_cuadratica == 'CXP Anticipos')
        elif pago_conciliacion == 'prestamos':
            apuntes = apuntes.filtered(lambda p: p.tipo_conciliacion_cuadratica == 'CXP Prestamos')
        elif pago_conciliacion == 'dividendos':
            pagos = pagos.filtered(lambda p: p.tipo_conciliacion_cuadratica == 'CXP Dividendos')
            apuntes = apuntes.filtered(lambda p: p.tipo_conciliacion_cuadratica == 'CXP Dividendos')
        elif pago_conciliacion == 'cxp_socios':
            apuntes = apuntes.filtered(lambda p: p.tipo_conciliacion_cuadratica == 'CXP Socios')
        elif pago_conciliacion == 'cxp_relacionadas_locales':
            apuntes = apuntes.filtered(lambda p: p.tipo_conciliacion_cuadratica == 'CXP Relacionadas Locales')
        elif pago_conciliacion == 'cxp_relacionadas_exterior':
            apuntes = apuntes.filtered(
                lambda t: not t.tipo_conciliacion_cuadratica and
                        (t.partner_id.country_id and t.partner_id.country_id.code != 'GT') and t.amount < 0)
        elif pago_conciliacion == 'transfer_interempresa':
            apuntes = apuntes.filtered(lambda p: p.tipo_conciliacion_cuadratica == 'CXP Transferencias Interempresa')
        elif pago_conciliacion == 'otros_egresos':
            pagos = pagos.filtered(lambda p: p.tipo_conciliacion_cuadratica == 'CXP Otros Egresos')

        return {
            'pagos': pagos,
            'apuntes': apuntes,
        }

    def obtener_montos_mensuales(self, datos):
        totales = [0.0] * 12
        for d in datos:
            mes = d.date.month
            totales[mes-1] += d.amount
        return totales
    
    def obtener_totales_mensuales(self, datos):
        totales = [0.0] * 12
        for mes in range(0, 12):
            for d in datos:
                totales[mes] += d[mes]
        return totales

    def obtener_montos_apuntes_por_mes(self, lineas, year):
        final = [0.0] * 12
        transito = [0.0] * 12

        for l in lineas:
            fecha_origen = l.date
            fecha_conciliado = l.date_conciliado

            # No conciliado
            if not l.is_reconciled or not fecha_conciliado:
                cursor = date(fecha_origen.year, fecha_origen.month, 1)
                while cursor.year <= year and cursor.month <= 12:
                    if cursor.year == year:
                        transito[cursor.month-1] += l.amount
                    # avanzar mes
                    if cursor.month == 12:
                        cursor = date(cursor.year + 1, 1, 1)
                    else:
                        cursor = date(cursor.year, cursor.month + 1, 1)
                continue

            # Conciliado
            cursor = date(fecha_origen.year, fecha_origen.month, 1)
            fin = date(fecha_conciliado.year, fecha_conciliado.month, 1)
            while cursor < fin:
                if cursor.year == year:
                    transito[cursor.month-1] += l.amount
                if cursor.month == 12:
                    cursor = date(cursor.year + 1, 1, 1)
                else:
                    cursor = date(cursor.year, cursor.month + 1, 1)

            # Mes de conciliación se guarda en final
            if fecha_conciliado.year == year:
                final[fecha_conciliado.month-1] += l.amount
        return {
            'final': final,
            'transito': transito
        }

    def sumar_pagos_apuntes(self, p, t):
        return [p[i] + t[i] for i in range(12)]
