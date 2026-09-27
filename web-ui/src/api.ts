import { MovieSearchResult, StreamingResponse } from './types';

const API_BASE = import.meta.env.VITE_API_BASE || '';

// Mock API calls that simulate the agent's behavior
// In production, these would call your actual agent API

export const searchMovies = async (query: string): Promise<MovieSearchResult[]> => {
  try {
    // Call the agent to search for movies
    const response = await fetch(`${API_BASE}/api/search-movie`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ title: query }),
    });

    if (!response.ok) {
      throw new Error('Failed to search movies');
    }

    const data = await response.json();
    return data.results || data;
  } catch (error) {
    console.error('Search error:', error);
    // Fallback: return mock data for demo purposes
    return getMockSearchResults(query);
  }
};

export const getStreamingInfo = async (movieId: number): Promise<StreamingResponse> => {
  try {
    const response = await fetch(`${API_BASE}/api/watch-providers`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ movie_id: movieId }),
    });

    if (!response.ok) {
      throw new Error('Failed to get streaming info');
    }

    const data = await response.json();
    return data;
  } catch (error) {
    console.error('Streaming info error:', error);
    // Fallback: return mock data
    return getMockStreamingInfo(movieId);
  }
};

// Mock data functions for demo mode
const getMockSearchResults = (query: string): MovieSearchResult[] => {
  const mockDatabase: Record<string, MovieSearchResult[]> = {
    'inception': [
      {
        id: 27205,
        title: 'Inception',
        original_language: 'en',
        release_year: '2010',
        overview: 'A thief who steals corporate secrets through the use of dream-sharing technology is given the inverse task of planting an idea into the mind of a C.E.O.',
        poster_path: '/9gk7adHYeDvHkCSEqAvQNLV5Uge.jpg',
      },
    ],
    'matrix': [
      {
        id: 603,
        title: 'The Matrix',
        original_language: 'en',
        release_year: '1999',
        overview: 'Set in the 22nd century, The Matrix tells the story of a computer hacker who joins a group of underground insurgents fighting the vast and powerful computers who now rule the earth.',
        poster_path: '/f89U3ADr1oiB1s9GkdPOEpXUk5H.jpg',
      },
      {
        id: 604,
        title: 'The Matrix Reloaded',
        original_language: 'en',
        release_year: '2003',
        overview: 'Six months after the events depicted in The Matrix, Neo has proved to be a good omen for the free humans, as more and more humans are being freed from the matrix and brought to Zion, the one and only stronghold of the Resistance.',
        poster_path: '/9TGHDvWrqKBzwDxDodHYXEmOE6J.jpg',
      },
    ],
    'interstellar': [
      {
        id: 157336,
        title: 'Interstellar',
        original_language: 'en',
        release_year: '2014',
        overview: 'A team of explorers travel through a wormhole in space in an attempt to ensure humanity\'s survival.',
        poster_path: '/xJHokMbljvjADYdit5fK5VQsXEG.jpg',
      },
    ],
    'john wick': [
      {
        id: 299536,
        title: 'John Wick',
        original_language: 'en',
        release_year: '2014',
        overview: 'An ex-hit-man comes out of retirement to track down the gangsters that took everything from him.',
        poster_path: '/jLXBX0Qx8s6gQz2vJll2TYcgGlS.jpg',
      },
      {
        id: 324552,
        title: 'John Wick: Chapter 2',
        original_language: 'en',
        release_year: '2017',
        overview: 'After returning to the criminal underworld to repay a debt, John Wick discovers that a large bounty has been put on his life.',
        poster_path: '/xCL5VWJ8y6XQowP8p8G3I8Q2Q0o.jpg',
      },
    ],
    '': [
      {
        id: 27205,
        title: 'Inception',
        original_language: 'en',
        release_year: '2010',
        overview: 'A thief who steals corporate secrets through the use of dream-sharing technology is given the inverse task of planting an idea into the mind of a C.E.O.',
        poster_path: '/9gk7adHYeDvHkCSEqAvQNLV5Uge.jpg',
      },
      {
        id: 157336,
        title: 'Interstellar',
        original_language: 'en',
        release_year: '2014',
        overview: 'A team of explorers travel through a wormhole in space in an attempt to ensure humanity\'s survival.',
        poster_path: '/xJHokMbljvjADYdit5fK5VQsXEG.jpg',
      },
      {
        id: 603,
        title: 'The Matrix',
        original_language: 'en',
        release_year: '1999',
        overview: 'Set in the 22nd century, The Matrix tells the story of a computer hacker who joins a group of underground insurgents fighting the vast and powerful computers who now rule the earth.',
        poster_path: '/f89U3ADr1oiB1s9GkdPOEpXUk5H.jpg',
      },
    ],
  };

  const lowerQuery = query.toLowerCase();
  for (const [key, results] of Object.entries(mockDatabase)) {
    if (lowerQuery.includes(key)) {
      return results;
    }
  }

  // Return popular movies if no match
  return mockDatabase[''];
};

const getMockStreamingInfo = (movieId: number): StreamingResponse => {
  const streamingData: Record<number, StreamingResponse> = {
    27205: {
      flatrate: [
        { Type: 'flatrate', Provider: 'NETFLIX', Country: ['Netherlands', 'United States'] },
        { Type: 'flatrate', Provider: 'AMAZON', Country: ['Germany', 'France'] },
      ],
      rent: [
        { Type: 'rent', Provider: 'APPLE', Country: ['Netherlands', 'United Kingdom'] },
        { Type: 'rent', Provider: 'GOOGLE', Country: ['United States'] },
      ],
      buy: [
        { Type: 'buy', Provider: 'APPLE', Country: ['Netherlands'] },
        { Type: 'buy', Provider: 'AMAZON', Country: ['United States'] },
      ],
    },
    603: {
      flatrate: [
        { Type: 'flatrate', Provider: 'NETFLIX', Country: ['Netherlands', 'United States'] },
        { Type: 'flatrate', Provider: 'HBO', Country: ['United States'] },
      ],
      free: [
        { Type: 'free', Provider: 'TUBI', Country: ['United States'] },
      ],
    },
    157336: {
      flatrate: [
        { Type: 'flatrate', Provider: 'NETFLIX', Country: ['Netherlands'] },
        { Type: 'flatrate', Provider: 'AMAZON', Country: ['United States', 'Germany'] },
        { Type: 'flatrate', Provider: 'DISNEY', Country: ['France'] },
      ],
      rent: [
        { Type: 'rent', Provider: 'APPLE', Country: ['Netherlands'] },
      ],
    },
    299536: {
      flatrate: [
        { Type: 'flatrate', Provider: 'NETFLIX', Country: ['Netherlands'] },
        { Type: 'flatrate', Provider: 'AMAZON', Country: ['United States'] },
      ],
      buy: [
        { Type: 'buy', Provider: 'APPLE', Country: ['Netherlands'] },
        { Type: 'buy', Provider: 'GOOGLE', Country: ['United States'] },
      ],
    },
  };

  return streamingData[movieId] || streamingData[27205];
};

// Direct agent call for the full workflow
export const callAgent = async (query: string): Promise<{
  searchResults: MovieSearchResult[];
  streamingInfo: StreamingResponse | null;
}> => {
  try {
    const response = await fetch(`${API_BASE}/api/agent`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ query }),
    });

    if (!response.ok) {
      throw new Error('Agent call failed');
    }

    return await response.json();
  } catch (error) {
    console.error('Agent call error:', error);
    // Fallback to mock workflow
    const searchResults = await searchMovies(query);
    const streamingInfo = searchResults.length > 0 ? await getStreamingInfo(searchResults[0].id) : null;
    return { searchResults, streamingInfo };
  }
};
