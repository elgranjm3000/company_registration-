; ====================================================================
; SCRIPT: Instalador Inno Setup para Sincronizador PostgreSQL → MySQL
; AUTOR: Sistema de Sincronización
; FECHA: 2025-01-22
; ====================================================================

[Setup]
AppName=Sincronizador PostgreSQL MySQL
AppVersion=1.0
DefaultDirName={pf}\PostgreSQLMySQLSync
DefaultGroupName=PostgreSQL MySQL Sync
OutputDir=output
OutputBaseFilename=setup_sync_service
Compression=lzma2
SolidCompression=yes
PrivilegesRequired=admin
UninstallDisplayIcon={app}\SyncManager.exe
WizardImageFile=assets\installer.bmp
WizardSmallImageFile=assets\installer_small.bmp

[Messages]
WizardSelectDir=Seleccione el directorio de instalación
WelcomeLabel1=Bienvenido al Asistente de Instalación
WelcomeLabel2=Este programa instalará el Sincronizador PostgreSQL → MySQL en su computadora.%n%nSe recomienda cerrar todas las aplicaciones antes de continuar.
FinishedLabel=El Sincronizador PostgreSQL → MySQL ha sido instalado exitosamente en su computadora.

[Files]
; Ejecutables
Source: "dist\PostgreSQLMySQLSyncService.exe"; DestDir: "{app}"; Flags: ignoreversion
Source: "dist\SyncManager.exe"; DestDir: "{app}"; Flags: ignoreversion

; Módulos Python
Source: "smart_sync_complete.py"; DestDir: "{app}"; Flags: ignoreversion
Source: "smart_sellers_sync_module.py"; DestDir: "{app}"; Flags: ignoreversion

; Scripts SQL
Source: "sql\01_create_sync_hashes.sql"; DestDir: "{app}\sql"; Flags: ignoreversion
Source: "sql\02_queries_utilidades.sql"; DestDir: "{app}\sql"; Flags: ignoreversion

; Configuración
Source: ".env"; DestDir: "{app}"; Flags: onlyifdoesntexist uninsneveruninstall

; Iconos (opcional)
Source: "assets\icon.ico"; DestDir: "{app}\assets"; Flags: ignoreversion

[Icons]
Name: "{group}\Sync Manager"; Filename: "{app}\SyncManager.exe"
Name: "{group}\Desinstalar"; Filename: "{uninstallexe}"
Name: "{commondesktop}\Sync Manager"; Filename: "{app}\SyncManager.exe"

[Run]
; Iniciar SyncManager al finalizar instalación
Filename: "{app}\SyncManager.exe"; Description: "Abrir Sync Manager"; Flags: postinstall nowait skipifsilent

[UninstallDelete]
; Archivos de log (opcional - comentado para no borrar)
; Type: files; Name: "{app}\sync_service.log"

[Code]
var
  ConfigPage: TInputQueryWizardPage;
  IntervalPage: TInputOptionWizardPage;

procedure InitializeWizard;
begin
  // Crear página de configuración de conexiones
  ConfigPage := CreateInputQueryPage(wpSelectDir, 'Configuración de Bases de Datos',
    'Ingrese los datos de conexión', False);

  ConfigPage.Add('Host PostgreSQL:', False);
  ConfigPage.Add('Database PostgreSQL:', False);
  ConfigPage.Add('Usuario PostgreSQL:', False);
  ConfigPage.Add('Password PostgreSQL:', False);

  ConfigPage.Add('Host MySQL:', False);
  ConfigPage.Add('Database MySQL:', False);
  ConfigPage.Add('Usuario MySQL:', False);
  ConfigPage.Add('Password MySQL:', False);

  // Crear página de intervalo
  IntervalPage := CreateInputOptionPage(wpSelectDir, 'Intervalo de Sincronización',
    'Seleccione con qué frecuencia se debe sincronizar:', 'Selección:', True, False);

  IntervalPage.Add('5 minutos');
  IntervalPage.Add('15 minutos');
  IntervalPage.Add('30 minutos');
  IntervalPage.Add('1 hora');
  IntervalPage.Add('2 horas');
  IntervalPage.Add('4 horas');

  IntervalPage.SelectedValueIndex := 3; // 1 hora por defecto
end;

function NextButtonClick(CurPageID: Integer): Boolean;
var
  EnvFile: TStringList;
begin
  Result := True;

  if CurPageID = ConfigPage.ID then
  begin
    // Validar campos
    if ConfigPage.Values[0] = '' then
    begin
      MsgBox('El Host PostgreSQL es obligatorio', mbError, MB_OK);
      Result := False;
      Exit;
    end;

    // Crear archivo .env
    EnvFile := TStringList.Create;
    try
      EnvFile.Add('# Configuración generada por instalador');
      EnvFile.Add('DB_HOST=' + ConfigPage.Values[0]);
      EnvFile.Add('DB_DATABASE=' + ConfigPage.Values[1]);
      EnvFile.Add('DB_USER=' + ConfigPage.Values[2]);
      EnvFile.Add('DB_PASSWORD=' + ConfigPage.Values[3]);
      EnvFile.Add('');
      EnvFile.Add('DB_HOST_MYSQL=' + ConfigPage.Values[4]);
      EnvFile.Add('DB_PORT_DATABASE_MYSQL=' + ConfigPage.Values[5]);
      EnvFile.Add('DB_USER_MYSQL=' + ConfigPage.Values[6]);
      EnvFile.Add('DB_PASSWORD_MYSQL=' + ConfigPage.Values[7]);
      EnvFile.Add('');
      EnvFile.Add('# Intervalo de sincronización (segundos)');

      case IntervalPage.SelectedValueIndex of
        0: EnvFile.Add('SYNC_INTERVAL_SECONDS=300');
        1: EnvFile.Add('SYNC_INTERVAL_SECONDS=900');
        2: EnvFile.Add('SYNC_INTERVAL_SECONDS=1800');
        3: EnvFile.Add('SYNC_INTERVAL_SECONDS=3600');
        4: EnvFile.Add('SYNC_INTERVAL_SECONDS=7200');
        5: EnvFile.Add('SYNC_INTERVAL_SECONDS=14400');
      else
        EnvFile.Add('SYNC_INTERVAL_SECONDS=3600');
      end;

      EnvFile.SaveToFile(ExpandConstant('{app}\.env'));
    finally
      EnvFile.Free;
    end;
  end;
end;

[UninstallDelete]
Type: files; Name: "{app}\.env"

; ====================================================================
; FIN DEL SCRIPT
; ====================================================================
