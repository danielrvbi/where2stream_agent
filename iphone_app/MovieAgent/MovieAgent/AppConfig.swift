import Foundation

struct AppConfig {
    let mistralKey: String
    let mistralModel: String
    let tmdbReadAccessToken: String?
    let tmdbKey: String?

    static func load(from bundle: Bundle = .main) throws -> AppConfig {
        func value(_ name: String) -> String? {
            guard let text = bundle.object(forInfoDictionaryKey: name) as? String else { return nil }
            let trimmed = text.trimmingCharacters(in: .whitespacesAndNewlines)
            return trimmed.isEmpty || trimmed.hasPrefix("$(") ? nil : trimmed
        }

        guard let mistralKey = value("MISTRAL_API_KEY") else {
            throw AppError.configuration("MISTRAL_API_KEY is missing from Secrets.xcconfig.")
        }
        let token = value("TMDB_READ_ACCESS_TOKEN")
        let key = value("TMDB_API_KEY")
        guard token != nil || key != nil else {
            throw AppError.configuration("TMDB_read_access_token or TMDB_key is missing from Secrets.xcconfig.")
        }
        return AppConfig(
            mistralKey: mistralKey,
            mistralModel: value("MISTRAL_MODEL") ?? "mistral-small-latest",
            tmdbReadAccessToken: token,
            tmdbKey: key
        )
    }
}

enum AppError: LocalizedError {
    case configuration(String)
    case invalidResponse
    case httpStatus(Int, String)
    case invalidToolArguments(String)

    var errorDescription: String? {
        switch self {
        case .configuration(let message): message
        case .invalidResponse: "The service returned an unexpected response."
        case .httpStatus(let status, let service): "\(service) returned HTTP \(status). Check the key or try again."
        case .invalidToolArguments(let tool): "Mistral sent invalid arguments for \(tool)."
        }
    }
}

enum HTTPClient {
    static func data(for request: URLRequest, service: String, session: URLSession = .shared) async throws -> Data {
        let (data, response) = try await session.data(for: request)
        guard let response = response as? HTTPURLResponse else { throw AppError.invalidResponse }
        guard (200..<300).contains(response.statusCode) else {
            throw AppError.httpStatus(response.statusCode, service)
        }
        return data
    }
}
