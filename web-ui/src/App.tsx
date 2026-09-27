import React, { useState, useCallback } from 'react';
import { MovieSearchResult, SearchState } from './types';
import { searchMovies, getStreamingInfo } from './api';
import SearchBar from './components/SearchBar';
import MovieCard from './components/MovieCard';
import StreamingResults from './components/StreamingResults';
import ProgressIndicator from './components/ProgressIndicator';
import './App.css';

const App: React.FC = () => {
  const [state, setState] = useState<SearchState>({
    query: '',
    results: [],
    selectedMovie: null,
    streamingData: null,
    isLoading: false,
    error: null,
    step: 'search',
  });

  const [messages, setMessages] = useState<Array<{ role: string; content: string }>>([]);

  const handleSearch = useCallback(async (query: string) => {
    setState(prev => ({ ...prev, query, isLoading: true, error: null, step: 'search' }));
    setMessages(prev => [...prev, { role: 'user', content: `Searching for: ${query}` }]);

    try {
      const results = await searchMovies(query);
      setState(prev => ({
        ...prev,
        results,
        isLoading: false,
        step: results.length > 0 ? 'select' : 'search',
      }));
      
      setMessages(prev => [...prev, {
        role: 'assistant',
        content: `Found ${results.length} result${results.length !== 1 ? 's' : ''} for "${query}"`
      }]);
    } catch (error) {
      setState(prev => ({
        ...prev,
        isLoading: false,
        error: 'Failed to search for movies. Please try again.',
      }));
      setMessages(prev => [...prev, {
        role: 'assistant',
        content: 'Sorry, I encountered an error searching for movies.'
      }]);
    }
  }, []);

  const handleSelectMovie = useCallback(async (movie: MovieSearchResult) => {
    setState(prev => ({
      ...prev,
      selectedMovie: movie,
      isLoading: true,
      error: null,
      step: 'streaming',
    }));
    
    setMessages(prev => [...prev, {
      role: 'user',
      content: `Selected: ${movie.title} (${movie.release_year})`
    }]);

    try {
      const streamingData = await getStreamingInfo(movie.id);
      setState(prev => ({
        ...prev,
        streamingData,
        isLoading: false,
        step: 'complete',
      }));
      
      setMessages(prev => [...prev, {
        role: 'assistant',
        content: `Found streaming options for ${movie.title}!`
      }]);
    } catch (error) {
      setState(prev => ({
        ...prev,
        isLoading: false,
        error: 'Failed to get streaming information. Please try again.',
      }));
      setMessages(prev => [...prev, {
        role: 'assistant',
        content: 'Sorry, I couldn\'t find streaming information for this movie.'
      }]);
    }
  }, []);

  const handleReset = useCallback(() => {
    setState({
      query: '',
      results: [],
      selectedMovie: null,
      streamingData: null,
      isLoading: false,
      error: null,
      step: 'search',
    });
    setMessages([]);
  }, []);

  const getCurrentStepIndex = useCallback(() => {
    switch (state.step) {
      case 'search':
        return 1;
      case 'select':
        return 2;
      case 'streaming':
        return 3;
      case 'complete':
        return 4;
      default:
        return 1;
    }
  }, [state.step]);

  const steps = ['Search', 'Select Movie', 'Find Streaming', 'Complete'];

  return (
    <div className="app-container">
      <header className="app-header">
        <div className="header-content">
          <h1 className="app-title">
            <span className="title-icon">🎬</span>
            Where2Stream
          </h1>
          <p className="app-subtitle">Find where to watch your favorite movies</p>
        </div>
      </header>

      <main className="main-content">
        {/* Progress Indicator */}
        <div className="progress-section">
          <ProgressIndicator
            currentStep={getCurrentStepIndex()}
            steps={steps}
          />
        </div>

        {/* Search Section */}
        <div className="search-section">
          <SearchBar
            onSearch={handleSearch}
            isLoading={state.isLoading}
            placeholder="Enter movie title..."
          />
        </div>

        {/* Error Display */}
        {state.error && (
          <div className="error-message">
            <span className="error-icon">⚠️</span>
            {state.error}
            <button className="retry-button" onClick={() => handleSearch(state.query)}>
              Try Again
            </button>
          </div>
        )}

        {/* Results Section */}
        {state.step === 'select' && state.results.length > 0 && (
          <div className="results-section">
            <h2 className="section-title">
              <span className="results-count">{state.results.length}</span>
              {state.results.length === 1 ? ' Result' : ' Results'} Found
            </h2>
            <div className="movies-grid">
              {state.results.map((movie) => (
                <MovieCard
                  key={movie.id}
                  movie={movie}
                  isSelected={state.selectedMovie?.id === movie.id}
                  onSelect={handleSelectMovie}
                />
              ))}
            </div>
          </div>
        )}

        {/* Streaming Results */}
        {(state.step === 'streaming' || state.step === 'complete') && state.selectedMovie && (
          <div className="streaming-section">
            <div className="selected-movie-header">
              <h2 className="selected-movie-title">
                <span className="back-button" onClick={handleReset}>
                  ← Back
                </span>
                {state.selectedMovie.title}
              </h2>
              <p className="selected-movie-details">
                {state.selectedMovie.release_year} • {state.selectedMovie.original_language.toUpperCase()}
              </p>
              <p className="selected-movie-overview">{state.selectedMovie.overview}</p>
            </div>

            {state.isLoading ? (
              <div className="loading-state">
                <div className="loading-spinner-large" />
                <p>Finding streaming options...</p>
              </div>
            ) : state.streamingData ? (
              <StreamingResults
                streamingData={state.streamingData}
                movieTitle={state.selectedMovie.title}
              />
            ) : null}
          </div>
        )}

        {/* Chat Messages */}
        {messages.length > 0 && (
          <div className="chat-messages">
            {messages.map((msg, index) => (
              <div key={index} className={`message ${msg.role}`}>
                <span className="message-role">{msg.role === 'user' ? 'You' : 'Agent'}:</span>
                <span className="message-content">{msg.content}</span>
              </div>
            ))}
          </div>
        )}

        {/* Empty State */}
        {state.step === 'search' && !state.isLoading && state.results.length === 0 && (
          <div className="empty-state">
            <div className="empty-icon">🎥</div>
            <h3>Ready to find your next movie?</h3>
            <p>Search for any movie to see where it's streaming</p>
            <div className="example-searches">
              <button className="example-button" onClick={() => handleSearch('Inception')}>
                Inception
              </button>
              <button className="example-button" onClick={() => handleSearch('The Matrix')}>
                The Matrix
              </button>
              <button className="example-button" onClick={() => handleSearch('Interstellar')}>
                Interstellar
              </button>
            </div>
          </div>
        )}
      </main>

      <footer className="app-footer">
        <p>Powered by TMDB API | Where2Stream Agent v2</p>
      </footer>
    </div>
  );
};

export default App;
