# 核心约束（始终生效）

> 本文件包含 6 条强制约束，**绝对禁止**违反，违规代码不允许合并。

---

## 强制约束

| 约束 | 违规示例 | 正确做法 |
|------|---------|---------|
| 禁止意图理解硬编码 | `if "关键词" in text` | 使用 LLM 判断 |
| 禁止敏感信息硬编码 | `api_key = "sk-xxx"` | 从环境变量读取 |
| 禁止路径分隔符硬编码 | `path.replace("/", "\\")` | 使用 `pathlib.Path` |
| 禁止文本硬编码 | `return "你好"` | 使用 `i18n.t()` |
| 禁止使用标准 logging | `logging.getLogger(__name__)` | 使用 `common.logging_manager` |
| 禁止捕获所有异常 | `except:` | 指定具体异常类型 |

---

## 自检清单

每次提交前检查：

- [ ] 无意图理解硬编码关键词
- [ ] 无敏感信息硬编码（用环境变量）
- [ ] 路径用 `pathlib.Path`
- [ ] 日志使用统一日志系统 `common.logging_manager`
- [ ] 无用户可见文本硬编码（用 i18n）
- [ ] 无标准 `logging.getLogger`
- [ ] 无 `except:` 捕获所有异常
- [ ] common/ 只放基础设施代码