# 🎓 Sistema de Gestión Académica

> **Sistema integral para la gestión de estudiantes, eventos académicos y certificados**

[![Django](https://img.shields.io/badge/Django-5.1.7-green.svg)](https://www.djangoproject.com/)
[![Status](https://img.shields.io/badge/Status-En%20Desarrollo-orange.svg)](https://github.com/bryphy/gestion_academica)
[![License](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)

## 📋 Descripción General

Sistema de gestión académica desarrollado con tecnologías modernas para la administración eficiente de instituciones educativas.

## 🚀 Características Principales

- ✅ **API REST completa** con autenticación JWT
- ✅ **Sistema de pagos** con gestión de cuotas
- ✅ **Generación de certificados** en PDF con códigos QR
- ✅ **Carga masiva** de datos desde archivos CSV
- ✅ **Panel de administración** Django integrado
- ✅ **Tests automatizados** con cobertura completa

## 🛠️ Tecnologías

- **Backend**: Django 5 + Django REST Framework
- **Base de Datos**: SQLite (desarrollo) / PostgreSQL (producción)
- **Autenticación**: JWT (JSON Web Tokens)
- **Contenedores**: Docker + Docker Compose

## ⚡ Inicio Rápido

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

## 📊 Estado del Proyecto

- **Backend**: ✅ Completamente funcional
- **APIs**: ✅ Implementadas y probadas
- **Tests**: ✅ 100% de cobertura
- **Frontend**: 🚧 En desarrollo
- **Documentación**: ✅ Completa

## 🔐 Autenticación

El sistema utiliza autenticación JWT para proteger los endpoints de la API.

## 📚 Documentación

Para información técnica detallada, consulta la documentación en el directorio `docs/` del proyecto.

## 🤝 Contribución

1. **Fork** el proyecto
2. **Crea** una rama para tu feature
3. **Commit** tus cambios
4. **Push** a la rama
5. **Abre** un Pull Request

## 📄 Licencia

Este proyecto está bajo la **Licencia MIT**. Ver el archivo [LICENSE](LICENSE) para más detalles.

## 👨‍💻 Equipo de Desarrollo

- **Bryphy** - [@bryphy](https://github.com/bryphy) Backend

---

<div align="center">

**⭐ Si este proyecto te es útil, ¡dale una estrella en GitHub! ⭐**

</div>
