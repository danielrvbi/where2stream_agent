import Foundation
import Combine

struct ChatBubble: Identifiable {
    enum Speaker { case user, assistant }
    let id = UUID()
    let speaker: Speaker
    let text: String
}

@MainActor
final class ChatViewModel: ObservableObject {
    @Published private(set) var bubbles: [ChatBubble] = [
        ChatBubble(speaker: .assistant, text: "Ask me where to watch a movie or TV series.")
    ]
    @Published private(set) var candidates: [MediaCandidate] = []
    @Published private(set) var selectedMedia: MediaCandidate?
    @Published private(set) var availability: [ProviderAvailability] = []
    @Published private(set) var isBusy = false
    @Published private(set) var status: String?
    @Published private(set) var configurationError: String?

    private let tmdb: TMDBClient?
    private let mistral: MistralClient?
    private var history: [MistralMessage] = []
    private var searchedMovieIDs: Set<Int> = []
    private var searchedTVIDs: Set<Int> = []
    private var waitingForSelection = false

    init(config suppliedConfig: AppConfig? = nil) {
        do {
            let config = try suppliedConfig ?? AppConfig.load()
            tmdb = TMDBClient(config: config)
            mistral = MistralClient(config: config)
        } catch {
            tmdb = nil
            mistral = nil
            configurationError = error.localizedDescription
        }
    }

    func send(_ rawText: String) {
        let text = rawText.trimmingCharacters(in: .whitespacesAndNewlines)
        guard !text.isEmpty, !isBusy, configurationError == nil else { return }
        candidates = []
        availability = []
        selectedMedia = nil
        waitingForSelection = false
        bubbles.append(ChatBubble(speaker: .user, text: text))
        history.append(MistralMessage(role: "user", content: text))
        isBusy = true
        Task { await runConversation() }
    }

    func select(_ candidate: MediaCandidate) {
        guard !isBusy, configurationError == nil else { return }
        selectedMedia = candidate
        candidates = []
        waitingForSelection = false
        let clarification = "I mean the \(candidate.kind.label.lowercased()) \(candidate.title) (\(candidate.releaseYear)), TMDB ID \(candidate.id). Check where I can watch this exact title."
        bubbles.append(ChatBubble(speaker: .user, text: "\(candidate.title) (\(candidate.releaseYear))"))
        history.append(MistralMessage(role: "user", content: clarification))
        isBusy = true
        Task { await runConversation() }
    }

    func newChat() {
        guard !isBusy else { return }
        history = []
        searchedMovieIDs = []
        searchedTVIDs = []
        waitingForSelection = false
        candidates = []
        selectedMedia = nil
        availability = []
        status = nil
        bubbles = [ChatBubble(speaker: .assistant, text: "Ask me where to watch a movie or TV series.")]
    }

    private func runConversation() async {
        guard let mistral, let tmdb else { return }
        isBusy = true
        status = "Asking Mistral…"
        defer { isBusy = false; status = nil }

        do {
            for _ in 0..<10 {
                let reply = try await mistral.complete(messages: [Self.systemMessage] + history)
                history.append(reply)

                if let text = reply.content?.trimmingCharacters(in: .whitespacesAndNewlines), !text.isEmpty {
                    bubbles.append(ChatBubble(speaker: .assistant, text: text))
                }

                guard let calls = reply.toolCalls, !calls.isEmpty else {
                    if reply.content?.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty ?? true {
                        throw AppError.invalidResponse
                    }
                    return
                }
                for call in calls {
                    let result: String
                    do {
                        result = try await execute(call, with: tmdb)
                    } catch {
                        result = "{\"error\":\"\(Self.escape(error.localizedDescription))\"}"
                    }
                    history.append(MistralMessage(
                        role: "tool", content: result, toolCallID: call.id, name: call.function.name
                    ))
                }

                if waitingForSelection {
                    let text = "I found multiple titles with that name. Which one did you mean?"
                    bubbles.append(ChatBubble(speaker: .assistant, text: text))
                    history.append(MistralMessage(role: "assistant", content: text))
                    return
                }
                status = "Preparing answer…"
            }
            throw AppError.invalidResponse
        } catch {
            bubbles.append(ChatBubble(speaker: .assistant, text: "I couldn't complete that request. \(error.localizedDescription)"))
        }
    }

    private func execute(_ call: MistralToolCall, with tmdb: TMDBClient) async throws -> String {
        let arguments = try JSONSerialization.jsonObject(with: Data(call.function.arguments.utf8)) as? [String: Any] ?? [:]
        switch call.function.name {
        case "tmdb_search_movie", "tmdb_search_tv":
            guard let title = arguments["title"] as? String, !title.isEmpty else {
                throw AppError.invalidToolArguments(call.function.name)
            }
            let kind: MediaKind = call.function.name == "tmdb_search_movie" ? .movie : .tv
            let year = arguments["year"] as? Int
            status = "Searching TMDB for \(title)…"
            let results = try await tmdb.search(title: title, kind: kind, year: year)
            candidates = results
            if kind == .movie {
                searchedMovieIDs.formUnion(results.map(\.id))
            } else {
                searchedTVIDs.formUnion(results.map(\.id))
            }
            let exact = results.filter { Self.normalized($0.title) == Self.normalized(title) }
            waitingForSelection = year == nil && exact.count > 1
            return try Self.json(results)

        case "tmdb_watch_providers", "tmdb_tv_watch_providers":
            let kind: MediaKind = call.function.name == "tmdb_watch_providers" ? .movie : .tv
            let key = kind == .movie ? "movie_id" : "series_id"
            guard let id = arguments[key] as? Int else {
                throw AppError.invalidToolArguments(call.function.name)
            }
            let valid = kind == .movie ? searchedMovieIDs.contains(id) : searchedTVIDs.contains(id)
            guard valid else {
                return "{\"error\":\"Search TMDB for this title first and use an ID from that search.\"}"
            }
            status = "Checking streaming providers…"
            let providers = try await tmdb.providers(for: id, kind: kind)
            availability = providers
            if let match = candidates.first(where: { $0.id == id && $0.kind == kind }) {
                selectedMedia = match
            }
            return try Self.json(providers)

        default:
            return "{\"error\":\"Unknown tool.\"}"
        }
    }

    private static func json<T: Encodable>(_ value: T) throws -> String {
        String(data: try JSONEncoder().encode(value), encoding: .utf8) ?? "{}"
    }

    private static func normalized(_ title: String) -> String {
        title.folding(options: [.caseInsensitive, .diacriticInsensitive], locale: .current)
            .trimmingCharacters(in: .whitespacesAndNewlines)
    }

    private static func escape(_ text: String) -> String {
        let data = try? JSONEncoder().encode(text)
        let quoted = data.flatMap { String(data: $0, encoding: .utf8) } ?? "\"Error\""
        return String(quoted.dropFirst().dropLast())
    }

    private static let systemMessage = MistralMessage(role: "system", content: """
        You are a specialized entertainment assistant. Help with movies, TV series, and where to watch them.
        For a movie, call tmdb_search_movie before tmdb_watch_providers. For a TV series, call
        tmdb_search_tv before tmdb_tv_watch_providers. Use only an ID returned by the corresponding
        search. If several results are plausible, ask the user to choose the exact title or year.
        Never invent streaming availability. Prioritize availability in the Netherlands, then mention
        other countries accessible by VPN. Focus on subscription availability from Netflix, Amazon,
        HBO, Max, Apple, Disney, Hulu, and Tubi. If none is available, report any matching free,
        ad-supported, rental, or purchase options. Explain briefly what you are checking before
        making tool calls. If TMDB returns no providers, say so clearly.
        After checking providers, write a short, readable summary. State Netherlands availability
        first, then mention only the most useful international alternatives. Put separate points on
        separate lines. Do not repeat long country lists: the app shows the full provider and country
        list below your reply. Do not use Markdown headings, tables, or website links. Do not include
        TMDB IDs unless the user asks for them.
        """)
}
