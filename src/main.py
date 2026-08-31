import os
import sys
from flask import Flask, request, redirect, url_for, session
import mimetypes
import config

from routes.browse import browse_bp
from routes.files import files_bp
from routes.actions import actions_bp
from routes.torrents import torrents_bp
from routes.media_server import media_server_bp
from routes.auth import auth_bp  # Importamos el nuevo blueprint

# --- Configuration ---
app = Flask(__name__)
app.config.from_object(config)
mimetypes.init()

if not app.config.get('ADMIN_USERNAME') or not app.config.get('ADMIN_PASSWORD'):
        print("CRITICAL ERROR: Administrator credentials are not set.")
        print("Please set ADMIN_USERNAME and ADMIN_PASSWORD environment variables (e.g., in your .env file).")
        print("The application will not start to prevent unauthenticated access (CWE-798).")
        sys.exit(1)

app.register_blueprint(auth_bp)  # Registramos el blueprint
app.register_blueprint(browse_bp)
app.register_blueprint(files_bp)
app.register_blueprint(actions_bp)
app.register_blueprint(torrents_bp)
app.register_blueprint(media_server_bp)

# --- MIDDLEWARE GLOBAL DE SEGURIDAD ---
@app.before_request
def require_login():
    # Rutas a las que se puede acceder sin estar logueado
    allowed_routes = ['auth.login', 'static']
    
    # Si no hay sesión activa y no está en una ruta permitida, lo mandamos al login
    if not session.get('logged_in'):
        if request.endpoint not in allowed_routes:
            return redirect(url_for('auth.login'))

if __name__ == '__main__':
    fs_root = app.config['FILE_SYSTEM_ROOT']
    if not os.path.isdir(fs_root):
        os.makedirs(fs_root, exist_ok=True)
        print(f"INFO: The root path '{fs_root}' did not exist and has been created.")
        
    print(f"Serving and managing the directory: {fs_root}")
    print(f"Access the application at: http://localhost:{app.config['PORT']}")
    app.run(host='0.0.0.0', port=app.config['PORT'], debug=app.config['DEBUG'])