"use client";

import { Fragment, useEffect, useRef, useState, type PointerEvent as ReactPointerEvent, type ReactNode } from "react";
import Image from "next/image";
import type { CopilotCitation, CopilotContext, CopilotMessage, UiAction } from "./copilot-types";
import chatbotLogo from "@/chatbot-logo.png";

type Props = { open: boolean; context: CopilotContext; onClose: () => void; onAction: (action: UiAction) => void; onUndo?: () => void; canUndo?: boolean; onPanelDragStart?: (event: ReactPointerEvent<HTMLElement>) => void };

function endpoint() {
  return "/api/copilot/chat";
}

function parseSseChunk(chunk: string) {
  const event = chunk.match(/^event:\s*(.+)$/m)?.[1] ?? "message";
  const raw = chunk.match(/^data:\s*(.+)$/m)?.[1];
  if (!raw) return null;
  try { return { event, data: JSON.parse(raw) as Record<string, unknown> }; } catch { return null; }
}

function renderInlineMarkdown(text: string, keyPrefix: string): ReactNode[] {
  const tokenPattern = /(\[[^\]]+\]\(https?:\/\/[^)]+\)|\*\*[^*]+\*\*|\*[^*]+\*|`[^`]+`)/g;
  const nodes: ReactNode[] = [];
  let lastIndex = 0;
  let match: RegExpExecArray | null;
  let index = 0;

  while ((match = tokenPattern.exec(text)) !== null) {
    if (match.index > lastIndex) nodes.push(text.slice(lastIndex, match.index));
    const token = match[0];
    const link = token.match(/^\[([^\]]+)\]\((https?:\/\/[^)]+)\)$/);
    if (link) nodes.push(<a key={`${keyPrefix}-${index}`} href={link[2]} target="_blank" rel="noreferrer">{link[1]}</a>);
    else if (token.startsWith("**")) nodes.push(<strong key={`${keyPrefix}-${index}`}>{token.slice(2, -2)}</strong>);
    else if (token.startsWith("*")) nodes.push(<em key={`${keyPrefix}-${index}`}>{token.slice(1, -1)}</em>);
    else nodes.push(<code key={`${keyPrefix}-${index}`}>{token.slice(1, -1)}</code>);
    lastIndex = match.index + token.length;
    index += 1;
  }

  if (lastIndex < text.length) nodes.push(text.slice(lastIndex));
  return nodes;
}

function isTableSeparator(line: string) {
  return /^\s*\|?\s*:?-{3,}:?\s*(\|\s*:?-{3,}:?\s*)+\|?\s*$/.test(line);
}

function splitTableRow(line: string) {
  const trimmed = line.trim().replace(/^\|/, "").replace(/\|$/, "");
  return trimmed.split("|").map((cell) => cell.trim());
}

function MarkdownMessage({ text }: { text: string }) {
  const lines = text.split(/\r?\n/);
  const blocks: ReactNode[] = [];
  let index = 0;
  let blockIndex = 0;

  while (index < lines.length) {
    const line = lines[index];
    if (!line.trim()) { index += 1; continue; }

    if (/^\s*```/.test(line)) {
      const language = line.trim().slice(3).trim();
      const code: string[] = [];
      index += 1;
      while (index < lines.length && !/^\s*```/.test(lines[index])) {
        code.push(lines[index]);
        index += 1;
      }
      if (index < lines.length) index += 1;
      blocks.push(<pre key={`code-${blockIndex}`}><code className={language ? `language-${language}` : undefined}>{code.join("\n")}</code></pre>);
      blockIndex += 1;
      continue;
    }

    if (index + 1 < lines.length && line.includes("|") && isTableSeparator(lines[index + 1])) {
      const headers = splitTableRow(line);
      index += 2;
      const rows: string[][] = [];
      while (index < lines.length && lines[index].trim() && lines[index].includes("|")) {
        rows.push(splitTableRow(lines[index]));
        index += 1;
      }
      blocks.push(<div className="copilot-table-wrap" key={`table-${blockIndex}`}><table><thead><tr>{headers.map((header, headerIndex) => <th key={`table-head-${headerIndex}`}>{renderInlineMarkdown(header, `table-head-${blockIndex}-${headerIndex}`)}</th>)}</tr></thead><tbody>{rows.map((row, rowIndex) => <tr key={`table-row-${rowIndex}`}>{headers.map((_, cellIndex) => <td key={`table-cell-${rowIndex}-${cellIndex}`}>{renderInlineMarkdown(row[cellIndex] ?? "", `table-cell-${blockIndex}-${rowIndex}-${cellIndex}`)}</td>)}</tr>)}</tbody></table></div>);
      blockIndex += 1;
      continue;
    }

    if (/^\s*([-*_])\s*\1\s*\1(?:\s*\1)*\s*$/.test(line)) {
      blocks.push(<hr key={`rule-${blockIndex}`} />);
      index += 1;
      blockIndex += 1;
      continue;
    }

    if (/^\s*>\s?/.test(line)) {
      const quoteLines: string[] = [];
      while (index < lines.length && /^\s*>\s?/.test(lines[index])) {
        quoteLines.push(lines[index].replace(/^\s*>\s?/, ""));
        index += 1;
      }
      blocks.push(<blockquote key={`quote-${blockIndex}`}>{quoteLines.map((quoteLine, quoteIndex) => <Fragment key={`quote-${blockIndex}-${quoteIndex}`}>{quoteIndex > 0 && <br />}{renderInlineMarkdown(quoteLine, `quote-${blockIndex}-${quoteIndex}`)}</Fragment>)}</blockquote>);
      blockIndex += 1;
      continue;
    }

    const heading = line.match(/^(#{1,3})\s+(.+)$/);
    if (heading) {
      blocks.push(<h4 key={`heading-${blockIndex}`}>{renderInlineMarkdown(heading[2], `heading-${blockIndex}`)}</h4>);
      index += 1;
      blockIndex += 1;
      continue;
    }

    if (/^\s*[-*]\s+/.test(line)) {
      const items: string[] = [];
      while (index < lines.length && /^\s*[-*]\s+/.test(lines[index])) {
        items.push(lines[index].replace(/^\s*[-*]\s+/, ""));
        index += 1;
      }
      blocks.push(<ul key={`list-${blockIndex}`}>{items.map((item, itemIndex) => <li key={`list-${blockIndex}-${itemIndex}`}>{renderInlineMarkdown(item, `list-${blockIndex}-${itemIndex}`)}</li>)}</ul>);
      blockIndex += 1;
      continue;
    }

    if (/^\s*\d+[.)]\s+/.test(line)) {
      const items: string[] = [];
      while (index < lines.length && /^\s*\d+[.)]\s+/.test(lines[index])) {
        items.push(lines[index].replace(/^\s*\d+[.)]\s+/, ""));
        index += 1;
      }
      blocks.push(<ol key={`ordered-list-${blockIndex}`}>{items.map((item, itemIndex) => <li key={`ordered-list-${blockIndex}-${itemIndex}`}>{renderInlineMarkdown(item, `ordered-list-${blockIndex}-${itemIndex}`)}</li>)}</ol>);
      blockIndex += 1;
      continue;
    }

    const paragraph: string[] = [];
    while (index < lines.length && lines[index].trim() && !/^(#{1,3})\s+/.test(lines[index]) && !/^\s*[-*]\s+/.test(lines[index])) {
      paragraph.push(lines[index]);
      index += 1;
    }
    blocks.push(<p key={`paragraph-${blockIndex}`}>{paragraph.map((paragraphLine, lineIndex) => <Fragment key={`paragraph-${blockIndex}-${lineIndex}`}>{lineIndex > 0 && <br />}{renderInlineMarkdown(paragraphLine, `paragraph-${blockIndex}-${lineIndex}`)}</Fragment>)}</p>);
    blockIndex += 1;
  }

  return <div className="copilot-markdown">{blocks}</div>;
}

function progressLabel(stage: string) {
  const labels: Record<string, string> = {
    reading_map_context: "Mình đang đọc ngữ cảnh bản đồ",
    retrieving_sources: "Mình đang tìm nguồn chính thức",
    calling_model: "Mình đang phân tích",
    blocked: "Mình đang kiểm tra yêu cầu",
  };
  return labels[stage] ?? "Mình đang kiểm tra dữ liệu";
}

function safeAction(value: unknown, contextVersion: number): UiAction | null {
  if (!value || typeof value !== "object") return null;
  const candidate = value as { action?: unknown; arguments?: unknown };
  const allowed = ["set_radar_band", "toggle_layer", "select_scene", "set_timeline_index", "open_region_stats", "open_pixel_inspector"];
  if (typeof candidate.action !== "string" || !allowed.includes(candidate.action) || !candidate.arguments || typeof candidate.arguments !== "object") return null;
  const argumentsValue = candidate.arguments as Record<string, unknown>;
  if (argumentsValue.contextVersion !== contextVersion) return null;
  if (candidate.action === "set_radar_band" && !["HHHH", "HVHV", "COMPOSITE"].includes(String(argumentsValue.band))) return null;
  return { action: candidate.action as UiAction["action"], arguments: argumentsValue };
}

const COMMON_QUESTIONS = [
  "HVHV là gì?",
  "HHHH và HVHV khác nhau thế nào?",
  "Scene này có dữ liệu không?",
  "Mở thống kê khu vực",
];

export function CopilotPanel({ open, context, onClose, onAction, onUndo, canUndo = false, onPanelDragStart }: Props) {
  const [messages, setMessages] = useState<CopilotMessage[]>([]);
  const [input, setInput] = useState("");
  const [sending, setSending] = useState(false);
  const abortRef = useRef<AbortController | null>(null);

  useEffect(() => () => abortRef.current?.abort(), []);
  useEffect(() => { abortRef.current?.abort(); setSending(false); }, [context.contextVersion]);

  if (!open) return null;

  async function send(preset?: string) {
    const message = (preset ?? input).trim();
    if (!message || sending) return;
    const userMessage: CopilotMessage = { id: `${Date.now()}-user`, role: "user", text: message };
    const assistantId = `${Date.now()}-assistant`;
    setMessages((current) => [...current, userMessage, { id: assistantId, role: "assistant", text: "", progress: "Mình đang đọc bản đồ…" }]);
    setInput("");
    setSending(true);
    const controller = new AbortController();
    abortRef.current = controller;
    try {
      const response = await fetch(endpoint(), { method: "POST", headers: { "Content-Type": "application/json", Accept: "text/event-stream" }, body: JSON.stringify({ conversationId: "browser-session", message, mapContext: context }), signal: controller.signal });
      if (!response.ok || !response.body) throw new Error(`Copilot request failed: ${response.status}`);
      const reader = response.body.getReader();
      const decoder = new TextDecoder();
      let buffer = "";
      while (true) {
        const result = await reader.read();
        buffer += decoder.decode(result.value ?? new Uint8Array(), { stream: !result.done });
        const chunks = buffer.split("\n\n");
        buffer = chunks.pop() ?? "";
        for (const chunk of chunks) {
          const parsed = parseSseChunk(chunk);
          if (!parsed) continue;
          if (parsed.event === "token") setMessages((current) => current.map((item) => item.id === assistantId ? { ...item, text: `${item.text}${String(parsed.data.text ?? "")}`, progress: undefined } : item));
          if (parsed.event === "status") setMessages((current) => current.map((item) => item.id === assistantId ? { ...item, progress: progressLabel(String(parsed.data.stage ?? "")) } : item));
          if (parsed.event === "tool") setMessages((current) => current.map((item) => item.id === assistantId ? { ...item, progress: "Mình đang kiểm tra dữ liệu" } : item));
          if (parsed.event === "citation") setMessages((current) => current.map((item) => {
            if (item.id !== assistantId) return item;
            const citation = parsed.data as unknown as CopilotCitation;
            const citations = item.citations ?? [];
            const alreadyShown = citations.some((existing) => existing.canonicalUrl === citation.canonicalUrl || existing.sourceDocumentId === citation.sourceDocumentId);
            return alreadyShown ? item : { ...item, citations: [...citations, citation] };
          }));
          if (parsed.event === "action") {
            const action = safeAction(parsed.data, context.contextVersion);
            if (action) onAction(action);
          }
          if (parsed.event === "done") {
            const actions = Array.isArray(parsed.data.actions) ? parsed.data.actions as unknown as UiAction[] : [];
            const provenance = Array.isArray(parsed.data.provenance) ? parsed.data.provenance as CopilotMessage["provenance"] : undefined;
            setMessages((current) => current.map((item) => item.id === assistantId ? { ...item, text: String(parsed.data.text ?? item.text), status: String(parsed.data.status ?? "UNKNOWN"), actions, provenance, progress: undefined } : item));
          }
          if (parsed.event === "error") setMessages((current) => current.map((item) => item.id === assistantId ? { ...item, text: String(parsed.data.message ?? "Copilot gặp lỗi."), status: "ERROR", progress: undefined } : item));
        }
        if (result.done) break;
      }
    } catch (error) {
      if ((error as Error).name !== "AbortError") setMessages((current) => current.map((item) => item.id === assistantId ? { ...item, text: "Không kết nối được copilot. Map và analytics vẫn hoạt động độc lập.", status: "ERROR", progress: undefined } : item));
    } finally { setSending(false); abortRef.current = null; }
  }

  return (
    <aside className="copilot-panel" aria-label="GalaSEE Assistant">
      <div className="copilot-header" onPointerDown={(event) => { if (!(event.target as HTMLElement).closest("button")) onPanelDragStart?.(event); }}><div className="copilot-title"><span className="copilot-title-avatar"><Image src={chatbotLogo} alt="" aria-hidden="true" width={32} height={32} priority /></span><div><h2>GalaSEE Assistant</h2></div></div><div className="copilot-header-actions"><button className="copilot-undo" onClick={onUndo} disabled={!canUndo} aria-label="Hoàn tác thao tác gần nhất">Hoàn tác</button><button className="copilot-close" onClick={onClose} aria-label="Đóng trợ lý">×</button></div></div>
      <div className="copilot-messages">
        {messages.length === 0 && <div className="copilot-empty"><strong>Hỏi về bản đồ đang xem</strong><div className="copilot-suggestions">{COMMON_QUESTIONS.map((question) => <button key={question} type="button" onClick={() => void send(question)} disabled={sending}>{question}</button>)}</div></div>}
        {messages.map((message) => {
          const provenanceLabels = [...new Set((message.provenance ?? []).filter((item) => item.source !== "OpenRouter").map((item) => String(item.source ?? "")).filter(Boolean))];
          return <div key={message.id} className={`copilot-message ${message.role}`}>{message.text ? <MarkdownMessage text={message.text} /> : <div className="copilot-thinking" role="status" aria-label={message.progress ?? "Đang xử lý"}><span>{message.progress ?? "Đang xử lý"}</span><span className="copilot-dots" aria-hidden="true"><i>.</i><i>.</i><i>.</i></span></div>}{message.provenance && provenanceLabels.length > 0 && <small>Dữ liệu: {provenanceLabels.join(" · ")}</small>}{message.citations?.map((citation) => <a key={`${citation.sourceDocumentId}-${citation.canonicalUrl}`} href={citation.canonicalUrl} target="_blank" rel="noreferrer">Nguồn: {citation.title}</a>)}</div>;
        })}
      </div>
      <div className="copilot-composer"><textarea value={input} onChange={(event) => setInput(event.target.value)} onKeyDown={(event) => { if (event.key === "Enter" && !event.shiftKey) { event.preventDefault(); void send(); } }} placeholder="Hỏi về lớp dữ liệu hoặc scene đang xem…" rows={1} /><button className="copilot-send" aria-label={sending ? "Đang gửi" : "Gửi"} onClick={() => void send()} disabled={sending || !input.trim()}>{sending ? <span className="copilot-send-loading" aria-hidden="true">···</span> : <svg className="copilot-send-icon" viewBox="0 0 24 24" aria-hidden="true"><path d="M3.4 11.2 20.7 3.5a.65.65 0 0 1 .86.8l-6.05 16.2a.65.65 0 0 1-1.2.08l-3.48-6.2-7.1-2.03a.65.65 0 0 1-.33-1.15Z" fill="currentColor" /><path d="m10.65 14.37 4.56-4.28" fill="none" stroke="rgba(255,255,255,.72)" strokeLinecap="round" strokeWidth="1.2" /></svg>}</button></div>
    </aside>
  );
}
