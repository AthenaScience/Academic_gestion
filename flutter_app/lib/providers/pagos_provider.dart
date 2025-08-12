import 'package:flutter/foundation.dart';
import '../services/api_service.dart';

class PagosProvider with ChangeNotifier {
  final ApiService _apiService = ApiService();
  List<Map<String, dynamic>> _pagos = [];
  bool _isLoading = false;
  String? _error;

  List<Map<String, dynamic>> get pagos => _pagos;
  bool get isLoading => _isLoading;
  String? get error => _error;

  Future<void> fetchPagos() async {
    _isLoading = true;
    _error = null;
    notifyListeners();

    try {
      _pagos = await _apiService.getPagos();
      _isLoading = false;
      notifyListeners();
    } catch (e) {
      _error = e.toString();
      _isLoading = false;
      notifyListeners();
    }
  }

  Future<Map<String, dynamic>?> fetchPago(int id) async {
    try {
      return await _apiService.getPago(id);
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
