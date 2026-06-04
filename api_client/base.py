"""
Cliente HTTP Base con retry automático y rate limiting.
Escalable: thread-safe, reutilizable, con reconexión automática.
"""

import requests
import time
import logging
from typing import Optional, Dict, Any, List
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry


# =============================================================================
# EXCEPCIONES PERSONALIZADAS
# =============================================================================

class APIError(Exception):
    """Base exception for API errors"""
    pass


class RateLimitError(APIError):
    """Rate limit exceeded (HTTP 429)"""
    pass


class AuthenticationError(APIError):
    """Authentication failed (HTTP 401)"""
    pass


class ValidationError(APIError):
    """Validation error (HTTP 422)"""
    pass


class NotFoundError(APIError):
    """Resource not found (HTTP 404)"""
    pass


# =============================================================================
# CLIENTE BASE
# =============================================================================

class BaseAPIClient:
    """
    Cliente HTTP base con retry automático y rate handling.

    Características:
    - Retry automático con exponential backoff
    - Rate limiting handling (espera y reintenta en 429)
    - Timeout configurable
    - Session reutilizable (thread-safe con connection pooling)
    - Logging integrado

    Uso:
        client = BaseAPIClient(
            base_url='https://api.chrystal.com/api',
            api_key='tu-token-aqui',
            max_retries=3,
            timeout=30
        )

        response = client.get('/sync-client/batch/products', params={'company_id': 1})
        response = client.post('/sync-client/batch/products', json_data={...})
    """

    def __init__(
        self,
        base_url: str,
        api_key: str,
        max_retries: int = 3,
        backoff_factor: float = 0.5,
        timeout: int = 30,
        batch_size: int = 5000,
        logger=None,
        app_version: Optional[str] = None
    ):
        """
        Args:
            base_url: URL base de la API (ej: 'https://api.chrystal.com/api')
            api_key: Token Bearer para autenticación
            max_retries: Máximo de reintentos automáticos (default: 3)
            backoff_factor: Factor de espera entre reintentos (default: 0.5)
            timeout: Timeout en segundos para cada request (default: 30)
            batch_size: Tamaño máximo de lote (default: 5000)
            logger: Logger de Python personalizado (opcional)
            app_version: Versión de la aplicación para header X-App-Version (opcional)
        """
        self.base_url = base_url.rstrip('/')
        self.api_key = api_key
        self.max_retries = max_retries
        self.backoff_factor = backoff_factor
        self.timeout = timeout
        self.batch_size = batch_size
        self.app_version = app_version  # Versión de la app

        # Configurar sesión con retry automático
        self.session = self._create_session()

        # Logger (usar logger personalizado si se proporciona, sino crear uno nuevo)
        if logger:
            self.logger = logger
        else:
            self.logger = logging.getLogger(self.__class__.__name__)

    def _create_session(self) -> requests.Session:
        """
        Crea una sesión de requests con retry automático usando urllib3.Retry.

        Returns:
            requests.Session configurada con retry strategy
        """
        session = requests.Session()

        # Configurar retry strategy.
        #
        # Importante: NO incluir 5xx en status_forcelist. El bucle manual
        # en _request() maneja los errores 5xx con mejor logging, evita el
        # doble-retry (urllib3 + manual), y permite ver el cuerpo de la
        # respuesta del servidor (response.text) en el mensaje de error.
        #
        # 429 se mantiene en status_forcelist como fallback rápido, aunque
        # el bucle manual también lo maneja.
        retry_strategy = Retry(
            total=self.max_retries,
            backoff_factor=self.backoff_factor,
            status_forcelist=[429],
            allowed_methods=["GET", "POST", "PUT", "DELETE", "PATCH"]
        )

        adapter = HTTPAdapter(max_retries=retry_strategy)
        session.mount("http://", adapter)
        session.mount("https://", adapter)

        # Headers por defecto
        headers = {
            'Authorization': f'Bearer {self.api_key}',
            'Content-Type': 'application/json',
            'Accept': 'application/json',
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'X-App-Name': 'sincronizador'
        }

        # Agregar versión de la aplicación si está disponible
        if self.app_version:
            headers['X-App-Version'] = self.app_version

        session.headers.update(headers)

        return session

    def _request(
        self,
        method: str,
        endpoint: str,
        params: Optional[Dict] = None,
        json_data: Optional[Dict] = None,
        retry_on_rate_limit: bool = True
    ) -> Dict[str, Any]:
        """
        Método genérico para hacer requests HTTP con manejo robusto de errores.

        Args:
            method: Método HTTP (GET, POST, PUT, DELETE)
            endpoint: Endpoint sin la base URL (ej: '/sync-client/batch/products')
            params: Query parameters para GET
            json_data: Body para POST/PUT
            retry_on_rate_limit: Si True, espera y reintenta en 429

        Returns:
            Dict con la respuesta JSON

        Raises:
            AuthenticationError: Si el token es inválido (401)
            RateLimitError: Si excede el rate limit (429)
            ValidationError: Si hay error de validación (422)
            NotFoundError: Si el recurso no existe (404)
            APIError: Para otros errores
        """
        url = f"{self.base_url}{endpoint}"

        for attempt in range(self.max_retries + 1):
            try:
                # Log de la request
                self._log_request(method, endpoint, params, json_data)

                response = self.session.request(
                    method=method,
                    url=url,
                    params=params,
                    json=json_data,
                    timeout=self.timeout
                )

                # Log de la respuesta
                self._log_response(response, endpoint)

                # Manejar códigos de estado específicos
                if response.status_code == 401:
                    raise AuthenticationError(
                        f"Invalid API token (401): {response.text}"
                    )

                if response.status_code == 403:
                    # Forbidden - puede ser token inválido o permisos insuficientes
                    try:
                        error_detail = response.json()
                    except:
                        error_detail = response.text[:200]
                    raise APIError(
                        f"Access forbidden (403) for {endpoint}: {error_detail}"
                    )

                if response.status_code == 404:
                    raise NotFoundError(
                        f"Resource not found (404): {endpoint}"
                    )

                if response.status_code == 422:
                    error_data = response.json() if response.headers.get('content-type') == 'application/json' else {}
                    raise ValidationError(
                        f"Validation error (422): {error_data}"
                    )

                if response.status_code == 429:
                    if retry_on_rate_limit and attempt < self.max_retries:
                        # Rate limit: esperar y reintentar con exponential backoff
                        wait_time = (attempt + 1) * 2  # 2s, 4s, 6s...
                        self.logger.warning(
                            f"⏳ Rate limit (429). Esperando {wait_time}s... "
                            f"(intento {attempt + 1}/{self.max_retries})"
                        )
                        time.sleep(wait_time)
                        continue
                    else:
                        raise RateLimitError(
                            f"Rate limit exceeded (429) after {self.max_retries} retries"
                        )

                # Errores del servidor (5xx) - reintentar
                if response.status_code >= 500:
                    if attempt < self.max_retries:
                        # Error del servidor: esperar y reintentar con exponential backoff
                        wait_time = self.backoff_factor * (2 ** attempt)  # 0.5s, 1s, 2s, 4s...
                        self.logger.warning(
                            f"⚠️ Error del servidor ({response.status_code}). "
                            f"Reintentando en {wait_time:.1f}s... "
                            f"(intento {attempt + 1}/{self.max_retries})"
                        )
                        time.sleep(wait_time)
                        continue
                    else:
                        # Último intento falló, levantar excepción
                        raise APIError(
                            f"Server error ({response.status_code}) after {self.max_retries} retries: {response.text[:200]}"
                        )

                # Para otros errores HTTP, levantar excepción
                response.raise_for_status()

                # Retornar JSON de la respuesta
                return response.json()

            except requests.exceptions.Timeout:
                if attempt < self.max_retries:
                    wait_time = self.backoff_factor * (2 ** attempt)
                    self.logger.warning(
                        f"Timeout on attempt {attempt + 1}/{self.max_retries}. "
                        f"Retrying in {wait_time}s..."
                    )
                    time.sleep(wait_time)
                    continue
                raise APIError(
                    f"Request timeout after {self.max_retries} retries"
                )

            except requests.exceptions.ConnectionError:
                if attempt < self.max_retries:
                    wait_time = self.backoff_factor * (2 ** attempt)
                    self.logger.warning(
                        f"Connection error on attempt {attempt + 1}/{self.max_retries}. "
                        f"Retrying in {wait_time}s..."
                    )
                    time.sleep(wait_time)
                    continue
                raise APIError(
                    f"Connection failed after {self.max_retries} retries"
                )

        raise APIError("Max retries exceeded")

    def _log_request(self, method: str, endpoint: str, params: Optional[Dict], json_data: Optional[Dict]):
        """Log información de la request saliente."""
        try:
            # Mostrar endpoint y método
            msg = f"📤 {method} {endpoint}"

            # Si hay datos, mostrar cantidad
            if json_data and method in ['POST', 'PUT', 'PATCH']:
                if isinstance(json_data, dict):
                    if 'products' in json_data:
                        msg += f" ({len(json_data['products'])} products)"
                    elif 'customers' in json_data:
                        msg += f" ({len(json_data['customers'])} customers)"
                        # DEBUG: Mostrar primer customer para ver qué campos se envían
                        if len(json_data['customers']) > 0:
                            import json
                            print(f"\n{'='*70}")
                            print(f"📤 REQUEST PAYLOAD DETALLADO - {endpoint}")
                            print(f"{'='*70}")
                            print(f"Company ID: {json_data.get('company_id')}")
                            print(f"Primer customer completo:")
                            print(json.dumps(json_data['customers'][0], indent=2, ensure_ascii=False))
                            print(f"{'='*70}\n")
                    elif 'sellers' in json_data:
                        msg += f" ({len(json_data['sellers'])} sellers)"
                    elif 'categories' in json_data:
                        msg += f" ({len(json_data['categories'])} categories)"
                    else:
                        msg += " (1 item)"
                else:
                    msg += " (data)"

            self.logger.info(msg)  # Cambiar a info para verlo siempre
        except Exception:
            pass  # No fallar el request por error de logging

    def _log_response(self, response, endpoint: str):
        """Log información de la respuesta entrante (solo resultado, sin datos)."""
        try:
            # Status code
            status_icon = "✅" if 200 <= response.status_code < 300 else "❌"
            msg = f"{status_icon} {response.status_code} {endpoint}"

            # Intentar parsear JSON para extraer solo estadísticas
            try:
                if response.headers.get('content-type', '').startswith('application/json'):
                    json_resp = response.json()

                    if isinstance(json_resp, dict):
                        # Solo mostrar estadísticas, NO mostrar datos
                        stats = []

                        if 'success' in json_resp:
                            stats.append(f"success={json_resp['success']}")

                        if 'created' in json_resp:
                            stats.append(f"created={json_resp['created']}")

                        if 'updated' in json_resp:
                            stats.append(f"updated={json_resp['updated']}")

                        if 'errors' in json_resp and json_resp['errors'] > 0:
                            stats.append(f"errors={json_resp['errors']}")

                        if 'data' in json_resp and isinstance(json_resp['data'], list):
                            stats.append(f"items={len(json_resp['data'])}")

                        if stats:
                            msg += f" | {', '.join(stats)}"

                        # Si hay error, mostrar mensaje breve
                        if 'error' in json_resp and response.status_code >= 400:
                            msg += f" | Error: {str(json_resp['error'])[:100]}"

                    elif isinstance(json_resp, list):
                        msg += f" | items={len(json_resp)}"

            except Exception:
                pass  # Si no es JSON, no mostrar detalles

            # Log según status code
            if response.status_code >= 200 and response.status_code < 300:
                self.logger.info(msg)
            elif response.status_code >= 400:
                self.logger.warning(msg)
            else:
                self.logger.debug(msg)

        except Exception:
            pass  # No fallar el request por error de logging

    def get(self, endpoint: str, params: Optional[Dict] = None) -> Dict[str, Any]:
        """
        Conveniencia para GET requests.

        Args:
            endpoint: Endpoint sin base URL
            params: Query parameters

        Returns:
            Dict con respuesta JSON
        """
        return self._request('GET', endpoint, params=params)

    def post(self, endpoint: str, json_data: Dict) -> Dict[str, Any]:
        """
        Conveniencia para POST requests.

        Args:
            endpoint: Endpoint sin base URL
            json_data: Body del request

        Returns:
            Dict con respuesta JSON
        """
        return self._request('POST', endpoint, json_data=json_data)

    def delete(self, endpoint: str, json_data: Optional[Dict] = None) -> Dict[str, Any]:
        """
        Conveniencia para DELETE requests.

        Args:
            endpoint: Endpoint sin base URL
            json_data: Body del request (opcional)

        Returns:
            Dict con respuesta JSON
        """
        return self._request('DELETE', endpoint, json_data=json_data)

    def put(self, endpoint: str, json_data: Dict) -> Dict[str, Any]:
        """
        Conveniencia para PUT requests.

        Args:
            endpoint: Endpoint sin base URL
            json_data: Body del request

        Returns:
            Dict con respuesta JSON
        """
        return self._request('PUT', endpoint, json_data=json_data)

    def close(self):
        """Cerrar la sesión HTTP (liberar recursos)"""
        if self.session:
            self.session.close()
            self.logger.debug("HTTP session closed")

    def __enter__(self):
        """Context manager entry"""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit"""
        self.close()
