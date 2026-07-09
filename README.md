# 🛒 Tiendas Mass — Proyecto Académico

## 📋 Tecnologías utilizadas

- Python 3.10+
- Flask 3.0
- Flask-SQLAlchemy (ORM + SQLite)
- Flask-Login (autenticación y sesiones)
- Werkzeug (hash seguro de contraseñas)
- HTML5, CSS3 propio (sin frameworks de diseño), JavaScript vanilla
- Diseño responsive (mobile / tablet / desktop)

---

## 📁 Estructura del proyecto

```
tiendas_mass_flask/
├── app.py                  # Aplicación principal: modelos, rutas, lógica
├── requirements.txt        # Dependencias del proyecto
├── README.md                # Este archivo
├── database.db              # Se genera automáticamente al ejecutar (SQLite)
├── static/
│   ├── css/styles.css       # Estilos propios (sin Bootstrap)
│   ├── js/main.js           # JavaScript del frontend
│   ├── img/                 # Imagen placeholder de productos
│   └── uploads/              # Imágenes subidas desde el panel admin
└── templates/
    ├── base.html
    ├── index.html
    ├── login.html
    ├── register.html
    ├── recuperar_password.html
    ├── catalogo.html
    ├── detalle_producto.html
    ├── carrito.html
    ├── datos_entrega.html
    ├── checkout.html
    ├── boleta.html
    ├── historial.html
    └── admin/
        ├── dashboard.html
        ├── productos.html
        ├── producto_form.html
        ├── categorias.html
        ├── locales.html
        ├── local_form.html
        ├── pedidos.html
        └── usuarios.html
```

---

## ⚙️ Instalación

### 1. Requisitos previos
- Tener instalado **Python 3.10 o superior**.
- Tener **Visual Studio Code** (recomendado) con la extensión de Python.

### 2. Descomprimir el proyecto
Descomprime el archivo `tiendas_mass_flask.zip` y abre la carpeta en Visual Studio Code:

```bash
cd tiendas_mass_flask
code .
```

### 3. Crear un entorno virtual (recomendado)

**Windows:**
```bash
python -m venv venv
venv\Scripts\activate
```

**macOS / Linux:**
```bash
python3 -m venv venv
source venv/bin/activate
```

### 4. Instalar dependencias

```bash
pip install -r requirements.txt
```

---

## ▶️ Ejecución

Con el entorno virtual activado, ejecuta:

```bash
python app.py
```

La primera vez que se ejecuta, el sistema:
1. Crea automáticamente la base de datos SQLite (`database.db`).
2. Crea el usuario administrador inicial.
3. Carga categorías, locales y productos de ejemplo.

Verás en la consola el mensaje:
```
✅ Base de datos inicializada correctamente.
```

Luego abre tu navegador en:

```
http://127.0.0.1:5000
```

---

## 👤 Credenciales de acceso

### Administrador
| Campo | Valor |
|---|---|
| Correo | `admin@mass.com` |
| Contraseña | `admin123` |

Accede al panel administrativo desde el menú de usuario tras iniciar sesión, o directamente en:
```
http://127.0.0.1:5000/admin
```

### Cliente
Puedes registrar una cuenta nueva desde `/register`, o usar cualquier cuenta que crees durante las pruebas.

---

## 🗂️ Datos iniciales cargados

- **8 categorías**: Abarrotes, Bebidas, Limpieza, Higiene Personal, Lácteos, Snacks, Panadería, Mascotas.
- **30 productos** de ejemplo distribuidos en las categorías anteriores, varios con precio de oferta y marcados como destacados.
- **8 locales** (Mass San Juan de Lurigancho, Los Olivos, Comas, Ate, San Martín de Porres, Callao, Villa El Salvador, Chorrillos).
- **1 usuario administrador**.

---

## 🧭 Funcionalidades principales

### Cliente
- Registro e inicio de sesión tradicional.
- Catálogo con búsqueda, filtro por categoría y ordenamiento por precio/nombre.
- Detalle de producto con control de stock.
- Carrito de compras (agregar, modificar cantidad, eliminar, vaciar).
- Checkout en 3 pasos: datos de entrega → método de pago → boleta.
- Selección de tipo de entrega: **Delivery** (con cálculo de costo simulado por zona) o **Recojo en tienda** (selección de local).
- Métodos de pago simulados: tarjeta de crédito/débito (con validación de 16 dígitos, CVV de 3 dígitos y fecha), Yape, Plin, contra entrega.
- Boleta simulada imprimible.
- Historial de pedidos con estado actual.

### Administrador
- Dashboard con métricas: productos, pedidos, ventas simuladas, clientes, productos con bajo stock, últimos pedidos.
- CRUD completo de productos (con subida de imágenes), categorías y locales.
- Activar/desactivar productos y locales.
- Gestión de pedidos: ver, filtrar, buscar y cambiar estado (Pendiente → Preparando → En camino → Entregado / Cancelado).
- Gestión de usuarios: cambiar rol (cliente/admin) y activar/desactivar cuentas.

---

## 🔒 Seguridad implementada

- Contraseñas almacenadas con hash seguro (Werkzeug `generate_password_hash`).
- Rutas protegidas con `@login_required` y `@admin_required`.
- Validación de formularios en backend y frontend.
- Subida de archivos restringida por extensión (`secure_filename`, whitelist de formatos de imagen).
- Mensajes claros de advertencia en todo el flujo de pago indicando que es 100% simulado.

---

## ⚠️ Nota Académica Importante

Este proyecto fue desarrollado **exclusivamente con fines educativos** como parte de un trabajo universitario. No está afiliado, asociado ni respaldado por Tiendas Mass ni por ninguna entidad real. **No ingreses datos personales, bancarios o de tarjetas reales** en ningún formulario del sistema.

---

## 🛠️ Solución de problemas comunes

**Error `ModuleNotFoundError`:** asegúrate de haber activado el entorno virtual antes de ejecutar `pip install -r requirements.txt`.

**El puerto 5000 ya está en uso:** edita la última línea de `app.py` y cambia `app.run(debug=True)` por `app.run(debug=True, port=5001)`.

**Quiero reiniciar la base de datos desde cero:** borra el archivo `database.db` y vuelve a ejecutar `python app.py`.
