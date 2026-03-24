import React, { useEffect, useMemo, useState } from 'react';
import {
  Alert,
  Badge,
  Button,
  Card,
  ConfigProvider,
  Descriptions,
  Empty,
  Input,
  Layout,
  List,
  Select,
  Space,
  Spin,
  Table,
  Tag,
  Tabs,
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
  if (!raw) {
    return [createSession()];
  }
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
  const [forcedDomain, setForcedDomain] = useState<string | undefined>(undefined);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    saveSessions(sessions);
  }, [sessions]);

  useEffect(() => {
    fetch('/api/meta')
      .then((res) => res.json())
      .then((data: MetaResponse) => {
        setMeta(data);
      })
      .catch((err) => {
        setError(`Khong tai duoc metadata demo: ${String(err)}`);
      });
  }, []);

  const activeSession = useMemo(
    () => sessions.find((session) => session.id === activeSessionId) ?? sessions[0],
    [sessions, activeSessionId],
  );

  const activeResult = useMemo(() => {
    const assistantMessages = activeSession?.messages.filter((item) => item.role === 'assistant') ?? [];
    return assistantMessages.at(-1)?.result;
  }, [activeSession]);

  const modelLabel = useMemo(() => {
    const modelInfo = activeResult?.model_info;
    if (modelInfo && typeof modelInfo.active_model === 'string') {
      const active = modelInfo.active_model;
      return modelInfo.used_fallback ? `${active} fallback` : active;
    }
    if (meta?.models.primary_model) {
      return meta.models.primary_model;
    }
    return 'loading...';
  }, [activeResult, meta]);

  const createNewSession = () => {
    const next = createSession();
    setSessions((prev) => [next, ...prev]);
    setActiveSessionId(next.id);
    setError(null);
  };

  const handleSubmit = async () => {
    const message = input.trim();
    if (!message || loading || !activeSession) {
      return;
    }

    const userMessage: Message = {
      id: crypto.randomUUID(),
      role: 'user',
      content: message,
    };

    const nextSessions = sessions.map((session) =>
      session.id === activeSession.id
        ? {
            ...session,
            title: session.messages.length === 0 ? message.slice(0, 40) : session.title,
            messages: [...session.messages, userMessage],
            updatedAt: new Date().toISOString(),
          }
        : session,
    );
    setSessions(nextSessions);
    setInput('');
    setLoading(true);
    setError(null);

    try {
      const res = await fetch('/api/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          message,
          forced_domain: forcedDomain,
        }),
      });
      const data = (await res.json()) as ChatApiResponse;
      const assistantMessage: Message = {
        id: crypto.randomUUID(),
        role: 'assistant',
        content: data.assistant_message,
        result: data.result,
      };

      setSessions((prev) =>
        prev.map((session) =>
          session.id === activeSession.id
            ? {
                ...session,
                messages: [...session.messages, assistantMessage],
                updatedAt: new Date().toISOString(),
              }
            : session,
        ),
      );
    } catch (err) {
      setError(`Gui tin that bai: ${String(err)}`);
    } finally {
      setLoading(false);
    }
  };

  return (
    <ConfigProvider {...configProps}>
      <Layout className="app-shell">
        <Sider width={280} className="history-pane">
          <div className="pane-header">
            <div>
              <Text className="eyebrow">Conversation History</Text>
              <Title level={4} className="pane-title">
                Demo sessions
              </Title>
            </div>
            <Button type="primary" onClick={createNewSession}>
              New chat
            </Button>
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

        <Content className="center-pane">
          <div className="chat-header">
            <div>
              <Text className="eyebrow">Text2SQL Demo</Text>
              <Title level={2} className="hero-title">
                Chatbot quan sat duoc toan bo pipeline
              </Title>
              <Paragraph className="hero-copy">
                Demo nay chay `demo_mode`: van route domain, rank intent/schema, build prompt va sinh SQL,
                nhung ket qua Step 7 duoc luu local cache thay vi goi DB that.
              </Paragraph>
            </div>
            <Card size="small" className="model-card">
              <Space direction="vertical" size={4}>
                <Text type="secondary">Current model</Text>
                <Tag color="default" className="model-tag">
                  {modelLabel}
                </Tag>
                {meta?.models.fallback_model ? (
                  <Text type="secondary">Fallback: {meta.models.fallback_model}</Text>
                ) : null}
              </Space>
            </Card>
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
                    {message.result ? (
                      <Space wrap size={[8, 8]}>
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
              <Empty
                description="Chua co tin nhan nao. Thu hoi mot cau banking hoac HRM de xem domain router va prompt panel."
              />
            )}
            {loading ? (
              <div className="loading-block">
                <Spin />
              </div>
            ) : null}
          </div>

          <Card className="composer-card">
            <Space direction="vertical" size={12} style={{ width: '100%' }}>
              <Space wrap size={[8, 8]}>
                <Badge color="#18181b" text={`Model: ${modelLabel}`} />
                <Select
                  allowClear
                  placeholder="Force domain"
                  style={{ width: 180 }}
                  value={forcedDomain}
                  onChange={(value) => setForcedDomain(value)}
                  options={(meta?.domains ?? []).map((item) => ({
                    label: item.display_name,
                    value: item.domain_id,
                  }))}
                />
              </Space>
              <Input.TextArea
                value={input}
                onChange={(event) => setInput(event.target.value)}
                rows={4}
                placeholder="Nhap cau hoi demo... vi du: Liet ke nhan vien thuoc phong kinh doanh"
                onPressEnter={(event) => {
                  if (!event.shiftKey) {
                    event.preventDefault();
                    void handleSubmit();
                  }
                }}
              />
              <div className="composer-actions">
                <Text type="secondary">
                  Shift+Enter de xuong dong, Enter de gui.
                </Text>
                <Button type="primary" onClick={() => void handleSubmit()} loading={loading}>
                  Send
                </Button>
              </div>
            </Space>
          </Card>
        </Content>

        <Sider width={380} className="debug-pane">
          <div className="pane-header">
            <div>
              <Text className="eyebrow">Prompt Inspector</Text>
              <Title level={4} className="pane-title">
                Debug context
              </Title>
            </div>
          </div>

          {activeResult ? (
            <Tabs
              defaultActiveKey="prompt"
              items={[
                {
                  key: 'prompt',
                  label: 'Prompt',
                  children: (
                    <Card size="small">
                      <Paragraph className="code-panel">
                        {String(activeResult.debug?.prompt || activeResult.debug?.template_sql || 'Template-first mode, khong co prompt LLM.')}
                      </Paragraph>
                    </Card>
                  ),
                },
                {
                  key: 'context',
                  label: 'Context',
                  children: (
                    <Space direction="vertical" size={12} style={{ width: '100%' }}>
                      <Descriptions column={1} size="small" bordered>
                        <Descriptions.Item label="Domain">{String(activeResult.domain ?? 'N/A')}</Descriptions.Item>
                        <Descriptions.Item label="Candidate domains">
                          {String((activeResult.candidate_domains ?? []).join(', ') || 'N/A')}
                        </Descriptions.Item>
                        <Descriptions.Item label="Intent">
                          {String(activeResult.intent_name ?? activeResult.intent ?? 'N/A')}
                        </Descriptions.Item>
                        <Descriptions.Item label="Tables">
                          {String((activeResult.tables ?? []).join(', ') || 'N/A')}
                        </Descriptions.Item>
                        <Descriptions.Item label="Model">
                          {String((activeResult.model_info?.active_model as string) ?? modelLabel)}
                        </Descriptions.Item>
                      </Descriptions>
                      <Card size="small" title="Schema description">
                        <Paragraph className="code-panel">
                          {String(activeResult.debug?.schema_description || 'N/A')}
                        </Paragraph>
                      </Card>
                      <Card size="small" title="Entities">
                        <Paragraph className="code-panel">
                          {JSON.stringify(activeResult.debug?.entities ?? {}, null, 2)}
                        </Paragraph>
                      </Card>
                    </Space>
                  ),
                },
                {
                  key: 'result',
                  label: 'Result',
                  children: (
                    <Space direction="vertical" size={12} style={{ width: '100%' }}>
                      <Card size="small" title="SQL">
                        <Paragraph className="code-panel">{String(activeResult.sql || 'N/A')}</Paragraph>
                      </Card>
                      <Card size="small" title="Timing / trace">
                        <Paragraph className="code-panel">
                          {JSON.stringify(
                            {
                              validator: activeResult.validator,
                              timing: activeResult.timing,
                              domain_routing: activeResult.debug?.domain_routing,
                            },
                            null,
                            2,
                          )}
                        </Paragraph>
                      </Card>
                      {activeResult.result_data?.length ? (
                        <Table
                          size="small"
                          pagination={false}
                          rowKey={(_, index) => String(index)}
                          columns={buildColumns(activeResult.result_data)}
                          dataSource={activeResult.result_data}
                          scroll={{ x: true }}
                        />
                      ) : null}
                    </Space>
                  ),
                },
              ]}
            />
          ) : (
            <Empty description="Gui mot cau hoi de xem prompt, schema, intent va SQL." />
          )}
        </Sider>
      </Layout>
    </ConfigProvider>
  );
}
