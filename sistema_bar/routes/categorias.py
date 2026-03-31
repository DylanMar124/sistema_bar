from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required, current_user
from functools import wraps
from extensions import db
from models import Categoria

categorias_bp = Blueprint('categorias', __name__, url_prefix='/categorias')

def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or current_user.rol != 'admin':
            flash('Acceso no autorizado', 'info')
            return redirect(url_for('index'))
        return f(*args, **kwargs)
    return decorated_function

@categorias_bp.route('/')
@login_required
def lista_categorias():
    categorias = Categoria.query.where(Categoria.estado == True)
    return render_template('categorias.html', categorias=categorias)

@categorias_bp.route('/crear', methods=['POST'])
@login_required
def crear_categoria():
    nombre = request.form['nombre']
    
    # Verificar si ya existe
    if Categoria.query.filter_by(nombre=nombre).first():
        flash('Esta categoria ya existe', 'info')
        return redirect(url_for('categorias.lista_categorias'))
    
    nuevo = Categoria(
        nombre=nombre
    )
    db.session.add(nuevo)
    db.session.commit()

    flash('Categoria creada correctamente', 'success')
    return redirect(url_for('categorias.lista_categorias'))

@categorias_bp.route('/editar', methods=['POST'])
@login_required
def editar_categoria():
    categoria_id = request.form['categoria_id']
    nombre = request.form['nombre']

    categoria = Categoria.query.get_or_404(categoria_id)
    
    # Verificar si ya existe otra mesa con el mismo número
    existe = Categoria.query.filter(Categoria.nombre == nombre, Categoria.id != categoria_id).first()
    if existe:
        flash('Ya existe otra categoria con este nombre', 'info')
        return redirect(url_for('categorias.lista_categorias'))
    
    categoria.nombre = nombre
    db.session.commit()
    
    flash('Categoria actualizada correctamente', 'success')
    return redirect(url_for('categorias.lista_categorias'))

@categorias_bp.route('/eliminar/<int:categoria_id>', methods=['POST'])
@login_required
@admin_required
def eliminar_categoria(categoria_id):
    categoria = Categoria.query.get_or_404(categoria_id)
    
    categoria.estado = False
    db.session.commit()
    
    flash('Categoria eliminada correctamente', 'success')
    return redirect(url_for('categorias.lista_categorias'))