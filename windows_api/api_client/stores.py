"""
Stores API Client
Cliente HTTP para sincronizar stores.
"""

from typing import List, Dict, Optional
from .base import BaseAPIClient


class StoresClient(BaseAPIClient):
    """
    Cliente para el endpoint de stores.

    Endpoints:
    - POST /sync-client/batch/store
    - DELETE /sync-client/batch/store
    """

    def __init__(
        self,
        base_url: str,
        api_key: Optional[str] = None,
        max_retries: int = 3,
        timeout: int = 30,
        batch_size: int = 500,
        logger=None,
        app_version: Optional[str] = None,
        chrystal_version: Optional[str] = None,
        device_uuid: Optional[str] = None
    ):
        super().__init__(base_url, api_key, max_retries, 0.5, timeout, batch_size,
                         logger=logger, app_version=app_version,
                         chrystal_version=chrystal_version, device_uuid=device_uuid)

    def sync_batch(
        self,
        company_id: int,
        stores: List[Dict],
        batch_size: Optional[int] = None
    ) -> Dict:
        """
        Sincronizar stores en lote.

        Args:
            company_id: ID de la empresa
            stores: Lista de stores [{code, description}]
            batch_size: Tamaño de lote

        Returns:
            Dict con estadísticas {success, created, updated, errors, error_details}
        """
        batch_size = batch_size or self.batch_size
        batches = self._split_into_batches(stores, batch_size)

        stats = {
            'success': True,
            'created': 0,
            'updated': 0,
            'errors': 0,
            'error_details': []
        }

        for i, batch in enumerate(batches, 1):
            try:
                result = self.post('/sync-client/batch/store', {
                    'company_id': company_id,
                    'stores': batch
                })

                if result.get('success'):
                    created = result.get('created', 0)
                    updated = result.get('updated', 0)
                    # Si la API no retorna conteos, asumir que todos se procesaron
                    if created == 0 and updated == 0:
                        created = len(batch)
                    stats['created'] += created
                    stats['updated'] += updated
                    stats['errors'] += result.get('errors', 0)
                    stats['error_details'].extend(result.get('error_details', []))
                else:
                    stats['errors'] += len(batch)
                    stats['error_details'].append({
                        'batch': i,
                        'error': result.get('message', 'Unknown error')
                    })

            except Exception as e:
                self.logger.error(f"Exception in batch {i}: {e}")
                stats['errors'] += len(batch)
                stats['error_details'].append({'batch': i, 'error': str(e)})

        return stats

    def _split_into_batches(self, items, batch_size):
        return [items[i:i + batch_size] for i in range(0, len(items), batch_size)]

    def delete_batch(
        self,
        company_id: int,
        codes: List[str],
        batch_size: Optional[int] = None
    ) -> Dict:
        """
        Eliminar stores en lote.

        Args:
            company_id: ID de la empresa
            codes: Lista de códigos a eliminar
            batch_size: Tamaño de lote

        Returns:
            Dict con {success, deleted}
        """
        batch_size = batch_size or self.batch_size
        batches = self._split_into_batches(codes, batch_size)

        stats = {'success': True, 'deleted': 0}

        for batch in batches:
            try:
                result = self.delete('/sync-client/batch/store', {
                    'company_id': company_id,
                    'codes': batch
                })

                if result.get('success'):
                    stats['deleted'] += result.get('deleted', 0)

            except Exception as e:
                self.logger.error(f"Error deleting stores: {e}")

        return stats
