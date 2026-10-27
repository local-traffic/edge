# Traffic Detection Vue.js Frontend

Modern Vue.js 3 single-page application for traffic detection system with component-based architecture.

## Features

- **Detector Test UI** - Interactive image viewer with detection annotations
- **Live Stream UI** - Real-time video stream with zone editor
- **Zone Management** - Draw and edit line/polygon detection zones
- **Performance Metrics** - Real-time FPS and inference time monitoring
- **Dark Theme** - Cyberpunk-inspired UI with responsive design

## Tech Stack

- **Vue 3** - Progressive JavaScript framework with Composition API
- **Vite** - Fast build tool and dev server
- **Vue Router** - Client-side routing
- **Pinia** - State management
- **Axios** - HTTP client for API calls

## Project Structure

```
frontend/
├── src/
│   ├── components/
│   │   ├── common/         # Reusable UI components (Button, Slider, Panel)
│   │   ├── detector/       # Detector test components
│   │   └── stream/         # Live stream components
│   ├── views/
│   │   ├── DetectorTest.vue   # Detector testing page
│   │   └── LiveStream.vue     # Live stream page
│   ├── composables/        # Reusable logic (useDetector, useZones, useCanvas, useMetrics)
│   ├── utils/              # Utility functions (api, canvas, geometry)
│   ├── assets/
│   │   └── styles/         # CSS stylesheets
│   ├── router/             # Vue Router configuration
│   ├── App.vue             # Root component
│   └── main.js             # Application entry point
├── public/                 # Static assets
├── vite.config.js          # Vite configuration
└── package.json            # Project dependencies
```

## Development Setup

### Prerequisites

- Node.js 16+ and npm
- Flask backends running on ports 9090 and 9091

### Installation

```bash
cd frontend
npm install
```

### Development Server

Start the Vue dev server (port 3000):

```bash
npm run dev
```

The dev server will proxy API requests to the Flask backends:
- `/api/*` → `http://localhost:9091` (Detector test API)
- `/video_feed` → `http://localhost:9090` (Video stream)
- `/zones` → `http://localhost:9090` (Zone management API)

### Building for Production

Build the production-optimized bundle:

```bash
npm run build
```

The output will be in the `dist/` directory, which can be served by Flask.

## Component Architecture

### Common Components

- **Button.vue** - Reusable button with variants (primary, secondary, danger)
- **Slider.vue** - Range slider with label and formatting
- **Panel.vue** - Container panel with optional collapse

### Detector Components

- **ImageViewer.vue** - Display annotated detection images
- **NavigationControls.vue** - Previous/next navigation with keyboard shortcuts
- **ThresholdSlider.vue** - Confidence threshold control with debouncing
- **InfoPanel.vue** - Display metadata (filename, detections count)
- **DebugPanel.vue** - JSON viewer for detection details

### Stream Components

- **VideoCanvas.vue** - MJPEG stream with canvas overlay
- **ZoneEditor.vue** - Interactive zone drawing and editing
- **ZoneList.vue** - List of defined zones with management
- **PerformanceMetrics.vue** - Real-time performance monitoring
- **Toolbar.vue** - Zone creation mode selector
- **CameraControls.vue** - Pi Camera autofocus window controls

## Composables

### useDetector

Manages detector testing state and API calls:
- Image navigation
- Threshold updates
- Detection loading

### useZones

Zone CRUD operations:
- Fetch zones from API
- Create, update, delete zones
- Zone selection

### useCanvas

Canvas drawing and coordinate transformations:
- Initialize canvas context
- Coordinate conversion (normalized ↔ canvas)
- Zone rendering (lines, polygons, handles)

### useMetrics

Performance metrics polling:
- Auto-refresh metrics from API
- Start/stop polling
- FPS, inference time, tracking time

## API Integration

### Detector Test API (Port 9091)

- `GET /api/images` - List all images
- `GET /api/image/:index` - Get annotated image
- `POST /api/next` - Navigate to next image
- `POST /api/prev` - Navigate to previous image
- `POST /api/settings` - Update confidence threshold

### Stream API (Port 9090)

- `GET /zones` - Get all zones
- `POST /zones` - Create new zone
- `PUT /zones/:name` - Update zone
- `DELETE /zones/:name` - Delete zone
- `GET /video_feed` - MJPEG video stream
- `GET /metrics` - Performance metrics



## Zone Drawing

### Line Zones

1. Select "Line" mode from toolbar
2. Click two points on the video
3. Enter zone name and optional trigger classes
4. Click "Create Zone"

### Polygon Zones

1. Select "Polygon" mode from toolbar
2. Click multiple points to define polygon
3. Click near the first point to close polygon
4. Enter zone name and optional trigger classes
5. Click "Create Zone"

### Editing Zones

1. Select "Edit" mode from toolbar
2. Click on an existing zone to select it
3. Drag handles to modify zone shape
4. Changes are saved automatically on mouse release

## Keyboard Shortcuts

- **Arrow Left** - Previous image (Detector Test)
- **Arrow Right** - Next image (Detector Test)

## Browser Support

- Chrome/Edge 90+
- Firefox 88+
- Safari 14+

## Troubleshooting

### CORS Errors

Ensure Flask backends have `flask-cors` installed and enabled:

```python
from flask_cors import CORS
app = Flask(__name__)
CORS(app)
```

### Video Stream Not Loading

- Check Flask backend is running on port 9090
- Verify `/video_feed` endpoint is accessible
- Check browser console for errors

### Zone Drawing Not Working

- Ensure canvas overlay is properly sized
- Check browser console for JavaScript errors
- Verify mouse event handlers are attached

## Performance

- Uses virtual DOM for efficient rendering
- Debounced threshold updates to reduce API calls
- Optimized canvas redrawing
- Lazy loading of components

## Contributing

When adding new components:
1. Follow Vue 3 Composition API patterns
2. Use `<script setup>` syntax
3. Add proper TypeScript types (if using TS)
4. Include scoped styles
5. Document props and emits
6. Add to appropriate directory (common/detector/stream)

## License

TODO ..

## TODO

* consider additional detectors like https://codeberg.org/CCodeRun/darknet, optimize for RPI
- make tracking possible even when partialy hidden
- train detection also in the night
- https://github.com/mikel-brostrom/boxmot
- https://github.com/tryolabs/norfair
- na kaglu je te tutorial na mapy na geospacial
- zakomponovat https://motchallenge.net/




