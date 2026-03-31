from extensions import db
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
import pytz

mexico_tz = pytz.timezone('America/Mexico_City')

def local_now():
    """Retorna la fecha y hora actual en la zona horaria de México"""
    return datetime.now(mexico_tz)

# Modelo de ejemplo: Mesa
class Mesa(db.Model):
    __tablename__ = 'mesas'
    id = db.Column(db.Integer, primary_key=True)
    numero = db.Column(db.Integer, unique=True, nullable=False)
    capacidad = db.Column(db.Integer, default=4)
    estado = db.Column(db.String(20), default='libre')  # 'libre' u 'ocupada'

class Usuario(db.Model, UserMixin):
    __tablename__ = 'usuarios'
    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(100), unique=True, nullable=False)
    rol = db.Column(db.String(20), nullable=False, default='mesero')
    password_hash = db.Column(db.String(128), nullable=False)
    activo = db.Column(db.Boolean, default=True)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def is_active(self):
        return self.activo

class Categoria(db.Model):
    __tablename__ = 'categorias'
    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(50), unique=True, nullable=False)
    estado = db.Column(db.Boolean, nullable=False, default=True)

    # Relación con productos
    productos = db.relationship('Producto', backref='categoria', lazy=True)

class Producto(db.Model):
    __tablename__ = 'productos'
    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(100), nullable=False)
    precio = db.Column(db.Float, nullable=False)
    categoria_id = db.Column(db.Integer, db.ForeignKey('categorias.id'), nullable=False)
    activo = db.Column(db.Boolean, default=True)

    # Relación con detalle_orden y recetas
    detalles = db.relationship('DetalleOrden', backref='producto', lazy=True)
    recetas = db.relationship('Receta', backref='producto', lazy=True)

class Ingrediente(db.Model):
    __tablename__ = 'ingredientes'
    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(100), unique=True, nullable=False)
    unidad = db.Column(db.String(20), nullable=False)  # kg, litro, unidad, etc.
    stock_actual = db.Column(db.Float, default=0)
    stock_minimo = db.Column(db.Float, default=0)

    # Relación con recetas
    recetas = db.relationship('Receta', backref='ingrediente', lazy=True)

class Receta(db.Model):
    __tablename__ = 'recetas'
    id = db.Column(db.Integer, primary_key=True)
    producto_id = db.Column(db.Integer, db.ForeignKey('productos.id'), nullable=False)
    ingrediente_id = db.Column(db.Integer, db.ForeignKey('ingredientes.id'), nullable=False)
    cantidad = db.Column(db.Float, nullable=False)  # cantidad necesaria del ingrediente

    # Para garantizar que un producto no tenga dos veces el mismo ingrediente
    __table_args__ = (db.UniqueConstraint('producto_id', 'ingrediente_id', name='unique_producto_ingrediente'),)

class Orden(db.Model):
    __tablename__ = 'ordenes'
    id = db.Column(db.Integer, primary_key=True)
    mesa_id = db.Column(db.Integer, db.ForeignKey('mesas.id'), nullable=False)
    mesero_id = db.Column(db.Integer, db.ForeignKey('usuarios.id'), nullable=False)
    fecha_hora = db.Column(db.DateTime, default=local_now)
    estado = db.Column(db.String(20), default='abierta')  # 'abierta', 'pagada', 'cancelada'
    total = db.Column(db.Float, default=0)

    # Relaciones
    detalles = db.relationship('DetalleOrden', backref='orden', lazy=True, cascade='all, delete-orphan')
    pagos = db.relationship('Pago', backref='orden', lazy=True, cascade='all, delete-orphan')
    mesero = db.relationship('Usuario', backref='ordenes')
    mesa = db.relationship('Mesa', backref='mesas')

class DetalleOrden(db.Model):
    __tablename__ = 'detalle_orden'
    id = db.Column(db.Integer, primary_key=True)
    orden_id = db.Column(db.Integer, db.ForeignKey('ordenes.id'), nullable=False)
    producto_id = db.Column(db.Integer, db.ForeignKey('productos.id'), nullable=False)
    cantidad = db.Column(db.Integer, nullable=False)
    precio_unitario = db.Column(db.Float, nullable=False)  # Precio en el momento de la venta

    # Podemos calcular subtotal como propiedad, no como columna
    @property
    def subtotal(self):
        return self.cantidad * self.precio_unitario

class Pago(db.Model):
    __tablename__ = 'pagos'
    id = db.Column(db.Integer, primary_key=True)
    orden_id = db.Column(db.Integer, db.ForeignKey('ordenes.id'), nullable=False)
    monto = db.Column(db.Float, nullable=False)
    metodo_pago = db.Column(db.String(20), nullable=False)  # 'efectivo', 'tarjeta', 'otro'
    fecha_hora = db.Column(db.DateTime, default=local_now)

# class Movimientos(db.Model):
#     __tablename__ = 'movimientos'
#     id = db.Column(db.Integer, primary_key=True)
#     ingrediente_id = db.Column(db.Integer, db.ForeignKey('ingredientes.id'), nullable=False)
#     fecha_hora = db.Column(db.DateTime, default=db.func.current_timestamp())
#     tipo = db.Column(db.String(100), nullable=False)
#     cantidad = db.Column(db.Integer, nullable=False)
#     precio_unitario = db.Column(db.Float, nullable=False)

class Compra(db.Model):
    __tablename__ = 'compras'
    id = db.Column(db.Integer, primary_key=True)
    fecha = db.Column(db.DateTime, default=local_now)
    proveedor = db.Column(db.String(100))
    factura = db.Column(db.String(50))  # número de factura opcional
    observaciones = db.Column(db.Text)

    # Relación con los detalles
    detalles = db.relationship('CompraDetalle', backref='compra', lazy=True, cascade='all, delete-orphan')

    @property
    def total(self):
        return sum(d.subtotal for d in self.detalles)


class CompraDetalle(db.Model):
    __tablename__ = 'compra_detalles'
    id = db.Column(db.Integer, primary_key=True)
    compra_id = db.Column(db.Integer, db.ForeignKey('compras.id'), nullable=False)
    ingrediente_id = db.Column(db.Integer, db.ForeignKey('ingredientes.id'), nullable=False)
    cantidad = db.Column(db.Float, nullable=False)
    precio_unitario = db.Column(db.Float, nullable=True)  # opcional

    # Relación con ingrediente
    ingrediente = db.relationship('Ingrediente')

    @property
    def subtotal(self):
        return self.cantidad * (self.precio_unitario or 0)