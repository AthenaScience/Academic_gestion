import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';

import 'screens/login_screen.dart';
import 'screens/home_screen.dart';
import 'screens/estudiantes_screen.dart';
import 'screens/pagos_screen.dart';
import 'screens/certificados_screen.dart';

class App extends StatelessWidget {
  const App({super.key});

  @override
  Widget build(BuildContext context) {
    return MaterialApp.router(
      title: 'Gestión Académica',
      theme: ThemeData(
        primarySwatch: Colors.blue,
        useMaterial3: true,
        appBarTheme: const AppBarTheme(
          backgroundColor: Colors.blue,
          foregroundColor: Colors.white,
          elevation: 0,
        ),
      ),
      routerConfig: _router,
    );
  }
}

final _router = GoRouter(
  initialLocation: '/login',
  routes: [
    GoRoute(
      path: '/login',
      builder: (context, state) => const LoginScreen(),
    ),
    GoRoute(
      path: '/',
      builder: (context, state) => const HomeScreen(),
    ),
    GoRoute(
      path: '/estudiantes',
      builder: (context, state) => const EstudiantesScreen(),
    ),
    GoRoute(
      path: '/pagos',
      builder: (context, state) => const PagosScreen(),
    ),
    GoRoute(
      path: '/certificados',
      builder: (context, state) => const CertificadosScreen(),
    ),
  ],
);
