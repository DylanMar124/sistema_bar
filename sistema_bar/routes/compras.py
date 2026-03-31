from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required, current_user
from extensions import db
from models import Ingrediente, Compra, CompraDetalle
from datetime import datetime

compras_bp = Blueprint('compras', __name__, url_prefix='/compras')

def admin_required(f):
    from functools import wraps
    @wraps(f)
    def decorated(*args, **kwargs):
        if not current_user.is_authenticated or current_user.rol != 'admin':
            flash('Acceso no autorizado', 'danger')
            return redirect(url_for('index'))
        return f(*args, **kwargs)
    return decorated

@compras_bp.route('/')
@login_required
@admin_required
def lista_compras():
    compras = Compra.query.order_by(Compra.fecha.desc()).all()
    return render_template('compras.html', compras=compras)

@compras_bp.route('/nueva', methods=['GET', 'POST'])
@login_required
@admin_required
def nueva_compra():
    if request.method == 'POST':
        # Datos de la cabecera
        proveedor = request.form.get('proveedor', '').strip()
        factura = request.form.get('factura', '').strip()
        observaciones = request.form.get('observaciones', '').strip()

        # Crear la compra
        compra = Compra(
            proveedor=proveedor if proveedor else None,
            factura=factura if factura else None,
            observaciones=observaciones if observaciones else None
        )
        db.session.add(compra)
        db.session.flush()  # para obtener el id antes de commit

        # Procesar los detalles (vienen en arrays)
        ingredientes_ids = request.form.getlist('ingrediente_id[]')
        cantidades = request.form.getlist('cantidad[]')
        precios = request.form.getlist('precio_unitario[]')

        for i in range(len(ingredientes_ids)):
            if not ingredientes_ids[i] or not cantidades[i]:
                continue
            ingrediente_id = int(ingredientes_ids[i])
            cantidad = float(cantidades[i])
            precio = float(precios[i]) if precios[i] else None

            detalle = CompraDetalle(
                compra_id=compra.id,
                ingrediente_id=ingrediente_id,
                cantidad=cantidad,
                precio_unitario=precio
            )
            db.session.add(detalle)

            # Actualizar stock del ingrediente
            ingrediente = Ingrediente.query.get(ingrediente_id)
            ingrediente.stock_actual += cantidad

        db.session.commit()
        flash(f'Compra #{compra.id} registrada con éxito', 'success')
        return redirect(url_for('compras.lista_compras'))

    # GET: mostrar formulario
    ingredientes = Ingrediente.query.order_by(Ingrediente.nombre).all()
    return render_template('nueva_compra.html', ingredientes=ingredientes)

@compras_bp.route('/<int:compra_id>')
@login_required
@admin_required
def ver_compra(compra_id):
    compra = Compra.query.get_or_404(compra_id)
    return render_template('ver_compra.html', compra=compra)

# Opcional: eliminar compra (con cuidado)
@compras_bp.route('/<int:compra_id>/eliminar', methods=['POST'])
@login_required
@admin_required
def eliminar_compra(compra_id):
    compra = Compra.query.get_or_404(compra_id)
    # Primero revertir el stock (opcional, podría ser peligroso)
    for detalle in compra.detalles:
        ingrediente = detalle.ingrediente
        ingrediente.stock_actual -= detalle.cantidad
    db.session.delete(compra)
    db.session.commit()
    flash(f'Compra #{compra_id} eliminada y stock revertido', 'success')
    return redirect(url_for('compras.lista_compras'))