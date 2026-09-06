/** Reads an SSE body, handing each frame's parsed `data:` payload to onFrame.
    Comment lines (": …"), blank frames and malformed JSON are skipped. */
export async function readFrames<T>(
  body: ReadableStream<Uint8Array>,
  onFrame: (frame: T) => void,
) {
  const reader = body.getReader();
  const decoder = new TextDecoder();
  let buffer = '';

  for (;;) {
    const { done, value } = await reader.read();
    if (done) return;
    buffer += decoder.decode(value, { stream: true });

    let idx;
    while ((idx = buffer.indexOf('\n\n')) !== -1) {
      const frame = buffer.slice(0, idx);
      buffer = buffer.slice(idx + 2);
      const data = frame
        .split('\n')
        .filter((l) => l.startsWith('data:'))
        .map((l) => l.slice(5).trim())
        .join('\n');
      if (!data) continue;
      try {
        onFrame(JSON.parse(data) as T);
      } catch {
        // ignore malformed frame
      }
    }
  }
}
