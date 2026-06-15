# TUI 日志面板缺失日志修复规范

## Why

日志面板只显示部分日志，很多日志缺失。这是因为 `RichLog.write()` 默认是替换内容而非追加，且早期日志在 `on_mount` 之前就被丢弃了。

## What Changes

### 问题分析

1. **RichLog 追加模式问题** - `RichLog.write()` 默认行为是替换整个内容，需要研究正确的追加方式
2. **早期日志丢失** - `on_mount` 之前产生的日志被缓冲但未正确刷新
3. **日志截断** - 可能存在日志被过滤或截断的情况

### 修复方案

1. 研究 `RichLog` 的正确追加 API
2. 确保所有日志（包括缓冲的日志）都能正确显示
3. 验证日志显示完整性

## Impact

- Affected specs: TUI 日志面板
- Affected code: `cli/tui/textual_app.py` (TuiLogHandler), `cli/tui/sidebar.py` (RichLog)

## ADDED Requirements

### Requirement: 日志完整显示

系统 SHALL 显示所有后端产生的日志，不得丢失。

#### Scenario: 日志追加显示
- **WHEN** 后端产生日志消息
- **THEN** 日志消息追加显示在日志面板中，不覆盖之前的内容

#### Scenario: 早期日志刷新
- **WHEN** RichLog 组件就绪（on_mount）
- **THEN** 缓冲区内所有历史日志一次性刷新到面板中

#### Scenario: 大量日志显示
- **WHEN** 日志数量超过面板容量
- **THEN** 旧日志自动滚动出视图，但保留在历史记录中

## Success Criteria

- [ ] 日志面板能追加显示所有日志，不丢失
- [ ] on_mount 之前的日志能正确刷新到面板
- [ ] 大量日志时面板能正确滚动显示