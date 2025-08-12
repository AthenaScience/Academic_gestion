import 'package:flutter/foundation.dart';
import '../services/api_service.dart';

class CertificadosProvider with ChangeNotifier {
  final ApiService _apiService = ApiService();
  List<Map<String, dynamic>> _certificados = [];
  bool _isLoading = false;
  String? _error;

  List<Map<String, dynamic>> get certificados => _certificados;
  bool get isLoading => _isLoading;
  String? get error => _error;

  Future<void> fetchCertificados() async {
    _isLoading = true;
    _error = null;
    notifyListeners();

    try {
      _certificados = await _apiService.getCertificados();
      _isLoading = false;
      notifyListeners();
    } catch (e) {
      _error = e.toString();
      _isLoading = false;
      notifyListeners();
    }
  }

  Future<Map<String, dynamic>?> fetchCertificado(int id) async {
    try {
      return await _apiService.getCertificado(id);
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
