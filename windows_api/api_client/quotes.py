"""
Cliente API para Quotes (Pedidos/Cotizaciones)
"""

from typing import Dict, List, Any, Optional
from .base import BaseAPIClient


class QuotesClient(BaseAPIClient):
    """Cliente para interactuar con el endpoint de quotes de la API REST"""

    def __init__(
        self,
        base_url: str,
        api_key: str,
        timeout: int = 30,
        max_retries: int = 3,
        logger=None
    ):
        """
        Args:
            base_url: URL base de la API (ej: "https://api.com/sales-apiWEB/public/api")
            api_key: Token de autenticación Bearer
            timeout: Timeout en segundos
            max_retries: Máximo de reintentos
            logger: Logger de Python personalizado (opcional)
        """
        super().__init__(
            base_url=base_url,
            api_key=api_key,
            timeout=timeout,
            max_retries=max_retries,
            logger=logger
        )

    def get_pending_quotes(self, company_id: int) -> List[Dict]:
        """
        Obtener quotes pendientes de sincronización

        Args:
            company_id: ID de la empresa

        Returns:
            Lista de quotes con status=draft
        """
        try:
            response = self.get(
                "/sync-batch/quotes",
                params={
                    'company_id': company_id,
                    'status': 'draft'
                }
            )

            if response.get('success'):
                return response.get('quotes', [])
            else:
                return []

        except Exception as e:
            print(f"Error obteniendo quotes: {e}")
            return []

    def mark_quote_synced(self, quote_id: int) -> bool:
        """
        Marcar un quote como sincronizado

        Args:
            quote_id: ID del quote

        Returns:
            True si exitoso
        """
        try:
            response = self.post(f"/sync-batch/quotes/{quote_id}/synced", json_data={})
            return True

        except Exception as e:
            print(f"Error marcando quote como sincronizado: {e}")
            return False

    def update_quote_status(self, quote_id: int, company_id: int, status: str) -> bool:
        """
        Actualizar el status de un quote en la API REST

        Args:
            quote_id: ID del quote
            company_id: ID de la empresa
            status: Nuevo status ('approved', 'synced', etc.)

        Returns:
            True si exitoso, False si hubo error
        """
        try:
            response = self.put(
                f"/sync-batch/quotes/{quote_id}/status",
                json_data={
                    'company_id': company_id,
                    'status': status
                }
            )
            # Verificar que la respuesta sea exitosa
            if response and isinstance(response, dict):
                # Si tiene 'success' o 'status' en la respuesta
                if response.get('success') or response.get('status') == status:
                    return True
                else:
                    print(f"Error actualizando status del quote #{quote_id}: Respuesta indica fallo")
                    print(f"Response: {response}")
                    return False
            return True

        except Exception as e:
            print(f"Error actualizando status del quote #{quote_id}: {e}")
            import traceback
            print(f"Traceback: {traceback.format_exc()}")
            return False

