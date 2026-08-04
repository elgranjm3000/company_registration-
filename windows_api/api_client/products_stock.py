"""
Products Stock API Client
Cliente HTTP para sincronizar products-stock.
"""

from typing import List, Dict, Optional
from .base import BaseAPIClient


class ProductsStockClient(BaseAPIClient):
    """
    Cliente para el endpoint de products-stock.

    Endpoints:
    - POST /sync-client/batch/products-stock
    - DELETE /sync-client/batch/products-stock
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
        stocks: List[Dict],
        batch_size: Optional[int] = None
    ) -> Dict:
        """
        Sincronizar stocks en lote.

        Args:
            company_id: ID de la empresa
            stocks: Lista de stocks [{product_code, store, locations, stock, ordered_stock, committed_stock}]
            batch_size: Tamaño de lote

        Returns:
            Dict con estadísticas {success, created, updated, errors, error_details}
        """
        batch_size = batch_size or self.batch_size
        batches = self._split_into_batches(stocks, batch_size)

        stats = {
            'success': True,
            'created': 0,
            'updated': 0,
            'errors': 0,
            'error_details': []
        }

        for i, batch in enumerate(batches, 1):
            try:
                result = self.post('/sync-client/batch/products-stock', {
                    'company_id': company_id,
                    'stocks': batch
                })

                if result.get('success'):
                    data = result.get('data', {})
                    st = data.get('stats', {})
                    stats['created'] += st.get('created', 0)
                    stats['updated'] += st.get('updated', 0)
                    stats['errors'] += st.get('errors', 0)
                    stats['error_details'].extend(data.get('errors', []))
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

    def delete_batch(
        self,
        company_id: int,
        items: List[Dict],
        batch_size: Optional[int] = None,
    ) -> Dict:
        """
        Eliminar stocks en lote.

        Args:
            company_id: ID de la empresa
            items: Lista de dicts [{product_code, store, locations}]
            batch_size: Tamaño de lote

        Returns:
            Dict con {success, deleted}
        """
        batch_size = batch_size or self.batch_size
        batches = self._split_into_batches(items, batch_size)

        stats = {'success': True, 'deleted': 0}

        for batch in batches:
            try:
                result = self.delete('/sync-client/batch/products-stock', {
                    'company_id': company_id,
                    'items': batch,
                })

                if result.get('success'):
                    stats['deleted'] += result.get('deleted', 0)

            except Exception as e:
                self.logger.error(f"Error deleting stocks: {e}")

        return stats

    def _split_into_batches(self, items, batch_size):
        return [items[i:i + batch_size] for i in range(0, len(items), batch_size)]
