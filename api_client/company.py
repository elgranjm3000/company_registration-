"""
Cliente API para Company
Maneja la validación y creación de empresas
"""

from typing import Dict, Optional
import logging
from .base import BaseAPIClient


class CompanyClient(BaseAPIClient):
    """
    Cliente para el endpoint de company.

    Endpoint:
    - POST /api/sync-client/batch/company/validate

    Uso:
        client = CompanyClient(
            base_url='https://api.chrystal.com/api',
            api_key='tu-token-aqui'
        )

        result = client.validate(
            rif='J123456789',
            email='empresa@test.com',
            name='Mi Empresa S.A.'
        )

        if result['success']:
            company_id = result['company_id']
            print(f"Company ID: {company_id}")
    """

    def __init__(
        self,
        base_url: str,
        api_key: str,
        timeout: int = 30,
        max_retries: int = 3
    ):
        """
        Args:
            base_url: URL base de la API
            api_key: Token Bearer
            timeout: Timeout en segundos
            max_retries: Máximo de reintentos
        """
        super().__init__(base_url, api_key, max_retries, 0.5, timeout)
        self.logger = logging.getLogger(self.__class__.__name__)

    def validate(
        self,
        rif: str,
        email: str,
        name: Optional[str] = None
    ) -> Dict:
        """
        Validar o crear una empresa.

        Si la empresa existe (por RIF), retorna sus datos.
        Si no existe, la crea automáticamente.

        Args:
            rif: RIF de la empresa (máx 50 caracteres)
            email: Email de la empresa
            name: Nombre opcional (usa RIF si no se proporciona)

        Returns:
            Dict con:
                {
                    'success': True,
                    'company_id': 25,
                    'company': {
                        'id': 25,
                        'name': 'Mi Empresa S.A.',
                        'rif': 'J123456789',
                        'email': 'empresa@test.com'
                    }
                }

        Raises:
            ValidationError: Si el RIF o email son inválidos
            AuthenticationError: Si el token es inválido
            APIError: Para otros errores

        Example:
            >>> result = client.validate(
            ...     rif='J123456789',
            ...     email='miempresa@test.com',
            ...     name='Mi Compañía S.A.'
            ... )
            >>> if result['success']:
            ...     print(f"Company ID: {result['company_id']}")
        """
        payload = {
            'rif': rif,
            'email': email
        }

        if name:
            payload['name'] = name

        self.logger.info(f"Validating company: RIF={rif}, Email={email}")

        try:
            result = self.post('/sync-client/batch/company/validate', payload)

            if result.get('success'):
                company_id = result.get('company_id')
                company = result.get('company', {})
                company_name = company.get('name', 'N/A')

                self.logger.info(
                    f"✅ Company validated: {company_name} (ID: {company_id})"
                )

                # Guardar company_id para uso futuro
                self.company_id = company_id

            return result

        except Exception as e:
            self.logger.error(f"❌ Company validation failed: {e}")
            raise
