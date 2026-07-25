export interface MCPServer {
  id: string;
  name: string;
  endpoint: string;
  owner_team: string;
  labels: string[];
  trust_level: TrustLevel;
  health_status: HealthStatus;
  team_namespace: string;
  decommissioned_at: string | null;
  created_at: string;
  tools?: ServerTool[];
}

export interface ServerDetail extends MCPServer {
  tools: ServerTool[];
  routing_rules: RoutingRule[];
  trust_assignments: TrustAssignment[];
}

export interface ServerTool {
  id: string;
  server_id: string;
  tool_name: string;
  input_schema: Record<string, unknown>;
  output_schema: Record<string, unknown>;
}

export interface Capability {
  id: string;
  name: string;
  domain: string;
  description: string;
  norm_input_schema: Record<string, unknown>;
  norm_output_schema: Record<string, unknown>;
  status: 'active' | 'deprecated';
  deprecated_at: string | null;
  grace_period_days: number;
  aliases?: CapabilityAlias[];
}

export interface CapabilityMapping {
  id: string;
  capability_id: string;
  server_id: string;
  tool_name: string;
  is_primary: boolean;
  routing_weight: number;
  server?: MCPServer;
}

export interface CapabilityAlias {
  id: string;
  capability_id: string;
  alias: string;
}

export interface AgentClass {
  id: string;
  name: string;
  description: string;
  team_namespace: string;
}

export interface AgentIdentity {
  id: string;
  agent_class_id: string;
  token_prefix: string;
  status: 'active' | 'revoked' | 'expired';
  rate_limit_per_min: number;
  expires_at: string | null;
  created_at: string;
}

export interface TrustAssignment {
  id: string;
  agent_class_id: string;
  server_id: string;
  trust_level: TrustLevel;
  tool_scope: Record<string, unknown> | null;
  server_name?: string;
}

export interface RoutingRule {
  id: string;
  capability_id: string;
  server_id: string;
  priority: number;
  condition: Record<string, unknown> | null;
}

export interface PolicyDecision {
  allow: boolean;
  approval_required: boolean;
  trust_level: TrustLevel;
  agent_class: string;
}

export interface ApprovalRequest {
  id: string;
  agent_identity_id: string;
  capability_id: string;
  server_id: string;
  request_params: Record<string, unknown>;
  status: 'pending' | 'approved' | 'denied';
  approver_id: string | null;
  requested_at: string;
  resolved_at: string | null;
  agent_name?: string;
  capability_name?: string;
  server_name?: string;
}

export interface AuditEvent {
  id: string;
  event_type: string;
  actor_type: string;
  actor_id: string;
  target_type: string | null;
  target_id: string | null;
  details: Record<string, unknown>;
  created_at: string;
}

export interface CapabilityPack {
  id: string;
  name: string;
  description: string;
  team_namespace: string;
  capabilities?: Capability[];
  agent_classes?: AgentClass[];
}

export interface AlertRule {
  id: string;
  name: string;
  alert_type: string;
  condition: Record<string, unknown>;
  channels: string[];
  enabled: boolean;
}

export interface AlertEvent {
  id: string;
  rule_id: string;
  message: string;
  details: Record<string, unknown>;
  fired_at: string;
  acknowledged_at: string | null;
  acknowledged_by: string | null;
  rule_name?: string;
}

export interface AdminUser {
  id: string;
  username: string;
  email: string;
  role: AdminRole;
  team_namespace: string;
  mfa_enabled: boolean;
  status: 'active' | 'invited' | 'deactivated';
  created_at: string;
}

export interface Pagination {
  next_cursor?: string;
  has_more: boolean;
  per_page: number;
  total: number;
}

export interface PaginatedResponse<T> {
  items: T[];
  pagination: Pagination;
}

export type TrustLevel = 'trusted' | 'restricted' | 'approval-gated' | 'unreviewed';
export type HealthStatus = 'healthy' | 'degraded' | 'unhealthy';
export type AdminRole = 'admin' | 'editor' | 'viewer';

export interface AuthUser {
  id: string;
  username: string;
  role: AdminRole;
  team_namespace: string;
  mfa_enabled: boolean;
}

export interface LoginResponse {
  token: string;
  user: AuthUser;
  mfa_required: boolean;
}

export interface ResourceDimension {
  id: string;
  capability_id: string;
  dimension_key: string;
  display_name: string | null;
  created_at: string;
  value_maps?: DimensionValueMap[];
}

export interface DimensionValueMap {
  id: string;
  resource_dimension_id: string;
  source: 'param' | 'constant';
  param_path: string | null;
  constant_value: string | null;
}

export interface ResourceBinding {
  id: string;
  agent_identity_id?: string;
  pack_id?: string;
  dimension_key: string;
  allowed_value: string;
  created_at: string;
}

export interface DashboardStats {
  server_count: number;
  healthy_servers: number;
  pending_approvals: number;
  recent_audit_events: number;
  degraded_servers: number;
}
