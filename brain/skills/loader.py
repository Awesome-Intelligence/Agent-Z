"""
技能加载器
从 ~/.handsome_agent/skills/ 目录加载技能
支持 SKILL.md 格式
"""

import re
from pathlib import Path
from typing import List, Dict, Any, Optional
from dataclasses import dataclass, field


@dataclass
class LoadedSkill:
    """加载的技能"""
    skill_id: str
    name: str
    description: str
    category: str = ""
    tags: List[str] = field(default_factory=list)
    parameters: Dict[str, Any] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)
    path: str = ""
    enabled: bool = True


class SkillsLoader:
    """技能加载器 - 支持 SKILL.md 格式"""

    def __init__(self, skills_dir: Optional[str] = None):
        if skills_dir is None:
            from shared.config import get_skills_dir
            skills_dir = get_skills_dir()
        self.skills_dir = Path(skills_dir).expanduser()

    async def load_all(self) -> List[LoadedSkill]:
        """加载所有启用的技能"""
        skills = []

        if not self.skills_dir.exists():
            return []

        for skill_dir in self.skills_dir.iterdir():
            if not skill_dir.is_dir():
                continue

            if skill_dir.name.startswith("."):
                continue

            try:
                skill = await self._load_skill_dir(skill_dir)
                if skill:
                    skills.append(skill)
            except Exception as e:
                print(f"Failed to load skill {skill_dir}: {e}")

        return skills

    async def load_skill(self, skill_name: str) -> Optional[LoadedSkill]:
        """加载指定技能"""
        skill_dir = self.skills_dir / skill_name
        if not skill_dir.exists():
            return None
        return await self._load_skill_dir(skill_dir)

    async def _load_skill_dir(self, skill_dir: Path) -> Optional[LoadedSkill]:
        """从目录加载技能"""
        disabled_file = skill_dir / ".disabled"
        if disabled_file.exists():
            return None

        skill_file = skill_dir / "SKILL.md"
        if not skill_file.exists():
            return None

        try:
            content = skill_file.read_text(encoding="utf-8")
            metadata = self._parse_skill_md(content)

            return LoadedSkill(
                skill_id=skill_dir.name,
                name=metadata.get("name", skill_dir.name),
                description=metadata.get("description", ""),
                category=metadata.get("category", ""),
                tags=metadata.get("tags", []),
                parameters=metadata.get("parameters", {}),
                metadata=metadata,
                path=str(skill_dir),
                enabled=True,
            )
        except Exception as e:
            print(f"Failed to parse skill {skill_dir}: {e}")
            return None

    def _parse_skill_md(self, content: str) -> Dict[str, Any]:
        """解析 SKILL.md 内容"""
        metadata = {}

        lines = content.split("\n")
        in_frontmatter = False
        frontmatter_lines = []
        description_lines = []

        for line in lines:
            stripped = line.strip()

            if stripped == "---":
                if not in_frontmatter:
                    in_frontmatter = True
                    continue
                else:
                    in_frontmatter = False
                    metadata.update(self._parse_yaml_block("\n".join(frontmatter_lines)))
                    continue

            if in_frontmatter:
                frontmatter_lines.append(line)
            else:
                if stripped.startswith("# ") and not metadata.get("name"):
                    metadata["name"] = stripped[2:].strip()
                elif description_lines or (stripped and not stripped.startswith("#")):
                    description_lines.append(stripped)

        if not metadata.get("description") and description_lines:
            metadata["description"] = " ".join(description_lines[:3])

        return metadata

    def _parse_yaml_block(self, text: str) -> Dict[str, Any]:
        """简单解析 YAML frontmatter"""
        metadata = {}

        for line in text.split("\n"):
            if ":" in line:
                key, value = line.split(":", 1)
                key = key.strip()
                value = value.strip()

                if not value:
                    continue

                if value.startswith("[") and value.endswith("]"):
                    items = [item.strip() for item in value[1:-1].split(",")]
                    metadata[key] = items
                else:
                    metadata[key] = value

        return metadata

    def is_skill_enabled(self, skill_name: str) -> bool:
        """检查技能是否启用"""
        skill_dir = self.skills_dir / skill_name
        if not skill_dir.exists():
            return False
        disabled_file = skill_dir / ".disabled"
        return not disabled_file.exists()

    def get_disabled_skills(self) -> List[str]:
        """获取所有禁用的技能"""
        disabled = []

        if not self.skills_dir.exists():
            return disabled

        for skill_dir in self.skills_dir.iterdir():
            if not skill_dir.is_dir():
                continue
            if (skill_dir / ".disabled").exists():
                disabled.append(skill_dir.name)

        return disabled
