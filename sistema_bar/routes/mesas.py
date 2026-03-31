from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required, current_user
from functools import wraps
from extensions import db
from models import Mesa
from models import Orden, DetalleOrden, Producto, Pago
from models import Receta, Ingrediente

mesas_bp = Blueprint('mesas', __name__, url_prefix='/mesas')

def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or current_user.rol != 'admin':
            flash('Acceso no autorizado', 'danger')
            return redirect(url_for('index'))
        return f(*args, **kwargs)
    return decorated_function

@mesas_bp.route('/')
@login_required
def lista_mesas():
    mesas = Mesa.query.where(Mesa.estado != 'desactivada')
    return render_template('mesas.html', mesas=mesas)

@mesas_bp.route('/crear', methods=['POST'])
@login_required
def crear_mesa():
    numero = request.form['numero']
    capacidad = request.form['capacidad']
    
    # Verificar si ya existe
    if Mesa.query.filter_by(numero=numero).first():
        flash('Esta mesa ya existe', 'info')
        return redirect(url_for('mesas.lista_mesas'))
    
    nuevo = Mesa(
        numero=numero,
        capacidad=capacidad,
        estado='libre'
    )
    db.session.add(nuevo)
    db.session.commit()

    flash('Mesa creada correctamente', 'success')
    return redirect(url_for('mesas.lista_mesas'))

@mesas_bp.route('/editar/<int:mesa_id>', methods=['POST'])
@login_required
@admin_required
def editar_mesa(mesa_id):
    mesa = Mesa.query.get_or_404(mesa_id)
    numero = request.form['numero']
    capacidad = request.form['capacidad']
    
    # Verificar si ya existe otra mesa con el mismo número
    existe = Mesa.query.filter(Mesa.numero == numero, Mesa.id != mesa_id).first()
    if existe:
        flash('Ya existe otra mesa con ese número', 'info')
        return redirect(url_for('mesas.lista_mesas'))
    
    mesa.numero = numero
    mesa.capacidad = capacidad
    db.session.commit()
    
    flash('Mesa actualizada correctamente', 'success')
    return redirect(url_for('mesas.lista_mesas'))

@mesas_bp.route('/eliminar/<int:mesa_id>', methods=['POST'])
@login_required
@admin_required
def eliminar_mesa(mesa_id):
    mesa = Mesa.query.get_or_404(mesa_id)
    
    if mesa.estado == 'ocupada':
        flash('No se puede eliminar una mesa ocupada', 'info')
        return redirect(url_for('mesas.lista_mesas'))
    
    mesa.estado = 'desactivada'
    db.session.commit()
    
    flash('Mesa eliminada correctamente', 'success')
    return redirect(url_for('mesas.lista_mesas'))

@mesas_bp.route('/<int:mesa_id>/orden')
@login_required
def ver_orden(mesa_id):
    mesa = Mesa.query.get_or_404(mesa_id)
    
    # Buscar una orden abierta para esta mesa
    orden = Orden.query.filter_by(mesa_id=mesa.id, estado='abierta').first()
    
    # Si no existe, la creamos automáticamente y marcamos la mesa como ocupada
    if not orden:
        orden = Orden(
            mesa_id=mesa.id,
            mesero_id=current_user.id,
            estado='abierta'
        )
        db.session.add(orden)
        mesa.estado = 'ocupada'
        db.session.commit()
        flash('Nueva orden creada para esta mesa', 'info')
    
    productos = Producto.query.filter_by(activo=True).all()
    return render_template('orden.html', orden=orden, mesa=mesa, productos=productos)

@mesas_bp.route('/orden/<int:orden_id>/agregar', methods=['POST'])
@login_required
def agregar_producto(orden_id):
    orden = Orden.query.get_or_404(orden_id)
    
    # Verificar que la orden esté abierta
    if orden.estado != 'abierta':
        flash('La orden no está abierta', 'info')
        return redirect(url_for('mesas.lista_mesas'))
    
    producto_id = request.form['producto_id']
    cantidad = int(request.form['cantidad'])
    
    producto = Producto.query.get_or_404(producto_id)
    
    # Verificar si ya existe un detalle para ese producto
    detalle = DetalleOrden.query.filter_by(orden_id=orden.id, producto_id=producto.id).first()
    
    if detalle:
        detalle.cantidad += cantidad
    else:
        detalle = DetalleOrden(
            orden_id=orden.id,
            producto_id=producto.id,
            cantidad=cantidad,
            precio_unitario=producto.precio
        )
        db.session.add(detalle)
    
    # Actualizar total de la orden
    orden.total = sum(d.subtotal for d in orden.detalles)
    db.session.commit()
    
    return redirect(url_for('mesas.ver_orden', mesa_id=orden.mesa_id))

@mesas_bp.route('/orden/<int:orden_id>/quitar/<int:detalle_id>')
@login_required
def quitar_producto(orden_id, detalle_id):
    orden = Orden.query.get_or_404(orden_id)
    detalle = DetalleOrden.query.get_or_404(detalle_id)
    
    if detalle.orden_id != orden.id:
        flash('No se encontro la orden', 'info')
        return redirect(url_for('mesas.lista_mesas'))
    
    db.session.delete(detalle)
    orden.total = sum(d.subtotal for d in orden.detalles)
    db.session.commit()
    
    return redirect(url_for('mesas.ver_orden', mesa_id=orden.mesa_id))

@mesas_bp.route('/orden/<int:orden_id>/pagar', methods=['POST'])
@login_required
def pagar_orden(orden_id):
    orden = Orden.query.get_or_404(orden_id)
    
    if orden.estado != 'abierta':
        flash('La orden ya está pagada o cancelada', 'info')
        return redirect(url_for('mesas.ver_orden', mesa_id=orden.mesa_id))
    
    metodo = request.form['metodo_pago']
    monto_recibido = float(request.form.get('monto_recibido', 0))
    
    # Registrar pago
    pago = Pago(
        orden_id=orden.id,
        monto=orden.total,
        metodo_pago=metodo
    )
    db.session.add(pago)
    
    # Cambiar estado de la orden a pagada
    orden.estado = 'pagada'
    
    # Liberar la mesa
    mesa = Mesa.query.get(orden.mesa_id)
    mesa.estado = 'libre'
    
    # Descontar stock de ingredientes según recetas
    for detalle in orden.detalles:
        producto = detalle.producto
        cantidad_vendida = detalle.cantidad
        recetas = Receta.query.filter_by(producto_id=producto.id).all()
        for receta in recetas:
            ingrediente = receta.ingrediente
            cantidad_necesaria = receta.cantidad * cantidad_vendida
            if ingrediente.stock_actual < cantidad_necesaria:
                flash(f'Stock insuficiente de {ingrediente.nombre} para {producto.nombre}', 'info')
                # Podrías decidir si cancelar la operación o continuar
                # Por ahora, solo advertimos y continuamos descontando lo que se pueda
                # Pero lo ideal sería detener el pago y avisar
                db.session.rollback()
                flash('No se pudo completar el pago por falta de stock', 'danger')
                return redirect(url_for('mesas.ver_orden', mesa_id=orden.mesa_id))
            ingrediente.stock_actual -= cantidad_necesaria

    db.session.commit()
    
    flash('Pago registrado con éxito', 'success')
    return redirect(url_for('mesas.ticket_orden', orden_id=orden.id))

    # if metodo == 'efectivo':
    #     cambio = monto_recibido - orden.total
    #     flash(f'Pago registrado. Cambio: ${cambio:.2f}', 'success')
    # else:
    #     flash('Pago registrado con éxito', 'success')
    
    # return redirect(url_for('mesas.lista_mesas'))


@mesas_bp.route('/orden/<int:orden_id>/ticket')
@login_required
def ticket_orden(orden_id):
    orden = Orden.query.get_or_404(orden_id)
    # Opcional: solo mostrar si está pagada
    if orden.estado != 'pagada':
        flash('La orden no está pagada', 'warning')
        return redirect(url_for('mesas.lista_mesas'))
    return render_template('ticket.html', orden=orden)