from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from flask_login import login_required, current_user
from functools import wraps
from extensions import db
from models import Producto, Ingrediente, Receta

recetas_bp = Blueprint('recetas', __name__, url_prefix='/recetas')

def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or current_user.rol != 'admin':
            flash('Acceso no autorizado', 'info')
            return redirect(url_for('index'))
        return f(*args, **kwargs)
    return decorated_function

@recetas_bp.route('/')
@login_required
@admin_required
def lista_recetas():
    productos = Producto.query.filter_by(activo=True).all()
    return render_template('recetas.html', productos=productos)

@recetas_bp.route('/producto/<int:producto_id>')
@login_required
@admin_required
def ver_receta(producto_id):
    producto = Producto.query.get_or_404(producto_id)
    ingredientes = Ingrediente.query.all()
    recetas = Receta.query.filter_by(producto_id=producto.id).all()
    return render_template('receta_detalle.html', producto=producto, ingredientes=ingredientes, recetas=recetas)

@recetas_bp.route('/agregar', methods=['POST'])
@login_required
@admin_required
def agregar_ingrediente_receta():
    producto_id = request.form['producto_id']
    ingrediente_id = request.form['ingrediente_id']
    cantidad = float(request.form['cantidad'])
    
    # Verificar si ya existe
    existe = Receta.query.filter_by(producto_id=producto_id, ingrediente_id=ingrediente_id).first()
    if existe:
        flash('Ese ingrediente ya está en la receta', 'info')
        return redirect(url_for('recetas.ver_receta', producto_id=producto_id))
    
    receta = Receta(
        producto_id=producto_id,
        ingrediente_id=ingrediente_id,
        cantidad=cantidad
    )
    db.session.add(receta)
    db.session.commit()
    flash('Ingrediente agregado a la receta', 'success')
    return redirect(url_for('recetas.ver_receta', producto_id=producto_id))

@recetas_bp.route('/quitar/<int:receta_id>', methods=['POST'])
@login_required
@admin_required
def quitar_ingrediente_receta(receta_id):
    receta = Receta.query.get_or_404(receta_id)
    producto_id = receta.producto_id
    db.session.delete(receta)
    db.session.commit()
    flash('Ingrediente quitado de la receta', 'success')
    return redirect(url_for('recetas.ver_receta', producto_id=producto_id))