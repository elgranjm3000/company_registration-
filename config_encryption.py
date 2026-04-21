#!/usr/bin/env python3
"""
Módulo de encriptación para configuraciones sensibles
Usa Fernet (AES-128) para encriptar contraseñas y datos sensibles
"""

import base64
import hashlib
import os
import json
from cryptography.fernet import Fernet

# Clave de encriptación basada en el hardware de la máquina
# Esto hace que el archivo solo pueda desencriptarse en la misma máquina
def _get_machine_key() -> bytes:
    """
    Genera una clave única basada en el hardware de la máquina

    En Windows: Usa machine_guid del registro
    En Linux/Mac: Usa combo de hostname + id de máquina
    """
    try:
        import platform
        import uuid

        # Obtener identificadores únicos de la máquina
        hostname = platform.node()
        machine_id = str(uuid.getnode())

        # Combinar con un salt fijo
        salt = b"sync_config_salt_2024"

        # Generar clave usando SHA-256
        key_material = f"{hostname}{machine_id}".encode() + salt
        key = hashlib.sha256(key_material).digest()

        # Fernet necesita una clave de 32 bytes (AES-128)
        return base64.urlsafe_b64encode(key[:32])
    except Exception:
        # Fallback: clave basada en username
        import getpass
        username = getpass.getuser()
        key = hashlib.sha256(f"{username}_sync_config".encode()).digest()
        return base64.urlsafe_b64encode(key[:32])


def encrypt_password(password: str) -> str:
    """
    Encripta una contraseña

    Args:
        password: Contraseña en texto plano

    Returns:
        Contraseña encriptada (base64)
    """
    if not password:
        return ""

    key = _get_machine_key()
    fernet = Fernet(key)

    # Encriptar
    encrypted = fernet.encrypt(password.encode())

    # Retornar como base64 para guardar en JSON
    return base64.b64encode(encrypted).decode('utf-8')


def decrypt_password(encrypted_password: str) -> str:
    """
    Desencripta una contraseña

    Args:
        encrypted_password: Contraseña encriptada (base64)

    Returns:
        Contraseña en texto plano
    """
    if not encrypted_password:
        return ""

    try:
        key = _get_machine_key()
        fernet = Fernet(key)

        # Decodificar base64 y desencriptar
        encrypted_bytes = base64.b64decode(encrypted_password.encode('utf-8'))
        decrypted = fernet.decrypt(encrypted_bytes)

        return decrypted.decode('utf-8')
    except Exception as e:
        # Si falla, probablemente la clave cambió o el archivo fue movido a otra máquina
        print(f"Error desencriptando contraseña: {e}")
        return ""


def encrypt_config(config: dict) -> dict:
    """
    Encripta TODOS los campos sensibles del config

    Args:
        config: Diccionario de configuración con datos en texto plano

    Returns:
        Diccionario con datos encriptados
    """
    encrypted_config = config.copy()

    # Campos sensibles a encriptar - TODOS los datos del archivo de configuración
    sensitive_fields = [
        # API - TODOS los campos de la API
        'api_url',
        'api_email',
        'api_password',
        'api_password_encrypted',
        # PostgreSQL - TODOS los campos de conexión
        'postgres_host',
        'postgres_port',
        'postgres_database',
        'postgres_user',
        'postgres_password',
        # MySQL - TODOS los campos de conexión
        'mysql_host',
        'mysql_port',
        'mysql_database',
        'mysql_user',
        'mysql_password',
        # Empresa - información sensible
        'company_rif',
        'company_email',
        'company_name',
        # Otros campos sensibles
        'api_key',
        'secret_key',
        'access_token',
        'refresh_token'
    ]

    for field in sensitive_fields:
        if field in encrypted_config and encrypted_config[field]:
            # Encriptar solo si no está ya encriptado (no empieza con 'enc:')
            value = encrypted_config[field]
            if isinstance(value, str) and not value.startswith('enc:'):
                encrypted_config[field] = 'enc:' + encrypt_password(value)

    return encrypted_config


def decrypt_config(config: dict) -> dict:
    """
    Desencripta TODOS los campos sensibles del config

    Args:
        config: Diccionario de configuración con datos encriptados

    Returns:
        Diccionario con datos en texto plano
    """
    decrypted_config = config.copy()

    # Primero: Migración de formato antiguo a nuevo
    # Si existe api_password_encrypted (formato antiguo), migrarlo a api_password
    if 'api_password_encrypted' in decrypted_config and 'api_password' not in decrypted_config:
        encrypted_old = decrypted_config['api_password_encrypted']
        if encrypted_old and not encrypted_old.startswith('enc:'):
            # Formato antiguo: desencriptar y convertir a formato nuevo
            try:
                decrypted_value = decrypt_password(encrypted_old)
                decrypted_config['api_password'] = decrypted_value
                # Eliminar campo antiguo después de migrar
                del decrypted_config['api_password_encrypted']
            except Exception as e:
                print(f"Advertencia: No se pudo desencriptar api_password_encrypted: {e}")

    # Campos sensibles a desencriptar - TODOS los datos del archivo de configuración
    sensitive_fields = [
        # API - TODOS los campos de la API
        'api_url',
        'api_email',
        'api_password',
        'api_password_encrypted',  # Por si acaso quedó alguno antiguo
        # PostgreSQL - TODOS los campos de conexión
        'postgres_host',
        'postgres_port',
        'postgres_database',
        'postgres_user',
        'postgres_password',
        # MySQL - TODOS los campos de conexión
        'mysql_host',
        'mysql_port',
        'mysql_database',
        'mysql_user',
        'mysql_password',
        # Empresa - información sensible
        'company_rif',
        'company_email',
        'company_name',
        # Otros campos sensibles
        'api_key',
        'secret_key',
        'access_token',
        'refresh_token'
    ]

    for field in sensitive_fields:
        if field in decrypted_config and decrypted_config[field]:
            encrypted_value = decrypted_config[field]
            if isinstance(encrypted_value, str) and encrypted_value.startswith('enc:'):
                # Formato nuevo: Extraer y desencriptar
                encrypted_password = encrypted_value[4:]  # Quitar 'enc:'
                decrypted_config[field] = decrypt_password(encrypted_password)

    return decrypted_config


def is_encrypted(value: str) -> bool:
    """
    Verifica si un valor está encriptado

    Args:
        value: Valor a verificar

    Returns:
        True si está encriptado (empieza con 'enc:')
    """
    return isinstance(value, str) and value.startswith('enc:')


# ==============================================================================
# FUNCIONES PARA COMPATIBILIDAD CON WINDOWS CREDENTIAL MANAGER
# ==============================================================================

def save_to_windows_credential_manager(target_name: str, username: str, password: str) -> bool:
    """
    Guarda credenciales en Windows Credential Manager (más seguro que archivo)

    Args:
        target_name: Nombre del recurso (ej: 'PostgreSQL_Sync')
        username: Usuario
        password: Contraseña

    Returns:
        True si exitoso
    """
    try:
        import win32cred
        import win32security

        # Convertir password a bytes
        credential_blob = password.encode('utf-16-le')

        # Crear credencial
        win32cred.CredWrite(
            {
                "Type": win32cred.CRED_TYPE_GENERIC,
                "TargetName": target_name,
                "UserName": username,
                "CredentialBlob": credential_blob,
                "Persist": win32cred.CRED_PERSIST_ENTERPRISE  # Persiste después de reboot
            }
        )
        return True
    except ImportError:
        # pywin32 no está instalado
        return False
    except Exception as e:
        print(f"Error guardando en Credential Manager: {e}")
        return False


def read_from_windows_credential_manager(target_name: str) -> tuple:
    """
    Lee credenciales desde Windows Credential Manager

    Args:
        target_name: Nombre del recurso

    Returns:
        Tuple (username, password) o (None, None) si no existe
    """
    try:
        import win32cred

        cred = win32cred.CredRead(
            Type=win32cred.CRED_TYPE_GENERIC,
            TargetName=target_name
        )

        if cred:
            username = cred['UserName']
            password_blob = cred['CredentialBlob']
            password = password_blob.decode('utf-16-le')
            return (username, password)
        else:
            return (None, None)
    except ImportError:
        return (None, None)
    except Exception as e:
        print(f"Error leyendo de Credential Manager: {e}")
        return (None, None)
