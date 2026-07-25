from pydantic import BaseModel


class DashboardStats(BaseModel):
    server_count: int
    healthy_servers: int
    degraded_servers: int
    pending_approvals: int
