"""Contraseñas y sesiones usando solo la biblioteca estándar de Python."""

import hashlib
import hmac
import os
import secrets
import time

from fastapi import Header, HTTPException

from servidor.base_datos import CARPETA_BACKEND, consultar_uno

RUTA_CLAVE = CARPETA_BACKEND / ".clave_secreta"
DIAS_DE_SESION = 7


def leer_clave_secreta() -> bytes:
    """Clave que firma los tokens: la variable CLAVE_SECRETA o, si no existe, un archivo local.

    El archivo se crea la primera vez con una clave aleatoria y no se sube al repositorio,
    así nadie puede leer la clave en el código y falsificar sesiones.
    """
    if clave := os.getenv("CLAVE_SECRETA"):
        return clave.encode()
    if not RUTA_CLAVE.exists():
        RUTA_CLAVE.write_text(secrets.token_hex(32))
    return RUTA_CLAVE.read_text().strip().encode()


CLAVE_SECRETA = leer_clave_secreta()


def generar_hash(contraseña: str) -> str:
    """Guarda la contraseña como 'sal$hash' (PBKDF2 con SHA-256), nunca en texto plano."""
    sal = os.urandom(16)
    resumen = hashlib.pbkdf2_hmac("sha256", contraseña.encode(), sal, 100_000)
    return f"{sal.hex()}${resumen.hex()}"


def verificar_contraseña(contraseña: str, guardado: str) -> bool:
    try:
        sal, resumen = guardado.split("$")
        calculado = hashlib.pbkdf2_hmac("sha256", contraseña.encode(), bytes.fromhex(sal), 100_000)
    except ValueError:
        return False
    return hmac.compare_digest(calculado.hex(), resumen)


def firmar(texto: str) -> str:
    return hmac.new(CLAVE_SECRETA, texto.encode(), "sha256").hexdigest()


def crear_token(usuario: dict) -> str:
    """Token 'usuario.version.expiracion.firma'. La firma impide que alguien lo falsifique.

    La versión es la de la sesión del usuario: al cerrar sesión sube y los tokens anteriores dejan de servir.
    """
    expira = int(time.time()) + DIAS_DE_SESION * 24 * 3600
    cuerpo = f"{usuario['id']}.{usuario.get('version_sesion') or 0}.{expira}"
    return f"{cuerpo}.{firmar(cuerpo)}"


def usuario_actual(authorization: str | None = Header(None)) -> dict:
    """Dependencia de FastAPI: devuelve el usuario del token o responde 401."""
    try:
        token = authorization.removeprefix("Bearer ")
        usuario_id, version, expira, firma = token.split(".")
        valido = hmac.compare_digest(firma, firmar(f"{usuario_id}.{version}.{expira}"))
        vigente = int(expira) > time.time()
        usuario = consultar_uno("SELECT id, correo, version_sesion FROM usuarios WHERE id = ?", (int(usuario_id),))
    except (AttributeError, ValueError):
        valido = vigente = usuario = None

    if not (valido and vigente and usuario and str(usuario.pop("version_sesion") or 0) == version):
        raise HTTPException(401, "Sesión inválida o expirada")
    return usuario
