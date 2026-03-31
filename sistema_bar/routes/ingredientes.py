from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required, current_user
from functools import wraps
from extensions import db
from models import Ingrediente

ingredientes_bp = Blueprint('ingredientes', __name__, url_prefix='/ingredientes')

def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or current_user.rol != 'admin':
            flash('Acceso no autorizado', 'info')
            return redirect(url_for('index'))
        return f(*args, **kwargs)
    return decorated_function

@ingredientes_bp.route('/')
@login_required
@admin_required
def lista_ingredientes():
    ingredientes = Ingrediente.query.all()
    return render_template('ingredientes.html', ingredientes=ingredientes)

@ingredientes_bp.route('/crear', methods=['POST'])
@login_required
@admin_required
def crear_ingrediente():
    nombre = request.form['nombre']
    unidad = request.form['unidad']
    stock_actual = float(request.form.get('stock_actual', 0))
    stock_minimo = float(request.form.get('stock_minimo', 0))
    
    if Ingrediente.query.filter_by(nombre=nombre).first():
        flash('El ingrediente ya existe', 'info')
        return redirect(url_for('ingredientes.lista_ingredientes'))
    
    nuevo = Ingrediente(
        nombre=nombre,
        unidad=unidad,
        stock_actual=stock_actual,
        stock_minimo=stock_minimo
    )
    db.session.add(nuevo)
    db.session.commit()
    flash('Ingrediente creado correctamente', 'success')
    return redirect(url_for('ingredientes.lista_ingredientes'))

@ingredientes_bp.route('/editar', methods=['POST'])
@login_required
@admin_required
def editar_ingrediente():
    ingrediente_id = request.form['id']
    nombre = request.form['nombre']
    unidad = request.form['unidad']
    stock_actual = float(request.form['stock_actual'])
    stock_minimo = float(request.form['stock_minimo'])
    
    ingrediente = Ingrediente.query.get_or_404(ingrediente_id)
    
    # Verificar nombre único excepto el mismo
    existe = Ingrediente.query.filter(Ingrediente.nombre == nombre, Ingrediente.id != ingrediente_id).first()
    if existe:
        flash('Ya existe otro ingrediente con ese nombre', 'info')
        return redirect(url_for('ingredientes.lista_ingredientes'))
    
    ingrediente.nombre = nombre
    ingrediente.unidad = unidad
    ingrediente.stock_actual = stock_actual
    ingrediente.stock_minimo = stock_minimo
    db.session.commit()
    flash('Ingrediente actualizado', 'success')
    return redirect(url_for('ingredientes.lista_ingredientes'))

@ingredientes_bp.route('/eliminar/<int:ingrediente_id>', methods=['POST'])
@login_required
@admin_required
def eliminar_ingrediente(ingrediente_id):
    ingrediente = Ingrediente.query.get_or_404(ingrediente_id)
    # Verificar si está siendo usado en alguna receta
    from models import Receta
    if Receta.query.filter_by(ingrediente_id=ingrediente.id).first():
        flash('No se puede eliminar porque está siendo usado en una receta', 'info')
        return redirect(url_for('ingredientes.lista_ingredientes'))
    
    db.session.delete(ingrediente)
    db.session.commit()
    flash('Ingrediente eliminado', 'success')
    return redirect(url_for('ingredientes.lista_ingredientes'))