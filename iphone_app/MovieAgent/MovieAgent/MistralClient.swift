import Foundation

struct MistralToolCall: Codable {
    struct Function: Codable {
        let name: String
        let arguments: String
    }

    let id: String
    let type: String
    let function: Function
}

struct MistralMessage: Codable {
    let role: String
    let content: String?
    let toolCalls: [MistralToolCall]?
    let toolCallID: String?
    let name: String?

    enum CodingKeys: String, CodingKey {
        case role, content, name
        case toolCalls = "tool_calls"
        case toolCallID = "tool_call_id"
    }

    init(role: String, content: String? = nil, toolCalls: [MistralToolCall]? = nil, toolCallID: String? = nil, name: String? = nil) {
        self.role = role
        self.content = content
        self.toolCalls = toolCalls
        self.toolCallID = toolCallID
        self.name = name
    }

    init(from decoder: Decoder) throws {
        let values = try decoder.container(keyedBy: CodingKeys.self)
        role = try values.decode(String.self, forKey: .role)
        toolCalls = try values.decodeIfPresent([MistralToolCall].self, forKey: .toolCalls)
        toolCallID = try values.decodeIfPresent(String.self, forKey: .toolCallID)
        name = try values.decodeIfPresent(String.self, forKey: .name)
        if let text = try? values.decode(String.self, forKey: .content) {
            content = text
        } else if let blocks = try? values.decode([TextBlock].self, forKey: .content) {
            content = blocks.compactMap(\.text).joined()
        } else {
            content = nil
        }
    }

    private struct TextBlock: Decodable {
        let text: String?
    }
}

struct MistralClient {
    let config: AppConfig
    var session: URLSession = .shared

    func complete(messages: [MistralMessage]) async throws -> MistralMessage {
        let url = URL(string: "https://api.mistral.ai/v1/chat/completions")!
        var request = URLRequest(url: url)
        request.httpMethod = "POST"
        request.setValue("Bearer \(config.mistralKey)", forHTTPHeaderField: "Authorization")
        request.setValue("application/json", forHTTPHeaderField: "Content-Type")
        request.httpBody = try JSONEncoder().encode(ChatRequest(
            model: config.mistralModel,
            messages: messages,
            tools: Self.tools,
            temperature: 0,
            parallelToolCalls: false
        ))
        let data = try await HTTPClient.data(for: request, service: "Mistral", session: session)
        guard let message = try JSONDecoder().decode(ChatResponse.self, from: data).choices.first?.message else {
            throw AppError.invalidResponse
        }
        return message
    }

    private static let tools: [ToolSpecification] = [
        .init(name: "tmdb_search_movie", description: "Search TMDB for a movie by title. Returns up to 10 candidates with exact TMDB IDs.", properties: [
            "title": .init(type: "string", description: "Movie title"),
            "year": .init(type: "integer", description: "Optional release year")
        ], required: ["title"]),
        .init(name: "tmdb_watch_providers", description: "Find streaming availability for a movie ID returned by tmdb_search_movie.", properties: [
            "movie_id": .init(type: "integer", description: "Exact TMDB movie ID from a previous search")
        ], required: ["movie_id"]),
        .init(name: "tmdb_search_tv", description: "Search TMDB for a TV series by title. Returns up to 10 candidates with exact TMDB IDs.", properties: [
            "title": .init(type: "string", description: "TV series title"),
            "year": .init(type: "integer", description: "Optional first air year")
        ], required: ["title"]),
        .init(name: "tmdb_tv_watch_providers", description: "Find streaming availability for a TV series ID returned by tmdb_search_tv.", properties: [
            "series_id": .init(type: "integer", description: "Exact TMDB TV ID from a previous search")
        ], required: ["series_id"])
    ]
}

private struct ChatRequest: Encodable {
    let model: String
    let messages: [MistralMessage]
    let tools: [ToolSpecification]
    let temperature: Int
    let parallelToolCalls: Bool

    enum CodingKeys: String, CodingKey {
        case model, messages, tools, temperature
        case parallelToolCalls = "parallel_tool_calls"
    }
}

private struct ChatResponse: Decodable {
    struct Choice: Decodable { let message: MistralMessage }
    let choices: [Choice]
}

private struct ToolSpecification: Encodable {
    struct FunctionDefinition: Encodable {
        struct Parameters: Encodable {
            let type = "object"
            let properties: [String: Property]
            let required: [String]
        }

        let name: String
        let description: String
        let parameters: Parameters
    }

    struct Property: Encodable {
        let type: String
        let description: String
    }

    let type = "function"
    let function: FunctionDefinition

    init(name: String, description: String, properties: [String: Property], required: [String]) {
        function = FunctionDefinition(
            name: name,
            description: description,
            parameters: .init(properties: properties, required: required)
        )
    }
}
