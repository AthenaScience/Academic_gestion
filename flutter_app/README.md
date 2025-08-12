# Gestión Académica - App Flutter

Aplicación móvil multiplataforma para el sistema de gestión académica, desarrollada con Flutter.

## Características

- **Multiplataforma**: iOS, Android, Web y Desktop
- **Autenticación**: Sistema de login seguro con JWT
- **Gestión de Estudiantes**: Lista, búsqueda y detalles
- **Gestión de Pagos**: Seguimiento de pagos y estados
- **Certificados**: Solicitud y descarga de certificados
- **API REST**: Consumo de la API Django existente

## Requisitos

- Flutter SDK 3.0.0 o superior
- Dart SDK 3.0.0 o superior
- Android Studio / VS Code con extensiones Flutter

## Instalación

1. **Clonar el repositorio**
   ```bash
   git clone <url-del-repositorio>
   cd flutter_app
   ```

2. **Instalar dependencias**
   ```bash
   flutter pub get
   ```

3. **Configurar la API**
   - Editar `lib/services/api_service.dart`
   - Cambiar `baseUrl` según tu configuración

4. **Ejecutar la aplicación**
   ```bash
   flutter run
   ```

## Estructura del Proyecto

```
lib/
├── main.dart              # Punto de entrada
├── app.dart               # Configuración de la app
├── services/
│   └── api_service.dart   # Servicio para API REST
├── providers/             # Estado de la aplicación
│   ├── auth_provider.dart
│   ├── estudiantes_provider.dart
│   ├── pagos_provider.dart
│   └── certificados_provider.dart
└── screens/               # Pantallas de la aplicación
    ├── login_screen.dart
    ├── home_screen.dart
    ├── estudiantes_screen.dart
    ├── pagos_screen.dart
    └── certificados_screen.dart
```

## Configuración de la API

La aplicación consume la API Django en:
- **Desarrollo**: `http://localhost:8000/api/v1`
- **Producción**: cambiar `baseUrl` en `lib/services/api_service.dart`

Autenticación: enviar `Authorization: Bearer <access>` en cada request protegido.

## Funcionalidades Implementadas

### ✅ Completado
- Estructura base de la aplicación
- Sistema de autenticación
- Navegación entre pantallas
- Providers para estado global
- Consumo de API REST
- Pantallas principales (Estudiantes, Pagos, Certificados)

### 🚧 En Desarrollo
- Formularios de creación/edición
- Detalles de entidades
- Búsqueda y filtros
- Descarga de certificados
- Reportes y estadísticas

### 📋 Pendiente
- Notificaciones push
- Sincronización offline
- Temas personalizables
- Tests unitarios y de integración

## Desarrollo

### Agregar nuevas pantallas
1. Crear archivo en `lib/screens/`
2. Agregar ruta en `lib/app.dart`
3. Implementar navegación

### Agregar nuevos providers
1. Crear archivo en `lib/providers/`
2. Agregar al `MultiProvider` en `main.dart`
3. Implementar lógica de estado

### Consumir nuevos endpoints
1. Agregar métodos en `lib/services/api_service.dart`
2. Implementar en el provider correspondiente
3. Usar en las pantallas

## Build y Deploy

### Android APK
```bash
flutter build apk --release
```

### iOS
```bash
flutter build ios --release
```

### Web
```bash
flutter build web --release
```

## Contribución

1. Fork del repositorio
2. Crear rama para feature (`git checkout -b feature/nueva-funcionalidad`)
3. Commit de cambios (`git commit -am 'Agregar nueva funcionalidad'`)
4. Push a la rama (`git push origin feature/nueva-funcionalidad`)
5. Crear Pull Request

## Licencia

Este proyecto está bajo la misma licencia que el proyecto principal.
