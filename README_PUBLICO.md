# 🎓 Sistema de Gestión Académica

> **Sistema integral para la gestión de estudiantes, eventos académicos y certificados**

[![Django](https://img.shields.io/badge/Django-5.1.7-green.svg)](https://www.djangoproject.com/)
[![Status](https://img.shields.io/badge/Status-En%20Desarrollo-orange.svg)](https://github.com/bryphy/gestion_academica)

## 📋 Descripción General

Sistema de gestión académica desarrollado con tecnologías modernas para la administración eficiente de:

- **Estudiantes**: Registro y gestión de información académica
- **Eventos**: Organización de cursos, diplomados y actividades académicas
- **Certificados**: Generación y validación de certificados digitales
- **Pagos**: Sistema de gestión financiera y control de cuotas

## 🛠️ Tecnologías Principales

- **Backend**: Django 5 + Django REST Framework
- **Base de Datos**: SQLite (desarrollo) / PostgreSQL (producción)
- **Autenticación**: JWT (JSON Web Tokens)
- **Documentación**: Swagger/OpenAPI
- **Contenedores**: Docker + Docker Compose

## 🚀 Características Destacadas

- ✅ **API REST completa** con autenticación JWT
- ✅ **Sistema de pagos** con gestión de cuotas
- ✅ **Generación de certificados** en PDF con códigos QR
- ✅ **Carga masiva** de datos desde archivos CSV
- ✅ **Panel de administración** Django integrado
- ✅ **Health checks** y monitoreo del sistema
- ✅ **Tests automatizados** con cobertura completa

## 📁 Estructura del Proyecto

```
gestion_academica/
├── backend/           # Backend Django
├── frontend/          # Frontend (en desarrollo)
├── docs/             # Documentación técnica
├── docker-compose.yml # Configuración Docker
└── README.md         # Este archivo
```

## ⚡ Inicio Rápido

### **Requisitos Previos**
- Docker y Docker Compose
- Git

### **Instalación y Ejecución**
```bash
# Clonar repositorio
git clone <url-del-repositorio>
cd gestion_academica

# Iniciar servicios
docker-compose up -d

# Acceder al sistema
# Backend: http://localhost:8000
# Admin: http://localhost:8000/admin/
# API: http://localhost:8000/api/v1/
# Swagger: http://localhost:8000/swagger/
```

## 🌐 URLs del Sistema

- **Backend Django**: http://localhost:8000
- **Admin Django**: http://localhost:8000/admin/
- **API REST**: http://localhost:8000/api/v1/
- **Documentación API**: http://localhost:8000/swagger/
- **Health Check**: http://localhost:8000/_healthz/

## 🔐 Autenticación

El sistema utiliza autenticación JWT para proteger los endpoints de la API:

```bash
# Obtener token de acceso
POST /api/v1/auth/jwt/
{
  "username": "tu_usuario",
  "password": "tu_password"
}

# Usar token en requests
Authorization: Bearer <access_token>
```

## 📊 APIs Disponibles

### **Endpoints Principales**
- `GET /api/v1/estudiantes/` - Gestión de estudiantes
- `GET /api/v1/eventos/` - Gestión de eventos académicos
- `GET /api/v1/certificados/` - Gestión de certificados
- `GET /api/v1/pagos/` - Sistema de pagos y cuotas

### **Funcionalidades Especiales**
- Carga masiva de estudiantes desde CSV
- Generación automática de certificados
- Validación pública de certificados
- Exportación masiva de documentos

## 🧪 Testing

El proyecto incluye una suite completa de tests:

```bash
# Ejecutar todos los tests
docker-compose exec backend python manage.py test

# Tests específicos por módulo
python manage.py test modulos.modulo_estudiantes
python manage.py test modulos.modulo_certificados
python manage.py test modulos.modulo_pagos
```

## 🐳 Docker

### **Servicios Disponibles**
- **Backend**: Django + API REST
- **Base de Datos**: PostgreSQL (opcional)
- **Cache**: Redis (opcional)

### **Comandos Útiles**
```bash
# Iniciar servicios
docker-compose up -d

# Ver logs
docker-compose logs -f backend

# Ejecutar comandos Django
docker-compose exec backend python manage.py shell

# Reconstruir imágenes
docker-compose build --no-cache
```

## 🔧 Configuración

### **Variables de Entorno**
```bash
# Configuración básica
DJANGO_DEBUG=True
DJANGO_SECRET_KEY=tu-clave-secreta
DATABASE_URL=sqlite:///db.sqlite3

# Configuración de producción
DJANGO_DEBUG=False
ALLOWED_HOSTS=tu-dominio.com
CORS_ALLOWED_ORIGINS=https://tu-dominio.com
```

## 📈 Estado del Proyecto

### **✅ Completado**
- [x] Backend Django completamente funcional
- [x] APIs REST con autenticación JWT
- [x] Sistema de monitoreo y métricas
- [x] Módulos principales implementados
- [x] Panel de administración Django
- [x] Documentación de API (Swagger)
- [x] Tests automatizados
- [x] Configuración Docker completa

### **🚧 En Desarrollo**
- [ ] Frontend (aplicación web)
- [ ] Aplicación móvil
- [ ] Sistema de notificaciones
- [ ] Reportes avanzados

### **📋 Pendiente**
- [ ] Integración con sistemas externos
- [ ] Dashboard de analytics
- [ ] Sistema de backup automático
- [ ] CI/CD pipeline

## 🤝 Contribución

### **Cómo Contribuir**
1. **Fork** el proyecto
2. **Crea** una rama para tu feature
3. **Commit** tus cambios
4. **Push** a la rama
5. **Abre** un Pull Request

### **Estándares de Código**
- **Python**: PEP 8, Black formatter
- **Commits**: Conventional Commits
- **Documentación**: Docstrings en español

## 📚 Documentación Adicional

Para información técnica detallada, consulta la documentación en el directorio `docs/` del proyecto.

## 🐛 Reportar Problemas

- Usa el sistema de **Issues** de GitHub
- Incluye pasos para reproducir el problema
- Adjunta logs y capturas de pantalla
- Especifica tu entorno (OS, versiones)

## 📄 Licencia

Este proyecto está bajo la **Licencia MIT**. Ver el archivo [LICENSE](LICENSE) para más detalles.

---

## 🎯 **¡Comienza Ahora!**

```bash
# Clona y ejecuta en menos de 5 minutos
git clone <url-del-repositorio>
cd gestion_academica
docker-compose up -d
```

**¿Necesitas ayuda?** 
- 📖 Revisa la documentación en `docs/`
- 🐛 Reporta bugs en [Issues](https://github.com/bryphy/gestion_academica/issues)
- 💬 Únete a la discusión en [Discussions](https://github.com/bryphy/gestion_academica/discussions)

---

<div align="center">

**⭐ Si este proyecto te es útil, ¡dale una estrella en GitHub! ⭐**

</div>

---

## 👨‍💻 Equipo de Desarrollo

### **Desarrollador Principal**
- **Bryphy** - [bryphy@example.com](mailto:bryphy@example.com)
- **GitHub**: [@bryphy](https://github.com/bryphy)

### **Tecnologías y Herramientas**
- **Backend**: Django, Python, PostgreSQL
- **Frontend**: En desarrollo
- **DevOps**: Docker, Docker Compose
- **Monitoreo**: Sistema personalizado

---

**Última actualización**: Agosto 2025
