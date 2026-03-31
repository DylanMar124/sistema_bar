from flask import Flask, render_template
import webbrowser
import threading
import time
from extensions import app, db, login_manager
from models import Mesa, Usuario
from auth import auth_bp
from werkzeug.security import generate_password_hash
from flask_login import login_required
from routes.usuarios import usuarios_bp
from routes.mesas import mesas_bp
from routes.ordenesHistorial import ordenes_bp
from routes.categorias import categorias_bp
from routes.ingredientes import ingredientes_bp
from routes.recetas import recetas_bp
from routes.productos import productos_bp
from models import Mesa, Orden, Producto, Ingrediente
from datetime import datetime, date, timedelta
from sqlalchemy import func
from routes.compras import compras_bp
from routes.reportes import reportes_bp
from flask import request, render_template_string, redirect, url_for, session
from licencia import validar_licencia_guardada, verificar_codigo_licencia, guardar_licencia

# Template simple para activación (puedes personalizarlo)
ACTIVACION_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <title>Activación del Sistema</title>
    <style>
        body { font-family: Arial; text-align: center; padding: 50px; }
        input { padding: 10px; width: 400px; margin: 10px; }
        button { padding: 10px 20px; background: #4CAF50; color: white; border: none; cursor: pointer; }
        .error { color: red; }
    </style>
</head>
<body>
    <h2>Activación del Sistema</h2>
    <p>Ingrese el código de licencia proporcionado:</p>
    <form method="POST">
        <input type="text" name="codigo" placeholder="Código de licencia" required><br>
        <button type="submit">Activar</button>
    </form>
    {% if error %}
        <p class="error">{{ error }}</p>
    {% endif %}
    <hr>
    <p>Fingerprint de este equipo: <strong>{{ fingerprint }}</strong></p>
    <p>Envíe este código a su proveedor para obtener la licencia.</p>
</body>
</html>
"""

@app.before_request
def verificar_activacion():
    # Excluir rutas que no requieren activación (como la propia página de activación)
    if request.endpoint in ('activar', 'static'):
        return
    # Verificar si ya está activado
    valida, _ = validar_licencia_guardada()
    if not valida:
        return redirect(url_for('activar'))

@app.route('/activar', methods=['GET', 'POST'])
def activar():
    from licencia import get_fingerprint
    if request.method == 'POST':
        codigo = request.form.get('codigo', '').strip()
        ok, resultado = verificar_codigo_licencia(codigo)
        if ok:
            guardar_licencia(codigo)
            return redirect(url_for('auth.login'))  # redirige al inicio
        else:
            return render_template_string(ACTIVACION_TEMPLATE,
                                          error=resultado,
                                          fingerprint=get_fingerprint())
    return render_template_string(ACTIVACION_TEMPLATE,
                                  error=None,
                                  fingerprint=get_fingerprint())

# Registrar blueprint
app.register_blueprint(auth_bp)
app.register_blueprint(usuarios_bp)
app.register_blueprint(mesas_bp)
app.register_blueprint(ordenes_bp)
app.register_blueprint(categorias_bp)
app.register_blueprint(ingredientes_bp)
app.register_blueprint(recetas_bp)
app.register_blueprint(productos_bp)
app.register_blueprint(compras_bp)
app.register_blueprint(reportes_bp)

# Configurar Flask-Login user_loader
@login_manager.user_loader
def load_user(user_id):
    return Usuario.query.get(int(user_id))

with app.app_context():
    db.create_all()

    if not Usuario.query.first():
        admin = Usuario(
            nombre='superadmin',
            rol='admin',
            activo=True
        )
        admin.set_password('admin')  # Usamos el método set_password
        db.session.add(admin)
        db.session.commit()
        print("Usuario administrador creado con contraseña 'admin'")

# Ruta principal
@app.route('/')
@login_required
def dashboard():
    # Totales
    total_mesas = Mesa.query.count()
    mesas_ocupadas = Mesa.query.filter_by(estado='ocupada').count()
    
    # Ventas del día
    hoy = date.today()
    inicio_dia = datetime(hoy.year, hoy.month, hoy.day, 0, 0, 0)
    ventas_hoy = db.session.query(func.sum(Orden.total)).filter(
        Orden.estado == 'pagada',
        Orden.fecha_hora >= inicio_dia
    ).scalar() or 0
    
    # Productos con stock bajo (menor al mínimo)
    stock_bajo = Ingrediente.query.filter(Ingrediente.stock_actual < Ingrediente.stock_minimo).count()
    
    # Últimas órdenes pagadas (opcional)
    ultimas_ordenes = Orden.query.filter_by(estado='pagada').order_by(Orden.fecha_hora.desc()).limit(5).all()

    productos_activos = Producto.query.filter_by(activo=True).count()

    fechas = []
    ventas_diarias = []
    for i in range(6, -1, -1):
        dia = hoy - timedelta(days=i)
        inicio = datetime(dia.year, dia.month, dia.day, 0, 0, 0)
        fin = datetime(dia.year, dia.month, dia.day, 23, 59, 59)
        total = db.session.query(func.sum(Orden.total)).filter(
            Orden.estado == 'pagada',
            Orden.fecha_hora >= inicio,
            Orden.fecha_hora <= fin
        ).scalar() or 0
        fechas.append(dia.strftime('%d/%m'))
        ventas_diarias.append(float(total))

    hoy = date.today()
    inicio_dia = datetime.combine(hoy, datetime.min.time())
    fin_dia = datetime.combine(hoy, datetime.max.time())
    
    ventas_por_mesa_hoy = db.session.query(
        Mesa.numero,
        func.coalesce(func.sum(Orden.total), 0).label('total')
    ).outerjoin(
        Orden, 
        (Orden.mesa_id == Mesa.id) & 
        (Orden.estado == 'pagada') &
        (Orden.fecha_hora >= inicio_dia) &
        (Orden.fecha_hora <= fin_dia)
    ).group_by(Mesa.id).order_by(func.sum(Orden.total).desc()).all()

    return render_template('dashboard.html',
                           total_mesas=total_mesas,
                           mesas_ocupadas=mesas_ocupadas,
                           ventas_hoy=ventas_hoy,
                           stock_bajo=stock_bajo,
                           ultimas_ordenes=ultimas_ordenes,
                           productos_activos=productos_activos,
                           ventas_diarias=ventas_diarias,
                           fechas=fechas,
                           ventas_por_mesa=ventas_por_mesa_hoy)

# Función para abrir el navegador automáticamente
def abrir_navegador():
    time.sleep(1.5)
    webbrowser.open('http://127.0.0.1:5000')

# Punto de entrada
if __name__ == '__main__':
    threading.Thread(target=abrir_navegador).start()
    app.run(debug=False, host='127.0.0.1', port=5000)