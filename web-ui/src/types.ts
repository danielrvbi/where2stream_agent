export interface MovieSearchResult {
  id: number;
  title: string;
  original_language: string;
  release_year: string;
  overview: string;
  poster_path?: string;
}

export interface WatchProvider {
  provider_name: string;
  provider_id: number;
  display_priority: number;
  logo_path?: string;
}

export interface StreamingInfo {
  Type: string;
  Provider: string;
  Country: string[];
}

export interface StreamingResponse {
  [key: string]: StreamingInfo[];
}

export interface MovieDetails extends MovieSearchResult {
  backdrop_path?: string;
  vote_average?: number;
  genres?: { id: number; name: string }[];
}

export interface SearchState {
  query: string;
  results: MovieSearchResult[];
  selectedMovie: MovieSearchResult | null;
  streamingData: StreamingResponse | null;
  isLoading: boolean;
  error: string | null;
  step: 'search' | 'select' | 'streaming' | 'complete';
}

export interface Message {
  role: 'user' | 'assistant';
  content: string;
  timestamp: Date;
}
