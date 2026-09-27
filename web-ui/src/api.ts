import { MovieSearchResult, StreamingResponse } from './types';

// Relative URLs use Vite's development proxy and the production API host.
const API_BASE = import.meta.env.VITE_API_BASE || '';

async function post<T>(path: string, payload: object): Promise<T> {
  const response = await fetch(`${API_BASE}${path}`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  });
  if (!response.ok) {
    throw new Error(`API request failed (${response.status})`);
  }
  return response.json() as Promise<T>;
}

export async function searchMovies(query: string): Promise<MovieSearchResult[]> {
  const data = await post<{ results: MovieSearchResult[] }>('/api/search-movie', { title: query });
  return data.results;
}

export function getStreamingInfo(movieId: number): Promise<StreamingResponse> {
  return post<StreamingResponse>('/api/watch-providers', { movie_id: movieId });
}

export interface AgentReply {
  conversation_id: string;
  response: string;
}

// Keep conversation_id and pass it back to continue the same conversation.
export function callAgent(query: string, conversationId?: string): Promise<AgentReply> {
  return post<AgentReply>('/api/agent', { query, conversation_id: conversationId });
}
