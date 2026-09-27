import SwiftUI

struct ContentView: View {
    @Environment(\.colorScheme) private var colorScheme
    @StateObject private var chat = ChatViewModel()
    @State private var draft = ""
    @State private var showingCredits = false
    @FocusState private var composerFocused: Bool

    private var pageColor: Color { colorScheme == .dark ? .black : .white }
    private var surfaceColor: Color { Color(white: colorScheme == .dark ? 0.12 : 0.96) }
    private var borderColor: Color { Color.primary.opacity(colorScheme == .dark ? 0.16 : 0.07) }
    private var sendColor: Color { colorScheme == .dark ? .white : .black }
    private var canSend: Bool {
        !draft.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty
            && !chat.isBusy && chat.configurationError == nil
    }

    var body: some View {
        VStack(spacing: 0) {
            header
            ScrollViewReader { proxy in
                ScrollView {
                    LazyVStack(alignment: .leading, spacing: 26) {
                        if chat.bubbles.count == 1 && chat.configurationError == nil {
                            welcome
                        } else {
                            ForEach(Array(chat.bubbles.dropFirst())) { bubble in
                                messageView(bubble)
                            }
                        }
                        if !chat.candidates.isEmpty { candidateSection }
                        if !chat.availability.isEmpty { providerSection }
                        if let status = chat.status {
                            HStack(spacing: 10) {
                                ProgressView().tint(.secondary)
                                Text(status).font(.subheadline).foregroundStyle(.secondary)
                            }
                            .id("latest")
                        }
                        if let error = chat.configurationError {
                            Label(error, systemImage: "exclamationmark.triangle")
                                .font(.subheadline)
                                .foregroundStyle(.orange)
                                .padding(16)
                                .frame(maxWidth: .infinity, alignment: .leading)
                                .background(surfaceColor, in: RoundedRectangle(cornerRadius: 18))
                                .id("latest")
                        }
                    }
                    .frame(maxWidth: 740)
                    .frame(maxWidth: .infinity)
                    .padding(.horizontal, 20)
                    .padding(.bottom, 24)
                }
                .onChange(of: chat.bubbles.count) { _, count in
                    if count > 1 {
                        withAnimation { proxy.scrollTo(chat.bubbles.last?.id, anchor: .bottom) }
                    }
                }
                .onChange(of: chat.candidates.count) { _, count in
                    if count > 0 { withAnimation { proxy.scrollTo("candidates", anchor: .bottom) } }
                }
                .onChange(of: chat.availability.count) { _, count in
                    if count > 0 { withAnimation { proxy.scrollTo("providers", anchor: .bottom) } }
                }
                .onChange(of: chat.status) { _, status in
                    if status != nil { withAnimation { proxy.scrollTo("latest", anchor: .bottom) } }
                }
            }
            composer
        }
        .background(pageColor.ignoresSafeArea())
        .sheet(isPresented: $showingCredits) { creditsSheet }
    }

    private var header: some View {
        HStack {
            Button { showingCredits = true } label: {
                Image(systemName: "info.circle")
                    .font(.system(size: 20, weight: .medium))
                    .frame(width: 44, height: 44)
            }
            .accessibilityLabel("About and credits")

            Spacer()
            Text("Where2Stream")
                .font(.system(size: 17, weight: .semibold))
            Spacer()

            Button { chat.newChat() } label: {
                Image(systemName: "square.and.pencil")
                    .font(.system(size: 19, weight: .medium))
                    .frame(width: 44, height: 44)
            }
            .disabled(chat.isBusy)
            .accessibilityLabel("New chat")
        }
        .foregroundStyle(.primary)
        .padding(.horizontal, 10)
        .padding(.vertical, 4)
        .background(pageColor)
        .overlay(alignment: .bottom) { Rectangle().fill(borderColor).frame(height: 0.5) }
    }

    private var welcome: some View {
        VStack(spacing: 18) {
            Image(systemName: "film.stack.fill")
                .font(.system(size: 34, weight: .medium))
                .frame(width: 68, height: 68)
                .foregroundStyle(pageColor)
                .background(sendColor, in: RoundedRectangle(cornerRadius: 20))
            Text("What would you like to watch?")
                .font(.system(size: 26, weight: .semibold))
                .multilineTextAlignment(.center)
            Text("Ask about a movie or series and I’ll find where it’s streaming.")
                .font(.subheadline)
                .foregroundStyle(.secondary)
                .multilineTextAlignment(.center)
            VStack(spacing: 10) {
                suggestion("Where can I watch The Matrix?")
                suggestion("Find streaming options for Breaking Bad")
            }
            .padding(.top, 22)
        }
        .frame(maxWidth: .infinity)
        .padding(.top, 110)
    }

    private func suggestion(_ prompt: String) -> some View {
        Button { chat.send(prompt) } label: {
            HStack(spacing: 10) {
                Image(systemName: "sparkle.magnifyingglass")
                    .foregroundStyle(.secondary)
                Text(prompt)
                    .foregroundStyle(.primary)
                    .multilineTextAlignment(.leading)
                Spacer(minLength: 0)
                Image(systemName: "arrow.up.left")
                    .font(.caption)
                    .foregroundStyle(.tertiary)
            }
            .font(.subheadline)
            .padding(15)
            .background(surfaceColor, in: RoundedRectangle(cornerRadius: 16))
        }
        .buttonStyle(.plain)
        .disabled(chat.isBusy)
    }

    private func messageView(_ bubble: ChatBubble) -> some View {
        Group {
            if bubble.speaker == .user {
                HStack {
                    Spacer(minLength: 48)
                    Text(bubble.text)
                        .font(.body)
                        .textSelection(.enabled)
                        .padding(.horizontal, 16)
                        .padding(.vertical, 12)
                        .background(surfaceColor, in: RoundedRectangle(cornerRadius: 21))
                }
            } else {
                HStack(alignment: .top) {
                    assistantText(bubble.text)
                        .font(.body)
                        .lineSpacing(4)
                        .textSelection(.enabled)
                    Spacer(minLength: 20)
                }
            }
        }
        .id(bubble.id)
    }

    private func assistantText(_ content: String) -> Text {
        let options = AttributedString.MarkdownParsingOptions(interpretedSyntax: .inlineOnlyPreservingWhitespace)
        guard let markdown = try? AttributedString(markdown: content, options: options) else { return Text(content) }
        return Text(markdown)
    }

    private var candidateSection: some View {
        VStack(alignment: .leading, spacing: 12) {
            Text("Titles found")
                .font(.headline)
            ForEach(chat.candidates) { candidate in
                Button { chat.select(candidate) } label: {
                    HStack(alignment: .top, spacing: 13) {
                        AsyncImage(url: candidate.posterURL) { image in
                            image.resizable().scaledToFill()
                        } placeholder: {
                            Image(systemName: candidate.kind == .movie ? "film" : "tv")
                                .foregroundStyle(.secondary)
                                .frame(maxWidth: .infinity, maxHeight: .infinity)
                        }
                        .frame(width: 54, height: 80)
                        .clipped()
                        .background(surfaceColor)
                        .clipShape(RoundedRectangle(cornerRadius: 8))

                        VStack(alignment: .leading, spacing: 5) {
                            Text(candidate.title)
                                .font(.subheadline.weight(.semibold))
                                .foregroundStyle(.primary)
                            Text("\(candidate.kind.label) · \(candidate.releaseYear.isEmpty ? "Year unknown" : candidate.releaseYear)")
                                .font(.caption)
                                .foregroundStyle(.secondary)
                            if !candidate.overview.isEmpty {
                                Text(candidate.overview)
                                    .font(.caption)
                                    .foregroundStyle(.secondary)
                                    .lineLimit(2)
                            }
                        }
                        Spacer(minLength: 0)
                        Image(systemName: "chevron.right")
                            .font(.caption.weight(.semibold))
                            .foregroundStyle(.tertiary)
                    }
                    .padding(11)
                    .background(surfaceColor, in: RoundedRectangle(cornerRadius: 16))
                }
                .buttonStyle(.plain)
                .disabled(chat.isBusy)
            }
        }
        .id("candidates")
    }

    private var providerSection: some View {
        VStack(alignment: .leading, spacing: 12) {
            Text(chat.selectedMedia.map { "Where to watch \($0.title)" } ?? "Streaming options")
                .font(.headline)
            ForEach(["flatrate", "free", "ads", "rent", "buy"], id: \.self) { type in
                let entries = chat.availability.filter { $0.type == type }
                if !entries.isEmpty {
                    VStack(alignment: .leading, spacing: 10) {
                        Text(entries[0].typeLabel)
                            .font(.subheadline.weight(.semibold))
                        ForEach(entries) { entry in
                            HStack(alignment: .top) {
                                Text(entry.provider.capitalized)
                                    .font(.subheadline.weight(.medium))
                                Spacer(minLength: 10)
                                Text(entry.countries.joined(separator: " · "))
                                    .font(.caption)
                                    .foregroundStyle(.secondary)
                                    .multilineTextAlignment(.trailing)
                            }
                        }
                    }
                    .frame(maxWidth: .infinity, alignment: .leading)
                    .padding(16)
                    .background(surfaceColor, in: RoundedRectangle(cornerRadius: 16))
                }
            }
            Text("Streaming data: JustWatch via TMDB. Check the provider before watching.")
                .font(.caption2)
                .foregroundStyle(.secondary)
        }
        .id("providers")
    }

    private var composer: some View {
        HStack(alignment: .bottom, spacing: 10) {
            TextField("Ask anything about movies or TV", text: $draft)
                .textFieldStyle(.plain)
                .focused($composerFocused)
                .onTapGesture { composerFocused = true }
                .textInputAutocapitalization(.sentences)
                .submitLabel(.send)
                .onSubmit(sendDraft)
                .font(.body)
                .frame(minHeight: 34)
                .padding(.leading, 7)
                .padding(.vertical, 9)
            Button(action: sendDraft) {
                Image(systemName: "arrow.up")
                    .font(.system(size: 16, weight: .bold))
                    .foregroundStyle(pageColor)
                    .frame(width: 34, height: 34)
                    .background(canSend ? sendColor : Color.secondary.opacity(0.4), in: Circle())
            }
            .disabled(!canSend)
            .accessibilityLabel("Send message")
        }
        .padding(.horizontal, 12)
        .padding(.vertical, 7)
        .background(surfaceColor, in: RoundedRectangle(cornerRadius: 25))
        .overlay(RoundedRectangle(cornerRadius: 25).stroke(borderColor, lineWidth: 1))
        .frame(maxWidth: 740)
        .frame(maxWidth: .infinity)
        .padding(.horizontal, 14)
        .padding(.top, 8)
        .padding(.bottom, 10)
        .background(pageColor)
    }

    private func sendDraft() {
        guard canSend else { return }
        let text = draft
        draft = ""
        chat.send(text)
    }

    private var creditsSheet: some View {
        NavigationStack {
            VStack(alignment: .leading, spacing: 18) {
                Text("Where2Stream calls Mistral and TMDB directly from this iPhone.")
                Text("This product uses the TMDB API but is not endorsed or certified by TMDB.")
                Text("Streaming availability data is provided by JustWatch through TMDB.")
                Link("The Movie Database", destination: URL(string: "https://www.themoviedb.org")!)
                Link("JustWatch", destination: URL(string: "https://www.justwatch.com")!)
                Spacer()
            }
            .padding(20)
            .frame(maxWidth: .infinity, alignment: .leading)
            .background(pageColor)
            .navigationTitle("About & credits")
            .toolbar { Button("Done") { showingCredits = false } }
        }
        .presentationDetents([.medium, .large])
    }
}

#Preview { ContentView() }
