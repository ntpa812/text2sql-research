import React, { useEffect, useMemo, useState } from 'react';
import {
  Alert,
  Button,
  Card,
  Collapse,
  ConfigProvider,
  Empty,
  Input,
  Layout,
  List,
  Space,
  Spin,
  Table,
  Tag,
  Typography,
} from 'antd';
import useShadcnTheme from './shadcnTheme';

const { Sider, Content } = Layout;
const { Title, Text, Paragraph } = Typography;

type MetaResponse = {
  models: {
    backend: string;
    primary_model: string;
    fallback_model?: string;
  };
  domains: Array<{
    domain_id: string;
    display_name: string;
    description: string;
  }>;
};

type ResultPayload = {
  question: string;
  domain?: string | null;
  candidate_domains?: string[];
  tables?: string[];
  intent?: string | null;
  intent_name?: string | null;
  sql?: string | null;
  rows?: number;
  validator?: string;
  error?: string | null;
  explain?: string;
  result_data?: Array<Record<string, unknown>>;
  model_info?: Record<string, unknown>;
  debug?: Record<string, unknown>;
  timing?: Record<string, number>;
};

type ChatApiResponse = {
  assistant_message: string;
  result: ResultPayload;
};

type Message = {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  result?: ResultPayload;
};

type Session = {
  id: string;
  title: string;
  messages: Message[];
  updatedAt: string;
};

const SESSION_STORAGE_KEY = 'text2sql-demo-sessions';

function createSession(): Session {
  return {
    id: crypto.randomUUID(),
    title: 'New demo',
    messages: [],
    updatedAt: new Date().toISOString(),
  };
}

function loadSessions(): Session[] {
  const raw = window.localStorage.getItem(SESSION_STORAGE_KEY);
  if (!raw) return [createSession()];
  try {
    const parsed = JSON.parse(raw) as Session[];
    return parsed.length ? parsed : [createSession()];
  } catch {
    return [createSession()];
  }
}

function saveSessions(sessions: Session[]) {
  window.localStorage.setItem(SESSION_STORAGE_KEY, JSON.stringify(sessions));
}

function buildColumns(rows: Array<Record<string, unknown>>) {
  const first = rows[0];
  return Object.keys(first).map((key) => ({
    title: key,
    dataIndex: key,
    key,
    ellipsis: true,
    render: (value: unknown) => String(value ?? ''),
  }));
}

export default function App() {
  const configProps = useShadcnTheme();
  const [meta, setMeta] = useState<MetaResponse | null>(null);
  const [sessions, setSessions] = useState<Session[]>(() => loadSessions());
  const [activeSessionId, setActiveSessionId] = useState<string>(() => loadSessions()[0].id);
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    saveSessions(sessions);
  }, [sessions]);

  useEffect(() => {
    fetch('/api/meta')
      .then((res) => res.json())
      .then((data: MetaResponse) => setMeta(data))
      .catch((err) => setError(`Không tải được metadata demo: ${String(err)}`));
  }, []);

  const activeSession = useMemo(
    () => sessions.find((s) => s.id === activeSessionId) ?? sessions[0],
    [sessions, activeSessionId],
  );

  const activeResult = useMemo(() => {
    const msgs = activeSession?.messages.filter((m) => m.role === 'assistant') ?? [];
    return msgs.length ? msgs[msgs.length - 1].result : undefined;
  }, [activeSession]);

  const modelLabel = useMemo(() => {
    const modelInfo = activeResult?.model_info;
    if (modelInfo && typeof modelInfo.active_model === 'string') {
      return modelInfo.used_fallback ? `${modelInfo.active_model} (fallback)` : String(modelInfo.active_model);
    }
    return meta?.models.primary_model ?? 'loading...';
  }, [activeResult, meta]);

  const createNewSession = () => {
    const next = createSession();
    setSessions((prev) => [next, ...prev]);
    setActiveSessionId(next.id);
    setError(null);
  };

  const handleSubmit = async () => {
    const message = input.trim();
    if (!message || loading || !activeSession) return;

    const userMessage: Message = { id: crypto.randomUUID(), role: 'user', content: message };
    setSessions((prev) =>
      prev.map((s) =>
        s.id === activeSession.id
          ? {
              ...s,
              title: s.messages.length === 0 ? message.slice(0, 40) : s.title,
              messages: [...s.messages, userMessage],
              updatedAt: new Date().toISOString(),
            }
          : s,
      ),
    );
    setInput('');
    setLoading(true);
    setError(null);

    try {
      const res = await fetch('/api/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ message }),
      });
      const data = (await res.json()) as ChatApiResponse;
      const assistantMessage: Message = {
        id: crypto.randomUUID(),
        role: 'assistant',
        content: data.assistant_message,
        result: data.result,
      };
      setSessions((prev) =>
        prev.map((s) =>
          s.id === activeSession.id
            ? { ...s, messages: [...s.messages, assistantMessage], updatedAt: new Date().toISOString() }
            : s,
        ),
      );
    } catch (err) {
      setError(`Gửi tin thất bại: ${String(err)}`);
    } finally {
      setLoading(false);
    }
  };

  // ── Debug panel collapse items ────────────────────────────────────────────
  const debugCollapseItems = activeResult
    ? [
        {
          key: 'domain',
          label: (
            <Space size={6}>
              <Text strong>Domain</Text>
              {activeResult.domain ? (
                <Tag color="blue">{activeResult.domain}</Tag>
              ) : (
                <Tag color="default">N/A</Tag>
              )}
            </Space>
          ),
          children: (
            <Space direction="vertical" size={6} style={{ width: '100%' }}>
              <div>
                <Text type="secondary" style={{ fontSize: 12 }}>Domain đã chọn</Text>
                <Paragraph className="code-panel" style={{ marginTop: 4 }}>
                  {activeResult.domain ?? 'N/A'}
                </Paragraph>
              </div>
              <div>
                <Text type="secondary" style={{ fontSize: 12 }}>Các domain ứng viên</Text>
                <Paragraph className="code-panel" style={{ marginTop: 4 }}>
                  {(activeResult.candidate_domains ?? []).join(', ') || 'N/A'}
                </Paragraph>
              </div>
              <div>
                <Text type="secondary" style={{ fontSize: 12 }}>Intent</Text>
                <Paragraph className="code-panel" style={{ marginTop: 4 }}>
                  {activeResult.intent_name ?? activeResult.intent ?? 'N/A'}
                </Paragraph>
              </div>
              {activeResult.debug?.domain_routing ? (
                <div>
                  <Text type="secondary" style={{ fontSize: 12 }}>Routing scores</Text>
                  <Paragraph className="code-panel" style={{ marginTop: 4 }}>
                    {JSON.stringify(activeResult.debug.domain_routing, null, 2)}
                  </Paragraph>
                </div>
              ) : null}
            </Space>
          ),
        },
        {
          key: 'schema',
          label: (
            <Space size={6}>
              <Text strong>Schema</Text>
              {(activeResult.tables ?? []).length > 0 ? (
                <Tag color="geekblue">{(activeResult.tables ?? []).join(', ')}</Tag>
              ) : (
                <Tag color="default">N/A</Tag>
              )}
            </Space>
          ),
          children: (
            <Space direction="vertical" size={6} style={{ width: '100%' }}>
              <div>
                <Text type="secondary" style={{ fontSize: 12 }}>Bảng được sử dụng</Text>
                <Paragraph className="code-panel" style={{ marginTop: 4 }}>
                  {(activeResult.tables ?? []).join(', ') || 'N/A'}
                </Paragraph>
              </div>
              {activeResult.debug?.schema_description ? (
                <div>
                  <Text type="secondary" style={{ fontSize: 12 }}>Schema description</Text>
                  <Paragraph className="code-panel" style={{ marginTop: 4 }}>
                    {String(activeResult.debug.schema_description)}
                  </Paragraph>
                </div>
              ) : null}
              {activeResult.debug?.entities ? (
                <div>
                  <Text type="secondary" style={{ fontSize: 12 }}>Entities</Text>
                  <Paragraph className="code-panel" style={{ marginTop: 4 }}>
                    {JSON.stringify(activeResult.debug.entities, null, 2)}
                  </Paragraph>
                </div>
              ) : null}
            </Space>
          ),
        },
        {
          key: 'sql',
          label: (
            <Space size={6}>
              <Text strong>SQL Query</Text>
              <Tag color={activeResult.validator === 'PASS' ? 'green' : 'orange'}>
                {activeResult.validator ?? '—'}
              </Tag>
              <Tag>{activeResult.rows ?? 0} rows</Tag>
            </Space>
          ),
          children: (
            <Space direction="vertical" size={6} style={{ width: '100%' }}>
              <div>
                <Text type="secondary" style={{ fontSize: 12 }}>SQL sinh ra</Text>
                <Paragraph className="code-panel" style={{ marginTop: 4 }}>
                  {activeResult.sql ?? 'N/A'}
                </Paragraph>
              </div>
              {activeResult.timing ? (
                <div>
                  <Text type="secondary" style={{ fontSize: 12 }}>Timing (ms)</Text>
                  <Paragraph className="code-panel" style={{ marginTop: 4 }}>
                    {JSON.stringify(activeResult.timing, null, 2)}
                  </Paragraph>
                </div>
              ) : null}
              {activeResult.result_data?.length ? (
                <Table
                  size="small"
                  pagination={false}
                  rowKey={(_, idx) => String(idx)}
                  columns={buildColumns(activeResult.result_data)}
                  dataSource={activeResult.result_data}
                  scroll={{ x: true }}
                />
              ) : null}
            </Space>
          ),
        },
      ]
    : [];

  return (
    <ConfigProvider {...configProps}>
      <Layout className="app-shell">

        {/* ── Left: session history ──────────────────────────────────────── */}
        <Sider width={220} className="history-pane">
          <div className="pane-header">
            <Title level={4} className="pane-title">Demo sessions</Title>
            <Button type="primary" onClick={createNewSession}>New chat</Button>
          </div>
          <List
            dataSource={sessions}
            renderItem={(session) => (
              <List.Item
                className={`history-item ${session.id === activeSessionId ? 'active' : ''}`}
                onClick={() => setActiveSessionId(session.id)}
              >
                <div>
                  <Text strong>{session.title}</Text>
                  <div>
                    <Text type="secondary">{new Date(session.updatedAt).toLocaleString()}</Text>
                  </div>
                </div>
              </List.Item>
            )}
          />
        </Sider>

        {/* ── Center: chat ───────────────────────────────────────────────── */}
        <Content className="center-pane">
          <div className="chat-header">
            <Title level={3} className="hero-title">Text2SQL Demo</Title>
          </div>

          {error ? <Alert type="error" showIcon message={error} className="main-alert" /> : null}

          <div className="messages-scroll">
            {activeSession?.messages.length ? (
              activeSession.messages.map((message) => (
                <div
                  key={message.id}
                  className={`message-row ${message.role === 'user' ? 'user' : 'assistant'}`}
                >
                  <Card className={`message-card ${message.role}`}>
                    <Text className="message-role">
                      {message.role === 'user' ? 'User' : 'Assistant'}
                    </Text>
                    <Paragraph className="message-content">{message.content}</Paragraph>

                    {/* Bot: show explain below the main reply */}
                    {message.role === 'assistant' && message.result?.explain ? (
                      <div className="explain-block">
                        <Text type="secondary" style={{ fontSize: 12, display: 'block', marginBottom: 4 }}>
                          Giải thích
                        </Text>
                        <Paragraph className="explain-text">{message.result.explain}</Paragraph>
                      </div>
                    ) : null}

                    {/* Summary tags */}
                    {message.result ? (
                      <Space wrap size={[6, 6]} style={{ marginTop: 8 }}>
                        <Tag>{message.result.domain ?? 'N/A'}</Tag>
                        <Tag color="blue">{message.result.intent_name ?? message.result.intent ?? 'No intent'}</Tag>
                        <Tag color={message.result.validator === 'PASS' ? 'green' : 'orange'}>
                          {message.result.validator}
                        </Tag>
                        <Tag>{message.result.rows ?? 0} rows</Tag>
                      </Space>
                    ) : null}
                  </Card>
                </div>
              ))
            ) : (
              <Empty description="Chưa có tin nhắn. Thử hỏi về banking hoặc HRM để xem domain router và prompt panel." />
            )}
            {loading ? (
              <div className="loading-block"><Spin /></div>
            ) : null}
          </div>

          {/* ── Composer ── */}
          <Card className="composer-card">
            <div className="composer-textarea-wrap">
              <Input.TextArea
                value={input}
                onChange={(e) => setInput(e.target.value)}
                rows={3}
                placeholder="Nhập câu hỏi demo... ví dụ: Liệt kê nhân viên thuộc phòng kinh doanh"
                onPressEnter={(e) => {
                  if (!e.shiftKey) { e.preventDefault(); void handleSubmit(); }
                }}
              />
              <div className="composer-model-chip">
                <Tag color="default" className="model-tag">{modelLabel}</Tag>
              </div>
            </div>
            <div className="composer-actions" style={{ marginTop: 8 }}>
              <Text type="secondary" style={{ fontSize: 12 }}>
                Shift+Enter để xuống dòng · Enter để gửi
              </Text>
              <Button type="primary" onClick={() => void handleSubmit()} loading={loading}>
                Gửi
              </Button>
            </div>
          </Card>
        </Content>

        {/* ── Right: pipeline inspector ─────────────────────────────────── */}
        <Sider width={360} className="debug-pane">
          <div className="pane-header" style={{ marginBottom: 16 }}>
            <Title level={4} className="pane-title">Pipeline Inspector</Title>
          </div>

          {activeResult ? (
            <Collapse
              defaultActiveKey={['domain', 'sql']}
              className="inspector-collapse"
              items={debugCollapseItems}
            />
          ) : (
            <Empty description="Gửi một câu hỏi để xem domain, schema và SQL đã sinh ra." />
          )}
        </Sider>

      </Layout>
    </ConfigProvider>
  );
}
