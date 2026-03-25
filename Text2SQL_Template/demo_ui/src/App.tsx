import React, { useEffect, useMemo, useState } from 'react';
import {
  Alert,
  Button,
  Card,
  Collapse,
  ConfigProvider,
  DatePicker,
  Divider,
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
  Tooltip,
  Typography,
} from 'antd';
import {
  ApartmentOutlined,
  CalendarOutlined,
  MenuFoldOutlined,
  MenuUnfoldOutlined,
  MessageOutlined,
  TeamOutlined,
  UserOutlined,
} from '@ant-design/icons';
import useShadcnTheme from './shadcnTheme';

const { Sider, Content } = Layout;
const { Title, Text, Paragraph } = Typography;

// ── Types ─────────────────────────────────────────────────────────────────────

type View = 'chat' | 'hrm';

type MetaResponse = {
  models: { backend: string; primary_model: string; fallback_model?: string };
  domains: Array<{ domain_id: string; display_name: string; description: string }>;
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

type ChatApiResponse = { assistant_message: string; result: ResultPayload };

type Message = {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  result?: ResultPayload;
};

type Session = { id: string; title: string; messages: Message[]; updatedAt: string };

// ── HRM types ─────────────────────────────────────────────────────────────────

type Department = {
  department_id: string;
  department_name: string;
  manager_name: string | null;
  employee_count: number;
};

type Employee = {
  employee_id: string;
  employee_name: string;
  department_name: string;
  job_title: string;
  employment_status: string;
  hire_date: string;
  email: string;
  phone: string;
};

type Attendance = {
  attendance_date: string;
  employee_id: string;
  employee_name: string;
  department_name: string;
  check_in_time: string | null;
  check_out_time: string | null;
  status: string;
};

// ── Session helpers ────────────────────────────────────────────────────────────

const SESSION_KEY = 'text2sql-demo-sessions';

function createSession(): Session {
  return { id: crypto.randomUUID(), title: 'New demo', messages: [], updatedAt: new Date().toISOString() };
}

function loadSessions(): Session[] {
  const raw = window.localStorage.getItem(SESSION_KEY);
  if (!raw) return [createSession()];
  try { const p = JSON.parse(raw) as Session[]; return p.length ? p : [createSession()]; }
  catch { return [createSession()]; }
}

function saveSessions(s: Session[]) { window.localStorage.setItem(SESSION_KEY, JSON.stringify(s)); }

function buildColumns(rows: Array<Record<string, unknown>>) {
  return Object.keys(rows[0]).map((key) => ({
    title: key, dataIndex: key, key, ellipsis: true,
    render: (v: unknown) => String(v ?? ''),
  }));
}

// ── Status badge helper ───────────────────────────────────────────────────────

const STATUS_COLOR: Record<string, string> = {
  ACTIVE: 'green', PROBATION: 'blue', RESIGNED: 'default',
  SUSPENDED: 'red', PRESENT: 'green', LATE: 'orange',
  REMOTE: 'cyan', ABSENT: 'red', ON_LEAVE: 'purple',
};

// ── Main App ──────────────────────────────────────────────────────────────────

export default function App() {
  const configProps = useShadcnTheme();

  // ── Chat state ──────────────────────────────────────────────────────────────
  const [meta, setMeta] = useState<MetaResponse | null>(null);
  const [sessions, setSessions] = useState<Session[]>(() => loadSessions());
  const [activeSessionId, setActiveSessionId] = useState<string>(() => loadSessions()[0].id);
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // ── Nav state ───────────────────────────────────────────────────────────────
  const [view, setView] = useState<View>('chat');
  const [navOpen, setNavOpen] = useState(true);

  // ── HRM state ───────────────────────────────────────────────────────────────
  const [departments, setDepartments] = useState<Department[]>([]);
  const [employees, setEmployees] = useState<Employee[]>([]);
  const [attendance, setAttendance] = useState<Attendance[]>([]);
  const [hrmLoading, setHrmLoading] = useState(false);
  const [hrmTab, setHrmTab] = useState('departments');
  const [filterDept, setFilterDept] = useState<string | undefined>();
  const [filterStatus, setFilterStatus] = useState<string | undefined>();

  // ── Effects ─────────────────────────────────────────────────────────────────
  useEffect(() => { saveSessions(sessions); }, [sessions]);

  useEffect(() => {
    fetch('/api/meta').then((r) => r.json()).then((d: MetaResponse) => setMeta(d))
      .catch((e) => setError(`Không tải được metadata: ${String(e)}`));
  }, []);

  useEffect(() => {
    if (view !== 'hrm') return;
    setHrmLoading(true);
    Promise.all([
      fetch('/api/hrm/departments').then((r) => r.json()),
      fetch('/api/hrm/employees').then((r) => r.json()),
      fetch('/api/hrm/attendance').then((r) => r.json()),
    ]).then(([d, e, a]) => {
      setDepartments((d as { departments: Department[] }).departments);
      setEmployees((e as { employees: Employee[] }).employees);
      setAttendance((a as { attendance: Attendance[] }).attendance);
    }).catch(() => {}).finally(() => setHrmLoading(false));
  }, [view]);

  // ── Derived ─────────────────────────────────────────────────────────────────
  const activeSession = useMemo(
    () => sessions.find((s) => s.id === activeSessionId) ?? sessions[0],
    [sessions, activeSessionId],
  );

  const activeResult = useMemo(() => {
    const msgs = activeSession?.messages.filter((m) => m.role === 'assistant') ?? [];
    return msgs.length ? msgs[msgs.length - 1].result : undefined;
  }, [activeSession]);

  const modelLabel = useMemo(() => {
    const mi = activeResult?.model_info;
    if (mi && typeof mi.active_model === 'string')
      return mi.used_fallback ? `${mi.active_model} (fallback)` : String(mi.active_model);
    return meta?.models.primary_model ?? 'loading...';
  }, [activeResult, meta]);

  const filteredEmployees = useMemo(() => employees.filter((e) => {
    if (filterDept && e.department_name !== filterDept) return false;
    if (filterStatus && e.employment_status !== filterStatus) return false;
    return true;
  }), [employees, filterDept, filterStatus]);

  // ── Chat handlers ────────────────────────────────────────────────────────────
  const createNewSession = () => {
    const next = createSession();
    setSessions((prev) => [next, ...prev]);
    setActiveSessionId(next.id);
    setError(null);
  };

  const handleSubmit = async () => {
    const message = input.trim();
    if (!message || loading || !activeSession) return;
    const userMsg: Message = { id: crypto.randomUUID(), role: 'user', content: message };
    setSessions((prev) => prev.map((s) =>
      s.id === activeSession.id
        ? { ...s, title: s.messages.length === 0 ? message.slice(0, 40) : s.title, messages: [...s.messages, userMsg], updatedAt: new Date().toISOString() }
        : s,
    ));
    setInput('');
    setLoading(true);
    setError(null);
    try {
      const res = await fetch('/api/chat', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ message }) });
      const data = (await res.json()) as ChatApiResponse;
      const assistMsg: Message = { id: crypto.randomUUID(), role: 'assistant', content: data.assistant_message, result: data.result };
      setSessions((prev) => prev.map((s) =>
        s.id === activeSession.id ? { ...s, messages: [...s.messages, assistMsg], updatedAt: new Date().toISOString() } : s,
      ));
    } catch (err) { setError(`Gửi tin thất bại: ${String(err)}`); }
    finally { setLoading(false); }
  };

  // ── Debug collapse ───────────────────────────────────────────────────────────
  const debugCollapseItems = activeResult ? [
    {
      key: 'domain',
      label: (
        <Space size={6}>
          <Text strong>Domain</Text>
          {activeResult.domain ? <Tag color="blue">{activeResult.domain}</Tag> : <Tag color="default">N/A</Tag>}
        </Space>
      ),
      children: (
        <Space direction="vertical" size={6} style={{ width: '100%' }}>
          <div>
            <Text type="secondary" style={{ fontSize: 12 }}>Domain đã chọn</Text>
            <Paragraph className="code-panel" style={{ marginTop: 4 }}>{activeResult.domain ?? 'N/A'}</Paragraph>
          </div>
          <div>
            <Text type="secondary" style={{ fontSize: 12 }}>Các domain ứng viên</Text>
            <Paragraph className="code-panel" style={{ marginTop: 4 }}>{(activeResult.candidate_domains ?? []).join(', ') || 'N/A'}</Paragraph>
          </div>
          <div>
            <Text type="secondary" style={{ fontSize: 12 }}>Intent</Text>
            <Paragraph className="code-panel" style={{ marginTop: 4 }}>{activeResult.intent_name ?? activeResult.intent ?? 'N/A'}</Paragraph>
          </div>
          {activeResult.debug?.domain_routing && (
            <div>
              <Text type="secondary" style={{ fontSize: 12 }}>Routing scores</Text>
              <Paragraph className="code-panel" style={{ marginTop: 4 }}>{JSON.stringify(activeResult.debug.domain_routing, null, 2)}</Paragraph>
            </div>
          )}
        </Space>
      ),
    },
    {
      key: 'schema',
      label: (
        <Space size={6}>
          <Text strong>Schema</Text>
          {(activeResult.tables ?? []).length > 0 ? <Tag color="geekblue">{(activeResult.tables ?? []).join(', ')}</Tag> : <Tag color="default">N/A</Tag>}
        </Space>
      ),
      children: (
        <Space direction="vertical" size={6} style={{ width: '100%' }}>
          <div>
            <Text type="secondary" style={{ fontSize: 12 }}>Bảng được sử dụng</Text>
            <Paragraph className="code-panel" style={{ marginTop: 4 }}>{(activeResult.tables ?? []).join(', ') || 'N/A'}</Paragraph>
          </div>
          {activeResult.debug?.schema_description && (
            <div>
              <Text type="secondary" style={{ fontSize: 12 }}>Schema description</Text>
              <Paragraph className="code-panel" style={{ marginTop: 4 }}>{String(activeResult.debug.schema_description)}</Paragraph>
            </div>
          )}
          {activeResult.debug?.entities && (
            <div>
              <Text type="secondary" style={{ fontSize: 12 }}>Entities</Text>
              <Paragraph className="code-panel" style={{ marginTop: 4 }}>{JSON.stringify(activeResult.debug.entities, null, 2)}</Paragraph>
            </div>
          )}
        </Space>
      ),
    },
    {
      key: 'sql',
      label: (
        <Space size={6}>
          <Text strong>SQL Query</Text>
          <Tag color={activeResult.validator === 'PASS' ? 'green' : 'orange'}>{activeResult.validator ?? '—'}</Tag>
          <Tag>{activeResult.rows ?? 0} rows</Tag>
        </Space>
      ),
      children: (
        <Space direction="vertical" size={6} style={{ width: '100%' }}>
          <div>
            <Text type="secondary" style={{ fontSize: 12 }}>SQL sinh ra</Text>
            <Paragraph className="code-panel" style={{ marginTop: 4 }}>{activeResult.sql ?? 'N/A'}</Paragraph>
          </div>
          {activeResult.timing && (
            <div>
              <Text type="secondary" style={{ fontSize: 12 }}>Timing (ms)</Text>
              <Paragraph className="code-panel" style={{ marginTop: 4 }}>{JSON.stringify(activeResult.timing, null, 2)}</Paragraph>
            </div>
          )}
          {activeResult.result_data?.length ? (
            <Table size="small" pagination={false} rowKey={(_, idx) => String(idx)}
              columns={buildColumns(activeResult.result_data)} dataSource={activeResult.result_data} scroll={{ x: true }} />
          ) : null}
        </Space>
      ),
    },
  ] : [];

  // ── HRM table columns ────────────────────────────────────────────────────────
  const deptColumns = [
    { title: 'Mã PB', dataIndex: 'department_id', key: 'department_id', width: 90 },
    { title: 'Tên Phòng Ban', dataIndex: 'department_name', key: 'department_name' },
    { title: 'Trưởng Phòng', dataIndex: 'manager_name', key: 'manager_name', render: (v: string | null) => v ?? '—' },
    { title: 'Số NV', dataIndex: 'employee_count', key: 'employee_count', width: 80, align: 'center' as const },
  ];

  const empColumns = [
    { title: 'Mã NV', dataIndex: 'employee_id', key: 'employee_id', width: 80 },
    { title: 'Họ Tên', dataIndex: 'employee_name', key: 'employee_name' },
    { title: 'Phòng Ban', dataIndex: 'department_name', key: 'department_name' },
    { title: 'Chức Danh', dataIndex: 'job_title', key: 'job_title' },
    {
      title: 'Trạng Thái', dataIndex: 'employment_status', key: 'employment_status', width: 110,
      render: (v: string) => <Tag color={STATUS_COLOR[v] ?? 'default'}>{v}</Tag>,
    },
    { title: 'Ngày Vào', dataIndex: 'hire_date', key: 'hire_date', width: 100 },
    { title: 'Email', dataIndex: 'email', key: 'email' },
    { title: 'Điện Thoại', dataIndex: 'phone', key: 'phone', width: 115 },
  ];

  const attColumns = [
    { title: 'Ngày', dataIndex: 'attendance_date', key: 'attendance_date', width: 100 },
    { title: 'Mã NV', dataIndex: 'employee_id', key: 'employee_id', width: 80 },
    { title: 'Họ Tên', dataIndex: 'employee_name', key: 'employee_name' },
    { title: 'Phòng Ban', dataIndex: 'department_name', key: 'department_name' },
    { title: 'Giờ Vào', dataIndex: 'check_in_time', key: 'check_in_time', width: 90, render: (v: string | null) => v ?? '—' },
    { title: 'Giờ Ra', dataIndex: 'check_out_time', key: 'check_out_time', width: 90, render: (v: string | null) => v ?? '—' },
    {
      title: 'Trạng Thái', dataIndex: 'status', key: 'status', width: 100,
      render: (v: string) => <Tag color={STATUS_COLOR[v] ?? 'default'}>{v}</Tag>,
    },
  ];

  const deptOptions = [...new Set(employees.map((e) => e.department_name))].map((d) => ({ value: d, label: d }));
  const statusOptions = ['ACTIVE', 'PROBATION', 'RESIGNED', 'SUSPENDED'].map((s) => ({ value: s, label: s }));

  // ── Render ───────────────────────────────────────────────────────────────────
  return (
    <ConfigProvider {...configProps}>
      <Layout className="app-shell">

        {/* ── Left sidebar ─────────────────────────────────────────────────── */}
        <Sider width={300} className="history-pane">

          {/* Hamburger + nav icons */}
          <div className="nav-bar">
            <Tooltip title={navOpen ? 'Thu gọn' : 'Mở rộng'} placement="right">
              <Button
                type="text"
                icon={navOpen ? <MenuFoldOutlined /> : <MenuUnfoldOutlined />}
                className="nav-hamburger"
                onClick={() => setNavOpen((v) => !v)}
              />
            </Tooltip>

            <Tooltip title="Text2SQL Chatbot" placement="right">
              <Button
                type={view === 'chat' ? 'primary' : 'text'}
                icon={<MessageOutlined />}
                className="nav-icon-btn"
                onClick={() => setView('chat')}
              />
            </Tooltip>

            <Tooltip title="Hệ Thống HRM" placement="right">
              <Button
                type={view === 'hrm' ? 'primary' : 'text'}
                icon={<TeamOutlined />}
                className="nav-icon-btn"
                onClick={() => setView('hrm')}
              />
            </Tooltip>
          </div>

          <Divider style={{ margin: '8px 0' }} />

          {/* Session list — only for chat view */}
          {navOpen && view === 'chat' && (
            <>
              <div className="pane-header" style={{ marginBottom: 10 }}>
                <Title level={4} className="pane-title">Sessions</Title>
                <Button type="primary" size="small" onClick={createNewSession}>New chat</Button>
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
                      <div><Text type="secondary" style={{ fontSize: 12 }}>{new Date(session.updatedAt).toLocaleString()}</Text></div>
                    </div>
                  </List.Item>
                )}
              />
            </>
          )}

          {/* HRM nav links */}
          {navOpen && view === 'hrm' && (
            <>
              <Title level={4} className="pane-title" style={{ marginBottom: 12 }}>HRM System</Title>
              {[
                { key: 'departments', icon: <ApartmentOutlined />, label: 'Phòng Ban' },
                { key: 'employees',   icon: <UserOutlined />,      label: 'Nhân Viên' },
                { key: 'attendance',  icon: <CalendarOutlined />,  label: 'Chấm Công' },
              ].map((item) => (
                <div
                  key={item.key}
                  className={`hrm-nav-item ${hrmTab === item.key ? 'active' : ''}`}
                  onClick={() => setHrmTab(item.key)}
                >
                  {item.icon} <span style={{ marginLeft: 8 }}>{item.label}</span>
                </div>
              ))}
            </>
          )}
        </Sider>

        {/* ── Chat view ────────────────────────────────────────────────────── */}
        {view === 'chat' && (
          <>
            <Content className="center-pane">
              <div className="chat-header">
                <Title level={3} className="hero-title">Text2SQL Demo</Title>
              </div>

              {error ? <Alert type="error" showIcon message={error} className="main-alert" /> : null}

              <div className="messages-scroll">
                {activeSession?.messages.length ? (
                  activeSession.messages.map((message) => (
                    <div key={message.id} className={`message-row ${message.role === 'user' ? 'user' : 'assistant'}`}>
                      <Card className={`message-card ${message.role}`}>
                        <Text className="message-role">{message.role === 'user' ? 'User' : 'Assistant'}</Text>
                        <Paragraph className="message-content">{message.content}</Paragraph>

                        {message.role === 'assistant' && message.result?.explain && message.result.explain !== message.content ? (
                          <div className="explain-block">
                            <Text type="secondary" style={{ fontSize: 12, display: 'block', marginBottom: 4 }}>Giải thích</Text>
                            <Paragraph className="explain-text">{message.result.explain}</Paragraph>
                          </div>
                        ) : null}

                        {message.result ? (
                          <Space wrap size={[6, 6]} style={{ marginTop: 8 }}>
                            <Tag>{message.result.domain ?? 'N/A'}</Tag>
                            <Tag color="blue">{message.result.intent_name ?? message.result.intent ?? 'No intent'}</Tag>
                            <Tag color={message.result.validator === 'PASS' ? 'green' : 'orange'}>{message.result.validator}</Tag>
                            <Tag>{message.result.rows ?? 0} rows</Tag>
                          </Space>
                        ) : null}
                      </Card>
                    </div>
                  ))
                ) : (
                  <Empty description="Chưa có tin nhắn. Thử hỏi về banking hoặc HRM để xem domain router và prompt panel." />
                )}
                {loading ? <div className="loading-block"><Spin /></div> : null}
              </div>

              <Card className="composer-card">
                <div className="composer-textarea-wrap">
                  <Input.TextArea
                    value={input}
                    onChange={(e) => setInput(e.target.value)}
                    rows={3}
                    placeholder="Nhập câu hỏi demo... ví dụ: Liệt kê nhân viên thuộc phòng kinh doanh"
                    onPressEnter={(e) => { if (!e.shiftKey) { e.preventDefault(); void handleSubmit(); } }}
                  />
                  <div className="composer-model-chip">
                    <Tag color="default" className="model-tag">{modelLabel}</Tag>
                  </div>
                </div>
                <div className="composer-actions" style={{ marginTop: 8 }}>
                  <Text type="secondary" style={{ fontSize: 12 }}>Shift+Enter để xuống dòng · Enter để gửi</Text>
                  <Button type="primary" onClick={() => void handleSubmit()} loading={loading}>Gửi</Button>
                </div>
              </Card>
            </Content>

            {/* Debug panel */}
            <Sider width={360} className="debug-pane">
              <div className="pane-header" style={{ marginBottom: 16 }}>
                <Title level={4} className="pane-title"></Title>
              </div>
              {activeResult ? (
                <Collapse defaultActiveKey={['domain', 'sql']} className="inspector-collapse" items={debugCollapseItems} />
              ) : (
                <Empty description="Gửi một câu hỏi để xem domain, schema và SQL đã sinh ra." />
              )}
            </Sider>
          </>
        )}

        {/* ── HRM view ─────────────────────────────────────────────────────── */}
        {view === 'hrm' && (
          <Content className="hrm-pane">
            <div style={{ marginBottom: 20 }}>
              <Title level={3} style={{ margin: 0 }}>Hệ Thống Quản Lý Nhân Sự</Title>
              <Text type="secondary">Dữ liệu demo từ SQLite — {employees.length} nhân viên · {departments.length} phòng ban</Text>
            </div>

            {hrmLoading ? (
              <div className="loading-block"><Spin size="large" /></div>
            ) : (
              <Tabs
                activeKey={hrmTab}
                onChange={setHrmTab}
                items={[
                  {
                    key: 'departments',
                    label: <span><ApartmentOutlined /> Phòng Ban</span>,
                    children: (
                      <Table
                        dataSource={departments}
                        columns={deptColumns}
                        rowKey="department_id"
                        size="middle"
                        pagination={false}
                        bordered
                      />
                    ),
                  },
                  {
                    key: 'employees',
                    label: <span><UserOutlined /> Nhân Viên</span>,
                    children: (
                      <>
                        <Space style={{ marginBottom: 12 }}>
                          <Select allowClear placeholder="Lọc phòng ban" options={deptOptions}
                            style={{ width: 220 }} onChange={setFilterDept} />
                          <Select allowClear placeholder="Lọc trạng thái" options={statusOptions}
                            style={{ width: 150 }} onChange={setFilterStatus} />
                          <Text type="secondary">{filteredEmployees.length} kết quả</Text>
                        </Space>
                        <Table
                          dataSource={filteredEmployees}
                          columns={empColumns}
                          rowKey="employee_id"
                          size="small"
                          pagination={{ pageSize: 15, showSizeChanger: false }}
                          scroll={{ x: 900 }}
                          bordered
                        />
                      </>
                    ),
                  },
                  {
                    key: 'attendance',
                    label: <span><CalendarOutlined /> Chấm Công</span>,
                    children: (
                      <>
                        <Space style={{ marginBottom: 12 }}>
                          <Text type="secondary">Hiển thị 300 bản ghi gần nhất (01/03 – 24/03/2026)</Text>
                        </Space>
                        <Table
                          dataSource={attendance}
                          columns={attColumns}
                          rowKey={(_, i) => String(i)}
                          size="small"
                          pagination={{ pageSize: 20, showSizeChanger: false }}
                          scroll={{ x: 800 }}
                          bordered
                        />
                      </>
                    ),
                  },
                ]}
              />
            )}
          </Content>
        )}

      </Layout>
    </ConfigProvider>
  );
}
