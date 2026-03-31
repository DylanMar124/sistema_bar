from flask import Blueprint, redirect, render_template, request, flash, url_for
from flask_login import login_required
from extensions import db
from models import Orden, DetalleOrden, Producto, Pago
from sqlalchemy import func
from datetime import datetime, timedelta
from models import Ingrediente
from models import Usuario
from datetime import datetime
import pytz

mexico_tz = pytz.timezone('America/Mexico_City')

reportes_bp = Blueprint('reportes', __name__, url_prefix='/reportes')

@reportes_bp.route('/ventas-por-mesero/print')
@login_required
def ventas_por_mesero_print():
    hoy = datetime.now().date()
    fecha_inicio_str = request.args.get('fecha_inicio', hoy.strftime('%Y-%m-%d'))
    fecha_fin_str = request.args.get('fecha_fin', hoy.strftime('%Y-%m-%d'))

    try:
        fecha_inicio = mexico_tz.localize(datetime.strptime(fecha_inicio_str, '%Y-%m-%d'))
        fecha_fin = mexico_tz.localize(datetime.strptime(fecha_fin_str, '%Y-%m-%d') + timedelta(days=1))
    except ValueError:
        flash('Formato de fecha inválido', 'danger')
        return redirect(url_for('reportes.index'))

    resultados = db.session.query(
        Usuario.nombre,
        func.count(Orden.id).label('cantidad_ordenes'),
        func.sum(Orden.total).label('total_vendido')
    ).join(Orden, Orden.mesero_id == Usuario.id).filter(
        Orden.estado == 'pagada',
        Orden.fecha_hora >= fecha_inicio,
        Orden.fecha_hora < fecha_fin
    ).group_by(Usuario.id).order_by(func.sum(Orden.total).desc()).all()

    total_general = sum(r.total_vendido for r in resultados)

    return render_template('reportes/ventas_por_mesero_print.html',
                           fecha_inicio=fecha_inicio_str,
                           fecha_fin=fecha_fin_str,
                           resultados=resultados,
                           total_general=total_general)

@reportes_bp.route('/stock-critico/print')
@login_required
def stock_critico_print():
    ingredientes = Ingrediente.query.filter(Ingrediente.stock_actual < Ingrediente.stock_minimo).all()
    return render_template('reportes/stock_critico_print.html', ingredientes=ingredientes)

@reportes_bp.route('/cierre-caja/print')
@login_required
def cierre_caja_print():
    hoy = datetime.now().date()
    inicio = datetime.combine(hoy, datetime.min.time())
    fin = datetime.combine(hoy, datetime.max.time())

    ordenes = Orden.query.filter(
        Orden.estado == 'pagada',
        Orden.fecha_hora >= inicio,
        Orden.fecha_hora <= fin
    ).all()

    total = sum(o.total for o in ordenes)
    cantidad = len(ordenes)

    pagos = db.session.query(
        Pago.metodo_pago,
        func.count(Pago.id),
        func.sum(Pago.monto)
    ).join(Orden).filter(
        Orden.estado == 'pagada',
        Orden.fecha_hora >= inicio,
        Orden.fecha_hora <= fin
    ).group_by(Pago.metodo_pago).all()

    return render_template('reportes/cierre_caja_print.html',
                           fecha=hoy,
                           total=total,
                           cantidad=cantidad,
                           pagos=pagos,
                           ordenes=ordenes)