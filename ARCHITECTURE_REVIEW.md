# TianGong AI for Sustainability — 架构 Review 报告

**日期**: 2025年11月  
**范围**: 完整项目架构、代码组织、设计模式和可维护性分析

---

## 目录

1. [总体评估](#总体评估)
2. [强项](#强项)
3. [改进机会](#改进机会)
4. [具体建议](#具体建议)
5. [优先级行动计划](#优先级行动计划)

---

## 总体评估

### 现状

该项目**架构设计整体良好**，具有以下特点：

✅ **清晰的分层设计** — `core`、`adapters`、`services`、`cli` 模块边界分明  
✅ **声明式数据源管理** — 基于 YAML 的 registry 便于维护和扩展  
✅ **spec-first 开发流程** — `specs/` 和 `tasks/blueprint.yaml` 作为权威参考  
✅ **生产级代码质量** — 类型注解完整、错误处理细致、测试覆盖  
✅ **双语文档** — README 和 AGENTS 文档保持同步  

### 成熟度评级

| 维度 | 评分 | 备注 |
|------|------|------|
| **分层设计** | ⭐⭐⭐⭐⭐ | 模块职责清晰，依赖方向单向 |
| **错误处理** | ⭐⭐⭐⭐☆ | 适配器层完善，工作流层可增强 |
| **扩展性** | ⭐⭐⭐⭐⭐ | Registry 和适配器模式高度灵活 |
| **可观测性** | ⭐⭐⭐☆☆ | **缺少中央日志和追踪**（见改进项） |
| **缓存策略** | ⭐⭐⭐☆☆ | **规划完善但实现不完整** |
| **测试覆盖** | ⭐⭐⭐⭐☆ | 单元测试充分，集成测试可加强 |

---

## 强项

### 1. 模块化架构（Module Separation）

**现状**：`core`、`adapters`、`services`、`cli` 各司其职

```
core/
  ├── registry.py      # 数据源元数据及 YAML 加载
  ├── context.py       # 执行上下文和选项管理
  └── config.py        # 密钥和配置加载

adapters/
  ├── base.py          # 通用协议（Protocol）定义
  ├── api/             # HTTP 适配器（UN SDG、Semantic Scholar、OpenAlex 等）
  ├── environment/     # CLI 适配器（grid-intensity）
  └── tools/           # 工具集成（AntV MCP 图表服务）

services/
  └── research.py      # 高级 façade，包装适配器和业务逻辑

cli/
  └── main.py          # Typer 应用，暴露公共接口

workflows/
  ├── simple.py        # 轻量级多源研究流程
  ├── deep_lca.py      # LCA 分析工作流
  └── charting.py      # 图表生成助手
```

**优点**：
- 新数据源只需在 `adapters/` 中添加新适配器
- 业务逻辑与 CLI 解耦，易于测试和自动化
- `ExecutionContext` 和 `Registry` 为 AI agent 提供结构化接口

---

### 2. 声明式数据源管理

**现状**：`resources/datasources/core.yaml` 作为数据源元数据的单一事实来源

```yaml
- id: un_sdg_api
  name: "UN Sustainable Development Goals API"
  priority: P1
  status: active
  capabilities: ["list-goals", "list-targets", "list-indicators"]
  # ... 其他元数据
```

**优点**：
- YAML 格式非技术人员易读易修改
- 无需编译即可更新数据源状态（`active`/`trial`/`deprecated`/`blocked`）
- 支持权限检查（`requires_credentials`）和速率限制 hints
- Registry validation 防止无效条目

---

### 3. 设计模式良好应用

**数据源适配器协议** (`adapters/base.py`)：
```python
class DataSourceAdapter(Protocol):
    def verify(self) -> VerificationResult:
        """Perform a lightweight connectivity check."""
    
    @property
    def source_id(self) -> str:
        """Identifier matching the registry descriptor."""
```

**优点**：
- 通过 Protocol 实现鸭子类型，避免深继承层级
- 每个适配器只需实现两个接口方法，降低耦合
- 便于测试（可轻松 mock）

---

### 4. 重试和容错机制

**现状** (`adapters/api/base.py`)：
```python
@retry(
    retry=retry_if_exception_type(httpx.HTTPError),
    wait=wait_exponential(multiplier=1, min=1, max=8),
    stop=stop_after_attempt(3),
    reraise=True,
)
def _send() -> httpx.Response:
    # ...
```

**优点**：
- 指数退避策略
- 最多 3 次重试
- HTTPError 被主动捕获并转换为 `APIError`，便于上层处理

---

### 5. 执行上下文的灵活性

**现状** (`core/context.py`)：
```python
@dataclass(slots=True)
class ExecutionContext:
    enabled_sources: MutableSet[str]
    cache_dir: Path
    secrets: SecretsBundle
    options: ExecutionOptions = field(default_factory=ExecutionOptions)
    extra: Mapping[str, object] = field(default_factory=dict)
```

**优点**：
- `dry_run` 支持（planning without side effects）
- `background_tasks` 选项为异步扩展预留了接口
- `extra` 字段允许额外的上下文传递（向后兼容）
- `is_enabled(source_id)` 提供细粒度的数据源控制

---

## 改进机会

### 1. ⚠️ 缺失中央日志与可观测性层（High Priority）

**现状**：
- 适配器在失败时抛出异常，但无统一的日志/追踪机制
- CLI 命令中的 try-except 块单独处理错误，无一致性
- 工作流执行过程无追踪信息（tracing）

**问题**：
```python
# workflows/simple.py
try:
    payload = services.github_topics_client().search_repositories(topic, per_page=limit)
except APIError as exc:
    return [{"full_name": "(error)", "description": str(exc), ...}]  # 无日志记录
```

**改进方案**：
- 在 `core/` 添加 `logging.py` 模块，定义统一的日志等级和格式
- 创建 `Tracer` 类用于 function-level tracing（支持 span 和 metric）
- 在 `ExecutionContext` 中注入 logger，所有服务自动继承
- 考虑集成 OpenTelemetry SDK（可选，为未来准备）

```python
# 建议的文件结构
core/
  ├── logging.py       # Logger 工厂和配置
  ├── tracing.py       # Span 和 metric 定义
  └── context.py       # 修改以支持 logger 注入
```

---

### 2. ⚠️ 缓存层实现不完整（High Priority）

**现状**：
- 规划中支持 "caching is deferred to services" 但实现不完全
- 只有 `_sdg_goal_cache` 在 `ResearchServices` 中有单一实现
- 无统一的缓存策略（TTL、LRU、持久化）

**问题**：
```python
# services/research.py
_sdg_goal_cache: Optional[Dict[str, Dict[str, Any]]] = field(default=None, init=False, repr=False)

# 问题：这是内存缓存，无 TTL、无持久化、重启后丢失
```

**改进方案**：
- 创建 `core/cache.py` 模块，实现统一的缓存接口
- 支持多种后端：in-memory、DuckDB（持久化）、Redis（分布式）
- 为每个数据源定义合理的 TTL

```python
# 建议的设计
from abc import ABC, abstractmethod

class CacheBackend(ABC):
    @abstractmethod
    def get(self, key: str) -> Optional[Any]:
        pass
    
    @abstractmethod
    def set(self, key: str, value: Any, ttl: Optional[int] = None) -> None:
        pass

class InMemoryCache(CacheBackend):
    # LRU + TTL 实现

class DuckDBCache(CacheBackend):
    # 持久化实现
```

---

### 3. ⚠️ 工作流错误恢复不足（Medium Priority）

**现状**：
- 工作流函数（如 `run_simple_workflow`）在某个步骤失败时返回部分结果
- 无重试机制、无检查点、无从故障点恢复

**问题**：
```python
# workflows/simple.py
def run_simple_workflow(...) -> WorkflowArtifacts:
    sdg_matches = _match_sdgs(services, topic)           # 可能失败
    repositories = _fetch_repositories(services, topic)  # 如果上面失败，这里无法重试
    papers = _fetch_papers(services, topic)
    # ...
```

**改进方案**：
- 实现 `Checkpoint` 机制：每个步骤的结果保存到 cache
- 如果重新执行相同的工作流，可以从最后一个成功的检查点恢复
- 为每个工作流定义重试策略（指数退避、最大尝试次数）

```python
# 建议的模式
@checkpoint(name="match_sdgs", ttl=3600)
def _match_sdgs_cached(services, topic):
    # 自动缓存结果 1 小时

# 调用时自动处理缓存
result = _match_sdgs_cached(services, "renewable energy")  # 第二次调用命中缓存
```

---

### 4. ⚠️ 数据模型缺失（Medium Priority）

**现状**：
- `core/` 中只有 registry 和 context，缺少业务实体模型
- 工作流和适配器使用 `Dict[str, Any]` 传递数据，类型信息丢失
- 无 standardized 的 GRI/SDG/LCA 数据结构

**问题**：
```python
# 工作流中：无类型安全
papers: List[Dict[str, Any]] = _fetch_papers(...)  # Dict 内容无法IDE提示
for paper in papers:
    title = paper.get("title", "unknown")  # 容易出错，无 schema 验证
```

**改进方案**：
- 创建 `domain/` 包，定义 Pydantic 模型

```python
# domain/models.py
from pydantic import BaseModel, Field

class SDGGoal(BaseModel):
    code: str
    title: str
    description: str
    targets: List[str] = []

class Paper(BaseModel):
    id: str
    title: str
    authors: List[str]
    year: int
    url: Optional[str] = None
    abstract: Optional[str] = None

class Repository(BaseModel):
    full_name: str
    stars: int = 0
    url: Optional[str] = None
    description: Optional[str] = None
```

**好处**：
- 类型安全和 IDE 自动完成
- Pydantic 提供自动验证和序列化
- 支持 OpenAPI schema 生成（未来接口化时有用）

---

### 5. ⚠️ CLI 错误信息不够友好（Medium Priority）

**现状**：
- 某些错误消息过于技术性，缺少用户指导
- 缺少 "you might want to do" 式的建议

**问题**：
```python
# cli/main.py
if descriptor.requires_credentials and source_id not in context.enabled_sources:
    typer.echo(
        f"Source '{source_id}' requires credentials. Provide API keys in .secrets or enable explicitly.",
        err=True,
    )
```

**改进方案**：
- 创建 `cli/errors.py` 定义用户友好的错误消息
- 为常见错误场景提供修复建议

```python
# cli/errors.py
class UserFriendlyError(Exception):
    """用户友好的错误类"""
    def __init__(self, message: str, suggestions: Optional[List[str]] = None):
        self.message = message
        self.suggestions = suggestions or []

# 使用
raise UserFriendlyError(
    "OSDG API requires credentials",
    suggestions=[
        "1. Create .secrets/secrets.toml with OSDG_API_KEY",
        "2. Run: uv run tiangong-research sources verify osdg_api",
    ]
)
```

---

### 6. ⚠️ 测试体系不完整（Medium Priority）

**现状**：
- 单元测试覆盖 `core` 和 CLI 基础
- 缺少：集成测试、性能测试、端到端测试

**问题**：
```bash
tests/
  ├── test_cli.py              # ✅ 有
  ├── test_core.py             # ✅ 有
  ├── test_registry.py         # ✅ 有
  ├── test_services.py         # ✅ 有
  ├── test_workflow.py         # ✅ 有
  # 缺少：
  # ❌ test_adapters/           # 适配器集成测试
  # ❌ test_workflows/          # 工作流端到端测试
  # ❌ test_performance.py      # 性能基准
```

**改进方案**：
- 添加 fixture 和 mocking 框架以支持真实 API 的可选测试
- 为每个工作流添加端到端测试（使用 mocked 适配器）
- 添加性能基准测试

```bash
tests/
  ├── conftest.py              # 共享 fixtures
  ├── test_cli.py
  ├── test_core.py
  ├── test_services.py
  ├── adapters/                # 新增
  │   ├── test_un_sdg.py
  │   ├── test_semantic_scholar.py
  │   └── test_github_topics.py
  ├── workflows/               # 新增
  │   ├── test_simple_workflow.py
  │   └── test_deep_lca.py
  └── performance/             # 新增
      └── test_benchmarks.py
```

---

### 7. ⚠️ 依赖管理可优化（Low Priority）

**现状**：
- `pyproject.toml` 依赖列表简洁
- 但缺少可选依赖组（optional dependencies）

**改进方案**：
```toml
[project.optional-dependencies]
pdf = ["pdfminer.six>=20201018"]
database = ["duckdb>=1.0.0", "sqlalchemy>=2.0"]
visualization = ["matplotlib>=3.5", "plotly>=5.0"]
dev = ["pytest>=8.0", "black>=25.0", "ruff>=0.14"]
```

**好处**：
- 用户可根据需要安装子集：`uv sync --extra pdf --extra visualization`
- 减少默认依赖的大小

---

### 8. ⚠️ 配置管理散乱（Low Priority）

**现状**：
- 配置分散在多个地方：`config.py`、`.secrets/secrets.toml`、环境变量
- 无统一的配置层（configuration layer）

**改进方案**：
- 创建 `core/settings.py` 统一管理配置

```python
# core/settings.py
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    cache_backend: str = "memory"  # or "duckdb", "redis"
    duckdb_path: Optional[Path] = None
    log_level: str = "INFO"
    enable_tracing: bool = False
    
    class Config:
        env_file = ".env"
        env_prefix = "TIANGONG_"

settings = Settings()
```

---

### 9. ⚠️ 文档化代码示例缺少（Low Priority）

**现状**：
- README 提供了基础用法
- 但缺少高级场景的代码示例

**改进方案**：
- 在 `docs/` 目录下添加使用指南

```
docs/
  ├── getting_started.md
  ├── advanced_workflows.md
  ├── creating_custom_adapters.md
  ├── using_deep_research.md
  └── api_reference.md
```

---

## 具体建议

### 短期改进（1-2 周）

| # | 任务 | 优先级 | 工作量 | 影响 |
|---|------|--------|--------|------|
| 1 | 添加中央日志模块（`core/logging.py`） | ⚠️ 高 | 2h | 可观测性显著提升 |
| 2 | 统一工作流错误处理 | ⚠️ 高 | 3h | 减少 fail-silent 问题 |
| 3 | 增加用户友好的错误消息 | 中 | 2h | 改善用户体验 |
| 4 | 补充适配器单元测试 | 中 | 4h | 提高代码质量 |

### 中期改进（1 个月）

| # | 任务 | 优先级 | 工作量 | 影响 |
|---|------|--------|--------|------|
| 5 | 实现通用缓存层（`core/cache.py`） | ⚠️ 高 | 6h | 显著提升性能，避免重复 API 调用 |
| 6 | 定义 Pydantic 数据模型（`domain/`） | 中 | 8h | 类型安全、IDE 支持 |
| 7 | 实现工作流检查点机制 | 中 | 6h | 容错能力提升 |
| 8 | 添加端到端工作流测试 | 中 | 6h | 覆盖率提升 |

### 长期改进（2-3 个月）

| # | 任务 | 优先级 | 工作量 | 影响 |
|---|------|--------|--------|------|
| 9 | OpenTelemetry 集成（可选） | 低 | 8h | 支持分布式追踪、Prometheus metrics |
| 10 | Redis 缓存后端支持 | 低 | 4h | 支持多实例部署 |
| 11 | GraphQL 或 REST API 层 | 低 | 12h | 支持外部系统集成 |
| 12 | 可视化改进和交互式报告 | 低 | 10h | 提升用户体验 |

---

## 优先级行动计划

### 🔴 立即采取行动

**1. 添加中央日志系统**
```python
# src/tiangong_ai_for_sustainability/core/logging.py

import logging
from typing import Optional

def get_logger(name: str) -> logging.Logger:
    logger = logging.getLogger(name)
    handler = logging.StreamHandler()
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    handler.setFormatter(formatter)
    if not logger.handlers:
        logger.addHandler(handler)
    return logger

# 在 services 和 adapters 中使用
logger = get_logger(__name__)

class ResearchServices:
    def __init__(self, ...):
        self.logger = get_logger(self.__class__.__name__)
    
    def get_carbon_intensity(self, location: str):
        self.logger.info(f"Fetching carbon intensity for {location}")
        try:
            result = ...
            self.logger.debug(f"Result: {result}")
            return result
        except Exception as e:
            self.logger.error(f"Failed to fetch carbon intensity: {e}")
            raise
```

---

**2. 改进工作流容错机制**
```python
# workflows/simple.py

def run_simple_workflow(...) -> WorkflowArtifacts:
    logger = get_logger(__name__)
    
    try:
        logger.info(f"Starting workflow for topic: {topic}")
        sdg_matches = _match_sdgs(services, topic)
        logger.info(f"Matched {len(sdg_matches)} SDG goals")
    except Exception as e:
        logger.error(f"SDG matching failed: {e}")
        sdg_matches = []  # 明确的 fallback
    
    try:
        repositories = _fetch_repositories(services, topic, github_limit)
        logger.info(f"Found {len(repositories)} repositories")
    except Exception as e:
        logger.error(f"Repository fetching failed: {e}")
        repositories = []
    
    # 继续其他步骤...
    
    logger.info("Workflow completed")
    return WorkflowArtifacts(...)
```

---

**3. 添加用户友好的错误提示**
```python
# cli/errors.py

class CLIError(Exception):
    def __init__(self, message: str, hints: Optional[List[str]] = None):
        self.message = message
        self.hints = hints or []
        super().__init__(message)

def format_error_with_hints(error: CLIError) -> str:
    output = f"\n❌ Error: {error.message}\n"
    if error.hints:
        output += "\n💡 Suggestions:\n"
        for i, hint in enumerate(error.hints, 1):
            output += f"  {i}. {hint}\n"
    return output

# 在 CLI 中使用
@research_app.command("find-code")
def find_code(...):
    try:
        ...
    except AdapterError as e:
        raise CLIError(
            f"Failed to query GitHub: {e}",
            hints=[
                "Check your internet connection",
                "Verify GitHub API is accessible: https://api.github.com/",
                "If rate-limited, provide a GitHub token in .secrets/secrets.toml",
            ]
        )
```

---

### 🟡 1-2 周内完成

**4. 实现基础缓存层**
```python
# core/cache.py

from abc import ABC, abstractmethod
from typing import Any, Optional
from datetime import datetime, timedelta

class CacheBackend(ABC):
    @abstractmethod
    def get(self, key: str) -> Optional[Any]:
        pass
    
    @abstractmethod
    def set(self, key: str, value: Any, ttl_seconds: Optional[int] = None) -> None:
        pass

class InMemoryCache(CacheBackend):
    def __init__(self, max_size: int = 1000):
        self.cache: Dict[str, tuple[Any, Optional[datetime]]] = {}
        self.max_size = max_size
    
    def get(self, key: str) -> Optional[Any]:
        if key in self.cache:
            value, expires = self.cache[key]
            if expires is None or expires > datetime.now():
                return value
            del self.cache[key]
        return None
    
    def set(self, key: str, value: Any, ttl_seconds: Optional[int] = None) -> None:
        expires = datetime.now() + timedelta(seconds=ttl_seconds) if ttl_seconds else None
        if len(self.cache) >= self.max_size:
            # Simple LRU: remove first item
            self.cache.pop(next(iter(self.cache)))
        self.cache[key] = (value, expires)
```

---

### 🟢 后续工作

**5. 定义数据模型**
```python
# domain/models.py

from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime

class SDGGoal(BaseModel):
    code: str = Field(..., description="E.g., '1', '2', etc.")
    title: str
    description: str
    targets: List[str] = []

class Paper(BaseModel):
    id: str
    title: str
    authors: List[str]
    year: int
    url: Optional[str] = None
    abstract: Optional[str] = None

class Repository(BaseModel):
    full_name: str
    stars: int = 0
    url: Optional[str] = None
    description: Optional[str] = None

class WorkflowResult(BaseModel):
    topic: str
    sdg_matches: List[SDGGoal]
    papers: List[Paper]
    repositories: List[Repository]
    carbon_intensity: Optional[float] = None
    generated_at: datetime = Field(default_factory=datetime.now)
```

---

## 总结与建议

### 核心建议

1. **立即添加日志和追踪**（高影响，快速）
2. **统一缓存策略**（性能收益大）
3. **增强工作流容错**（提升稳定性）
4. **定义数据模型**（类型安全）
5. **改进错误消息**（用户体验）

### 长期展望

- 该项目**架构基础扎实**，易于演进
- 建议按优先级逐步实施改进
- 每个改进都应伴随相应的测试用例

### 维护建议

- 保持 `specs/architecture.md` 与实现同步
- 定期审查 `tasks/blueprint.yaml` 并更新完成状态
- 每季度进行一次轻量级架构 review

---

## 附录：快速参考

### 推荐的新增模块结构

```
src/tiangong_ai_for_sustainability/
  ├── core/
  │   ├── __init__.py
  │   ├── registry.py          # ✅ 现有
  │   ├── context.py           # ✅ 现有
  │   ├── config.py            # ✅ 现有
  │   ├── logging.py           # 🆕 新增（日志）
  │   ├── cache.py             # 🆕 新增（缓存）
  │   ├── settings.py          # 🆕 新增（配置）
  │   └── tracing.py           # 🆕 新增（追踪，后续）
  │
  ├── domain/                  # 🆕 新增（数据模型）
  │   ├── __init__.py
  │   ├── models.py
  │   └── validators.py
  │
  ├── adapters/
  │   ├── api/
  │   │   ├── __init__.py
  │   │   ├── base.py          # ✅ 现有
  │   │   ├── github_topics.py
  │   │   └── ...
  │   ├── environment/
  │   ├── tools/
  │   └── errors.py            # 🆕 新增（适配器错误定义）
  │
  ├── cli/
  │   ├── main.py              # ✅ 现有
  │   └── errors.py            # 🆕 新增（用户友好错误）
  │
  ├── services/
  │   ├── research.py          # ✅ 现有
  │   └── base.py              # 🆕 新增（基础服务类）
  │
  └── workflows/
      ├── simple.py            # ✅ 现有
      └── ...
```

---

**Review 完成** ✓  
建议与工程团队讨论优先级并分配实施任务。
