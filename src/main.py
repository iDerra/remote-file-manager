import os
from flask import Flask
import mimetypes

import config

from routes.browse import browse_bp
from routes.files import files_bp
from routes.actions import actions_bp
from routes.torrents import torrents_bp
from routes.media_server import media_server_bp

# --- Configuration ---
app = Flask(__name__)
app.config.from_object(config)

mimetypes.init()

app.register_blueprint(browse_bp)
app.register_blueprint(files_bp)
app.register_blueprint(actions_bp)
app.register_blueprint(torrents_bp)
app.register_blueprint(media_server_bp)

if __name__ == '__main__':
    fs_root = app.config['FILE_SYSTEM_ROOT']
    if not os.path.isdir(fs_root):
        os.makedirs(fs_root, exist_ok=True)
        print(f"INFO: The root path'{fs_root}' did not exist and has been created.")
    
    print(f"Serving and managing the directory: {fs_root}")
    print(f"Access the application at: http://localhost:{app.config['PORT']}")
    app.run(host='0.0.0.0', port=app.config['PORT'], debug=app.config['DEBUG'])