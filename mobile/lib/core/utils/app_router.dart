import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';
import '../../features/dashboard/presentation/screens/dashboard_screen.dart';

class AppRouter {
  static const String dashboard = '/';
  static const String charts = '/charts';
  static const String predictions = '/predictions';
  static const String alerts = '/alerts';
  static const String education = '/education';
  static const String settings = '/settings';
  static const String about = '/about';

  static final GoRouter router = GoRouter(
    initialLocation: dashboard,
    routes: [
      GoRoute(
        path: dashboard,
        name: 'dashboard',
        builder: (context, state) => const DashboardScreen(),
      ),
      GoRoute(
        path: charts,
        name: 'charts',
        builder: (context, state) => const PlaceholderScreen(title: 'Charts'),
      ),
      GoRoute(
        path: predictions,
        name: 'predictions',
        builder: (context, state) =>
            const PlaceholderScreen(title: 'AI Predictions'),
      ),
      GoRoute(
        path: alerts,
        name: 'alerts',
        builder: (context, state) => const PlaceholderScreen(title: 'Alerts'),
      ),
      GoRoute(
        path: education,
        name: 'education',
        builder: (context, state) =>
            const PlaceholderScreen(title: 'Education'),
      ),
      GoRoute(
        path: settings,
        name: 'settings',
        builder: (context, state) =>
            const PlaceholderScreen(title: 'Settings'),
      ),
      GoRoute(
        path: about,
        name: 'about',
        builder: (context, state) => const PlaceholderScreen(title: 'About'),
      ),
    ],
    errorBuilder: (context, state) => const ErrorScreen(),
  );
}

// Placeholder screen for routes not yet implemented
class PlaceholderScreen extends StatelessWidget {
  final String title;

  const PlaceholderScreen({
    required this.title,
    Key? key,
  }) : super(key: key);

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: Text(title),
      ),
      body: Center(
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            Icon(
              Icons.construction,
              size: 64,
              color: Theme.of(context).colorScheme.primary,
            ),
            const SizedBox(height: 16),
            Text(
              '$title Screen',
              style: Theme.of(context).textTheme.headlineSmall,
            ),
            const SizedBox(height: 8),
            Text(
              'Coming soon...',
              style: Theme.of(context).textTheme.bodyMedium,
            ),
            const SizedBox(height: 24),
            ElevatedButton.icon(
              onPressed: () => context.go(AppRouter.dashboard),
              icon: const Icon(Icons.home),
              label: const Text('Back to Dashboard'),
            ),
          ],
        ),
      ),
    );
  }
}

// Error screen for navigation errors
class ErrorScreen extends StatelessWidget {
  const ErrorScreen({Key? key}) : super(key: key);

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('Error'),
      ),
      body: Center(
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            Icon(
              Icons.error_outline,
              size: 64,
              color: Theme.of(context).colorScheme.error,
            ),
            const SizedBox(height: 16),
            Text(
              'Page Not Found',
              style: Theme.of(context).textTheme.headlineSmall,
            ),
            const SizedBox(height: 8),
            Text(
              'The page you are looking for does not exist.',
              style: Theme.of(context).textTheme.bodyMedium,
              textAlign: TextAlign.center,
            ),
            const SizedBox(height: 24),
            ElevatedButton.icon(
              onPressed: () => context.go(AppRouter.dashboard),
              icon: const Icon(Icons.home),
              label: const Text('Back to Dashboard'),
            ),
          ],
        ),
      ),
    );
  }
}
