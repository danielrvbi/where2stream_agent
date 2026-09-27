import Foundation

enum MediaKind: String, Codable, Hashable {
    case movie
    case tv

    var label: String { self == .movie ? "Movie" : "TV series" }
}

struct MediaCandidate: Identifiable, Codable, Hashable {
    let id: Int
    let kind: MediaKind
    let title: String
    let releaseYear: String
    let originalLanguage: String
    let overview: String
    let posterPath: String?

    var posterURL: URL? {
        guard let posterPath else { return nil }
        return URL(string: "https://image.tmdb.org/t/p/w342\(posterPath)")
    }
}

struct ProviderAvailability: Identifiable, Codable, Hashable {
    let type: String
    let provider: String
    let countries: [String]

    var id: String { "\(type):\(provider)" }

    var typeLabel: String {
        switch type {
        case "flatrate": "Subscription"
        case "ads": "With ads"
        case "free": "Free"
        case "rent": "Rent"
        case "buy": "Buy"
        default: type.capitalized
        }
    }
}

struct TMDBClient {
    let config: AppConfig
    var session: URLSession = .shared

    func search(title: String, kind: MediaKind, year: Int? = nil) async throws -> [MediaCandidate] {
        var parameters = [URLQueryItem(name: "query", value: title), URLQueryItem(name: "include_adult", value: "false")]
        if let year {
            parameters.append(URLQueryItem(name: kind == .movie ? "year" : "first_air_date_year", value: String(year)))
        }
        let data = try await get(path: "/search/\(kind.rawValue)", parameters: parameters)
        let response = try JSONDecoder.tmdb.decode(SearchResponse.self, from: data)
        return Array(response.results.prefix(10)).map { result in
            MediaCandidate(
                id: result.id,
                kind: kind,
                title: result.title ?? result.name ?? "Untitled",
                releaseYear: String((result.releaseDate ?? result.firstAirDate ?? "").prefix(4)),
                originalLanguage: result.originalLanguage ?? "",
                overview: result.overview ?? "",
                posterPath: result.posterPath
            )
        }
    }

    func providers(for id: Int, kind: MediaKind) async throws -> [ProviderAvailability] {
        let data = try await get(path: "/\(kind.rawValue)/\(id)/watch/providers")
        let response = try JSONDecoder.tmdb.decode(ProvidersResponse.self, from: data)
        let preferredTypes = ["flatrate", "free", "ads"]
        let fallbackTypes = ["rent", "buy"]

        func collect(_ types: [String]) -> [ProviderAvailability] {
            var grouped: [String: Set<String>] = [:]
            for (countryCode, country) in response.results {
                for type in types {
                    for provider in country.providers(for: type) where Self.isSubscribed(provider.providerName) {
                        grouped["\(type)|\(provider.providerName.uppercased())", default: []].insert(countryCode)
                    }
                }
            }
            return grouped.map { key, countryCodes in
                let parts = key.split(separator: "|", maxSplits: 1).map(String.init)
                let countries = countryCodes.sorted { lhs, rhs in
                    if lhs == "NL" { return true }
                    if rhs == "NL" { return false }
                    return lhs < rhs
                }.map { code in
                    Locale(identifier: "en_US").localizedString(forRegionCode: code) ?? code
                }
                return ProviderAvailability(type: parts[0], provider: parts[1], countries: countries)
            }.sorted { lhs, rhs in
                let l = types.firstIndex(of: lhs.type) ?? types.count
                let r = types.firstIndex(of: rhs.type) ?? types.count
                return l == r ? lhs.provider < rhs.provider : l < r
            }
        }

        let preferred = collect(preferredTypes)
        return preferred.isEmpty ? collect(fallbackTypes) : preferred
    }

    private func get(path: String, parameters: [URLQueryItem] = []) async throws -> Data {
        var components = URLComponents(string: "https://api.themoviedb.org/3\(path)")!
        var query = parameters
        if config.tmdbReadAccessToken == nil, let key = config.tmdbKey {
            query.append(URLQueryItem(name: "api_key", value: key))
        }
        components.queryItems = query.isEmpty ? nil : query
        guard let url = components.url else { throw AppError.invalidResponse }
        var request = URLRequest(url: url)
        request.setValue("application/json", forHTTPHeaderField: "Accept")
        if let token = config.tmdbReadAccessToken {
            request.setValue("Bearer \(token)", forHTTPHeaderField: "Authorization")
        }
        return try await HTTPClient.data(for: request, service: "TMDB", session: session)
    }

    private static func isSubscribed(_ name: String) -> Bool {
        let upper = name.uppercased()
        return ["NETFLIX", "AMAZON", "HBO", "MAX", "APPLE", "DISNEY", "HULU", "TUBI"]
            .contains { upper.contains($0) }
    }
}

private extension JSONDecoder {
    static var tmdb: JSONDecoder {
        let decoder = JSONDecoder()
        decoder.keyDecodingStrategy = .convertFromSnakeCase
        return decoder
    }
}

private struct SearchResponse: Decodable {
    let results: [SearchResult]
}

private struct SearchResult: Decodable {
    let id: Int
    let title: String?
    let name: String?
    let releaseDate: String?
    let firstAirDate: String?
    let originalLanguage: String?
    let overview: String?
    let posterPath: String?
}

private struct ProvidersResponse: Decodable {
    let results: [String: CountryProviders]
}

private struct CountryProviders: Decodable {
    let flatrate: [WatchProvider]?
    let free: [WatchProvider]?
    let ads: [WatchProvider]?
    let rent: [WatchProvider]?
    let buy: [WatchProvider]?

    func providers(for type: String) -> [WatchProvider] {
        switch type {
        case "flatrate": flatrate ?? []
        case "free": free ?? []
        case "ads": ads ?? []
        case "rent": rent ?? []
        case "buy": buy ?? []
        default: []
        }
    }
}

private struct WatchProvider: Decodable {
    let providerName: String
}
