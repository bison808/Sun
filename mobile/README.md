# Solar Cycle Mobile App

A beautiful Flutter mobile application for monitoring solar activity and space weather in real-time.

## Overview

The Solar Cycle Mobile App provides real-time solar activity data, historical trends, AI-powered predictions, and educational content about solar cycles. It connects to the Solar Cycle API backend to deliver comprehensive space weather information in a user-friendly mobile interface.

## Features

### ✅ Implemented
- **Dashboard Screen**: Real-time solar status with activity cards
- **Material Design 3**: Modern, beautiful UI with dark/light mode support
- **State Management**: Riverpod for efficient state handling
- **API Integration**: Full integration with Solar Cycle API
- **Responsive Design**: Optimized for both phones and tablets
- **Pull-to-Refresh**: Easy data updates
- **Error Handling**: Comprehensive error states and retry mechanisms
- **Loading States**: Shimmer effects and loading indicators
- **Theme Switching**: System, light, and dark mode support

### 🚧 Coming Soon
- Charts Screen - Historical data visualization
- AI Predictions Screen - ML forecasts with confidence intervals
- Alerts Screen - Solar event notifications with filters
- Education Screen - Learning content about solar cycles
- Settings Screen - User preferences and customization
- About Screen - App information and data sources
- WebSocket Support - Live real-time updates
- Background Sync - Automatic data updates
- Offline Mode - Cached data access
- Push Notifications - Alert notifications

## Architecture

The app follows a **feature-based clean architecture** pattern:

```
mobile/
├── lib/
│   ├── core/                          # Core utilities and shared components
│   │   ├── constants/                 # App-wide constants
│   │   ├── theme/                     # Theme configuration (Material Design 3)
│   │   ├── utils/                     # Utility functions and helpers
│   │   └── widgets/                   # Reusable widgets
│   ├── features/                      # Feature modules
│   │   ├── dashboard/                 # Dashboard feature
│   │   │   ├── data/                  # Data layer (models, repositories)
│   │   │   ├── domain/                # Domain layer (entities, use cases)
│   │   │   └── presentation/          # UI layer (screens, widgets, providers)
│   │   ├── charts/                    # Charts feature (coming soon)
│   │   ├── predictions/               # AI Predictions feature (coming soon)
│   │   ├── alerts/                    # Alerts feature (coming soon)
│   │   ├── education/                 # Education feature (coming soon)
│   │   ├── settings/                  # Settings feature (coming soon)
│   │   └── about/                     # About feature (coming soon)
│   ├── shared/                        # Shared across features
│   │   ├── services/                  # API services, data sources
│   │   └── providers/                 # Shared providers
│   └── main.dart                      # App entry point
└── test/                              # Tests
```

## Tech Stack

| Category | Technology | Purpose |
|----------|-----------|---------|
| Framework | Flutter 3.16+ | Cross-platform mobile development |
| State Management | Riverpod 2.4+ | Reactive state management |
| Navigation | GoRouter 13.0+ | Declarative routing |
| HTTP Client | Dio 5.4+ | API communication |
| Local Storage | Hive 2.2+ | Offline caching |
| DI | GetIt 7.6+ | Dependency injection |
| Charts | FL Chart 0.66+ | Data visualization |
| WebSocket | web_socket_channel 2.4+ | Real-time updates |

## Prerequisites

- Flutter SDK 3.0.0 or higher
- Dart SDK 3.0.0 or higher
- Android Studio / Xcode (for mobile development)
- Solar Cycle API running on `http://localhost:3000`

## Getting Started

### 1. Install Flutter

Follow the official Flutter installation guide:
- https://docs.flutter.dev/get-started/install

### 2. Clone the Repository

```bash
git clone <repository-url>
cd Sun/mobile
```

### 3. Install Dependencies

```bash
flutter pub get
```

### 4. Run Code Generation

```bash
flutter pub run build_runner build --delete-conflicting-outputs
```

### 5. Configure API Endpoint

Update the base URL in `lib/core/constants/app_constants.dart`:

```dart
static const String baseUrl = 'http://YOUR_API_HOST:3000';
```

For Android emulator, use `http://10.0.2.2:3000` to access localhost.
For iOS simulator, use `http://localhost:3000`.

### 6. Run the App

```bash
# Development mode
flutter run

# Release mode
flutter run --release

# Specific device
flutter run -d <device-id>
```

## Project Structure Details

### Core Layer
- **Constants**: API endpoints, cache keys, timeouts, UI constants
- **Theme**: Material Design 3 theme with custom color schemes
- **Widgets**: Reusable UI components (cards, loading states, errors)
- **Utils**: Router configuration, helpers

### Feature Layer (Dashboard Example)
```
dashboard/
├── data/
│   ├── models/              # Data models (API responses)
│   └── repositories/        # Data repositories
├── domain/
│   ├── entities/            # Business entities
│   └── usecases/            # Business logic
└── presentation/
    ├── providers/           # Riverpod providers (state management)
    ├── screens/             # Screen widgets
    └── widgets/             # Feature-specific widgets
```

### Shared Layer
- **Services**: API clients, WebSocket handlers, cache managers
- **Providers**: App-wide providers (theme, connectivity, etc.)

## State Management

The app uses **Riverpod** for state management:

```dart
// Provider definition
final dashboardProvider = StateNotifierProvider<DashboardNotifier, DashboardState>((ref) {
  final apiService = ref.watch(solarApiServiceProvider);
  return DashboardNotifier(apiService);
});

// Usage in widgets
final dashboardState = ref.watch(dashboardProvider);
```

## API Integration

The app communicates with the Solar Cycle API:

```dart
// Current Status
GET /api/current-status

// Sunspot History
GET /api/sunspot-history?range=1y&limit=100

// Alerts
GET /api/alerts?limit=20

// Forecast
GET /api/forecast?days=30

// ML Predictions
POST /api/ml/predict/short-term
POST /api/ml/predict/long-term

// Anomalies
GET /api/ml/anomaly/current
```

## Theme Configuration

The app supports three theme modes:
- **Light Mode**: Optimized for daytime use
- **Dark Mode**: OLED-friendly dark theme
- **System**: Follows device theme settings

Custom color scheme based on solar activity:
- Primary: Solar Orange (#FF6B35)
- Secondary: Deep Space Blue (#004E89)
- Tertiary: Sky Blue (#1A659E)

## Development Guidelines

### Code Style
- Follow official Dart style guide
- Use `flutter analyze` and `flutter format`
- Prefer const constructors for performance
- Use meaningful variable names

### Widget Best Practices
```dart
// ✅ Good - const constructor
const SolarCard(child: Text('Hello'));

// ✅ Good - extract methods
Widget _buildHeader() { ... }

// ✅ Good - use keys for lists
ListView.builder(
  itemBuilder: (context, index) => Card(key: ValueKey(items[index].id)),
)
```

### State Management Best Practices
```dart
// ✅ Good - use providers for dependency injection
final apiService = ref.watch(solarApiServiceProvider);

// ✅ Good - handle loading and error states
if (state.isLoading) return LoadingWidget();
if (state.error != null) return ErrorWidget(error: state.error);

// ✅ Good - use async state
ref.listen(dashboardProvider, (previous, next) {
  if (next.error != null) {
    ScaffoldMessenger.of(context).showSnackBar(...);
  }
});
```

## Testing

### Run Tests
```bash
# All tests
flutter test

# With coverage
flutter test --coverage

# Specific test file
flutter test test/features/dashboard/dashboard_test.dart
```

### Test Structure
```
test/
├── unit/                 # Unit tests
│   ├── providers/        # Provider tests
│   └── services/         # Service tests
├── widget/               # Widget tests
│   └── features/         # Feature widget tests
└── integration/          # Integration tests
```

## Building for Production

### Android
```bash
# Build APK
flutter build apk --release

# Build App Bundle
flutter build appbundle --release
```

### iOS
```bash
# Build iOS
flutter build ios --release

# Build IPA
flutter build ipa --release
```

## Performance Optimization

- **Const Constructors**: Used throughout for widget rebuilds optimization
- **Lazy Loading**: Lists use lazy loading with pagination
- **Image Caching**: Cached network images with `cached_network_image`
- **State Optimization**: Riverpod providers prevent unnecessary rebuilds
- **Code Splitting**: Feature-based architecture enables modular loading

## Troubleshooting

### Common Issues

**1. API Connection Issues**
```dart
// For Android Emulator, use:
static const String baseUrl = 'http://10.0.2.2:3000';

// For iOS Simulator, use:
static const String baseUrl = 'http://localhost:3000';

// For Physical Device, use:
static const String baseUrl = 'http://YOUR_COMPUTER_IP:3000';
```

**2. Code Generation Errors**
```bash
# Clean and regenerate
flutter clean
flutter pub get
flutter pub run build_runner build --delete-conflicting-outputs
```

**3. Theme Not Persisting**
```bash
# Clear app data and restart
flutter clean
flutter run
```

## Roadmap

### Phase 1: Core Features (Completed) ✅
- [x] Dashboard with real-time status
- [x] API integration
- [x] State management
- [x] Theme system
- [x] Navigation structure

### Phase 2: Data Visualization (Next)
- [ ] Charts screen with historical data
- [ ] Interactive charts with zoom/pan
- [ ] Data range selection
- [ ] Export functionality

### Phase 3: Predictions & Alerts
- [ ] AI predictions screen
- [ ] Alert notifications
- [ ] Alert filtering and search
- [ ] WebSocket real-time updates

### Phase 4: Education & Settings
- [ ] Educational content
- [ ] Settings and preferences
- [ ] About screen
- [ ] Feedback mechanism

### Phase 5: Advanced Features
- [ ] Offline mode
- [ ] Background sync
- [ ] Push notifications
- [ ] Widget support
- [ ] Accessibility improvements

## Contributing

1. Fork the repository
2. Create a feature branch
3. Write tests for new features
4. Ensure all tests pass
5. Submit a pull request

## License

MIT

## Support

For issues and questions:
- Create an issue in the repository
- Email: support@solarcycle.app

## Acknowledgments

- NOAA SWPC for solar data
- NASA for space weather information
- Flutter team for the amazing framework
- Riverpod team for excellent state management

---

**Made with ❤️ for space weather enthusiasts**
