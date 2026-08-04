import os
import shutil
import subprocess
import re

def get_system_disk_info(file_system_root):
    """
    Obtiene la información de estado, espacio y salud S.M.A.R.T. del disco.
    """
    total, used, free = shutil.disk_usage(file_system_root)
    percent = round((used / total) * 100, 1) if total > 0 else 0
    
    device_path = "Desconocido"
    fs_type = "Desconocido"
    raw_device = ""
    
    df_result = subprocess.run(['df', '-T', file_system_root], capture_output=True, text=True)
    if df_result.returncode == 0:
        lines = df_result.stdout.strip().split('\n')
        if len(lines) > 1:
            parts = lines[1].split()
            device_path = parts[0]
            fs_type = parts[1]
            
            match = re.match(r'(/dev/sd[a-z]|/dev/nvme\d+n\d+|/dev/mmcblk\d+)', device_path)
            if match:
                raw_device = match.group(1)

    power_status = "Desconocido"
    temperature = "N/A"
    health = "Desconocido"
    is_writable = os.access(file_system_root, os.W_OK)

    if raw_device:
        hdparm_res = subprocess.run(['sudo', 'hdparm', '-C', raw_device], capture_output=True, text=True)
        if hdparm_res.returncode == 0:
            stdout_lower = hdparm_res.stdout.lower()
            if "standby" in stdout_lower:
                power_status = "Reposo (Standby)"
            elif "active" in stdout_lower or "idle" in stdout_lower:
                power_status = "Activo (Girando)"

        smart_res = subprocess.run(['sudo', 'smartctl', '-a', raw_device], capture_output=True, text=True)
        if "SMART support is: Enabled" in smart_res.stdout or "SMART overall-health" in smart_res.stdout:
            if "PASSED" in smart_res.stdout or "OK" in smart_res.stdout:
                health = "Correcto"
            elif "FAILED" in smart_res.stdout:
                health = "Riesgo de fallo"
            
            for line in smart_res.stdout.split('\n'):
                if "Temperature_Celsius" in line:
                    parts = line.split()
                    temperature = f"{parts[-1]} °C"
                    break
                elif "Current Drive Temperature:" in line:
                    temperature = f"{line.split(':')[1].strip()} °C"
                    break

    return {
        "success": True,
        "total": total,
        "used": used,
        "free": free,
        "percent": percent,
        "device": device_path,
        "fs_type": fs_type.upper(),
        "power_status": power_status,
        "health": health,
        "temperature": temperature,
        "is_writable": is_writable
    }

def safely_unmount_disk(file_system_root):
    """
    Fuerza el sincronizado de datos y desmonta el disco de forma segura.
    """
    subprocess.run(['sync'])
    res = subprocess.run(['sudo', 'umount', file_system_root], capture_output=True, text=True)
    
    if res.returncode == 0:
        return True, "Disco desconectado con seguridad. Ya puedes retirar el cable USB."
    else:
        return False, "El disco está en uso y no se puede expulsar. Detén cualquier descarga o transferencia primero."