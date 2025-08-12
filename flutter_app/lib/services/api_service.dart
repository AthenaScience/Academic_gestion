import 'package:dio/dio.dart';
import 'package:shared_preferences/shared_preferences.dart';

class ApiService {
  static const String baseUrl = 'http://localhost:8000/api/v1';
  late Dio _dio;

  ApiService() {
    _dio = Dio(BaseOptions(
      baseUrl: baseUrl,
      connectTimeout: const Duration(seconds: 30),
      receiveTimeout: const Duration(seconds: 30),
    ));

    _dio.interceptors.add(InterceptorsWrapper(
      onRequest: (options, handler) async {
        final prefs = await SharedPreferences.getInstance();
        final token = prefs.getString('jwt_token');
        if (token != null) {
          options.headers['Authorization'] = 'Bearer $token';
        }
        handler.next(options);
      },
      onError: (error, handler) {
        if (error.response?.statusCode == 401) {
          // Token expirado o inválido
          _clearToken();
        }
        handler.next(error);
      },
    ));
  }

  Future<void> _clearToken() async {
    final prefs = await SharedPreferences.getInstance();
    await prefs.remove('jwt_token');
  }

  // Autenticación (JWT SimpleJWT)
  Future<Map<String, dynamic>> login(String username, String password) async {
    try {
      final response = await _dio.post('/auth/jwt/', data: {
        'username': username,
        'password': password,
      });

      // Espera { access, refresh }
      final data = Map<String, dynamic>.from(response.data);
      final access = data['access'] as String?;
      final refresh = data['refresh'] as String?;

      if (access != null) {
        final prefs = await SharedPreferences.getInstance();
        await prefs.setString('jwt_token', access);
        if (refresh != null) {
          await prefs.setString('jwt_refresh', refresh);
        }
      }

      return response.data;
    } catch (e) {
      rethrow;
    }
  }

  Future<void> refreshTokenIfNeeded() async {
    final prefs = await SharedPreferences.getInstance();
    final refresh = prefs.getString('jwt_refresh');
    if (refresh == null) return;
    try {
      final response = await _dio.post('/auth/jwt/refresh/', data: {
        'refresh': refresh,
      });
      final access = response.data['access'] as String?;
      if (access != null) {
        await prefs.setString('jwt_token', access);
      }
    } catch (_) {
      // Ignorar; el interceptor limpiará tokens si 401
    }
  }

  // Estudiantes
  Future<List<Map<String, dynamic>>> getEstudiantes() async {
    try {
      final response = await _dio.get('/estudiantes/');
      return List<Map<String, dynamic>>.from(response.data);
    } catch (e) {
      rethrow;
    }
  }

  Future<Map<String, dynamic>> getEstudiante(int id) async {
    try {
      final response = await _dio.get('/estudiantes/$id/');
      return response.data;
    } catch (e) {
      rethrow;
    }
  }

  // Pagos
  Future<List<Map<String, dynamic>>> getPagos() async {
    try {
      final response = await _dio.get('/pagos/');
      return List<Map<String, dynamic>>.from(response.data);
    } catch (e) {
      rethrow;
    }
  }

  Future<Map<String, dynamic>> getPago(int id) async {
    try {
      final response = await _dio.get('/pagos/$id/');
      return response.data;
    } catch (e) {
      rethrow;
    }
  }

  // Certificados
  Future<List<Map<String, dynamic>>> getCertificados() async {
    try {
      final response = await _dio.get('/certificados/');
      return List<Map<String, dynamic>>.from(response.data);
    } catch (e) {
      rethrow;
    }
  }

  Future<Map<String, dynamic>> getCertificado(int id) async {
    try {
      final response = await _dio.get('/certificados/$id/');
      return response.data;
    } catch (e) {
      rethrow;
    }
  }
}
