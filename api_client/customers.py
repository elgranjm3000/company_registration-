"""
Cliente API para Customers
Maneja todos los endpoints relacionados con clientes
"""

from typing import List, Dict, Iterator, Optional
import logging
from .base import BaseAPIClient


class CustomersClient(BaseAPIClient):
    """
    Cliente para el endpoint de customers con batch inteligente.

    Endpoints implementados:
    - GET /api/sync-client/batch/customers
    - POST /api/sync-client/batch/customers
    - DELETE /api/sync-client/batch/customers

    Uso:
        client = CustomersClient(
            base_url='https://api.chrystal.com/api',
            api_key='tu-token-aqui'
        )

        # Sincronizar en lote
        result = client.sync_batch(company_id=1, customers=[...])

        # Obtener todos los clientes
        for customer in client.get_all(company_id=1):
            print(customer['name'])

        # Eliminar en lote
        client.delete_batch(company_id=1, documents=['V12345678'])
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
        Obtener todos los clientes con paginación automática.
        Devuelve un generator para memoria eficiente.

        Args:
            company_id: ID de la empresa
            search: Búsqueda en nombre, documento, email (opcional)
            from_date: Fecha inicial (opcional)

        Yields:
            Dict con datos de cada cliente:
                {
                    'id': 45,
                    'company_id': 1,
                    'document_number': 'V12345678',
                    'name': 'Juan Pérez',
                    'email': 'juan@test.com',
                    'phone': '+58-414-1234567',
                    'address': 'Calle 123, Urbanización',
                    'status': 'active',
                    'created_at': '2024-03-13T10:00:00.000000Z',
                    'updated_at': '2024-03-13T10:00:00.000000Z'
                }

        Example:
            >>> for customer in client.get_all(company_id=1):
            ...     print(f"{customer['document_number']}: {customer['name']}")
        """
        page = 1

        while True:
            params = {'company_id': company_id, 'page': page}

            if search:
                params['search'] = search
            if from_date:
                params['from_date'] = from_date

            try:
                response = self.get('/sync-client/batch/customers', params)
            except Exception as e:
                self.logger.error(f"Error fetching customers page {page}: {e}")
                break

            if not response.get('success'):
                self.logger.error(f"API returned success=False: {response}")
                break

            data = response.get('data', {})
            customers = data.get('data', [])

            if not customers:
                break

            # Yield cada cliente
            for customer in customers:
                yield customer

            # Verificar si hay más páginas
            last_page = data.get('last_page', 1)
            if page >= last_page:
                break

            page += 1

            self.logger.debug(f"Fetched page {page}/{last_page} of customers")

    def get_by_document(
        self,
        company_id: int,
        document_number: str
    ) -> Optional[Dict]:
        """
        Obtener un cliente por su número de documento.

        Args:
            company_id: ID de la empresa
            document_number: Documento de identidad

        Returns:
            Dict con el cliente o None si no existe
        """
        for customer in self.get_all(company_id=company_id):
            if customer['document_number'] == document_number:
                return customer

        return None

    # =========================================================================
    # BATCH OPERATIONS
    # =========================================================================

    def sync_batch(
        self,
        company_id: int,
        customers: List[Dict],
        batch_size: Optional[int] = None
    ) -> Dict:
        """
        Sincronizar clientes en lote.
        Divide automáticamente en sub-lotes si excede el máximo.

        Realiza UPSERT: si el cliente existe (por document_number) lo actualiza,
        si no existe lo crea.

        Args:
            company_id: ID de la empresa
            customers: Lista de clientes a sincronizar.
                        Cada dict debe tener:
                        {
                            'document_number': 'V12345678',  # REQUERIDO
                            'name': 'Juan Pérez',              # REQUERIDO
                            'email': 'juan@test.com',          # Opcional
                            'phone': '+58-414-1234567',       # Opcional
                            'address': 'Calle 123',            # Opcional
                            'status': 'active'                # Opcional
                        }
            batch_size: Tamaño de lote (default usa self.batch_size)

        Returns:
            Dict con estadísticas agregadas de todos los lotes:
                {
                    'success': True,
                    'created': 30,
                    'updated': 5,
                    'errors': 0,
                    'error_details': []
                }

        Example:
            >>> result = client.sync_batch(
            ...     company_id=1,
            ...     customers=[{
            ...         'document_number': 'V12345678',
            ...         'name': 'María González',
            ...         'email': 'maria.g@test.com',
            ...         'phone': '+58-424-9876543',
            ...         'address': 'Calle 45, Urbanización El Rosal'
            ...     }]
            ... )
            >>> print(f"Created: {result['created']}, Updated: {result['updated']}")
        """
        batch_size = batch_size or self.batch_size

        # Dividir en lotes
        batches = self._split_into_batches(customers, batch_size)

        stats = {
            'success': True,
            'created': 0,
            'updated': 0,
            'errors': 0,
            'error_details': []
        }

        total_batches = len(batches)
        total_customers = len(customers)

        self.logger.info(
            f"Starting batch sync: {total_customers} customers in {total_batches} batches"
        )

        for i, batch in enumerate(batches, 1):
            self.logger.info(
                f"Processing batch {i}/{total_batches} ({len(batch)} customers)"
            )

            try:
                result = self.post('/sync-client/batch/customers', {
                    'company_id': company_id,
                    'customers': batch
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
        documents: List[str]
    ) -> Dict:
        """
        Eliminar clientes en lote por su número de documento.

        ⚠️ ADVERTENCIA: Esta operación es irreversible.

        Args:
            company_id: ID de la empresa
            documents: Lista de números de documento a eliminar

        Returns:
            Dict con:
                {
                    'success': True,
                    'deleted': 3  # Cantidad eliminada
                }

        Example:
            >>> result = client.delete_batch(
            ...     company_id=1,
            ...     documents=['V12345678', 'V87654321']
            ... )
            >>> print(f"Deleted: {result['deleted']} customers")
        """
        if not documents:
            self.logger.warning("No documents provided for deletion")
            return {'success': True, 'deleted': 0}

        self.logger.info(f"Deleting {len(documents)} customers from company {company_id}")

        try:
            result = self.delete('/sync-client/batch/customers', {
                'company_id': company_id,
                'documents': documents
            })

            deleted = result.get('deleted', 0)
            self.logger.info(f"Deleted {deleted} customers")

            return result

        except Exception as e:
            self.logger.error(f"Error deleting customers: {e}")
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

    def get_customers_map(
        self,
        company_id: int
    ) -> Dict[str, int]:
        """
        Obtener un diccionario {document_number: id} de todos los clientes.
        Útil para mapear documentos a customer_ids.

        Args:
            company_id: ID de la empresa

        Returns:
            Dict donde clave=document_number, valor=id
            {
                'V12345678': 45,
                'V87654321': 46,
                'J12345678': 47
            }

        Example:
            >>> customers_map = client.get_customers_map(company_id=1)
            >>> customer_id = customers_map.get('V12345678')
            >>> print(f"Customer V12345678 has ID: {customer_id}")
        """
        customers_map = {}

        for customer in self.get_all(company_id=company_id):
            doc_number = customer['document_number']
            customer_id = customer['id']
            customers_map[doc_number] = customer_id

        self.logger.debug(f"Built customers map with {len(customers_map)} entries")

        return customers_map
