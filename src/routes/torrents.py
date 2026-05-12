from flask import Blueprint, request, jsonify, current_app
import os
from werkzeug.utils import secure_filename
from utils.utilsHandler import is_safe_path

try:
    import transmission_rpc
except ImportError:
    transmission_rpc = None

torrents_bp = Blueprint('torrents', __name__)

def get_transmission_client():
    if not transmission_rpc:
        raise Exception("The transmission-rpc library is not installed.")
    return transmission_rpc.Client(host='127.0.0.1', port=9091)

@torrents_bp.route('/api/torrents/add', methods=['POST'])
def add_torrent():
    FILE_SYSTEM_ROOT = current_app.config['FILE_SYSTEM_ROOT']
    
    magnet_link = request.form.get('magnet_link', '').strip()
    torrent_file = request.files.get('torrent_file')
    download_path_relative = request.form.get('download_path', '').strip()

    if download_path_relative == '__root__':
        download_path_relative = ''

    if not is_safe_path(FILE_SYSTEM_ROOT, download_path_relative):
        return jsonify({"success": False, "message": "The download path is not valid or not allowed."}), 403
    
    download_dir_abs = os.path.join(FILE_SYSTEM_ROOT, download_path_relative)
    
    if not os.path.exists(download_dir_abs):
        try:
            os.makedirs(download_dir_abs, exist_ok=True)
        except OSError as e:
            return jsonify({"success": False, "message": f"Error creating the destination folder: {e}"}), 500

    try:
        tc = get_transmission_client()
        
        if magnet_link:
            tc.add_torrent(magnet_link, download_dir=download_dir_abs)
            return jsonify({"success": True, "message": "Magnet link added successfully."})
            
        elif torrent_file and torrent_file.filename:
            torrent_bytes = torrent_file.read()
            if not torrent_bytes:
                return jsonify({"success": False, "message": "The .torrent file is empty."}), 400
            
            tc.add_torrent(torrent_bytes, download_dir=download_dir_abs)
            return jsonify({"success": True, "message": "The .torrent file was added successfully."})
            
        else:
            return jsonify({"success": False, "message": "You must provide a Magnet Link or a .torrent file."}), 400

    except Exception as e:
        current_app.logger.error(f"Error adding torrent: {e}")
        return jsonify({"success": False, "message": f"Transmission error: {str(e)}"}), 500

@torrents_bp.route('/api/torrents/list', methods=['GET'])
def list_torrents():
    try:
        tc = get_transmission_client()
        torrents = tc.get_torrents()
        torrents_data = []
        for t in torrents:
            rate = getattr(t, 'rate_download', 0)
            progress = getattr(t, 'progress', 0.0)
            
            torrents_data.append({
                "id": t.id,
                "name": t.name,
                "progress": round(progress, 1),
                "status": t.status,
                "downloadRate": round(rate / 1024, 1),
                "errorString": getattr(t, 'error_string', '')
            })
        return jsonify({"success": True, "torrents": torrents_data})
    except Exception as e:
        current_app.logger.error(f"Error listing torrents: {e}")
        return jsonify({"success": False, "message": str(e)}), 500

@torrents_bp.route('/api/torrents/remove', methods=['POST'])
def remove_torrent():
    try:
        data = request.get_json()
        torrent_id = data.get('id')
        
        if torrent_id is None:
            return jsonify({"success": False, "message": "No valid ID provided."}), 400

        tc = get_transmission_client()
        tc.remove_torrent(torrent_id, delete_data=True)
        
        return jsonify({"success": True, "message": "Torrent and files removed successfully."})
        
    except Exception as e:
        current_app.logger.error(f"Error removing torrent: {e}")
        return jsonify({"success": False, "message": str(e)}), 500