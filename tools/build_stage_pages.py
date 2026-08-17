#!/usr/bin/env python3
"""Build dependency-ordered stage pages from the canonical interview volumes.

The eight volume Markdown files remain the source of truth.  This script copies
complete <details class="qa"> blocks into curated stage pages, so fixes to an
answer flow into both the original volume and the ordered learning experience.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
INTERVIEWS = ROOT / "docs" / "interviews"
OUTPUT = ROOT / "docs" / "stages"

VOLUMES = {
    "v1": ("卷一", INTERVIEWS / "01_basics.md"),
    "v2": ("卷二", INTERVIEWS / "02_rl_algo.md"),
    "v3": ("卷三", INTERVIEWS / "03_vla_il.md"),
    "v4": ("卷四", INTERVIEWS / "04_world_sim.md"),
    "v5": ("卷五", INTERVIEWS / "05_engineering.md"),
    "v6": ("卷六", INTERVIEWS / "06_legged_control.md"),
    "v7": ("卷七", INTERVIEWS / "07_perception_nav.md"),
    "v8": ("卷八", INTERVIEWS / "08_coding_systemdesign.md"),
}

DETAIL_RE = re.compile(
    r'<details\s+class="[^"]*\bqa\b[^"]*"[^>]*>\s*<summary>.*?</summary>.*?</details>',
    re.DOTALL,
)
QUESTION_ID_RE = re.compile(r"<b>[^A-Z<]*([A-Z]+\d+[A-Z]?)</b>")


def qr(start: int, end: int, prefix: str = "Q") -> list[str]:
    return [f"{prefix}{number:02d}" for number in range(start, end + 1)]


@dataclass(frozen=True)
class Group:
    title: str
    why: str
    items: list[tuple[str, str]]


@dataclass(frozen=True)
class Stage:
    filename: str
    title: str
    subtitle: str
    prerequisite: str
    outcome: str
    groups: list[Group]
    previous: str
    next_page: str


def items(volume: str, question_ids: list[str]) -> list[tuple[str, str]]:
    return [(volume, question_id) for question_id in question_ids]


STAGE_4_GROUPS = [
    Group(
        "先理解模仿学习的基本矛盾",
        "先知道行为克隆为什么简单、又为什么会在闭环中累积错误。",
        items("v3", ["Q01", "Q02"]),
    ),
    Group(
        "建立 VLA 的组件视角",
        "先分清 VLM 与 VLA，再认识数据、视觉编码器和多模态连接器。",
        items("v3", ["Q30", "Q28", "Q29", "Q31"]),
    ),
    Group(
        "理解动作分块与 ACT",
        "从单步误差累积出发，理解为什么预测 action chunk，以及 ACT 如何实现。",
        items("v3", ["Q24", "Q26", "Q25"]),
    ),
    Group(
        "理解生成式动作头",
        "把多峰动作分布、Diffusion Policy、Flow Matching 和 π0 连起来。",
        items("v3", ["Q18", "Q20", "Q19"]),
    ),
    Group(
        "最后阅读 VLA 架构时间线",
        "现在再比较 RT、OpenVLA 与 π 系列，模型名会落到已经理解的组件上。",
        items("v3", qr(9, 17)),
    ),
]


STAGES = [
    Stage(
        "01_ml_foundations.md",
        "阶段 1 · 机器学习共同语言",
        "从训练闭环走到 Transformer，不再孤立背名词",
        "完成阶段 0，能解释张量、输入 / 输出和一次训练 step。",
        "能用“数据—模型—损失—更新—评测”解释分类、行为克隆和动作预测。",
        [
            Group("先理解训练为什么有效或失效", "从梯度、损失和数据划分建立训练闭环。", items("v1", ["Q02", "Q07", "Q19", "Q04", "Q10", "Q12", "Q13"])),
            Group("再理解深层网络如何稳定训练", "残差、归一化和 Dropout 分别处理不同问题。", items("v1", ["Q06", "Q03", "Q05"])),
            Group("最后进入 Transformer 与视觉 token", "先有优化直觉，再理解 Attention、位置、Softmax 和 ViT。", items("v1", ["Q01", "Q08", "Q14", "Q18"])),
            Group("最小手撕练习", "只实现最能检验理解的 LayerNorm 与 scaled dot-product attention。", items("v1", ["H04", "H01"])),
        ],
        "../learning/00_prerequisites.html",
        "02_robotics_control.html",
    ),
    Stage(
        "02_robotics_control.md",
        "阶段 2 · 机器人学与控制闭环",
        "从坐标表示到关节命令，建立动作真正落地的链路",
        "阶段 0 的坐标系直觉，以及基本向量 / 矩阵运算。",
        "能解释末端移动目标如何经过坐标变换、IK 和反馈控制变成电机命令。",
        [
            Group("从姿态与坐标变换开始", "任何运动学问题都先明确相对坐标系。", items("v1", ["Q35", "Q36", "Q37"])),
            Group("从正运动学走到逆运动学", "雅可比连接关节速度与末端速度，也是数值 IK 的核心。", items("v1", ["Q39", "Q38", "Q43"])),
            Group("把目标接入反馈控制", "区分控制空间，再理解 PID、阻抗与频率边界。", items("v1", ["Q41", "Q40", "Q42", "Q44"])),
            Group("最小手撕练习", "用代码把变换、数值 IK 与 PID 连成可执行链路。", items("v6", ["CH09", "CH07", "CH01"])),
        ],
        "01_ml_foundations.html",
        "03_rl_backbone.html",
    ),
    Stage(
        "03_rl_backbone.md",
        "阶段 3 · 强化学习骨架",
        "从 MDP 与 Bellman 方程走到 PPO、SAC 和 DQN",
        "理解状态、动作、轨迹、概率和梯度。",
        "能解释 PPO 与 SAC 的数据来源、更新方式和数据复用差异。",
        [
            Group("先定义问题与长期价值", "MDP 定义任务，折扣与 Bellman 方程定义如何评价未来。", items("v1", ["Q21", "Q28", "Q22", "Q24"])),
            Group("沿值函数与策略两条路线前进", "先分别理解 Q-learning 与 Policy Gradient，再在 Actor-Critic 合流。", items("v1", ["Q23", "Q25", "Q26"])),
            Group("建立算法选择坐标系", "on/off-policy、Advantage、PPO、SAC 与 Offline RL 是后续算法的定位骨架。", items("v1", ["Q27", "Q30", "Q31", "Q32", "Q33"])),
            Group("深入策略优化基础", "用 TD、GAE、重要性采样和多步回报理解 PPO 的来源。", items("v2", qr(1, 13))),
            Group("补齐连续与离散动作算法", "按 DDPG → TD3 / SAC、Q-learning → DQN 的问题改进链阅读。", items("v2", qr(14, 21))),
        ],
        "02_robotics_control.html",
        "04_vla_il.html",
    ),
    Stage(
        "04_vla_il.md",
        "阶段 4 · 模仿学习到 VLA",
        "从闭环分布偏移出发，逐层搭起视觉—语言—动作模型",
        "完成机器学习、机器人控制和 RL 三个基础阶段。",
        "看到新 VLA 时，能主动拆解 backbone、视觉编码、融合、动作头、数据和控制接口。",
        STAGE_4_GROUPS,
        "03_rl_backbone.html",
        "05_sim2real_world_models.html",
    ),
    Stage(
        "05_sim2real_world_models.md",
        "阶段 5 · 数据、Sim2Real 与世界模型",
        "先认识现实差距，再理解仿真、适应与想象训练",
        "理解轨迹、动力学、行为克隆和强化学习。",
        "能区分仿真器、世界模型、域随机化、系统辨识和教师—学生迁移。",
        [
            Group("先给 reality gap 分类", "从视觉、动力学、接触、传感器和时延理解仿真为何不能直接等同真机。", items("v4", qr(11, 16))),
            Group("再学习适应与仿真工程", "按 teacher-student → 仿真器 → 真机实战的顺序建立迁移流程。", items("v4", qr(17, 31))),
            Group("回头理解世界模型", "现在再看 RSSM、latent imagination 与 Dreamer，能分清学习模型和物理仿真器。", items("v4", qr(1, 10))),
            Group("连接 Offline RL", "理解固定数据上的分布外动作问题和约束方法。", items("v2", qr(22, 27))),
            Group("连接真实数据飞轮", "最后落到数据采集、公开数据与自主回流。", items("v5", qr(21, 26))),
        ],
        "04_vla_il.html",
        "06_engineering_debugging.html",
    ),
    Stage(
        "06_engineering_debugging.md",
        "阶段 6 · 工程落地与项目排障",
        "按数据流和频率边界，把模型接进真实机器人系统",
        "至少完成阶段 0–4，最好跑过一次训练或机器人实验。",
        "面对 loss 正常但真机失败，能按固定链路定位而不是随机调参。",
        [
            Group("先建立系统分层", "先明确感知、规划、控制、通信和任务编排的接口。", items("v5", qr(1, 5))),
            Group("沿真实项目数据链路前进", "从奖励、观测和动作设计走到采集、同步、清洗与真机故障。", items("v3", qr(53, 68))),
            Group("形成数据飞轮与排障顺序", "采集闭环之后，按可观测链路逐层排查失败。", items("v5", qr(21, 33))),
            Group("最后处理速度和训练规模", "模型先正确，再学习推理加速、边缘部署和分布式训练。", items("v5", qr(6, 20))),
        ],
        "05_sim2real_world_models.html",
        "../roadmap.html#阶段-7a--操作--vla-岗支线",
    ),
    Stage(
        "07a_vla_track.md",
        "阶段 7A · 操作 / VLA 岗支线",
        "把数据采集、动作表示、控制频率与真机评测连成项目故事",
        "完成阶段 0–6。",
        "能从数据到部署完整设计一个操作 VLA 项目，并解释关键取舍。",
        STAGE_4_GROUPS + [
            Group("补齐部署与数据回流", "聚焦 VLA 推理、数据采集和真机失败诊断。", items("v5", qr(6, 13) + qr(21, 33))),
            Group("补齐操作场景 Sim2Real", "把 reality gap、适应、仿真器和真机验证接入操作项目。", items("v4", qr(11, 31))),
            Group("用系统设计收口", "最后用完整 pipeline、服务和机器人系统设计检验表达。", items("v8", qr(31, 40))),
        ],
        "06_engineering_debugging.html",
        "08_coding_system_design.html",
    ),
    Stage(
        "07b_legged_track.md",
        "阶段 7B · 人形 / 四足控制岗支线",
        "按动力学—MPC—WBC—RL—Sim2Real—遥操作构建控制栈",
        "完成阶段 0–3，尤其是机器人学与 RL。",
        "能说明经典控制、RL 低层策略和 VLA 高层决策各自的边界。",
        [
            Group("浮动基座与接触动力学", "先理解腿足系统为什么不同于固定机械臂。", items("v6", qr(1, 7))),
            Group("MPC", "从模型、预测时域和接触时序进入实时优化控制。", items("v6", qr(8, 14))),
            Group("WBC", "把多个身体任务和约束统一到全身控制。", items("v6", qr(15, 20))),
            Group("RL locomotion", "在经典控制骨架之上理解并行仿真、奖励、适应和蒸馏。", items("v6", qr(21, 28))),
            Group("腿足 Sim2Real", "再处理执行器、接触与真机差异。", items("v6", qr(40, 45))),
            Group("遥操作", "进入人体动作映射、数据采集和闭环延迟。", items("v6", qr(29, 34))),
            Group("Loco-manipulation", "最后理解上下身耦合和分层控制。", items("v6", qr(35, 39))),
        ],
        "06_engineering_debugging.html",
        "08_coding_system_design.html",
    ),
    Stage(
        "07c_navigation_track.md",
        "阶段 7C · 感知 / SLAM / 导航岗支线",
        "先有几何定位，再加入语义、语言与端到端决策",
        "完成阶段 0–2，并理解基础视觉表示。",
        "能从传感器、定位和地图讲到语言目标、规划、控制与评测。",
        [
            Group("3D 感知", "先建立深度、点云和空间表征。", items("v7", qr(1, 6))),
            Group("SLAM 与状态估计", "有了几何观测，再处理跨帧位姿和地图。", items("v7", qr(12, 17))),
            Group("经典导航栈", "定位和地图稳定后，再学习全局 / 局部规划。", items("v7", qr(18, 22))),
            Group("Embodied VLM", "在几何栈上接入开放词汇检测、分割和语义地图。", items("v7", qr(43, 52))),
            Group("VLN", "理解语言指令如何变成导航决策。", items("v7", qr(23, 32))),
            Group("ObjectNav", "再处理开放目标、探索和零样本泛化。", items("v7", qr(33, 42))),
            Group("端到端与前沿判断", "最后评价分层方案和端到端 VLA 的边界。", items("v7", qr(53, 57))),
        ],
        "06_engineering_debugging.html",
        "08_coding_system_design.html",
    ),
    Stage(
        "08_coding_system_design.md",
        "阶段 8 · Coding 与系统设计收口",
        "按数据结构成组练习，再用十道系统题连接全部模块",
        "至少完成通用阶段，并选修一条岗位支线。",
        "能先澄清需求与指标，再讲数据流、频率、模型、部署、监控和恢复。",
        [
            Group("数组 / 哈希 / 滑动窗口", "先掌握最常用的线性扫描与状态维护。", items("v8", ["Q11", "Q01", "Q03", "Q14", "Q17"])),
            Group("链表", "从基本指针操作走到分组翻转与多链表合并。", items("v8", ["Q02", "Q13", "Q27", "Q07", "Q20"])),
            Group("栈 / 队列 / BFS", "把括号、单调结构、树和网格搜索放在一起。", items("v8", ["Q16", "Q18", "Q10", "Q12", "Q22"])),
            Group("区间 / 堆 / 搜索", "练习排序、优先队列和组合搜索。", items("v8", ["Q19", "Q05", "Q26", "Q28"])),
            Group("动态规划", "按一维状态到二维序列 DP 的难度推进。", items("v8", ["Q06", "Q08", "Q21", "Q25", "Q29", "Q24", "Q23"])),
            Group("系统设计", "用十道综合题把训练、推理、数据、传感器和机器人系统串起来。", items("v8", qr(31, 40))),
        ],
        "../roadmap.html",
        "../roadmap.html#28-天最小计划",
    ),
]


def load_questions() -> dict[str, dict[str, str]]:
    result: dict[str, dict[str, str]] = {}
    for volume_key, (_, path) in VOLUMES.items():
        markdown = path.read_text(encoding="utf-8")
        questions: dict[str, str] = {}
        for block in DETAIL_RE.findall(markdown):
            match = QUESTION_ID_RE.search(block)
            if not match:
                raise RuntimeError(f"Question without identifier in {path}")
            question_id = match.group(1)
            if question_id in questions:
                raise RuntimeError(f"Duplicate {question_id} in {path}")
            questions[question_id] = block.strip()
        result[volume_key] = questions
    return result


def render_stage(stage: Stage, question_bank: dict[str, dict[str, str]]) -> str:
    total = sum(len(group.items) for group in stage.groups)
    lines = [
        f"# {stage.title}",
        "",
        f"> {stage.subtitle}",
        "> 本页由原八卷题库自动抽取完整问答，并严格按知识依赖排序。原卷仍是内容源。",
        "",
        f"**先修**：{stage.prerequisite}",
        "",
        f"**本阶段共 {total} 题 · 通过标准**：{stage.outcome}",
        "",
        f"[← 上一步]({stage.previous}) · [返回总路线](../roadmap.html) · [下一步 →]({stage.next_page})",
        "",
        "---",
        "",
    ]
    sequence = 0
    for group_index, group in enumerate(stage.groups, start=1):
        lines.extend(
            [
                f"## 第 {group_index} 步 · {group.title}",
                "",
                f"> {group.why}",
                "",
            ]
        )
        for volume_key, question_id in group.items:
            sequence += 1
            volume_label = VOLUMES[volume_key][0]
            try:
                block = question_bank[volume_key][question_id]
            except KeyError as exc:
                raise RuntimeError(
                    f"Missing question {volume_key}/{question_id} in stage {stage.filename}"
                ) from exc
            enriched = block.replace(
                "<summary>",
                f'<summary><span class="seq">{sequence:02d}</span> '
                f'<span class="origin">{volume_label}</span> ',
                1,
            )
            lines.extend([enriched, ""])
        lines.extend(["---", ""])
    lines.extend(
        [
            "## 阶段结束时怎么复习",
            "",
            "1. 点击“全部折叠”，只看题目口述答案。",
            "2. 能说出答案后标记“已掌握”；不要因为“看懂了”就标记。",
            "3. 第二天使用“只看未掌握”，第 7 天再完整复述一次。",
            "4. 回到[总学习路线](../roadmap.html)，检查通过标准后再进入下一阶段。",
            "",
        ]
    )
    return "\n".join(lines)


def main() -> int:
    question_bank = load_questions()
    OUTPUT.mkdir(parents=True, exist_ok=True)
    expected = set()
    for stage in STAGES:
        target = OUTPUT / stage.filename
        target.write_text(render_stage(stage, question_bank), encoding="utf-8", newline="\n")
        expected.add(target.name)
        print(f"wrote {target.relative_to(ROOT)}")

    for stale in OUTPUT.glob("*.md"):
        if stale.name not in expected:
            raise RuntimeError(f"Unexpected stage source left in output: {stale}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
