"""
Cliente API para Categories
Maneja todos los endpoints relacionados con categorías
"""

from typing import List, Dict, Iterator, Optional
import logging
from .base import BaseAPIClient


class CategoriesClient(BaseAPIClient):
    """
    Cliente para el endpoint de categories con batch inteligente.

    Endpoints implementados:
    - GET /api/sync-client/batch/categories
    - POST /api/sync-client/batch/categories
    - DELETE /api/sync-client/batch/categories

    Uso:
        client = CategoriesClient(
            base_url='https://api.chrystal.com/api',
            api_key='tu-token-aqui'
        )

        # Sincronizar en lote
        result = client.sync_batch(company_id=1, categories=[...])

        # Obtener todas las categorías
        for category in client.get_all(company_id=1):
            print(category['name'])

        # Eliminar en lote
        client.delete_batch(company_id=1, names=['Electrónica', 'Ropa'])
    """

    def __init__(
        self,
        base_url: str,
        api_key: str,
        timeout: int = 30,
        max_retries: int = 3,
        batch_size: int = 5000,
        logger=None,
        app_version: Optional[str] = None
    ):
        """
        Args:
            base_url: URL base de la API
            api_key: Token Bearer
            timeout: Timeout en segundos
            max_retries: Máximo de reintentos
            batch_size: Tamaño máximo de lote
            logger: Logger de Python personalizado (opcional)
            app_version: Versión de la aplicación para header X-App-Version (opcional)
        """
        super().__init__(base_url, api_key, max_retries, 0.5, timeout, batch_size, logger=logger, app_version=app_version)

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
        Obtener todas las categorías con paginación automática.
        Devuelve un generator para memoria eficiente.

        Args:
            company_id: ID de la empresa
            search: Búsqueda textual (opcional)
            from_date: Fecha inicial (opcional)

        Yields:
            Dict con datos de cada categoría:
                {
                    'id': 1,
                    'company_id': 1,
                    'name': 'Electrónica',
                    'description': 'Productos electrónicos',
                    'status': 'active',
                    'created_at': '2024-01-01T00:00:00.000000Z',
                    'updated_at': '2024-01-01T00:00:00.000000Z'
                }

        Example:
            >>> for category in client.get_all(company_id=1):
            ...     print(f"Category: {category['name']}")
        """
        page = 1

        while True:
            params = {'company_id': company_id, 'page': page}

            if search:
                params['search'] = search
            if from_date:
                params['from_date'] = from_date

            try:
                response = self.get('/sync-client/batch/categories', params)
            except Exception as e:
                self.logger.error(f"Error fetching categories page {page}: {e}")
                break

            if not response.get('success'):
                self.logger.error(f"API returned success=False: {response}")
                break

            data = response.get('data', {})
            categories = data.get('data', [])

            if not categories:
                break

            # Yield cada categoría
            for category in categories:
                yield category

            # Verificar si hay más páginas
            last_page = data.get('last_page', 1)
            if page >= last_page:
                break

            page += 1

            self.logger.debug(f"Fetched page {page}/{last_page} of categories")

    def get_by_name(
        self,
        company_id: int,
        name: str
    ) -> Optional[Dict]:
        """
        Obtener una categoría por su nombre.

        Args:
            company_id: ID de la empresa
            name: Nombre de la categoría

        Returns:
            Dict con la categoría o None si no existe
        """
        for category in self.get_all(company_id=company_id):
            if category['name'] == name:
                return category

        return None

    # =========================================================================
    # BATCH OPERATIONS
    # =========================================================================

    def sync_batch(
        self,
        company_id: int,
        categories: List[Dict],
        batch_size: Optional[int] = None
    ) -> Dict:
        """
        Sincronizar categorías en lote.
        Divide automáticamente en sub-lotes si excede el máximo.

        Realiza UPSERT: si la categoría existe (por name) la actualiza,
        si no existe la crea.

        Args:
            company_id: ID de la empresa
            categories: Lista de categorías a sincronizar.
                        Cada dict debe tener:
                        {
                            'name': 'Electrónica',
                            'description': 'Productos electrónicos',
                            'status': 'active'  # opcional
                        }
            batch_size: Tamaño de lote (default usa self.batch_size)

        Returns:
            Dict con estadísticas agregadas de todos los lotes:
                {
                    'success': True,
                    'created': 5,
                    'updated': 2,
                    'errors': 0,
                    'error_details': []
                }

        Example:
            >>> result = client.sync_batch(
            ...     company_id=1,
            ...     categories=[
            ...         {'name': 'Electrónica', 'description': 'Tecnología'},
            ...         {'name': 'Ropa', 'description': 'Prendas'}
            ...     ]
            ... )
            >>> print(f"Created: {result['created']}, Updated: {result['updated']}")
        """
        batch_size = batch_size or self.batch_size

        # Dividir en lotes
        batches = self._split_into_batches(categories, batch_size)

        stats = {
            'success': True,
            'created': 0,
            'updated': 0,
            'errors': 0,
            'error_details': []
        }

        total_batches = len(batches)
        self.logger.info(f"Starting batch sync: {len(categories)} categories in {total_batches} batches")

        for i, batch in enumerate(batches, 1):
            self.logger.info(
                f"Processing batch {i}/{total_batches} ({len(batch)} categories)"
            )

            try:
                result = self.post('/sync-client/batch/categories', {
                    'company_id': company_id,
                    'categories': batch
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
        names: List[str]
    ) -> Dict:
        """
        Eliminar categorías en lote por sus nombres.

        ⚠️ ADVERTENCIA: Esta operación es irreversible.

        Args:
            company_id: ID de la empresa
            names: Lista de nombres de categorías a eliminar

        Returns:
            Dict con:
                {
                    'success': True,
                    'deleted': 3  # Cantidad eliminada
                }

        Example:
            >>> result = client.delete_batch(
            ...     company_id=1,
            ...     names=['Categoría Vieja', 'Otra Categoría']
            ... )
            >>> print(f"Deleted: {result['deleted']} categories")
        """
        if not names:
            self.logger.warning("No names provided for deletion")
            return {'success': True, 'deleted': 0}

        self.logger.info(f"Deleting {len(names)} categories from company {company_id}")

        try:
            result = self.delete('/sync-client/batch/categories', {
                'company_id': company_id,
                'names': names
            })

            deleted = result.get('deleted', 0)
            self.logger.info(f"Deleted {deleted} categories")

            return result

        except Exception as e:
            self.logger.error(f"Error deleting categories: {e}")
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

    def get_categories_map(
        self,
        company_id: int
    ) -> Dict[str, int]:
        """
        Obtener un diccionario {name: id} de todas las categorías.
        Útil para mapear department codes a category_ids.

        Args:
            company_id: ID de la empresa

        Returns:
            Dict donde clave=nombre, valor=id
            {
                'Electrónica': 1,
                'Ropa': 5,
                'Alimentos': 8
            }

        Example:
            >>> categories_map = client.get_categories_map(company_id=1)
            >>> category_id = categories_map.get('Electrónica')
            >>> print(f"Electrónica has ID: {category_id}")
        """
        categories_map = {}

        for category in self.get_all(company_id=company_id):
            name = category['name']
            category_id = category['id']
            categories_map[name] = category_id

        self.logger.debug(f"Built categories map with {len(categories_map)} entries")

        return categories_map
