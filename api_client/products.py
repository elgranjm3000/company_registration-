"""
Cliente API para Products
Maneja todos los endpoints relacionados con productos
"""

from typing import List, Dict, Iterator, Optional
import logging
from .base import BaseAPIClient


class ProductsClient(BaseAPIClient):
    """
    Cliente para el endpoint de products con batch inteligente.

    Endpoints implementados:
    - GET /api/sync-client/batch/products
    - POST /api/sync-client/batch/products
    - DELETE /api/sync-client/batch/products

    Uso:
        client = ProductsClient(
            base_url='https://api.chrystal.com/api',
            api_key='tu-token-aqui'
        )

        # Sincronizar en lote
        result = client.sync_batch(company_id=1, products=[...])

        # Obtener todos los productos
        for product in client.get_all(company_id=1):
            print(product['name'])

        # Eliminar en lote
        client.delete_batch(company_id=1, codes=['PROD001', 'PROD002'])
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
        from_date: Optional[str] = None,
        category_id: Optional[int] = None
    ) -> Iterator[Dict]:
        """
        Obtener todos los productos con paginación automática.
        Devuelve un generator para memoria eficiente.

        Args:
            company_id: ID de la empresa
            search: Búsqueda textual (opcional)
            from_date: Fecha inicial (opcional)
            category_id: Filtrar por categoría ID (opcional)

        Yields:
            Dict con datos de cada producto:
                {
                    'id': 277,
                    'company_id': 1,
                    'code': 'LAPTOP001',
                    'name': 'Laptop HP 15.6"',
                    'description': 'Laptop con procesador Intel i7',
                    'price': '800.00',
                    'cost': '600.00',
                    'higher_price': '850.00',
                    'coin': 'USD',
                    'stock': 50,
                    'min_stock': 5,
                    'category_id': 1,
                    'status': 'active',
                    'weight': 2.5,
                    'unitary_cost': 600.00,
                    'buy_tax': '0',
                    'buy_aliquot': 0.0,
                    'sale_tax': '16',
                    'aliquot': 16.0,
                    'created_at': '2024-03-13T10:00:00.000000Z',
                    'updated_at': '2024-03-13T10:00:00.000000Z'
                }

        Example:
            >>> for product in client.get_all(company_id=1):
            ...     print(f"{product['code']}: {product['name']}")
        """
        page = 1

        while True:
            params = {'company_id': company_id, 'page': page}

            if search:
                params['search'] = search
            if from_date:
                params['from_date'] = from_date
            if category_id:
                params['category_id'] = category_id

            try:
                response = self.get('/sync-client/batch/products', params)
            except Exception as e:
                self.logger.error(f"Error fetching products page {page}: {e}")
                break

            if not response.get('success'):
                self.logger.error(f"API returned success=False: {response}")
                break

            data = response.get('data', {})
            products = data.get('data', [])

            if not products:
                break

            # Yield cada producto
            for product in products:
                yield product

            # Verificar si hay más páginas
            last_page = data.get('last_page', 1)
            if page >= last_page:
                break

            page += 1

            self.logger.debug(f"Fetched page {page}/{last_page} of products")

    def get_by_code(
        self,
        company_id: int,
        code: str
    ) -> Optional[Dict]:
        """
        Obtener un producto por su código.

        Args:
            company_id: ID de la empresa
            code: Código del producto

        Returns:
            Dict con el producto o None si no existe
        """
        for product in self.get_all(company_id=company_id):
            if product['code'] == code:
                return product

        return None

    # =========================================================================
    # BATCH OPERATIONS
    # =========================================================================

    def sync_batch(
        self,
        company_id: int,
        products: List[Dict],
        batch_size: Optional[int] = None
    ) -> Dict:
        """
        Sincronizar productos en lote.
        Divide automáticamente en sub-lotes si excede el máximo.

        Realiza UPSERT: si el producto existe (por code) lo actualiza,
        si no existe lo crea.

        Args:
            company_id: ID de la empresa
            products: Lista de productos a sincronizar.
                        Cada dict debe tener:
                        {
                            'code': 'PROD001',              # REQUERIDO
                            'name': 'Laptop HP',             # REQUERIDO
                            'description': 'Descripción',
                            'price': 800.00,                # REQUERIDO
                            'cost': 600.00,                 # REQUERIDO
                            'higher_price': 850.00,         # REQUERIDO
                            'coin': 'USD',                  # REQUERIDO
                            'description_coin': 'Dólares',  # REQUERIDO
                            'stock': 50,                    # REQUERIDO
                            'min_stock': 5,                 # REQUERIDO
                            'category_id': 1,               # REQUERIDO
                            'status': 'active',
                            'weight': 2.5,                  # REQUERIDO
                            'unitary_cost': 600.00,         # REQUERIDO
                            'buy_tax': '0',                 # REQUERIDO
                            'buy_aliquot': 0.0,             # REQUERIDO
                            'sale_tax': '16',               # REQUERIDO
                            'aliquot': 16.0,               # REQUERIDO
                            'product_type': 'P',            # Tipo de producto (P=Producto, C=Combo)
                            'unidad': 'Pound',              # Unidad de medida
                            'allow_decimal': False          # Permite decimales (booleano)
                        }
            batch_size: Tamaño de lote (default usa self.batch_size)

        Returns:
            Dict con estadísticas agregadas de todos los lotes:
                {
                    'success': True,
                    'created': 45,
                    'updated': 12,
                    'errors': 0,
                    'error_details': []
                }

        Example:
            >>> result = client.sync_batch(
            ...     company_id=1,
            ...     products=[{
            ...         'code': 'LAPTOP-HP-001',
            ...         'name': 'Laptop HP 15.6"',
            ...         'price': 800,
            ...         'cost': 600,
            ...         'higher_price': 850,
            ...         'coin': 'USD',
            ...         'description_coin': 'Dólares',
            ...         'stock': 50,
            ...         'min_stock': 5,
            ...         'category_id': 1,
            ...         'weight': 2.5,
            ...         'unitary_cost': 600,
            ...         'buy_tax': '0',
            ...         'buy_aliquot': 0,
            ...         'sale_tax': '16',
            ...         'aliquot': 16
            ...     }]
            ... )
            >>> print(f"Created: {result['created']}, Updated: {result['updated']}")
        """
        batch_size = batch_size or self.batch_size

        # Dividir en lotes
        batches = self._split_into_batches(products, batch_size)

        stats = {
            'success': True,
            'created': 0,
            'updated': 0,
            'errors': 0,
            'error_details': []
        }

        total_batches = len(batches)
        total_products = len(products)

        self.logger.info(
            f"Starting batch sync: {total_products} products in {total_batches} batches"
        )

        for i, batch in enumerate(batches, 1):
            self.logger.info(
                f"Processing batch {i}/{total_batches} ({len(batch)} products)"
            )

            try:
                result = self.post('/sync-client/batch/products', {
                    'company_id': company_id,
                    'products': batch
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
        Eliminar productos en lote por sus códigos.

        ⚠️ ADVERTENCIA: Esta operación es irreversible.

        Args:
            company_id: ID de la empresa
            codes: Lista de códigos de productos a eliminar

        Returns:
            Dict con:
                {
                    'success': True,
                    'deleted': 3  # Cantidad eliminada
                }

        Example:
            >>> result = client.delete_batch(
            ...     company_id=1,
            ...     codes=['PROD001', 'PROD002', 'LAPTOP-HP-001']
            ... )
            >>> print(f"Deleted: {result['deleted']} products")
        """
        if not codes:
            self.logger.warning("No codes provided for deletion")
            return {'success': True, 'deleted': 0}

        self.logger.info(f"Deleting {len(codes)} products from company {company_id}")

        try:
            result = self.delete('/sync-client/batch/products', {
                'company_id': company_id,
                'codes': codes
            })

            deleted = result.get('deleted', 0)
            self.logger.info(f"Deleted {deleted} products")

            return result

        except Exception as e:
            self.logger.error(f"Error deleting products: {e}")
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

    def get_products_map(
        self,
        company_id: int
    ) -> Dict[str, int]:
        """
        Obtener un diccionario {code: id} de todos los productos.
        Útil para mapear product codes a product_ids.

        Args:
            company_id: ID de la empresa

        Returns:
            Dict donde clave=code, valor=id
            {
                'PROD001': 277,
                'PROD002': 278,
                'LAPTOP-HP-001': 279
            }

        Example:
            >>> products_map = client.get_products_map(company_id=1)
            >>> product_id = products_map.get('PROD001')
            >>> print(f"PROD001 has ID: {product_id}")
        """
        products_map = {}

        for product in self.get_all(company_id=company_id):
            code = product['code']
            product_id = product['id']
            products_map[code] = product_id

        self.logger.debug(f"Built products map with {len(products_map)} entries")

        return products_map

    def get_categories_map(
        self,
        company_id: int
    ) -> Dict[str, int]:
        """
        Obtener mapa de categorías {name: id}.
        Este método llama internamente al endpoint de categories.

        Args:
            company_id: ID de la empresa

        Returns:
            Dict donde clave=nombre, valor=id
            {
                'Electrónica': 1,
                'Ropa': 5,
                'Alimentos': 8
            }

        Note:
            Este método requiere que CategoriesClient esté disponible.
            Si no está importado, retornará un dict vacío.
        """
        try:
            # Import dinámico para evitar dependencias circulares
            from .categories import CategoriesClient

            categories_client = CategoriesClient(
                base_url=self.base_url,
                api_key=self.api_key,
                timeout=self.timeout,
                max_retries=self.max_retries
            )

            return categories_client.get_categories_map(company_id)

        except ImportError:
            self.logger.warning("CategoriesClient not available, returning empty map")
            return {}
        except Exception as e:
            self.logger.error(f"Error fetching categories map: {e}")
            return {}
