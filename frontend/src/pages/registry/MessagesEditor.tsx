import type { PromptContent, PromptMessage, PromptRole } from '../../api/types';

interface MessagesEditorProps {
  content: PromptContent;
  disabled?: boolean;
  onChange: (content: PromptContent) => void;
}

const ROLES: PromptRole[] = ['system', 'user', 'assistant'];

/**
 * Editor for a chat prompt's message list (role + multiline content) with
 * add / remove / reorder controls, or a single textarea for text prompts.
 */
export function MessagesEditor({ content, disabled, onChange }: MessagesEditorProps) {
  const setMessages = (messages: PromptMessage[]) =>
    onChange({ ...content, messages });

  const updateMessage = (index: number, patch: Partial<PromptMessage>) => {
    const next = content.messages.map((m, i) => (i === index ? { ...m, ...patch } : m));
    setMessages(next);
  };

  const addMessage = () =>
    setMessages([...content.messages, { role: 'user', content: '' }]);

  const removeMessage = (index: number) =>
    setMessages(content.messages.filter((_, i) => i !== index));

  const move = (index: number, dir: -1 | 1) => {
    const target = index + dir;
    if (target < 0 || target >= content.messages.length) return;
    const next = [...content.messages];
    const a = next[index]!;
    const b = next[target]!;
    next[index] = b;
    next[target] = a;
    setMessages(next);
  };

  if (content.kind === 'text') {
    return (
      <div className="messages-editor">
        <label className="field-label">Prompt text</label>
        <textarea
          className="msg__textarea"
          rows={12}
          disabled={disabled}
          value={content.text ?? ''}
          spellCheck={false}
          placeholder="Enter prompt text with {{variables}}…"
          onChange={(e) => onChange({ ...content, text: e.target.value })}
        />
      </div>
    );
  }

  return (
    <div className="messages-editor">
      {content.messages.map((msg, i) => (
        <div className="msg" key={i}>
          <div className="msg__head">
            <select
              className="msg__role"
              value={msg.role}
              disabled={disabled}
              onChange={(e) => updateMessage(i, { role: e.target.value as PromptRole })}
            >
              {ROLES.map((r) => (
                <option key={r} value={r}>
                  {r}
                </option>
              ))}
            </select>
            <div className="msg__actions">
              <button
                className="btn btn--icon"
                disabled={disabled || i === 0}
                onClick={() => move(i, -1)}
                title="Move up"
              >
                ↑
              </button>
              <button
                className="btn btn--icon"
                disabled={disabled || i === content.messages.length - 1}
                onClick={() => move(i, 1)}
                title="Move down"
              >
                ↓
              </button>
              <button
                className="btn btn--icon btn--danger"
                disabled={disabled || content.messages.length === 1}
                onClick={() => removeMessage(i)}
                title="Remove"
              >
                ✕
              </button>
            </div>
          </div>
          <textarea
            className="msg__textarea"
            rows={5}
            disabled={disabled}
            value={msg.content}
            spellCheck={false}
            placeholder="Message content with {{variables}}…"
            onChange={(e) => updateMessage(i, { content: e.target.value })}
          />
        </div>
      ))}
      {!disabled && (
        <button className="btn btn--ghost btn--sm" onClick={addMessage}>
          + Add message
        </button>
      )}
    </div>
  );
}
