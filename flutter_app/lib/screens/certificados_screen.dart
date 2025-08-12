import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../providers/certificados_provider.dart';

class CertificadosScreen extends StatefulWidget {
  const CertificadosScreen({super.key});

  @override
  State<CertificadosScreen> createState() => _CertificadosScreenState();
}

class _CertificadosScreenState extends State<CertificadosScreen> {
  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addPostFrameCallback((_) {
      context.read<CertificadosProvider>().fetchCertificados();
    });
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('Certificados'),
        actions: [
          IconButton(
            icon: const Icon(Icons.refresh),
            onPressed: () {
              context.read<CertificadosProvider>().fetchCertificados();
            },
          ),
        ],
      ),
      body: Consumer<CertificadosProvider>(
        builder: (context, provider, child) {
          if (provider.isLoading) {
            return const Center(
              child: CircularProgressIndicator(),
            );
          }

          if (provider.error != null) {
            return Center(
              child: Column(
                mainAxisAlignment: MainAxisAlignment.center,
                children: [
                  const Icon(
                    Icons.error_outline,
                    size: 64,
                    color: Colors.red,
                  ),
                  const SizedBox(height: 16),
                  Text(
                    'Error: ${provider.error}',
                    style: const TextStyle(
                      fontSize: 16,
                      color: Colors.red,
                    ),
                    textAlign: TextAlign.center,
                  ),
                  const SizedBox(height: 16),
                  ElevatedButton(
                    onPressed: () {
                      provider.clearError();
                      provider.fetchCertificados();
                    },
                    child: const Text('Reintentar'),
                  ),
                ],
              ),
            );
          }

          if (provider.certificados.isEmpty) {
            return const Center(
              child: Column(
                mainAxisAlignment: MainAxisAlignment.center,
                children: [
                  Icon(
                    Icons.verified_outlined,
                    size: 64,
                    color: Colors.grey,
                  ),
                  SizedBox(height: 16),
                  Text(
                    'No hay certificados registrados',
                    style: TextStyle(
                      fontSize: 18,
                      color: Colors.grey,
                    ),
                  ),
                ],
              ),
            );
          }

          return ListView.builder(
            padding: const EdgeInsets.all(16),
            itemCount: provider.certificados.length,
            itemBuilder: (context, index) {
              final certificado = provider.certificados[index];
              final tipo = certificado['tipo'] ?? 'N/A';
              final estado = certificado['estado'] ?? 'Pendiente';
              
              return Card(
                margin: const EdgeInsets.only(bottom: 12),
                child: ListTile(
                  leading: CircleAvatar(
                    backgroundColor: _getEstadoColor(estado),
                    child: Icon(
                      _getEstadoIcon(estado),
                      color: Colors.white,
                    ),
                  ),
                  title: Text(
                    'Certificado #${certificado['id'] ?? 'N/A'}',
                    style: const TextStyle(
                      fontWeight: FontWeight.bold,
                    ),
                  ),
                  subtitle: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text('Estudiante: ${certificado['estudiante_nombre'] ?? 'N/A'}'),
                      Text('Tipo: $tipo'),
                      Text('Estado: $estado'),
                      if (certificado['fecha_emision'] != null)
                        Text('Fecha: ${certificado['fecha_emision']}'),
                    ],
                  ),
                  trailing: Row(
                    mainAxisSize: MainAxisSize.min,
                    children: [
                      if (estado.toLowerCase() == 'emitido')
                        IconButton(
                          icon: const Icon(Icons.download),
                          onPressed: () {
                            // TODO: Descargar certificado
                          },
                        ),
                      const Icon(Icons.arrow_forward_ios),
                    ],
                  ),
                  onTap: () {
                    // TODO: Navegar a detalle del certificado
                  },
                ),
              );
            },
          );
        },
      ),
      floatingActionButton: FloatingActionButton(
        onPressed: () {
          // TODO: Solicitar nuevo certificado
        },
        child: const Icon(Icons.add),
      ),
    );
  }

  Color _getEstadoColor(String estado) {
    switch (estado.toLowerCase()) {
      case 'emitido':
        return Colors.green;
      case 'en_proceso':
        return Colors.blue;
      case 'pendiente':
        return Colors.orange;
      case 'rechazado':
        return Colors.red;
      default:
        return Colors.grey;
    }
  }

  IconData _getEstadoIcon(String estado) {
    switch (estado.toLowerCase()) {
      case 'emitido':
        return Icons.verified;
      case 'en_proceso':
        return Icons.hourglass_empty;
      case 'pendiente':
        return Icons.schedule;
      case 'rechazado':
        return Icons.cancel;
      default:
        return Icons.help;
    }
  }
}
