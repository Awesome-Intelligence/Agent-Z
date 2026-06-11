# Tasks - CLI 增强功能（Provider/Models/Profiles/Backup/Auth）

## 阶段 1: providers 命令

- [x] Task 1.1: 创建 `cli/providers.py`
  - [x] 定义 PROVIDERS 常量（所有支持的 Provider）
  - [x] 实现 `list_providers()` 函数
  - [x] 实现 `get_provider_info()` 函数
  - [x] 实现 `check_provider_status()` 函数

- [x] Task 1.2: 注册 providers 命令到 _parser.py
- [x] Task 1.3: 注册 providers 命令到 main.py

## 阶段 2: models 命令

- [x] Task 2.1: 创建 `cli/models.py`
  - [x] 定义 MODELS 常量（所有支持的模型）
  - [x] 实现 `list_models()` 函数
  - [x] 实现 `get_model_info()` 函数
  - [x] 实现 `compare_models()` 函数

- [x] Task 2.2: 注册 models 命令到 _parser.py
- [x] Task 2.3: 注册 models 命令到 main.py

## 阶段 3: profiles 命令

- [x] Task 3.1: 使用现有 `cli/profiles.py`
  - [x] 使用 `ProfileManager` 类
  - [x] 实现 `list_profiles()` 函数
  - [x] 实现 `create_profile()` 函数
  - [x] 实现 `switch_profile()` 函数
  - [x] 实现 `delete_profile()` 函数

- [x] Task 3.2: 注册 profiles 命令到 _parser.py
- [x] Task 3.3: 注册 profiles 命令到 main.py

## 阶段 4: backup 命令

- [x] Task 4.1: 使用现有 `cli/backup.py`
  - [x] 使用 `backup_config()` 函数
  - [x] 使用 `list_backups()` 函数
  - [x] 使用 `restore_backup()` 函数
  - [x] 使用 `delete_backup()` 函数

- [x] Task 4.2: 注册 backup 命令到 _parser.py
- [x] Task 4.3: 注册 backup 命令到 main.py

## 阶段 5: auth 命令

- [x] Task 5.1: 增强 `cli/auth_cli.py`
  - [x] 实现 `AuthManager` 类
  - [x] 实现 `add_credential()` 函数
  - [x] 实现 `list_credentials()` 函数
  - [x] 实现 `delete_credential()` 函数
  - [x] 实现 `test_connection()` 函数

- [x] Task 5.2: 注册 auth 命令到 _parser.py
- [x] Task 5.3: 注册 auth 命令到 main.py

## Task Dependencies

- 所有任务已完成