from datetime import date, datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, Field

from app.models import (
    CategoryType,
    DatabaseType,
    ProjectEnvironment,
    ProjectStatus,
    ServerProvider,
    ServerStatus,
    ServerType,
    UserRole,
)


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class RefreshRequest(BaseModel):
    refresh_token: str


class PasswordChangeRequest(BaseModel):
    current_password: str
    new_password: str = Field(min_length=6)


class UserBase(BaseModel):
    email: EmailStr
    role: UserRole = UserRole.viewer


class UserCreate(UserBase):
    password: str = Field(min_length=6)


class UserUpdate(BaseModel):
    email: EmailStr | None = None
    role: UserRole | None = None
    password: str | None = Field(default=None, min_length=6)
    is_active: bool | None = None


class UserResponse(UserBase):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    is_active: bool
    created_at: datetime


class CategoryBase(BaseModel):
    name: str
    type: CategoryType
    color: str = "#8b5cf6"
    description: str | None = None


class CategoryCreate(CategoryBase):
    pass


class CategoryUpdate(BaseModel):
    name: str | None = None
    type: CategoryType | None = None
    color: str | None = None
    description: str | None = None


class CategoryResponse(CategoryBase):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    created_at: datetime
    updated_at: datetime


class ServerBase(BaseModel):
    name: str
    category_id: UUID | None = None
    provider: ServerProvider = ServerProvider.other
    server_type: ServerType = ServerType.hosting
    panel_url: str | None = None
    expiry_date: date | None = None
    renewal_cost: float | None = None
    notes: str | None = None
    tags: list[str] = Field(default_factory=list)
    status: ServerStatus = ServerStatus.active


class ServerCreate(ServerBase):
    username: str | None = None
    password: str | None = None
    ssh_key: str | None = None


class ServerUpdate(BaseModel):
    name: str | None = None
    category_id: UUID | None = None
    provider: ServerProvider | None = None
    server_type: ServerType | None = None
    panel_url: str | None = None
    username: str | None = None
    password: str | None = None
    ssh_key: str | None = None
    expiry_date: date | None = None
    renewal_cost: float | None = None
    notes: str | None = None
    tags: list[str] | None = None
    status: ServerStatus | None = None


class ServerResponse(ServerBase):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    has_credentials: bool = False
    username: str | None = None
    password: str | None = None
    ssh_key: str | None = None
    created_at: datetime
    updated_at: datetime


class DomainBase(BaseModel):
    domain_name: str
    registrar: str | None = None
    dns_provider: str | None = None
    expiry_date: date | None = None
    ssl_expiry: date | None = None
    notes: str | None = None


class DomainCreate(DomainBase):
    pass


class DomainUpdate(BaseModel):
    domain_name: str | None = None
    registrar: str | None = None
    dns_provider: str | None = None
    expiry_date: date | None = None
    ssl_expiry: date | None = None
    notes: str | None = None


class DomainResponse(DomainBase):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    created_at: datetime
    updated_at: datetime


class DatabaseBase(BaseModel):
    name: str
    server_id: UUID | None = None
    db_type: DatabaseType = DatabaseType.postgres
    notes: str | None = None


class DatabaseCreate(DatabaseBase):
    connection_string: str | None = None


class DatabaseUpdate(BaseModel):
    name: str | None = None
    server_id: UUID | None = None
    db_type: DatabaseType | None = None
    connection_string: str | None = None
    notes: str | None = None


class DatabaseResponse(DatabaseBase):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    has_connection_string: bool = False
    connection_string: str | None = None
    created_at: datetime
    updated_at: datetime


class ProjectBase(BaseModel):
    name: str
    category_id: UUID | None = None
    server_id: UUID | None = None
    domain_id: UUID | None = None
    database_id: UUID | None = None
    environment: ProjectEnvironment = ProjectEnvironment.production
    main_url: str | None = None
    frontend_url: str | None = None
    backend_url: str | None = None
    tech_stack: list[str] = Field(default_factory=list)
    status: ProjectStatus = ProjectStatus.live
    notes: str | None = None


class ProjectCreate(ProjectBase):
    pass


class ProjectUpdate(BaseModel):
    name: str | None = None
    category_id: UUID | None = None
    server_id: UUID | None = None
    domain_id: UUID | None = None
    database_id: UUID | None = None
    environment: ProjectEnvironment | None = None
    main_url: str | None = None
    frontend_url: str | None = None
    backend_url: str | None = None
    tech_stack: list[str] | None = None
    status: ProjectStatus | None = None
    notes: str | None = None


class ProjectResponse(ProjectBase):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    created_at: datetime
    updated_at: datetime
    category_name: str | None = None
    server_name: str | None = None
    domain_name: str | None = None
    database_name: str | None = None


class ExpiringItem(BaseModel):
    id: UUID
    name: str
    type: str
    expiry_date: date
    days_remaining: int


class DashboardStats(BaseModel):
    total_categories: int
    total_servers: int
    total_projects: int
    total_domains: int
    total_databases: int
    expiring_servers: list[ExpiringItem]
    expiring_domains: list[ExpiringItem]


class SearchResult(BaseModel):
    id: UUID
    name: str
    type: str
    subtitle: str | None = None


class AuditLogResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    user_email: str | None = None
    action: str
    entity_type: str
    entity_id: str | None
    details: str | None
    created_at: datetime
