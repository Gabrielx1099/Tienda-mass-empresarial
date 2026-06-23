import os
import json
from datetime import datetime
from flask import Flask, render_template, redirect, url_for, flash, request, session, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from functools import wraps
from authlib.integrations.flask_client import OAuth

app = Flask(__name__)

app.config['SECRET_KEY'] = 'tiendas-mass-secretkey-2024-academia'

app.config['SQLALCHEMY_DATABASE_URI'] = 'mysql+pymysql://root:@localhost/tienda_mass'

app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

app.config['UPLOAD_FOLDER'] = os.path.join('static', 'uploads')

app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024

ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'webp'}

db = SQLAlchemy(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'
login_manager.login_message = 'Por favor inicia sesión para acceder.'
login_manager.login_message_category = 'warning'

# ─── MODELOS ───────────────────────────────────────────────────────────────────

class Usuario(UserMixin, db.Model):
    __tablename__ = 'usuarios'
    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(100), nullable=False)
    apellido = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(150), unique=True, nullable=False)
    telefono = db.Column(db.String(20))
    password_hash = db.Column(db.String(256))
    google_id = db.Column(db.String(200))
    rol = db.Column(db.String(20), default='cliente')
    activo = db.Column(db.Boolean, default=True)
    fecha_registro = db.Column(db.DateTime, default=datetime.utcnow)
    pedidos = db.relationship('Pedido', backref='cliente', lazy=True)
    carrito = db.relationship('Carrito', backref='usuario', uselist=False, lazy=True)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def nombre_completo(self):
        return f"{self.nombre} {self.apellido}"


class Categoria(db.Model):
    __tablename__ = 'categorias'
    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(100), nullable=False)
    descripcion = db.Column(db.Text)
    icono = db.Column(db.String(50), default='🛒')
    productos = db.relationship('Producto', backref='categoria', lazy=True)


class Local(db.Model):
    __tablename__ = 'locales'
    id = db.Column(db.Integer, primary_key=True)
    nombre_local = db.Column(db.String(150), nullable=False)
    departamento = db.Column(db.String(100), nullable=False)
    provincia = db.Column(db.String(100), nullable=False)
    distrito = db.Column(db.String(100), nullable=False)
    direccion = db.Column(db.String(250), nullable=False)
    telefono = db.Column(db.String(20))
    horario = db.Column(db.String(200))
    activo = db.Column(db.Boolean, default=True)


class Producto(db.Model):
    __tablename__ = 'productos'
    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(200), nullable=False)
    descripcion = db.Column(db.Text)
    precio = db.Column(db.Float, nullable=False)
    precio_oferta = db.Column(db.Float)
    stock = db.Column(db.Integer, default=0)
    imagen = db.Column(db.String(300), default='default_product.png')
    categoria_id = db.Column(db.Integer, db.ForeignKey('categorias.id'))
    activo = db.Column(db.Boolean, default=True)
    destacado = db.Column(db.Boolean, default=False)
    fecha_creacion = db.Column(db.DateTime, default=datetime.utcnow)


class Carrito(db.Model):
    __tablename__ = 'carritos'
    id = db.Column(db.Integer, primary_key=True)
    usuario_id = db.Column(db.Integer, db.ForeignKey('usuarios.id'))
    detalles = db.relationship('CarritoDetalle', backref='carrito', lazy=True, cascade='all, delete-orphan')


class CarritoDetalle(db.Model):
    __tablename__ = 'carrito_detalles'
    id = db.Column(db.Integer, primary_key=True)
    carrito_id = db.Column(db.Integer, db.ForeignKey('carritos.id'))
    producto_id = db.Column(db.Integer, db.ForeignKey('productos.id'))
    cantidad = db.Column(db.Integer, default=1)
    producto = db.relationship('Producto', lazy=True)


class Pedido(db.Model):
    __tablename__ = 'pedidos'
    id = db.Column(db.Integer, primary_key=True)
    numero_pedido = db.Column(db.String(20), unique=True)
    usuario_id = db.Column(db.Integer, db.ForeignKey('usuarios.id'))
    local_id = db.Column(db.Integer, db.ForeignKey('locales.id'), nullable=True)
    fecha = db.Column(db.DateTime, default=datetime.utcnow)
    metodo_pago = db.Column(db.String(50))
    tipo_entrega = db.Column(db.String(20))
    subtotal = db.Column(db.Float)
    delivery = db.Column(db.Float, default=0)
    total = db.Column(db.Float)
    estado = db.Column(db.String(30), default='Pendiente')
    # Datos de entrega
    dep_entrega = db.Column(db.String(100))
    prov_entrega = db.Column(db.String(100))
    dist_entrega = db.Column(db.String(100))
    direccion_entrega = db.Column(db.String(250))
    referencia = db.Column(db.String(250))
    nombre_receptor = db.Column(db.String(200))
    telefono_receptor = db.Column(db.String(20))
    dni_receptor = db.Column(db.String(20))
    detalles = db.relationship('PedidoDetalle', backref='pedido', lazy=True)
    local = db.relationship('Local', lazy=True)


class PedidoDetalle(db.Model):
    __tablename__ = 'pedido_detalles'
    id = db.Column(db.Integer, primary_key=True)
    pedido_id = db.Column(db.Integer, db.ForeignKey('pedidos.id'))
    producto_id = db.Column(db.Integer, db.ForeignKey('productos.id'))
    cantidad = db.Column(db.Integer)
    precio_unitario = db.Column(db.Float)
    producto = db.relationship('Producto', lazy=True)


@login_manager.user_loader
def load_user(user_id):
    return Usuario.query.get(int(user_id))


# ─── DECORADORES ──────────────────────────────────────────────────────────────

def admin_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if not current_user.is_authenticated or current_user.rol != 'admin':
            flash('Acceso restringido. Solo administradores.', 'danger')
            return redirect(url_for('index'))
        return f(*args, **kwargs)
    return decorated


def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


def get_carrito_count():
    if current_user.is_authenticated:
        carrito = Carrito.query.filter_by(usuario_id=current_user.id).first()
        if carrito:
            return sum(d.cantidad for d in carrito.detalles)
    return 0


def generar_numero_pedido():
    now = datetime.utcnow()
    ultimo = Pedido.query.order_by(Pedido.id.desc()).first()
    num = (ultimo.id + 1) if ultimo else 1
    return f"MASS-{now.strftime('%Y%m')}-{num:04d}"


# ─── CONTEXTO GLOBAL ──────────────────────────────────────────────────────────

@app.context_processor
def inject_globals():
    categorias = Categoria.query.all()
    carrito_count = get_carrito_count()
    return dict(categorias=categorias, carrito_count=carrito_count)


# ─── RUTAS PÚBLICAS ───────────────────────────────────────────────────────────

@app.route('/')
def index():
    productos_destacados = Producto.query.filter_by(activo=True, destacado=True).limit(8).all()
    productos_oferta = Producto.query.filter(
        Producto.activo == True,
        Producto.precio_oferta != None
    ).limit(6).all()
    categorias = Categoria.query.all()
    return render_template('index.html',
                           productos_destacados=productos_destacados,
                           productos_oferta=productos_oferta,
                           categorias=categorias)


@app.route('/catalogo')
def catalogo():
    q = request.args.get('q', '')
    cat_id = request.args.get('categoria', type=int)
    orden = request.args.get('orden', 'nombre')
    query = Producto.query.filter_by(activo=True)
    if q:
        query = query.filter(Producto.nombre.ilike(f'%{q}%'))
    if cat_id:
        query = query.filter_by(categoria_id=cat_id)
    if orden == 'precio_asc':
        query = query.order_by(Producto.precio.asc())
    elif orden == 'precio_desc':
        query = query.order_by(Producto.precio.desc())
    else:
        query = query.order_by(Producto.nombre.asc())
    productos = query.all()
    categorias = Categoria.query.all()
    return render_template('catalogo.html', productos=productos, categorias=categorias,
                           q=q, cat_id=cat_id, orden=orden)


@app.route('/producto/<int:id>')
def detalle_producto(id):
    producto = Producto.query.get_or_404(id)
    relacionados = Producto.query.filter_by(categoria_id=producto.categoria_id, activo=True)\
        .filter(Producto.id != id).limit(4).all()
    return render_template('detalle_producto.html', producto=producto, relacionados=relacionados)


# ─── AUTENTICACIÓN ────────────────────────────────────────────────────────────

@app.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    if request.method == 'POST':
        nombre = request.form.get('nombre', '').strip()
        apellido = request.form.get('apellido', '').strip()
        email = request.form.get('email', '').strip().lower()
        telefono = request.form.get('telefono', '').strip()
        password = request.form.get('password', '')
        confirm = request.form.get('confirm_password', '')

        if not all([nombre, apellido, email, password]):
            flash('Completa todos los campos obligatorios.', 'danger')
            return render_template('register.html')
        if password != confirm:
            flash('Las contraseñas no coinciden.', 'danger')
            return render_template('register.html')
        if len(password) < 6:
            flash('La contraseña debe tener al menos 6 caracteres.', 'danger')
            return render_template('register.html')
        if Usuario.query.filter_by(email=email).first():
            flash('Ya existe una cuenta con ese correo.', 'danger')
            return render_template('register.html')

        usuario = Usuario(nombre=nombre, apellido=apellido, email=email, telefono=telefono)
        usuario.set_password(password)
        db.session.add(usuario)
        db.session.commit()
        login_user(usuario)
        flash(f'¡Bienvenido/a {nombre}! Tu cuenta fue creada exitosamente.', 'success')
        return redirect(url_for('index'))
    return render_template('register.html')


@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    if request.method == 'POST':
        email = request.form.get('email', '').strip().lower()
        password = request.form.get('password', '')
        usuario = Usuario.query.filter_by(email=email).first()
        if usuario and usuario.check_password(password) and usuario.activo:
            login_user(usuario, remember=True)
            next_page = request.args.get('next')
            flash(f'¡Bienvenido/a de vuelta, {usuario.nombre}!', 'success')
            if usuario.rol == 'admin':
                return redirect(url_for('admin_dashboard'))
            return redirect(next_page or url_for('index'))
        flash('Correo o contraseña incorrectos.', 'danger')
    return render_template('login.html')


@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('Sesión cerrada correctamente.', 'info')
    return redirect(url_for('index'))


@app.route('/recuperar-password', methods=['GET', 'POST'])
def recuperar_password():
    if request.method == 'POST':
        email = request.form.get('email', '').strip().lower()
        usuario = Usuario.query.filter_by(email=email).first()
        flash('Si el correo existe, recibirás instrucciones (simulado para fines académicos).', 'info')
        return redirect(url_for('login'))
    return render_template('recuperar_password.html')


# ─── CARRITO ──────────────────────────────────────────────────────────────────

@app.route('/carrito')
@login_required
def carrito():
    carrito_obj = Carrito.query.filter_by(usuario_id=current_user.id).first()
    detalles = carrito_obj.detalles if carrito_obj else []
    subtotal = sum((d.producto.precio_oferta or d.producto.precio) * d.cantidad for d in detalles)
    return render_template('carrito.html', detalles=detalles, subtotal=subtotal)


@app.route('/carrito/agregar/<int:producto_id>', methods=['POST'])
@login_required
def agregar_carrito(producto_id):
    producto = Producto.query.get_or_404(producto_id)
    cantidad = int(request.form.get('cantidad', 1))
    if cantidad < 1:
        cantidad = 1
    if cantidad > producto.stock:
        flash(f'Solo hay {producto.stock} unidades disponibles.', 'warning')
        return redirect(request.referrer or url_for('catalogo'))

    carrito_obj = Carrito.query.filter_by(usuario_id=current_user.id).first()
    if not carrito_obj:
        carrito_obj = Carrito(usuario_id=current_user.id)
        db.session.add(carrito_obj)
        db.session.flush()

    detalle = CarritoDetalle.query.filter_by(
        carrito_id=carrito_obj.id, producto_id=producto_id).first()
    if detalle:
        nueva_cantidad = detalle.cantidad + cantidad
        if nueva_cantidad > producto.stock:
            flash(f'Solo hay {producto.stock} unidades disponibles.', 'warning')
            return redirect(request.referrer or url_for('catalogo'))
        detalle.cantidad = nueva_cantidad
    else:
        detalle = CarritoDetalle(carrito_id=carrito_obj.id, producto_id=producto_id, cantidad=cantidad)
        db.session.add(detalle)

    db.session.commit()
    flash(f'"{producto.nombre}" agregado al carrito.', 'success')
    return redirect(request.referrer or url_for('catalogo'))


@app.route('/carrito/actualizar/<int:detalle_id>', methods=['POST'])
@login_required
def actualizar_carrito(detalle_id):
    detalle = CarritoDetalle.query.get_or_404(detalle_id)
    cantidad = int(request.form.get('cantidad', 1))
    if cantidad < 1:
        db.session.delete(detalle)
    elif cantidad > detalle.producto.stock:
        flash('No hay suficiente stock.', 'warning')
    else:
        detalle.cantidad = cantidad
    db.session.commit()
    return redirect(url_for('carrito'))


@app.route('/carrito/eliminar/<int:detalle_id>', methods=['POST'])
@login_required
def eliminar_carrito(detalle_id):
    detalle = CarritoDetalle.query.get_or_404(detalle_id)
    db.session.delete(detalle)
    db.session.commit()
    flash('Producto eliminado del carrito.', 'info')
    return redirect(url_for('carrito'))


@app.route('/carrito/vaciar', methods=['POST'])
@login_required
def vaciar_carrito():
    carrito_obj = Carrito.query.filter_by(usuario_id=current_user.id).first()
    if carrito_obj:
        for d in carrito_obj.detalles:
            db.session.delete(d)
        db.session.commit()
    flash('Carrito vaciado.', 'info')
    return redirect(url_for('carrito'))


# ─── CHECKOUT ─────────────────────────────────────────────────────────────────

@app.route('/checkout/entrega', methods=['GET', 'POST'])
@login_required
def datos_entrega():
    carrito_obj = Carrito.query.filter_by(usuario_id=current_user.id).first()
    if not carrito_obj or not carrito_obj.detalles:
        flash('Tu carrito está vacío.', 'warning')
        return redirect(url_for('carrito'))

    locales = Local.query.filter_by(activo=True).all()

    if request.method == 'POST':
        tipo = request.form.get('tipo_entrega')
        session['tipo_entrega'] = tipo
        session['nombre_receptor'] = request.form.get('nombre_receptor', '')
        session['telefono_receptor'] = request.form.get('telefono_receptor', '')

        if tipo == 'delivery':
            session['dep_entrega'] = request.form.get('departamento', '')
            session['prov_entrega'] = request.form.get('provincia', '')
            session['dist_entrega'] = request.form.get('distrito', '')
            session['direccion_entrega'] = request.form.get('direccion', '')
            session['referencia'] = request.form.get('referencia', '')
            dept = session['dep_entrega'].lower()
            if 'callao' in dept:
                session['costo_delivery'] = 6.0
            elif 'lima' in dept:
                dist = session['dist_entrega'].lower()
                lejanos = ['lurigancho', 'carabayllo', 'puente piedra', 'santa rosa', 'ancón']
                session['costo_delivery'] = 8.0 if any(l in dist for l in lejanos) else 5.0
            else:
                session['costo_delivery'] = 8.0
            session['local_id'] = None
            session['dni_receptor'] = None
        else:
            local_id = request.form.get('local_id', type=int)
            session['local_id'] = local_id
            session['dni_receptor'] = request.form.get('dni_receptor', '')
            session['costo_delivery'] = 0.0
            session['dep_entrega'] = ''
            session['prov_entrega'] = ''
            session['dist_entrega'] = ''
            session['direccion_entrega'] = ''
            session['referencia'] = ''

        return redirect(url_for('checkout_pago'))

    return render_template('datos_entrega.html', locales=locales)


@app.route('/checkout/pago', methods=['GET', 'POST'])
@login_required
def checkout_pago():
    carrito_obj = Carrito.query.filter_by(usuario_id=current_user.id).first()
    if not carrito_obj or not carrito_obj.detalles:
        return redirect(url_for('carrito'))

    subtotal = sum((d.producto.precio_oferta or d.producto.precio) * d.cantidad
                   for d in carrito_obj.detalles)
    delivery = session.get('costo_delivery', 0)
    total = subtotal + delivery

    if request.method == 'POST':
        metodo = request.form.get('metodo_pago')
        session['metodo_pago'] = metodo

        # Crear pedido
        pedido = Pedido(
            numero_pedido=generar_numero_pedido(),
            usuario_id=current_user.id,
            local_id=session.get('local_id'),
            metodo_pago=metodo,
            tipo_entrega=session.get('tipo_entrega'),
            subtotal=subtotal,
            delivery=delivery,
            total=total,
            estado='Pendiente',
            dep_entrega=session.get('dep_entrega', ''),
            prov_entrega=session.get('prov_entrega', ''),
            dist_entrega=session.get('dist_entrega', ''),
            direccion_entrega=session.get('direccion_entrega', ''),
            referencia=session.get('referencia', ''),
            nombre_receptor=session.get('nombre_receptor', ''),
            telefono_receptor=session.get('telefono_receptor', ''),
            dni_receptor=session.get('dni_receptor', '')
        )
        db.session.add(pedido)
        db.session.flush()

        for d in carrito_obj.detalles:
            precio_u = d.producto.precio_oferta or d.producto.precio
            det = PedidoDetalle(
                pedido_id=pedido.id,
                producto_id=d.producto_id,
                cantidad=d.cantidad,
                precio_unitario=precio_u
            )
            db.session.add(det)
            # Reducir stock
            d.producto.stock = max(0, d.producto.stock - d.cantidad)

        # Vaciar carrito
        for d in list(carrito_obj.detalles):
            db.session.delete(d)

        db.session.commit()
        return redirect(url_for('boleta', pedido_id=pedido.id))

    return render_template('checkout.html',
                           detalles=carrito_obj.detalles,
                           subtotal=subtotal,
                           delivery=delivery,
                           total=total,
                           tipo_entrega=session.get('tipo_entrega'))


@app.route('/boleta/<int:pedido_id>')
@login_required
def boleta(pedido_id):
    pedido = Pedido.query.get_or_404(pedido_id)
    if pedido.usuario_id != current_user.id and current_user.rol != 'admin':
        flash('No tienes permiso para ver este pedido.', 'danger')
        return redirect(url_for('index'))
    return render_template('boleta.html', pedido=pedido)


@app.route('/historial')
@login_required
def historial():
    pedidos = Pedido.query.filter_by(usuario_id=current_user.id)\
        .order_by(Pedido.fecha.desc()).all()
    return render_template('historial.html', pedidos=pedidos)


# ─── PANEL ADMIN ──────────────────────────────────────────────────────────────

@app.route('/admin')
@login_required
@admin_required
def admin_dashboard():
    total_productos = Producto.query.filter_by(activo=True).count()
    total_pedidos = Pedido.query.count()
    total_clientes = Usuario.query.filter_by(rol='cliente').count()
    ventas = db.session.query(db.func.sum(Pedido.total)).scalar() or 0
    bajo_stock = Producto.query.filter(Producto.stock <= 5, Producto.activo == True).all()
    ultimos_pedidos = Pedido.query.order_by(Pedido.fecha.desc()).limit(10).all()
    return render_template('admin/dashboard.html',
                           total_productos=total_productos,
                           total_pedidos=total_pedidos,
                           total_clientes=total_clientes,
                           ventas=ventas,
                           bajo_stock=bajo_stock,
                           ultimos_pedidos=ultimos_pedidos)


# PRODUCTOS ADMIN
@app.route('/admin/productos')
@login_required
@admin_required
def admin_productos():
    productos = Producto.query.order_by(Producto.nombre).all()
    return render_template('admin/productos.html', productos=productos)


@app.route('/admin/producto/nuevo', methods=['GET', 'POST'])
@login_required
@admin_required
def admin_producto_nuevo():
    categorias = Categoria.query.all()
    if request.method == 'POST':
        nombre = request.form.get('nombre')
        descripcion = request.form.get('descripcion')
        precio = float(request.form.get('precio', 0))
        precio_oferta_raw = request.form.get('precio_oferta', '').strip()
        precio_oferta = float(precio_oferta_raw) if precio_oferta_raw else None
        stock = int(request.form.get('stock', 0))
        categoria_id = int(request.form.get('categoria_id'))
        destacado = 'destacado' in request.form

        imagen_nombre = 'default_product.png'
        if 'imagen' in request.files:
            file = request.files['imagen']
            if file and file.filename and allowed_file(file.filename):
                filename = secure_filename(file.filename)
                os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
                file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
                imagen_nombre = filename

        producto = Producto(nombre=nombre, descripcion=descripcion, precio=precio,
                            precio_oferta=precio_oferta, stock=stock,
                            categoria_id=categoria_id, imagen=imagen_nombre,
                            destacado=destacado)
        db.session.add(producto)
        db.session.commit()
        flash('Producto creado correctamente.', 'success')
        return redirect(url_for('admin_productos'))
    return render_template('admin/producto_form.html', categorias=categorias, producto=None)


@app.route('/admin/producto/editar/<int:id>', methods=['GET', 'POST'])
@login_required
@admin_required
def admin_producto_editar(id):
    producto = Producto.query.get_or_404(id)
    categorias = Categoria.query.all()
    if request.method == 'POST':
        producto.nombre = request.form.get('nombre')
        producto.descripcion = request.form.get('descripcion')
        producto.precio = float(request.form.get('precio', 0))
        precio_oferta_raw = request.form.get('precio_oferta', '').strip()
        producto.precio_oferta = float(precio_oferta_raw) if precio_oferta_raw else None
        producto.stock = int(request.form.get('stock', 0))
        producto.categoria_id = int(request.form.get('categoria_id'))
        producto.destacado = 'destacado' in request.form

        if 'imagen' in request.files:
            file = request.files['imagen']
            if file and file.filename and allowed_file(file.filename):
                filename = secure_filename(file.filename)
                os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
                file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
                producto.imagen = filename

        db.session.commit()
        flash('Producto actualizado.', 'success')
        return redirect(url_for('admin_productos'))
    return render_template('admin/producto_form.html', categorias=categorias, producto=producto)


@app.route('/admin/producto/toggle/<int:id>', methods=['POST'])
@login_required
@admin_required
def admin_producto_toggle(id):
    producto = Producto.query.get_or_404(id)
    producto.activo = not producto.activo
    db.session.commit()
    estado = 'activado' if producto.activo else 'desactivado'
    flash(f'Producto {estado}.', 'info')
    return redirect(url_for('admin_productos'))


@app.route('/admin/producto/eliminar/<int:id>', methods=['POST'])
@login_required
@admin_required
def admin_producto_eliminar(id):
    producto = Producto.query.get_or_404(id)
    db.session.delete(producto)
    db.session.commit()
    flash('Producto eliminado.', 'info')
    return redirect(url_for('admin_productos'))


# CATEGORÍAS ADMIN
@app.route('/admin/categorias', methods=['GET', 'POST'])
@login_required
@admin_required
def admin_categorias():
    if request.method == 'POST':
        nombre = request.form.get('nombre')
        descripcion = request.form.get('descripcion')
        icono = request.form.get('icono', '🛒')
        cat = Categoria(nombre=nombre, descripcion=descripcion, icono=icono)
        db.session.add(cat)
        db.session.commit()
        flash('Categoría creada.', 'success')
        return redirect(url_for('admin_categorias'))
    categorias = Categoria.query.all()
    return render_template('admin/categorias.html', categorias=categorias)


@app.route('/admin/categoria/editar/<int:id>', methods=['POST'])
@login_required
@admin_required
def admin_categoria_editar(id):
    cat = Categoria.query.get_or_404(id)
    cat.nombre = request.form.get('nombre')
    cat.descripcion = request.form.get('descripcion')
    cat.icono = request.form.get('icono', '🛒')
    db.session.commit()
    flash('Categoría actualizada.', 'success')
    return redirect(url_for('admin_categorias'))


@app.route('/admin/categoria/eliminar/<int:id>', methods=['POST'])
@login_required
@admin_required
def admin_categoria_eliminar(id):
    cat = Categoria.query.get_or_404(id)
    db.session.delete(cat)
    db.session.commit()
    flash('Categoría eliminada.', 'info')
    return redirect(url_for('admin_categorias'))


# LOCALES ADMIN
@app.route('/admin/locales')
@login_required
@admin_required
def admin_locales():
    locales = Local.query.all()
    return render_template('admin/locales.html', locales=locales)


@app.route('/admin/local/nuevo', methods=['GET', 'POST'])
@login_required
@admin_required
def admin_local_nuevo():
    if request.method == 'POST':
        local = Local(
            nombre_local=request.form.get('nombre_local'),
            departamento=request.form.get('departamento'),
            provincia=request.form.get('provincia'),
            distrito=request.form.get('distrito'),
            direccion=request.form.get('direccion'),
            telefono=request.form.get('telefono'),
            horario=request.form.get('horario')
        )
        db.session.add(local)
        db.session.commit()
        flash('Local creado.', 'success')
        return redirect(url_for('admin_locales'))
    return render_template('admin/local_form.html', local=None)


@app.route('/admin/local/editar/<int:id>', methods=['GET', 'POST'])
@login_required
@admin_required
def admin_local_editar(id):
    local = Local.query.get_or_404(id)
    if request.method == 'POST':
        local.nombre_local = request.form.get('nombre_local')
        local.departamento = request.form.get('departamento')
        local.provincia = request.form.get('provincia')
        local.distrito = request.form.get('distrito')
        local.direccion = request.form.get('direccion')
        local.telefono = request.form.get('telefono')
        local.horario = request.form.get('horario')
        db.session.commit()
        flash('Local actualizado.', 'success')
        return redirect(url_for('admin_locales'))
    return render_template('admin/local_form.html', local=local)


@app.route('/admin/local/toggle/<int:id>', methods=['POST'])
@login_required
@admin_required
def admin_local_toggle(id):
    local = Local.query.get_or_404(id)
    local.activo = not local.activo
    db.session.commit()
    flash(f'Local {"activado" if local.activo else "desactivado"}.', 'info')
    return redirect(url_for('admin_locales'))


@app.route('/admin/local/eliminar/<int:id>', methods=['POST'])
@login_required
@admin_required
def admin_local_eliminar(id):
    local = Local.query.get_or_404(id)
    db.session.delete(local)
    db.session.commit()
    flash('Local eliminado.', 'info')
    return redirect(url_for('admin_locales'))


# PEDIDOS ADMIN
@app.route('/admin/pedidos')
@login_required
@admin_required
def admin_pedidos():
    q = request.args.get('q', '')
    estado = request.args.get('estado', '')
    query = Pedido.query
    if q:
        query = query.filter(Pedido.numero_pedido.ilike(f'%{q}%'))
    if estado:
        query = query.filter_by(estado=estado)
    pedidos = query.order_by(Pedido.fecha.desc()).all()
    return render_template('admin/pedidos.html', pedidos=pedidos, q=q, estado=estado)


@app.route('/admin/pedido/<int:id>/estado', methods=['POST'])
@login_required
@admin_required
def admin_pedido_estado(id):
    pedido = Pedido.query.get_or_404(id)
    pedido.estado = request.form.get('estado')
    db.session.commit()
    flash('Estado del pedido actualizado.', 'success')
    return redirect(url_for('admin_pedidos'))


# USUARIOS ADMIN
@app.route('/admin/usuarios')
@login_required
@admin_required
def admin_usuarios():
    usuarios = Usuario.query.order_by(Usuario.fecha_registro.desc()).all()
    return render_template('admin/usuarios.html', usuarios=usuarios)


@app.route('/admin/usuario/<int:id>/toggle', methods=['POST'])
@login_required
@admin_required
def admin_usuario_toggle(id):
    usuario = Usuario.query.get_or_404(id)
    if usuario.id == current_user.id:
        flash('No puedes desactivar tu propia cuenta.', 'warning')
    else:
        usuario.activo = not usuario.activo
        db.session.commit()
        flash(f'Usuario {"activado" if usuario.activo else "desactivado"}.', 'info')
    return redirect(url_for('admin_usuarios'))


@app.route('/admin/usuario/<int:id>/rol', methods=['POST'])
@login_required
@admin_required
def admin_usuario_rol(id):
    usuario = Usuario.query.get_or_404(id)
    if usuario.id == current_user.id:
        flash('No puedes cambiar tu propio rol.', 'warning')
    else:
        usuario.rol = request.form.get('rol', 'cliente')
        db.session.commit()
        flash('Rol actualizado.', 'success')
    return redirect(url_for('admin_usuarios'))


# ─── INICIALIZACIÓN DE DATOS ──────────────────────────────────────────────────

def init_db():
    with app.app_context():
        db.create_all()

        if Usuario.query.filter_by(email='admin@mass.com').first():
            return

        # Admin
        admin = Usuario(nombre='Administrador', apellido='Mass', email='admin@mass.com',
                        telefono='999000001', rol='admin')
        admin.set_password('admin123')
        db.session.add(admin)

        # Categorías
        cats_data = [
            ('Abarrotes', 'Productos básicos de despensa', '🌾'),
            ('Bebidas', 'Agua, gaseosas, jugos y más', '🥤'),
            ('Limpieza', 'Productos para el hogar', '🧹'),
            ('Higiene Personal', 'Cuidado personal', '🧴'),
            ('Lácteos', 'Leche, queso y yogurt', '🥛'),
            ('Snacks', 'Golosinas y aperitivos', '🍿'),
            ('Panadería', 'Pan y productos horneados', '🍞'),
            ('Mascotas', 'Alimentos para mascotas', '🐾'),
        ]
        cats = []
        for nombre, desc, icono in cats_data:
            cat = Categoria(nombre=nombre, descripcion=desc, icono=icono)
            db.session.add(cat)
            cats.append(cat)
        db.session.flush()

        # Locales
        locales_data = [
            ('Mass San Juan de Lurigancho', 'Lima', 'Lima', 'San Juan de Lurigancho',
             'Av. Gran Chimú 1155, SJL', '(01) 700-0001', 'Lun-Dom 7:00am - 11:00pm'),
            ('Mass Los Olivos', 'Lima', 'Lima', 'Los Olivos',
             'Av. Antúnez de Mayolo 1200, Los Olivos', '(01) 700-0002', 'Lun-Dom 7:00am - 11:00pm'),
            ('Mass Comas', 'Lima', 'Lima', 'Comas',
             'Av. Universitaria Norte 3700, Comas', '(01) 700-0003', 'Lun-Dom 7:00am - 11:00pm'),
            ('Mass Ate', 'Lima', 'Lima', 'Ate',
             'Av. Nicolás Ayllón 2850, Ate', '(01) 700-0004', 'Lun-Dom 7:00am - 11:00pm'),
            ('Mass San Martín de Porres', 'Lima', 'Lima', 'San Martín de Porres',
             'Av. Perú 4500, SMP', '(01) 700-0005', 'Lun-Dom 7:00am - 11:00pm'),
            ('Mass Callao', 'Callao', 'Callao', 'Callao',
             'Av. Sáenz Peña 450, Callao', '(01) 700-0006', 'Lun-Dom 7:00am - 11:00pm'),
            ('Mass Villa El Salvador', 'Lima', 'Lima', 'Villa El Salvador',
             'Av. Separadora Industrial 1234, VES', '(01) 700-0007', 'Lun-Dom 7:00am - 11:00pm'),
            ('Mass Chorrillos', 'Lima', 'Lima', 'Chorrillos',
             'Av. Alameda Sur 890, Chorrillos', '(01) 700-0008', 'Lun-Dom 7:00am - 11:00pm'),
        ]
        for ld in locales_data:
            db.session.add(Local(nombre_local=ld[0], departamento=ld[1], provincia=ld[2],
                                 distrito=ld[3], direccion=ld[4], telefono=ld[5], horario=ld[6]))

        # Productos
        productos_data = [
            # (nombre, desc, precio, precio_oferta, stock, cat_index, destacado)
            ('Arroz Costeño 5kg', 'Arroz extra superior, ideal para el hogar', 24.90, 21.90, 80, 0, True),
            ('Aceite Primor 1L', 'Aceite vegetal sin colesterol', 9.90, None, 60, 0, True),
            ('Azúcar Rubia 1kg', 'Azúcar rubia de caña premium', 4.50, None, 100, 0, False),
            ('Fideos Don Vittorio 500g', 'Pasta de trigo semolado', 3.20, 2.80, 90, 0, False),
            ('Sal Marina 1kg', 'Sal de mesa yodada', 1.50, None, 120, 0, False),
            ('Leche Gloria 946ml', 'Leche entera evaporada', 5.90, 5.20, 75, 4, True),
            ('Yogurt Gloria 1L Fresa', 'Yogurt batido sabor fresa', 8.50, 7.90, 40, 4, True),
            ('Queso Fresco 200g', 'Queso fresco tipo andino', 6.90, None, 30, 4, False),
            ('Mantequilla Laive 200g', 'Mantequilla sin sal', 7.50, None, 35, 4, False),
            ('Atún Florida en aceite 170g', 'Atún sólido en aceite vegetal', 5.80, 4.90, 55, 0, True),
            ('Agua San Luis 2.5L', 'Agua mineral sin gas', 3.50, None, 200, 1, True),
            ('Inca Kola 1.5L', 'La bebida de sabor nacional', 7.90, 6.90, 80, 1, True),
            ('Coca Cola 1.5L', 'La bebida más famosa del mundo', 7.90, 6.90, 80, 1, False),
            ('Jugo Pulp Naranja 1L', 'Néctar de naranja con pulpa', 5.90, None, 45, 1, False),
            ('Detergente Ariel 2kg', 'Detergente en polvo con aroma', 18.90, 16.50, 40, 2, True),
            ('Limpiatodo Sapolio 750ml', 'Limpiador multiusos', 6.50, None, 55, 2, False),
            ('Lejía Clorox 680g', 'Blanqueador desinfectante', 5.90, None, 60, 2, False),
            ('Suavizante Downy 850ml', 'Suavizante de ropa aroma lavanda', 9.90, 8.50, 35, 2, False),
            ('Shampoo Head & Shoulders 400ml', 'Shampoo anticaspa', 15.90, 13.90, 40, 3, True),
            ('Jabón Dove 90g', 'Jabón hidratante con ¼ crema', 4.50, None, 80, 3, False),
            ('Papel Higiénico Elite x4', 'Papel higiénico doble hoja', 9.90, 8.90, 60, 3, True),
            ('Crema Dental Colgate 75ml', 'Crema dental triple acción', 6.90, None, 70, 3, False),
            ('Galletas Oreo x6', 'Galletas con crema de vainilla', 3.90, None, 90, 5, False),
            ('Chifles De la Costa 100g', 'Chifles de plátano salados', 2.90, None, 100, 5, False),
            ('Chocolate Sublime 36g', 'Chocolate con maní', 2.50, None, 120, 5, False),
            ('Papas Lay\'s 80g', 'Papas fritas clásicas', 4.90, None, 85, 5, True),
            ('Pan de Molde Bimbo 500g', 'Pan de molde blanco suave', 8.90, 7.90, 45, 6, True),
            ('Panetón D\'Onofrio 900g', 'Panetón tradicional italiano', 24.90, 19.90, 30, 6, True),
            ('Alimento Perro Dog Chow 3kg', 'Alimento completo para perros adultos', 42.90, 38.90, 25, 7, True),
            ('Alimento Gato Whiskas 500g', 'Alimento para gatos adultos', 12.90, None, 30, 7, False),
        ]
        for pd_data in productos_data:
            p = Producto(
                nombre=pd_data[0], descripcion=pd_data[1],
                precio=pd_data[2], precio_oferta=pd_data[3],
                stock=pd_data[4], categoria_id=cats[pd_data[5]].id,
                destacado=pd_data[6]
            )
            db.session.add(p)

        db.session.commit()
        print("✅ Base de datos inicializada correctamente.")


if __name__ == '__main__':
    init_db()
    app.run(debug=True)
