import React from 'react';
import { StreamingResponse, StreamingInfo } from '../types';

interface StreamingResultsProps {
  streamingData: StreamingResponse | null;
  movieTitle: string;
}

const StreamingResults: React.FC<StreamingResultsProps> = ({ streamingData, movieTitle }) => {
  if (!streamingData) {
    return <div className="no-results">No streaming information available</div>;
  }

  const getProviderLogo = (provider: string) => {
    const logos: Record<string, string> = {
      NETFLIX: 'https://upload.wikimedia.org/wikipedia/commons/0/08/Netflix_2015_logo.svg',
      AMAZON: 'https://upload.wikimedia.org/wikipedia/commons/f/ff/Amazon_Prime_Video_logo.svg',
      HBO: 'https://upload.wikimedia.org/wikipedia/commons/4/44/HBO_logo_2020.svg',
      MAX: 'https://upload.wikimedia.org/wikipedia/commons/4/44/HBO_logo_2020.svg',
      APPLE: 'https://upload.wikimedia.org/wikipedia/commons/4/43/Apple_TV_plus_logo.svg',
      DISNEY: 'https://upload.wikimedia.org/wikipedia/commons/3/32/Disney%2B_logo.svg',
      HULU: 'https://upload.wikimedia.org/wikipedia/commons/e/e4/Hulu_Logo.svg',
      TUBI: 'https://upload.wikimedia.org/wikipedia/commons/3/35/Tubi_logo.svg',
      GOOGLE: 'https://upload.wikimedia.org/wikipedia/commons/2/28/Google_Play_Movies_%26_TV_logo.svg',
    };
    return logos[provider.toUpperCase()] || null;
  };

  const getTypeIcon = (type: string) => {
    switch (type.toLowerCase()) {
      case 'flatrate':
        return '📺';
      case 'rent':
        return '💰';
      case 'buy':
        return '🛒';
      case 'free':
        return '🆓';
      case 'ads':
        return '📢';
      default:
        return '🎬';
    }
  };

  const getTypeLabel = (type: string) => {
    switch (type.toLowerCase()) {
      case 'flatrate':
        return 'Subscription';
      case 'rent':
        return 'Rent';
      case 'buy':
        return 'Buy';
      case 'free':
        return 'Free';
      case 'ads':
        return 'With Ads';
      default:
        return type;
    }
  };

  // Group by type
  const groupedByType: Record<string, StreamingInfo[]> = {};
  Object.entries(streamingData).forEach(([type, infos]) => {
    groupedByType[type] = infos;
  });

  return (
    <div className="streaming-results">
      <h2 className="results-title">
        <span className="movie-title-highlight">{movieTitle}</span>
        <span className="available-text"> is available on:</span>
      </h2>

      <div className="streaming-grid">
        {Object.entries(groupedByType).map(([type, infos]) => (
          <div key={type} className="streaming-category">
            <div className="category-header">
              <span className="type-icon">{getTypeIcon(type)}</span>
              <span className="type-label">{getTypeLabel(type)}</span>
            </div>
            <div className="providers-list">
              {infos.map((info, index) => (
                <div key={index} className="provider-item">
                  <div className="provider-logo">
                    {getProviderLogo(info.Provider) ? (
                      <img
                        src={getProviderLogo(info.Provider)!}
                        alt={info.Provider}
                        onError={(e) => {
                          (e.target as HTMLImageElement).style.display = 'none';
                        }}
                      />
                    ) : (
                      <span className="provider-name">{info.Provider}</span>
                    )}
                  </div>
                  <div className="provider-countries">
                    {info.Country.map((country, i) => (
                      <span key={i} className="country-badge">
                        {country}
                      </span>
                    ))}
                  </div>
                </div>
              ))}
            </div>
          </div>
        ))}
      </div>

      <div className="results-summary">
        <p>
          <strong>Total Options:</strong> 
          {Object.values(groupedByType).reduce((sum, infos) => sum + infos.length, 0)}
        </p>
      </div>
    </div>
  );
};

export default StreamingResults;
