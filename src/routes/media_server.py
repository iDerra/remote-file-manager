from flask import Blueprint, jsonify
import subprocess

media_server_bp = Blueprint('media_server', __name__)

@media_server_bp.route('/api/services/minidlna/<action>', methods=['POST'])
def control_minidlna(action):
    valid_actions = ['start', 'stop', 'restart', 'status', 'rescan']
    if action not in valid_actions:
        return jsonify({"success": False, "message": "Invalid action."}), 400

    try:
        if action == 'status':
            result = subprocess.run(['sudo', 'systemctl', 'is-active', 'minidlna'], capture_output=True, text=True)
            is_active = result.stdout.strip() == 'active'
            return jsonify({"success": True, "active": is_active})
            
        elif action == 'rescan':
            subprocess.run(['sudo', 'systemctl', 'restart', 'minidlna'], check=True)
            return jsonify({"success": True, "message": "Service restarted and scanning media..."})
            
        else:
            # start, stop, restart
            subprocess.run(['sudo', 'systemctl', action, 'minidlna'], check=True)
            return jsonify({"success": True, "message": f"Command '{action}' executed successfully."})

    except subprocess.CalledProcessError as e:
        return jsonify({"success": False, "message": f"System error occurred while executing {action}."}), 500
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500