import Foundation

private final class MockURLProtocol: URLProtocol {
    static var handler: ((URLRequest) throws -> (Int, Data))?

    override class func canInit(with request: URLRequest) -> Bool { true }
    override class func canonicalRequest(for request: URLRequest) -> URLRequest { request }

    override func startLoading() {
        do {
            let (status, data) = try Self.handler!(request)
            let response = HTTPURLResponse(url: request.url!, statusCode: status, httpVersion: nil, headerFields: nil)!
            client?.urlProtocol(self, didReceive: response, cacheStoragePolicy: .notAllowed)
            client?.urlProtocol(self, didLoad: data)
            client?.urlProtocolDidFinishLoading(self)
        } catch {
            client?.urlProtocol(self, didFailWithError: error)
        }
    }

    override func stopLoading() {}
}

@main
struct ServiceSmoke {
    static func main() async throws {
        let configuration = URLSessionConfiguration.ephemeral
        configuration.protocolClasses = [MockURLProtocol.self]
        let session = URLSession(configuration: configuration)
        let config = AppConfig(mistralKey: "test-mistral", mistralModel: "mistral-small-latest", tmdbReadAccessToken: "test-tmdb", tmdbKey: nil)
        let tmdb = TMDBClient(config: config, session: session)

        MockURLProtocol.handler = { request in
            precondition(request.url?.host == "api.themoviedb.org")
            precondition(request.value(forHTTPHeaderField: "Authorization") == "Bearer test-tmdb")
            if request.url?.path == "/3/search/movie" {
                return (200, Data(#"{"results":[{"id":12,"title":"Example","release_date":"2020-01-01","overview":"A film","poster_path":"/poster.jpg","original_language":"en"}]}"#.utf8))
            }
            return (200, Data(#"{"results":{"NL":{"flatrate":[{"provider_name":"Netflix"},{"provider_name":"Other"}]},"US":{"flatrate":[{"provider_name":"Netflix"}]}}}"#.utf8))
        }
        let movies = try await tmdb.search(title: "Example", kind: .movie)
        precondition(movies.count == 1 && movies[0].id == 12 && movies[0].releaseYear == "2020")
        let providers = try await tmdb.providers(for: 12, kind: .movie)
        precondition(providers.count == 1 && providers[0].provider == "NETFLIX")
        precondition(providers[0].countries == ["Netherlands", "United States"])

        MockURLProtocol.handler = { request in
            precondition(request.url?.host == "api.mistral.ai")
            precondition(request.httpMethod == "POST")
            precondition(request.value(forHTTPHeaderField: "Authorization") == "Bearer test-mistral")
            let data: Data
            if let direct = request.httpBody {
                data = direct
            } else {
                let stream = request.httpBodyStream!
                stream.open()
                defer { stream.close() }
                var bytes = [UInt8](repeating: 0, count: 4096)
                var collected = Data()
                while stream.hasBytesAvailable {
                    let count = stream.read(&bytes, maxLength: bytes.count)
                    if count <= 0 { break }
                    collected.append(contentsOf: bytes.prefix(count))
                }
                data = collected
            }
            let body = try JSONSerialization.jsonObject(with: data) as! [String: Any]
            precondition(body["model"] as? String == "mistral-small-latest")
            precondition((body["tools"] as? [[String: Any]])?.count == 4)
            return (200, Data(#"{"choices":[{"message":{"role":"assistant","content":null,"tool_calls":[{"id":"call-1","type":"function","function":{"name":"tmdb_search_movie","arguments":"{\"title\":\"Example\"}"}}]}}]}"#.utf8))
        }
        let reply = try await MistralClient(config: config, session: session).complete(messages: [MistralMessage(role: "user", content: "Where is Example streaming?")])
        precondition(reply.toolCalls?.first?.function.name == "tmdb_search_movie")
        print("Swift service smoke tests passed")
    }
}
