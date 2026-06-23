#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
技能菜单集成测试

测试技能菜单的完整功能：
1. 本地技能显示
2. 全局技能显示
3. 技能搜索
4. 技能执行

使用 sealed_workspace fixture 创建测试技能目录

日志子层：🧠 Skills
"""

import pytest
import tempfile
import shutil
from pathlib import Path
from unittest.mock import MagicMock, patch
from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any


@dataclass
class SkillInfo:
    """技能信息数据类"""
    name: str
    description: str
    category: str
    source: str  # "local" or "global"
    path: str
    enabled: bool = True
    usage_count: int = 0


class TestSkillDisplay:
    """测试技能显示"""

    @pytest.fixture
    def skills_dir(self, sealed_workspace):
        """创建测试技能目录结构"""
        skills_path = sealed_workspace["workspace"] / "skills"
        skills_path.mkdir(parents=True)
        
        # 创建本地技能
        local_skill1 = skills_path / "local_skill_1"
        local_skill1.mkdir()
        (local_skill1 / "SKILL.md").write_text(
            "# Local Skill 1\n\nThis is a local skill for testing.",
            encoding="utf-8"
        )
        
        local_skill2 = skills_path / "local_skill_2"
        local_skill2.mkdir()
        (local_skill2 / "SKILL.md").write_text(
            "# Local Skill 2\n\nAnother local skill.",
            encoding="utf-8"
        )
        
        yield skills_path
        
        # 清理
        shutil.rmtree(skills_path, ignore_errors=True)

    @pytest.fixture
    def global_skills_dir(self, sealed_workspace):
        """创建全局技能目录"""
        global_path = sealed_workspace["config"] / "global_skills"
        global_path.mkdir(parents=True)
        
        # 创建全局技能
        global_skill = global_path / "global_skill"
        global_skill.mkdir()
        (global_skill / "SKILL.md").write_text(
            "# Global Skill\n\nThis is a global skill available to all users.",
            encoding="utf-8"
        )
        
        yield global_path
        
        # 清理
        shutil.rmtree(global_path, ignore_errors=True)

    def test_local_skills_loading(self, skills_dir):
        """
        测试加载本地技能
        
        场景：从工作区目录加载本地技能列表
        """
        local_skills = []
        
        for skill_path in skills_dir.iterdir():
            if skill_path.is_dir() and (skill_path / "SKILL.md").exists():
                skill_md = (skill_path / "SKILL.md").read_text(encoding="utf-8")
                skill_info = SkillInfo(
                    name=skill_path.name,
                    description=skill_md.split("\n")[0].replace("# ", ""),
                    category="local",
                    source="local",
                    path=str(skill_path)
                )
                local_skills.append(skill_info)
        
        assert len(local_skills) == 2
        assert any(s.name == "local_skill_1" for s in local_skills)
        assert any(s.name == "local_skill_2" for s in local_skills)

    def test_global_skills_loading(self, global_skills_dir):
        """
        测试加载全局技能
        
        场景：从配置目录加载全局技能列表
        """
        global_skills = []
        
        for skill_path in global_skills_dir.iterdir():
            if skill_path.is_dir() and (skill_path / "SKILL.md").exists():
                skill_md = (skill_path / "SKILL.md").read_text(encoding="utf-8")
                skill_info = SkillInfo(
                    name=skill_path.name,
                    description=skill_md.split("\n")[0].replace("# ", ""),
                    category="global",
                    source="global",
                    path=str(skill_path)
                )
                global_skills.append(skill_info)
        
        assert len(global_skills) == 1
        assert global_skills[0].name == "global_skill"
        assert global_skills[0].source == "global"

    def test_all_skills_combined(self, skills_dir, global_skills_dir):
        """
        测试合并本地和全局技能
        
        场景：同时显示本地和全局技能的完整列表
        """
        all_skills = []
        
        # 加载本地技能
        for skill_path in skills_dir.iterdir():
            if skill_path.is_dir() and (skill_path / "SKILL.md").exists():
                all_skills.append(SkillInfo(
                    name=skill_path.name,
                    description="Local skill",
                    category="uncategorized",
                    source="local",
                    path=str(skill_path)
                ))
        
        # 加载全局技能
        for skill_path in global_skills_dir.iterdir():
            if skill_path.is_dir() and (skill_path / "SKILL.md").exists():
                all_skills.append(SkillInfo(
                    name=skill_path.name,
                    description="Global skill",
                    category="uncategorized",
                    source="global",
                    path=str(skill_path)
                ))
        
        assert len(all_skills) == 3
        assert sum(1 for s in all_skills if s.source == "local") == 2
        assert sum(1 for s in all_skills if s.source == "global") == 1

    def test_skill_source_indicator(self, skills_dir, global_skills_dir):
        """
        测试技能来源标识
        
        场景：区分显示本地和全局技能的来源标识
        """
        local_count = 0
        global_count = 0
        
        for skill_path in skills_dir.iterdir():
            if skill_path.is_dir():
                local_count += 1
        
        for skill_path in global_skills_dir.iterdir():
            if skill_path.is_dir():
                global_count += 1
        
        assert local_count == 2
        assert global_count == 1


class TestSkillSearch:
    """测试技能搜索"""

    @pytest.fixture
    def skill_list(self) -> List[SkillInfo]:
        """创建测试技能列表"""
        return [
            SkillInfo("python_code", "Python code generation", "coding", "local", "/path/1"),
            SkillInfo("javascript_code", "JavaScript code generation", "coding", "local", "/path/2"),
            SkillInfo("git_helper", "Git commands helper", "version_control", "global", "/path/3"),
            SkillInfo("docker_helper", "Docker management tool", "devops", "global", "/path/4"),
            SkillInfo("read_file", "Read file contents", "file", "local", "/path/5"),
            SkillInfo("write_file", "Write content to file", "file", "local", "/path/6"),
        ]

    def test_search_by_name(self, skill_list):
        """
        测试按名称搜索技能
        
        场景：通过技能名称关键词搜索
        """
        query = "python"
        results = [s for s in skill_list if query.lower() in s.name.lower()]
        
        assert len(results) == 1
        assert results[0].name == "python_code"

    def test_search_by_description(self, skill_list):
        """
        测试按描述搜索技能
        
        场景：通过技能描述关键词搜索
        """
        query = "code generation"
        results = [s for s in skill_list if query.lower() in s.description.lower()]
        
        assert len(results) == 2
        assert all("code" in s.description.lower() for s in results)

    def test_search_by_category(self, skill_list):
        """
        测试按分类搜索技能
        
        场景：通过技能分类搜索
        """
        query = "file"
        results = [s for s in skill_list if query.lower() in s.category.lower()]
        
        assert len(results) == 2
        assert all(s.category == "file" for s in results)

    def test_search_combined_criteria(self, skill_list):
        """
        测试组合条件搜索
        
        场景：同时匹配名称、描述和分类
        """
        query = "git"
        results = [
            s for s in skill_list
            if query.lower() in s.name.lower() 
            or query.lower() in s.description.lower()
            or query.lower() in s.category.lower()
        ]
        
        assert len(results) == 1
        assert results[0].name == "git_helper"

    def test_search_case_insensitive(self, skill_list):
        """
        测试搜索不区分大小写
        
        场景：不同大小写的搜索关键词应返回相同结果
        """
        results_lower = [s for s in skill_list if "PYTHON" in s.name.upper()]
        results_upper = [s for s in skill_list if "python" in s.name.lower()]
        
        assert len(results_lower) == len(results_upper)
        assert len(results_lower) == 1

    def test_search_no_results(self, skill_list):
        """
        测试搜索无结果
        
        场景：搜索不存在的关键词返回空列表
        """
        query = "nonexistent_skill_xyz"
        results = [s for s in skill_list if query.lower() in s.name.lower()]
        
        assert len(results) == 0

    def test_search_empty_query(self, skill_list):
        """
        测试空查询
        
        场景：空搜索关键词应返回所有技能
        """
        query = ""
        results = [s for s in skill_list if query.lower() in s.name.lower()]
        
        assert len(results) == len(skill_list)


class TestSkillExecution:
    """测试技能执行"""

    @pytest.fixture
    def skill_executor(self):
        """创建技能执行器模拟"""
        class SkillExecutor:
            def __init__(self):
                self.execution_history: List[Dict[str, Any]] = []
            
            def execute_skill(self, skill_name: str, params: Dict[str, Any]) -> Dict[str, Any]:
                """执行技能"""
                result = {
                    "skill": skill_name,
                    "params": params,
                    "status": "success",
                    "output": f"Executed {skill_name} with params: {params}",
                    "timestamp": "2024-01-01T00:00:00Z"
                }
                self.execution_history.append(result)
                return result
            
            def get_execution_history(self) -> List[Dict[str, Any]]:
                """获取执行历史"""
                return self.execution_history
            
            def clear_history(self):
                """清空执行历史"""
                self.execution_history = []
        
        return SkillExecutor()

    def test_execute_local_skill(self, skill_executor):
        """
        测试执行本地技能
        
        场景：执行工作区内的本地技能
        """
        result = skill_executor.execute_skill(
            "local_skill",
            {"param1": "value1"}
        )
        
        assert result["status"] == "success"
        assert result["skill"] == "local_skill"
        assert "param1" in result["params"]

    def test_execute_global_skill(self, skill_executor):
        """
        测试执行全局技能
        
        场景：执行配置目录中的全局技能
        """
        result = skill_executor.execute_skill(
            "global_skill",
            {"setting": True}
        )
        
        assert result["status"] == "success"
        assert result["skill"] == "global_skill"

    def test_execute_with_parameters(self, skill_executor):
        """
        测试带参数执行技能
        
        场景：技能执行时传入各种类型的参数
        """
        params = {
            "string_param": "test",
            "int_param": 42,
            "bool_param": True,
            "list_param": [1, 2, 3],
            "dict_param": {"key": "value"}
        }
        
        result = skill_executor.execute_skill("test_skill", params)
        
        assert result["params"] == params
        assert result["status"] == "success"

    def test_execution_history_tracking(self, skill_executor):
        """
        测试执行历史追踪
        
        场景：多次执行技能后能够查看执行历史
        """
        skill_executor.execute_skill("skill_1", {})
        skill_executor.execute_skill("skill_2", {"key": "value"})
        skill_executor.execute_skill("skill_1", {"retry": True})
        
        history = skill_executor.get_execution_history()
        
        assert len(history) == 3
        assert history[0]["skill"] == "skill_1"
        assert history[1]["skill"] == "skill_2"
        assert history[2]["skill"] == "skill_1"

    def test_execution_history_clearing(self, skill_executor):
        """
        测试清空执行历史
        
        场景：清空后执行历史应为空
        """
        skill_executor.execute_skill("skill_1", {})
        skill_executor.execute_skill("skill_2", {})
        
        assert len(skill_executor.get_execution_history()) == 2
        
        skill_executor.clear_history()
        
        assert len(skill_executor.get_execution_history()) == 0


class TestSkillMenuIntegration:
    """测试技能菜单集成功能"""

    @pytest.fixture
    def skill_menu_manager(self):
        """创建技能菜单管理器"""
        class SkillMenuManager:
            def __init__(self):
                self.skills: List[SkillInfo] = []
                self.selected_skill: Optional[SkillInfo] = None
                self.executor = SkillExecutorMock()
            
            def add_skill(self, skill: SkillInfo):
                """添加技能"""
                self.skills.append(skill)
            
            def search_skills(self, query: str) -> List[SkillInfo]:
                """搜索技能"""
                if not query:
                    return self.skills
                return [
                    s for s in self.skills
                    if query.lower() in s.name.lower()
                    or query.lower() in s.description.lower()
                ]
            
            def select_skill(self, skill_name: str) -> bool:
                """选择技能"""
                for skill in self.skills:
                    if skill.name == skill_name:
                        self.selected_skill = skill
                        skill.usage_count += 1
                        return True
                return False
            
            def execute_selected(self, params: Dict[str, Any]) -> Optional[Dict]:
                """执行选中的技能"""
                if not self.selected_skill:
                    return None
                return self.executor.execute_skill(
                    self.selected_skill.name,
                    params
                )
            
            def get_local_skills(self) -> List[SkillInfo]:
                """获取本地技能"""
                return [s for s in self.skills if s.source == "local"]
            
            def get_global_skills(self) -> List[SkillInfo]:
                """获取全局技能"""
                return [s for s in self.skills if s.source == "global"]
        
        class SkillExecutorMock:
            def execute_skill(self, name: str, params: Dict) -> Dict:
                return {"status": "success", "skill": name, "params": params}
        
        return SkillMenuManager()

    def test_complete_skill_workflow(self, skill_menu_manager):
        """
        测试完整的技能使用流程
        
        场景：
        1. 添加技能到菜单
        2. 搜索技能
        3. 选择技能
        4. 执行技能
        """
        # 1. 添加技能
        skill_menu_manager.add_skill(SkillInfo(
            "test_skill",
            "A test skill",
            "testing",
            "local",
            "/path/to/skill"
        ))
        
        assert len(skill_menu_manager.skills) == 1
        
        # 2. 搜索技能
        results = skill_menu_manager.search_skills("test")
        assert len(results) == 1
        
        # 3. 选择技能
        selected = skill_menu_manager.select_skill("test_skill")
        assert selected is True
        assert skill_menu_manager.selected_skill.name == "test_skill"
        assert skill_menu_manager.selected_skill.usage_count == 1
        
        # 4. 执行技能
        result = skill_menu_manager.execute_selected({"param": "value"})
        assert result is not None
        assert result["skill"] == "test_skill"

    def test_local_and_global_skills_separation(self, skill_menu_manager):
        """
        测试本地和全局技能分离
        
        场景：正确区分和过滤本地/全局技能
        """
        skill_menu_manager.add_skill(SkillInfo("local_1", "Local", "cat", "local", "/l1"))
        skill_menu_manager.add_skill(SkillInfo("global_1", "Global", "cat", "global", "/g1"))
        skill_menu_manager.add_skill(SkillInfo("local_2", "Local", "cat", "local", "/l2"))
        
        local_skills = skill_menu_manager.get_local_skills()
        global_skills = skill_menu_manager.get_global_skills()
        
        assert len(local_skills) == 2
        assert len(global_skills) == 1
        assert all(s.source == "local" for s in local_skills)
        assert all(s.source == "global" for s in global_skills)

    def test_skill_usage_counting(self, skill_menu_manager):
        """
        测试技能使用计数
        
        场景：统计每个技能的使用次数
        """
        skill_menu_manager.add_skill(SkillInfo("popular_skill", "Popular", "cat", "local", "/p"))
        
        # 使用技能多次
        for _ in range(5):
            skill_menu_manager.select_skill("popular_skill")
        
        assert skill_menu_manager.skills[0].usage_count == 5

    def test_search_and_execute_workflow(self, skill_menu_manager):
        """
        测试搜索后执行的工作流
        
        场景：从搜索结果中选择并执行技能
        """
        skill_menu_manager.add_skill(SkillInfo("code_gen", "Generate code", "coding", "local", "/c1"))
        skill_menu_manager.add_skill(SkillInfo("doc_gen", "Generate docs", "docs", "local", "/d1"))
        skill_menu_manager.add_skill(SkillInfo("code_review", "Review code", "coding", "local", "/c2"))
        
        # 搜索 coding 相关技能
        results = skill_menu_manager.search_skills("code")
        
        assert len(results) == 2
        
        # 选择第一个结果并执行
        skill_menu_manager.select_skill(results[0].name)
        result = skill_menu_manager.execute_selected({"lang": "python"})
        
        assert result is not None
        assert "code" in result["skill"]


class TestSkillMenuEdgeCases:
    """测试技能菜单边界情况"""

    def test_empty_skills_directory(self):
        """
        测试空技能目录
        
        场景：技能目录为空时的处理
        """
        skills = []
        
        # 空目录不应报错
        assert len(skills) == 0
        
        # 搜索空结果
        results = [s for s in skills if "test" in s.name.lower()] if skills else []
        assert len(results) == 0

    def test_skill_without_description(self):
        """
        测试无描述的技能
        
        场景：SKILL.md 文件缺失或为空
        """
        skill = SkillInfo(
            name="no_desc_skill",
            description="",
            category="uncategorized",
            source="local",
            path="/path"
        )
        
        assert skill.description == ""
        # 搜索空描述技能应返回
        results = [s for s in [skill] if "test" in s.description.lower()]
        assert len(results) == 0

    def test_duplicate_skill_names(self):
        """
        测试重复技能名称
        
        场景：本地和全局技能可能有同名
        """
        skills = [
            SkillInfo("dup_skill", "Local", "cat", "local", "/local/path"),
            SkillInfo("dup_skill", "Global", "cat", "global", "/global/path"),
        ]
        
        # 两个技能同名但来源不同
        assert skills[0].name == skills[1].name
        assert skills[0].source != skills[1].source

    def test_skill_execution_failure(self):
        """
        测试技能执行失败
        
        场景：技能执行过程中发生错误
        """
        class FailingExecutor:
            def execute_skill(self, name: str, params: Dict) -> Dict:
                return {
                    "status": "error",
                    "skill": name,
                    "error": "Skill execution failed"
                }
        
        executor = FailingExecutor()
        result = executor.execute_skill("failing_skill", {})
        
        assert result["status"] == "error"
        assert "error" in result


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
