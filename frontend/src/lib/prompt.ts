import type { PromptContent } from '../api/types';

/** A sensible default prompt content document for newly created prompts. */
export function defaultPromptContent(): PromptContent {
  return {
    format_version: 1,
    kind: 'chat',
    template_engine: 'simple-v1',
    messages: [{ role: 'system', content: 'You are a helpful assistant.' }],
    text: null,
    input_schema: { type: 'object', properties: {}, required: [] },
    output: { mode: 'text', schema: null },
    tools: [],
    tool_choice: 'auto',
    default_model: null,
  };
}

/** Extract `{{variable}}` names referenced anywhere in a prompt's templates. */
export function extractVariables(content: PromptContent): string[] {
  const found = new Set<string>();
  const scan = (s: string | null | undefined) => {
    if (!s) return;
    const re = /\{\{\s*([a-zA-Z_][a-zA-Z0-9_.]*)\s*\}\}/g;
    let m: RegExpExecArray | null;
    while ((m = re.exec(s)) !== null) {
      if (m[1]) found.add(m[1]);
    }
  };
  if (content.kind === 'chat') {
    for (const msg of content.messages) scan(msg.content);
  } else {
    scan(content.text);
  }
  return Array.from(found);
}

/** Deep clone helper used to avoid mutating cached query data. */
export function cloneContent(content: PromptContent): PromptContent {
  return JSON.parse(JSON.stringify(content)) as PromptContent;
}
