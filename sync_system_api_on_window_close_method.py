    def on_window_close(self):
        """Manejador de cierre de ventana de configuración.
        Valida email en PostgreSQL antes de permitir cerrar la ventana.
        """
        # Obtener email a validar
        company_email = self.company_email_var.get().strip().lower()

        if not company_email:
            # Email vacío - permitir cerrar
            self.root.destroy()
            return

        # Conectar a PostgreSQL para validar
        try:
            import psycopg2

            conn = psycopg2.connect(
                host=self.pg_host_var.get().strip(),
                port=int(self.pg_port_var.get().strip()),
                database=self.pg_database_var.get().strip(),
                user=self.pg_user_var.get().strip(),
                password=self.pg_password_var.get().strip() or '',
                connect_timeout=10
            )

            cursor = conn.cursor()

            # Buscar email en tabla company (case-insensitive)
            cursor.execute("""
                SELECT email, description
                FROM company
                WHERE LOWER(email) = LOWER(%s)
                LIMIT 1
            """, (company_email,))

            result = cursor.fetchone()
            cursor.close()
            conn.close()

            if result:
                # Email encontrado - permitir cerrar
                self.root.destroy()
            else:
                # Email NO encontrado - mostrar error, NO cerrar
                messagebox.showerror(
                    "Email no encontrado",
                    f"El email '{company_email}' NO existe en la base de datos local.\n"
                    f"Por favor verifica:\n"
                    f"• El email esté escrito correctamente\n"
                    f"• La empresa esté registrada en el sistema\n"
                    f"Luego intenta guardar nuevamente."
                )
                # Enfocar campo de email para corregir
                self.email_entry.focus_set()
                self.email_entry.select_range(0, tk.END)

        except psycopg2.OperationalError as e:
            # Error de conexión - permitir cerrar pero mostrar error
            messagebox.showerror(
                "Error de conexión",
                f"No se pudo conectar a PostgreSQL para validar el email:\n{e}\n"
                    f"Verifica los datos de conexión PostgreSQL."
            )
            self.root.destroy()
        except Exception as e:
            # Error general - permitir cerrar pero mostrar error
            messagebox.showerror(
                "Error",
                f"Error validando email en PostgreSQL:\n{e}"
            )
            self.root.destroy()
