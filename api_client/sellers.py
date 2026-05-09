"""
Cliente API para Sellers
Maneja todos los endpoints relacionados con vendedores
"""

from typing import List, Dict, Iterator, Optional
import logging
from .base import BaseAPIClient


class SellersClient(BaseAPIClient):
    """
    Cliente para el endpoint de sellers con batch inteligente.

    Endpoints implementados:
    - GET /api/sync-client/batch/sellers
    - POST /api/sync-client/batch/sellers
    - DELETE /api/sync-client/batch/sellers

    Particularidad:
    - Crea users automáticamente cuando no existen
    - Password DEBE venir hasheado con bcrypt
    - Email es único globalmente (para users)

    Uso:
        client = SellersClient(
            base_url='https://api.chrystal.com/api',
            api_key='tu-token-aqui'
        )

        # Sincronizar en lote
        result = client.sync_batch(company_id=1, sellers=[...])

        # Obtener todos los vendedores
        for seller in client.get_all(company_id=1):
            print(seller['code'])

        # Eliminar en lote
        client.delete_batch(company_id=1, codes=['V001', 'V002'])
    """

    def __init__(
        self,
        base_url: str,
        api_key: str,
        timeout: int = 30,
        max_retries: int = 3,
        batch_size: int = 5000,
        logger=None
    ):
        """
        Args:
            base_url: URL base de la API
            api_key: Token Bearer
            timeout: Timeout en segundos
            max_retries: Máximo de reintentos
            batch_size: Tamaño máximo de lote (default: 5000)
            logger: Logger de Python personalizado (opcional)
        """
        super().__init__(base_url, api_key, max_retries, 0.5, timeout, batch_size, logger=logger)

    # =========================================================================
    # CRUD BÁSICO
    # =========================================================================

    def get_all(
        self,
        company_id: int,
        search: Optional[str] = None,
        from_date: Optional[str] = None
    ) -> Iterator[Dict]:
        """
        Obtener todos los vendedores con paginación automática.
        Devuelve un generator para memoria eficiente.

        Args:
            company_id: ID de la empresa
            search: Búsqueda en código, nombre, email (opcional)
            from_date: Fecha inicial (opcional)

        Yields:
            Dict con datos de cada vendedor:
                {
                    'id': 12,
                    'company_id': 1,
                    'code': 'SELLER01',
                    'status': 'active',
                    'created_at': '2024-03-13T10:00:00.000000Z',
                    'updated_at': '2024-03-13T10:00:00.000000Z',
                    'user': {
                        'id': 8,
                        'name': 'Juan Pérez',
                        'email': 'juanp@company.com'
                    }
                }

        Example:
            >>> for seller in client.get_all(company_id=1):
            ...     print(f"{seller['code']}: {seller['user']['name']}")
        """
        page = 1

        while True:
            params = {'company_id': company_id, 'page': page}

            if search:
                params['search'] = search
            if from_date:
                params['from_date'] = from_date

            try:
                response = self.get('/sync-client/batch/sellers', params)
            except Exception as e:
                self.logger.error(f"Error fetching sellers page {page}: {e}")
                break

            if not response.get('success'):
                self.logger.error(f"API returned success=False: {response}")
                break

            data = response.get('data', {})
            sellers = data.get('data', [])

            if not sellers:
                break

            # Yield cada vendedor
            for seller in sellers:
                yield seller

            # Verificar si hay más páginas
            last_page = data.get('last_page', 1)
            if page >= last_page:
                break

            page += 1

            self.logger.debug(f"Fetched page {page}/{last_page} of sellers")

    def get_by_code(
        self,
        company_id: int,
        code: str
    ) -> Optional[Dict]:
        """
        Obtener un vendedor por su código.

        Args:
            company_id: ID de la empresa
            code: Código del vendedor

        Returns:
            Dict con el vendedor o None si no existe
        """
        for seller in self.get_all(company_id=company_id):
            if seller['code'] == code:
                return seller

        return None

    # =========================================================================
    # BATCH OPERATIONS
    # =========================================================================

    def sync_batch(
        self,
        company_id: int,
        sellers: List[Dict],
        batch_size: Optional[int] = None
    ) -> Dict:
        """
        Sincronizar vendedores en lote.
        Divide automáticamente en sub-lotes si excede el máximo.

        Particularidad:
        - Crea users automáticamente si no existen
        - Asocia user_id con seller

        Args:
            company_id: ID de la empresa
            sellers: Lista de vendedores a sincronizar.
                        Cada dict debe tener:
                        {
                            'code': 'V001',                  # REQUERIDO
                            'description': 'Juan Pérez',     # REQUERIDO
                            'email': 'juan@email.com',       # REQUERIDO
                            'password': '$2y$10$...',        # REQUERIDO (bcrypt)
                            'status': 'active'               # Opcional
                        }
            batch_size: Tamaño de lote (default usa self.batch_size)

        Returns:
            Dict con estadísticas agregadas de todos los lotes:
                {
                    'success': True,
                    'created': 3,
                    'updated': 1,
                    'errors': 0,
                    'error_details': []
                }

        Example:
            >>> result = client.sync_batch(
            ...     company_id=1,
            ...     sellers=[{
            ...         'code': 'SELLER_JUAN',
            ...         'description': 'Juan Pérez',
            ...         'email': 'juan.perez@email.com',
            ...         'password': '$2y$10$92IXUNpkjO0rOQ5byMi.Ye4oKoEa3Ro9llC/.og/at2.uheWG/igi'
            ...     }]
            ... )
            >>> print(f"Created: {result['created']}, Updated: {result['updated']}")
        """
        batch_size = batch_size or self.batch_size

        # Dividir en lotes
        batches = self._split_into_batches(sellers, batch_size)

        stats = {
            'success': True,
            'created': 0,
            'updated': 0,
            'errors': 0,
            'error_details': []
        }

        total_batches = len(batches)
        total_sellers = len(sellers)

        self.logger.info(
            f"Starting batch sync: {total_sellers} sellers in {total_batches} batches"
        )

        for i, batch in enumerate(batches, 1):
            self.logger.info(
                f"Processing batch {i}/{total_batches} ({len(batch)} sellers)"
            )

            try:
                result = self.post('/sync-client/batch/sellers', {
                    'company_id': company_id,
                    'sellers': batch
                })

                # Acumular estadísticas
                if result.get('success'):
                    stats['created'] += result.get('created', 0)
                    stats['updated'] += result.get('updated', 0)
                    stats['errors'] += result.get('errors', 0)
                    stats['error_details'].extend(result.get('error_details', []))

                    self.logger.debug(
                        f"Batch {i} complete: {result.get('created', 0)} created, "
                        f"{result.get('updated', 0)} updated"
                    )
                else:
                    self.logger.error(f"Batch {i} failed: {result}")
                    stats['errors'] += len(batch)
                    stats['error_details'].append({
                        'batch': i,
                        'error': result.get('message', 'Unknown error')
                    })

            except Exception as e:
                self.logger.error(f"Exception in batch {i}: {e}")
                stats['errors'] += len(batch)
                stats['error_details'].append({
                    'batch': i,
                    'error': str(e)
                })

        self.logger.info(
            f"Batch sync complete: {stats['created']} created, "
            f"{stats['updated']} updated, {stats['errors']} errors"
        )

        return stats

    def delete_batch(
        self,
        company_id: int,
        codes: List[str]
    ) -> Dict:
        """
        Eliminar vendedores en lote por sus códigos.

        ⚠️ ADVERTENCIA: Esta operación es irreversible.
        También elimina los users asociados.

        Args:
            company_id: ID de la empresa
            codes: Lista de códigos de vendedores a eliminar

        Returns:
            Dict con:
                {
                    'success': True,
                    'deleted': 2  # Cantidad eliminada
                }

        Example:
            >>> result = client.delete_batch(
            ...     company_id=1,
            ...     codes=['V001', 'V002']
            ... )
            >>> print(f"Deleted: {result['deleted']} sellers")
        """
        if not codes:
            self.logger.warning("No codes provided for deletion")
            return {'success': True, 'deleted': 0}

        self.logger.info(f"Deleting {len(codes)} sellers from company {company_id}")

        try:
            result = self.delete('/sync-client/batch/sellers', {
                'company_id': company_id,
                'codes': codes
            })

            deleted = result.get('deleted', 0)
            self.logger.info(f"Deleted {deleted} sellers")

            return result

        except Exception as e:
            self.logger.error(f"Error deleting sellers: {e}")
            raise

    # =========================================================================
    # UTILIDADES
    # =========================================================================

    def _split_into_batches(self, items: List, batch_size: int) -> List[List]:
        """
        Dividir una lista en lotes más pequeños.

        Args:
            items: Lista de elementos
            batch_size: Tamaño de cada lote

        Returns:
            Lista de listas (lotes)

        Example:
            >>> _split_into_batches([1,2,3,4,5], 2)
            [[1,2], [3,4], [5]]
        """
        return [
            items[i:i + batch_size]
            for i in range(0, len(items), batch_size)
        ]

    def get_sellers_map(
        self,
        company_id: int
    ) -> Dict[str, int]:
        """
        Obtener un diccionario {code: id} de todos los vendedores.
        Útil para mapear códigos a seller_ids.

        Args:
            company_id: ID de la empresa

        Returns:
            Dict donde clave=code, valor=id
            {
                'V001': 12,
                'V002': 13,
                'V003': 14
            }

        Example:
            >>> sellers_map = client.get_sellers_map(company_id=1)
            >>> seller_id = sellers_map.get('V001')
            >>> print(f"Seller V001 has ID: {seller_id}")
        """
        sellers_map = {}

        for seller in self.get_all(company_id=company_id):
            code = seller['code']
            seller_id = seller['id']
            sellers_map[code] = seller_id

        self.logger.debug(f"Built sellers map with {len(sellers_map)} entries")

        return sellers_map
