import React from 'react';
import { MovieSearchResult } from '../types';

interface MovieCardProps {
  movie: MovieSearchResult;
  isSelected: boolean;
  onSelect: (movie: MovieSearchResult) => void;
}

const MovieCard: React.FC<MovieCardProps> = ({ movie, isSelected, onSelect }) => {
  const posterUrl = movie.poster_path
    ? `https://image.tmdb.org/t/p/w500${movie.poster_path}`
    : '/placeholder-movie.png';

  return (
    <div
      className={`movie-card ${isSelected ? 'selected' : ''}`}
      onClick={() => onSelect(movie)}
    >
      <div className="movie-poster">
        <img
          src={posterUrl}
          alt={movie.title}
          onError={(e) => {
            (e.target as HTMLImageElement).src = '/placeholder-movie.png';
          }}
        />
        {isSelected && <div className="selection-overlay">
          <span className="check-icon">✓</span>
        </div>}
      </div>
      <div className="movie-info">
        <h3 className="movie-title">{movie.title}</h3>
        <p className="movie-year">{movie.release_year}</p>
        <p className="movie-overview">{movie.overview.substring(0, 100)}{movie.overview.length > 100 ? '...' : ''}</p>
        <div className="movie-meta">
          <span className="language-badge">{movie.original_language.toUpperCase()}</span>
        </div>
      </div>
    </div>
  );
};

export default MovieCard;
