from sage_poc.skill_ids import SKILL_REGISTRY
from sage_poc.skills.schema import load_skill

_SKILLS = {sid: load_skill(sid) for sid in SKILL_REGISTRY}
