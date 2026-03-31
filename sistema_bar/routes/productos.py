from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required, current_user
from functools import wraps
from extensions import db
from models import Producto, Categoria, Receta

productos_bp = Blueprint('productos', __name__, url_prefix='/productos')

# Decorador para admin (opcional, si quieres restringir)
def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or current_user.rol != 'admin':
            flash('Acceso no autorizado', 'info')
            return redirect(url_for('index'))
        return f(*args, **kwargs)
    return decorated_function

@productos_bp.route('/')
@login_required
@admin_required
def lista_productos():
    productos = Producto.query.all()
    categorias = Categoria.query.where(Categoria.estado==True)
    return render_template('productos.html', productos=productos, categorias=categorias)

@productos_bp.route('/crear', methods=['POST'])
@login_required
@admin_required
def crear_producto():
    nombre = request.form['nombre']
    precio = float(request.form['precio'])
    categoria_id = int(request.form['categoria_id'])

    # Verificar si ya existe un producto con el mismo nombre
    if Producto.query.filter_by(nombre=nombre).first():
        flash('Ya existe un producto con ese nombre', 'info')
        return redirect(url_for('productos.lista_productos'))

    nuevo = Producto(
        nombre=nombre,
        precio=precio,
        categoria_id=categoria_id,
        activo=True
    )
    db.session.add(nuevo)
    db.session.commit()
    flash('Producto creado correctamente', 'success')
    return redirect(url_for('productos.lista_productos'))

@productos_bp.route('/editar', methods=['POST'])
@login_required
@admin_required
def editar_producto():
    producto_id = request.form['id']
    nombre = request.form['nombre']
    precio = float(request.form['precio'])
    categoria_id = int(request.form['categoria_id'])
    activo = 'activo' in request.form  # Checkbox

    producto = Producto.query.get_or_404(producto_id)

    # Verificar duplicado de nombre (excluyendo el actual)
    existe = Producto.query.filter(Producto.nombre == nombre, Producto.id != producto_id).first()
    if existe:
        flash('Ya existe otro producto con ese nombre', 'info')
        return redirect(url_for('productos.lista_productos'))

    producto.nombre = nombre
    producto.precio = precio
    producto.categoria_id = categoria_id
    producto.activo = activo
    db.session.commit()
    flash('Producto actualizado', 'success')
    return redirect(url_for('productos.lista_productos'))

@productos_bp.route('/toggle/<int:producto_id>')
@login_required
@admin_required
def toggle_producto(producto_id):
    producto = Producto.query.get_or_404(producto_id)
    producto.activo = not producto.activo
    db.session.commit()
    estado = 'activado' if producto.activo else 'desactivado'
    flash(f'Producto {producto.nombre} {estado}', 'success')
    return redirect(url_for('productos.lista_productos'))