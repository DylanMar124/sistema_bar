from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required, current_user
from functools import wraps
from extensions import db
from models import Orden
from models import Orden, DetalleOrden, Producto, Pago, Mesa, Receta

ordenes_bp = Blueprint('ordenes', __name__, url_prefix='/ordenes')

def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or current_user.rol != 'admin':
            flash('Acceso no autorizado', 'info')
            return redirect(url_for('index'))
        return f(*args, **kwargs)
    return decorated_function

@ordenes_bp.route('/')
@login_required
def lista_ordenes():
    ordenes = Orden.query.order_by(Orden.fecha_hora.desc()).all()
    return render_template('ordenes.html', ordenes=ordenes)

@ordenes_bp.route('/<int:orden_id>/cancelar')
@login_required
@admin_required
def cancelar_orden(orden_id):
    orden = Orden.query.get_or_404(orden_id)

    orden.estado = 'cancelada'
    orden.total = 0.0

    # Liberar la mesa
    mesa = Mesa.query.get(orden.mesa_id)
    mesa.estado = 'libre'
    
    for detalle in orden.detalles:
        producto = detalle.producto
        cantidad_vendida = detalle.cantidad
        recetas = Receta.query.filter_by(producto_id=producto.id).all()
        for receta in recetas:
            ingrediente = receta.ingrediente
            cantidad_necesaria = receta.cantidad * cantidad_vendida
            ingrediente.stock_actual += cantidad_necesaria
        
    db.session.commit()
    
    flash('Orden cancelada', 'success')
    return redirect(url_for('ordenes.lista_ordenes'))