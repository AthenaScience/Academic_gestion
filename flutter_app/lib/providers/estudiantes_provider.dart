import 'package:flutter/foundation.dart';
import '../services/api_service.dart';

class EstudiantesProvider with ChangeNotifier {
  final ApiService _apiService = ApiService();
  List<Map<String, dynamic>> _estudiantes = [];
  bool _isLoading = false;
  String? _error;

  List<Map<String, dynamic>> get estudiantes => _estudiantes;
  bool get isLoading => _isLoading;
  String? get error => _error;

  Future<void> fetchEstudiantes() async {
    _isLoading = true;
    _error = null;
    notifyListeners();

    try {
      _estudiantes = await _apiService.getEstudiantes();
      _isLoading = false;
      notifyListeners();
    } catch (e) {
      _error = e.toString();
      _isLoading = false;
      notifyListeners();
    }
  }

  Future<Map<String, dynamic>?> fetchEstudiante(int id) async {
    try {
      return await _apiService.getEstudiante(id);
    } catch (e) {
      _error = e.toString();
      notifyListeners();
      return null;
    }
  }

  void clearError() {
    _error = null;
    notifyListeners();
  }
}
