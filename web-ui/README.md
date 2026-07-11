# Where2Stream Web UI

A visual interactive TypeScript web application for the Where2Stream agent. This provides a modern, user-friendly interface to search for movies and find where to stream them.

## Features

- **Interactive Search**: Real-time movie search with autocomplete suggestions
- **Visual Movie Cards**: Beautiful card layout with movie posters and details
- **Streaming Information**: Clear display of where movies are available to stream
- **Progress Tracking**: Visual progress indicator showing the workflow steps
- **Responsive Design**: Works on desktop, tablet, and mobile devices
- **Chat Interface**: Conversation-style interaction with the agent

## Tech Stack

- **Frontend**: React 18 + TypeScript + Vite
- **Styling**: Custom CSS with modern design patterns
- **Backend**: FastAPI (Python) to connect with the existing agent
- **API**: TMDB (The Movie Database) for movie data

## Installation

### Prerequisites

- Node.js 18+ 
- Python 3.8+
- Your existing where2stream_agent codebase

### Setup

1. **Install dependencies**:
   ```bash
   cd web-ui
   npm install
   ```

2. **Set up environment variables**:
   Create a `.env` file in the web-ui directory:
   ```env
   VITE_API_BASE=http://localhost:8000
   ```

3. **Install Python dependencies** (for the API server):
   ```bash
   pip install fastapi uvicorn python-multipart
   ```

## Running the Application

### Development Mode

1. **Start the API server**:
   ```bash
   python server.py
   ```

2. **Start the Vite dev server**:
   ```bash
   npm run dev
   ```

3. Open your browser to `http://localhost:3000`

### Production Mode

1. **Build the frontend**:
   ```bash
   npm run build
   ```

2. **Run the server with static files**:
   ```bash
   python server.py
   ```

3. The app will be available at `http://localhost:8000`

## Project Structure

```
web-ui/
├── src/
│   ├── components/          # React components
│   │   ├── MovieCard.tsx
│   │   ├── SearchBar.tsx
│   │   ├── StreamingResults.tsx
│   │   └── ProgressIndicator.tsx
│   ├── types.ts             # TypeScript interfaces
│   ├── api.ts               # API client functions
│   ├── App.tsx              # Main application component
│   ├── App.css              # Main styles
│   ├── main.tsx             # Entry point
│   └── index.css            # Global styles
├── server.py               # FastAPI backend
├── package.json
├── tsconfig.json
├── vite.config.ts
└── README.md
```

## API Endpoints

- `POST /api/search-movie` - Search for movies by title
- `POST /api/watch-providers` - Get streaming providers for a movie
- `POST /api/tv-search` - Search for TV shows
- `POST /api/tv-providers` - Get streaming providers for TV shows
- `POST /api/agent` - Full agent workflow

## Customization

### Changing Colors
Edit the CSS variables in `App.css`:
```css
:root {
  --primary-color: #6366f1;
  --secondary-color: #8b5cf6;
  --background-color: #0f172a;
  /* ... other colors */
}
```

### Adding More Movie Data
The API uses your existing agent functions. To add more data sources, modify the `server.py` file.

### Changing the Workflow
Edit the `App.tsx` file to modify the search and selection workflow.

## Browser Support

- Chrome (recommended)
- Firefox
- Safari
- Edge
- Mobile browsers (iOS Safari, Chrome for Android)

## Performance

- Uses React's useCallback and useMemo for optimization
- Lazy loading of images
- Responsive grid layouts
- Efficient API calls with error handling

## Future Enhancements

- [ ] Add user authentication
- [ ] Save favorite movies
- [ ] Watchlist functionality
- [ ] Multi-language support
- [ ] Dark/light mode toggle
- [ ] Advanced filtering options
- [ ] Integration with more streaming services

## License

This project is part of the where2stream_agent repository.

## Contributing

Feel free to submit pull requests or open issues for bugs and feature requests.
