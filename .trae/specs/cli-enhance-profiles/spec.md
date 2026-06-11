# CLI 增强功能规范 - Provider/Models/Profiles/Backup/Auth

## Why
当前 CLI 相比 Hermes 缺少一些增强功能模块：Provider 管理、模型目录、配置 profiles、备份恢复、认证系统。这些功能可以提升用户体验。

## What Changes

### 新增/增强模块

| 模块 | 文件 | 说明 |
|------|------|------|
| Provider 管理 | `cli/providers.py` | 增强 LLM Provider 统一管理 |
| 模型目录 | `cli/models.py` | 模型信息、对比、推荐 |
| 配置 Profiles | `cli/profiles.py` | 多配置文件切换 |
| 备份恢复 | `cli/backup.py` | 增强现有备份功能 |
| 认证系统 | `cli/auth_cli.py` | API Key 安全存储、Token 管理 |

### 目录结构变更

```
cli/
├── cli_commands/            # 已完成
├── components/              # 已完成
├── tui/                     # 已完成
├── providers.py            # 🆕 Provider 管理（增强现有）
├── models.py               # 🆕 模型目录（增强现有）
├── profiles.py             # 🆕 配置 Profiles（增强现有）
├── backup.py               # 🆕 备份恢复（增强现有）
├── auth_cli.py             # 🆕 认证系统（已有，扩展）
└── ...
```

## Impact

### 影响的规格
- CLI Provider 管理
- CLI 模型目录
- CLI 配置 Profiles
- CLI 备份恢复
- CLI 认证系统

### 影响的代码
- `cli/_parser.py` - 需要注册新命令
- `cli/main.py` - 需要处理新命令

## ADDED Requirements

### Requirement: providers 命令
系统 SHALL 提供 Provider 管理功能：
- `providers list` - 列出所有可用 Provider
- `providers info <provider>` - 显示 Provider 详细信息
- `providers status` - 检查 Provider 连接状态

#### Scenario: 列出 Provider
- **WHEN** 用户执行 `python -m cli.main providers list`
- **THEN** 显示所有可用 Provider 及状态

### Requirement: models 命令
系统 SHALL 提供模型目录功能：
- `models list` - 列出所有可用模型
- `models info <model>` - 显示模型详细信息
- `models compare <model1> <model2>` - 比较两个模型

#### Scenario: 模型对比
- **WHEN** 用户执行 `python -m cli.main models compare gpt-4o claude-3-opus`
- **THEN** 显示两个模型的对比（价格、上下文、速度等）

### Requirement: profiles 命令
系统 SHALL 提供配置 Profiles 功能：
- `profiles list` - 列出所有 Profiles
- `profiles create <name>` - 创建新 Profile
- `profiles switch <name>` - 切换 Profile
- `profiles delete <name>` - 删除 Profile

#### Scenario: 切换 Profile
- **WHEN** 用户执行 `python -m cli.main profiles switch dev`
- **THEN** 切换到 dev Profile，加载对应配置

### Requirement: backup 命令
系统 SHALL 提供备份恢复功能：
- `backup create` - 创建备份
- `backup list` - 列出备份
- `backup restore <backup>` - 恢复备份
- `backup delete <backup>` - 删除备份

### Requirement: auth 命令
系统 SHALL 提供认证管理功能：
- `auth add <provider> <api_key>` - 添加 API Key
- `auth list` - 列出已存储的认证
- `auth delete <provider>` - 删除认证
- `auth test <provider>` - 测试连接

## 技术实现

### 1. Provider 管理

```python
# cli/providers.py

PROVIDERS = {
    "openai": {
        "name": "OpenAI",
        "models": ["gpt-4o", "gpt-4-turbo", "gpt-3.5-turbo"],
        "pricing": {...},
        "status": "active",
    },
    # ...
}

def list_providers():
    """列出所有 Provider"""
    
def get_provider_info(name):
    """获取 Provider 详细信息"""
    
def check_provider_status(name):
    """检查 Provider 连接状态"""
```

### 2. Models 目录

```python
# cli/models.py

MODELS = {
    "gpt-4o": {
        "provider": "openai",
        "context_window": 128000,
        "input_price": 5.0,  # $/1M tokens
        "output_price": 15.0,
        "capabilities": ["chat", "vision", "function_calling"],
    },
    # ...
}

def list_models(provider=None):
    """列出模型"""
    
def get_model_info(name):
    """获取模型详细信息"""
    
def compare_models(name1, name2):
    """比较两个模型"""
```

### 3. Profiles

```python
# cli/profiles.py

class ProfileManager:
    """配置 Profile 管理器"""
    
    def list_profiles(self):
        """列出所有 Profile"""
        
    def create_profile(self, name):
        """创建新 Profile"""
        
    def switch_profile(self, name):
        """切换 Profile"""
        
    def delete_profile(self, name):
        """删除 Profile"""
```

### 4. Backup

```python
# cli/backup.py

class BackupManager:
    """备份管理器"""
    
    def create_backup(self):
        """创建备份"""
        
    def list_backups(self):
        """列出备份"""
        
    def restore_backup(self, backup_id):
        """恢复备份"""
        
    def delete_backup(self, backup_id):
        """删除备份"""
```

### 5. Auth

```python
# cli/auth_cli.py

class AuthManager:
    """认证管理器"""
    
    def add_credential(self, provider, api_key):
        """添加 API Key"""
        
    def list_credentials(self):
        """列出已存储的认证"""
        
    def delete_credential(self, provider):
        """删除认证"""
        
    def test_connection(self, provider):
        """测试连接"""
```