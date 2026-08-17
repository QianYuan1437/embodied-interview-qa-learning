# 阶段 4 · 模仿学习到 VLA

> 从闭环分布偏移出发，逐层搭起视觉—语言—动作模型
> 本页由原八卷题库自动抽取完整问答，并严格按知识依赖排序。原卷仍是内容源。

**先修**：完成机器学习、机器人控制和 RL 三个基础阶段。

**本阶段共 21 题 · 通过标准**：看到新 VLA 时，能主动拆解 backbone、视觉编码、融合、动作头、数据和控制接口。

[← 上一步](03_rl_backbone.html) · [返回总路线](../roadmap.html) · [下一步 →](05_sim2real_world_models.html)

---

## 第 1 步 · 先理解模仿学习的基本矛盾

> 先知道行为克隆为什么简单、又为什么会在闭环中累积错误。

<details class="qa">
<summary><span class="seq">01</span> <span class="origin">卷三</span> <span class="lv lv-l1">L1</span> <span class="freq">🔥×12</span> <b>Q01</b> · Behavior Cloning（BC）是什么？为什么会有 covariate shift？怎么缓解？</summary>

**答**：BC 把专家轨迹 $(s, a^*)$ 当监督学习样本，学 $\pi_\theta(a \mid s)$ 最小化 $\|a - a^*\|^2$（连续动作）或交叉熵（离散）。

**Covariate shift**（协变量偏移）：策略一旦小偏离专家分布，落入未见状态 → 误差累积 → 长程任务复利崩塌，T 步误差按 $O(\epsilon T^2)$ 增长。

**缓解**：① **DAgger** — 迭代收集策略访问态 + 专家标注，几乎消除 shift；② 数据扩增（轨迹噪声/镜像/回放）；③ **Action Chunking** — 一次预测 K 步，把"复利"压成 $T/K$ 次；④ Diffusion Policy 多模态分布建模；⑤ 加 RL 微调（IL + RL）。

**易错**：BC 不是"数据多就行"——数据多但仍偏专家分布，shift 不会自动消失；需要让策略实际访问的状态分布也在数据里。

</details>

<details class="qa">
<summary><span class="seq">02</span> <span class="origin">卷三</span> <span class="lv lv-l1">L1</span> <span class="freq">🔥×11</span> <b>Q02</b> · BC、DAgger、GAIL、IRL 的区别与适用场景？</summary>

**答**：
- **BC**：监督学习直接学 $\pi(a\mid s)$；简单、需要大量演示，有 shift。**场景**：数据足、任务短。
- **DAgger**：BC + 主动学习，迭代让策略访问的新状态由专家标注；几乎消除 shift。**场景**：专家在线可查询（仿真 / 人在回路）。
- **GAIL**：生成对抗 IL，判别器区分"策略 vs 专家"轨迹，policy 通过 RL 最大化欺骗判别器；无需 reward。**场景**：复杂行为、reward 难写。
- **IRL**：反推 reward function $R(s,a)$，再 RL 求解；可解释、可泛化。**场景**：想理解专家"为什么这么做"。

**易错**：DAgger 不是 BC 的"训练 trick"，是要持续访问专家；GAIL 训练不稳（GAN 通病），机器人上较少用。

</details>

---

## 第 2 步 · 建立 VLA 的组件视角

> 先分清 VLM 与 VLA，再认识数据、视觉编码器和多模态连接器。

<details class="qa">
<summary><span class="seq">03</span> <span class="origin">卷三</span> <span class="lv lv-l1">L1</span> <span class="freq">🔥×5</span> <b>Q30</b> · VLM 和 VLA 的区别是什么？VLA 多了什么模块？token 化方案怎么变？</summary>

**答**：
| | VLM（Vision-Language Model） | VLA（Vision-Language-Action） |
|---|---|---|
| 输入 | 图像 + 文本 | 图像 + 文本指令 + 历史 proprio |
| 输出 | 文本 token | **动作**（连续 / 离散 token） |
| 训练数据 | web 图文 | web + **机器人轨迹** |
| 多出模块 | — | **Action head**（离散 token 或 Flow Matching 头） |

**Token 化方案**：
- VLM：仅 text token（如 32K vocab）。
- VLA：text token + **action token**——
  - 离散方案（RT-2 / OpenVLA）：每维动作 256 bin，复用 LLM 词表最不常用 256 token；一步 7 维 = 7 token。
  - 连续方案（π0 / RDT）：action 不 token 化，直接由独立 Action Expert（Flow Matching / Diffusion）输出。
  - FAST：DCT + BPE 把 chunk 压成更少 token，介于两者之间。

**易错**：VLA 不是 "VLM 加个 head" 就完事——训练时要 co-finetune 机器人数据，否则 VLM 在动作分布上零样本不行。

</details>

<details class="qa">
<summary><span class="seq">04</span> <span class="origin">卷三</span> <span class="lv lv-l1">L1</span> <span class="freq">🔥×8</span> <b>Q28</b> · 介绍一下 Open-X-Embodiment 数据集，它解决了什么问题？数据多样性对 VLA 泛化的影响？</summary>

**答**：**Open-X-Embodiment（OXE）**：2023-10 Google 联合 21 个 lab 发布，约 **60 个数据集 / 22 种 embodiment / 1M+ 轨迹**（OpenVLA 训练用其中 curated **~970K** 子集）。是迄今最大的跨实验室、跨形态机器人数据集。

**解决的问题**：
1. **单 lab 数据量太小**（< 100K），scale 不起来。
2. **跨形态无数据**：每 lab 用不同机器人，无法对比/合并。
3. **任务覆盖窄**：单数据集多为 pick & place，缺多样性。

**对 VLA 泛化的影响**：
- RT-X 论文实证：在 OXE 上联合训练比单数据集训练，跨场景成功率显著提升。
- 数据多样性（任务 / 场景 / embodiment）比数据量本身更关键。
- OpenVLA / π0 都以 OXE 为预训练基础。

**易错**：OXE ≠ 一个统一格式的数据集，是 ~60 个原始数据集 + RLDS 统一接口；动作空间标准化到 7 维末端 + gripper（不足补 0）。

</details>

<details class="qa">
<summary><span class="seq">05</span> <span class="origin">卷三</span> <span class="lv lv-l2">L2</span> <span class="freq">🔥×7</span> <b>Q29</b> · OpenVLA 的视觉编码器为什么用 SigLIP + DINOv2 双路融合？只用 CLIP 行不行？</summary>

**答**：**SigLIP** 与 **DINOv2** 各有所长：
- **SigLIP**（image-text contrastive）：偏**语义**（"杯子" → 杯子图像），对自然语言强对齐。
- **DINOv2**（自监督）：偏**空间几何**（深度、表面纹理、空间结构），对场景结构敏感。

**双路融合**：两个编码器各出 patch tokens，**channel-wise concat**（不是 cross-attention），喂给 LLM。

**只用 SigLIP 不行**：
1. SigLIP / CLIP 对**空间几何弱**——能识别"杯子"但不知"杯子距夹爪 5 cm 偏左"。
2. 机器人操作高度依赖空间推理（抓取位姿、避障）。
3. **Prismatic VLM** 论文实证：双路 > SigLIP > DINOv2 > CLIP，在 robotics benchmark 上差距明显。

**易错**：双路融合不是 ensemble，是同时给 LLM 输入两套 tokens；LLM 自己学如何用。

</details>

<details class="qa">
<summary><span class="seq">06</span> <span class="origin">卷三</span> <span class="lv lv-l2">L2</span> <span class="freq">🔥×4</span> <b>Q31</b> · 多模态对齐里 Q-Former、projection、cross-attention 这几种 connector 的区别？</summary>

**答**：**Connector** = 把视觉特征对齐到 LLM 输入空间的模块。

| Connector | 代表 | 机制 | token 数 |
|---|---|---|---|
| **Projection** | LLaVA | MLP 直接映射 patch → token | = patch 数（多） |
| **Q-Former** | BLIP-2 | 可学 query 通过 cross-attn 提取关键视觉特征 | **可压缩**（少） |
| **Cross-Attention** | Flamingo | 在 LLM 每层插 cross-attn 与视觉特征交互 | 不增 input token，但**改 LLM 结构** |

**VLA 实务**：
- **Projection（OpenVLA / Prismatic）**：简单、稳；token 数多（256-576 / 图）但 LLM 能扛。
- **Q-Former**：复杂、训练不稳；VLA 上较少用。
- **Cross-Attention**：需改 LLM 架构；不便于直接用现成 VLM 权重。

**易错**：Q-Former 不是"更先进"——LLaVA 系列证明 projection 简单 + 数据多反而更好。

</details>

---

## 第 3 步 · 理解动作分块与 ACT

> 从单步误差累积出发，理解为什么预测 action chunk，以及 ACT 如何实现。

<details class="qa">
<summary><span class="seq">07</span> <span class="origin">卷三</span> <span class="lv lv-l1">L1</span> <span class="freq">🔥×10</span> <b>Q24</b> · 什么是 Action Chunking？为什么 VLA 要预测一个动作 chunk 而不是单步动作？块大小怎么选？</summary>

**答**：**Action Chunking**：策略一次预测 K 步连续动作 $a_{t:t+K}$ 而非单步 $a_t$。

**执行方式**：
- **Open-loop**：执行整个 chunk 再重新规划。
- **Receding-horizon**：执行 1 步重规划，类似 MPC。
- **Ensemble**：多 chunk 重叠用 EMA / 投票（ACT 用法）。

**好处**：
1. **减少高频推理开销**：K 倍。
2. **平滑动作**：相邻步内插值好，减少抖动。
3. **显式建模时序相关性**：尤其 diffusion / flow 类策略受益。
4. **缓解复合误差**：T 步任务的"高层决策点"从 T 降到 $T/K$，整体偏离专家分布的次数变少；但 chunk 内仍是 open-loop，不能严格消除 covariate shift。

**块大小**：
- ALOHA / 精细操作：K = 8-16（160-320 ms）。
- π0：K = 50（50 Hz 下 1 秒，长程任务）。
- 任务变化慢可更长；环境多变需更短。

**易错**：chunk 太长牺牲反应性（环境突变前已锁死动作）；4-16 在 manipulation 上是甜区。

</details>

<details class="qa">
<summary><span class="seq">08</span> <span class="origin">卷三</span> <span class="lv lv-l1">L1</span> <span class="freq">🔥×7</span> <b>Q26</b> · 模仿学习里"复合误差"指什么？Action Chunking 是怎么缓解它的？理论解释是什么？</summary>

**答**：**复合误差**（compounding error）：BC 在每步犯小错 $\epsilon$，T 步后误差累积为 $O(\epsilon T^2)$（在最坏情况下二次增长）；策略一旦偏离专家分布，错误像复利一样雪崩。

**Action Chunking 缓解**：一次决策 K 步，等价于把 T 步轨迹划成 $T/K$ 个"决策点"，**chunk 内动作 joint 预测，不会因单步偏离累积**；只在 chunk 之间的决策点处可能累积。

**直觉**：高层重规划次数从 $T$ 降到 $T/K$，复合误差量级随之缩小；但 chunk 内部仍是 open-loop，环境扰动或专家不一致仍会让单 chunk 内误差累积，因此并非"严格平方降阶"。

**实证**：ACT 论文中较大 chunk 在插针等高精度任务上显著优于单步；最佳 K 与任务变化率相关，过长牺牲反应性。

**易错**：chunking 不解决"OOD 状态"本身——只减少"高层决策点数量"；仍需 DAgger / 数据多样性来覆盖 OOD。

</details>

<details class="qa">
<summary><span class="seq">09</span> <span class="origin">卷三</span> <span class="lv lv-l2">L2</span> <span class="freq">🔥×8</span> <b>Q25</b> · ACT（Action Chunking with Transformers）的结构是什么？它用 VAE / CVAE 解决了什么问题？</summary>

**答**：**ACT 结构**（ALOHA 团队 2023）：Encoder-Decoder Transformer + **CVAE**。

- **Encoder**：图像 + proprio + 文本指令 → 上下文特征。
- **Decoder**：自回归 / 一次性输出 K 步动作 chunk。
- **CVAE**：训练时额外 encoder 把 (动作 chunk, 观测) → latent $z$，KL 正则到 $\mathcal{N}(0, I)$；decoder 用 $(z, \text{观测})$ 还原 chunk。
- **推理时不用 encoder**：直接 $z = 0$（mean）→ decoder 出 chunk。

**CVAE 解决的问题**：**多模态动作分布**。直接 MSE 回归 chunk 会把"专家 A 走左路 / 专家 B 走右路"平均成"中间路"（物理不可执行）。CVAE 让 $z$ 编码"走哪条路的意图"，推理 $z=0$ 输出**某条代表性路径**而非 mean。

**易错**：ACT 推理用 $z=0$ 不是"取所有路径平均"，而是"取 prior 的 mode"，仍是某条具体路径。

</details>

---

## 第 4 步 · 理解生成式动作头

> 把多峰动作分布、Diffusion Policy、Flow Matching 和 π0 连起来。

<details class="qa">
<summary><span class="seq">10</span> <span class="origin">卷三</span> <span class="lv lv-l2">L2</span> <span class="freq">🔥×11</span> <b>Q18</b> · Diffusion Policy 怎么把动作建模成"去噪过程"？相比 BC 直接回归动作有什么优势？</summary>

**答**：**建模**：把动作分布 $\pi(a \mid s)$ 用 score-based diffusion 建模。
- **训练**：在专家动作 $a^*$ 上加噪 $a_\tau = \sqrt{\bar\alpha_\tau} a^* + \sqrt{1-\bar\alpha_\tau}\,\varepsilon$，学噪声预测器 $\varepsilon_\theta(a_\tau, \tau, s)$。
- **推理**：从 $\varepsilon \sim \mathcal{N}(0, I)$ 起，反向 SDE/ODE 逐步 denoise 到 $a$（DDPM 50 步 / DDIM 10-20 步）。

**vs BC 优势**：
1. **多模态分布**：BC 回归会"平均"多专家路径输出"中间"不可执行动作；diffusion 显式建模多峰。
2. **chunk 一次生成**：天然支持 K 步动作 chunk（去噪整段而非单步）。
3. **长尾任务更稳**：噪声扰动训练相当于隐式数据增强。

**缺点**：① **推理慢**（10-50 step），高频控制需并行/蒸馏；② 训练目标对噪声调度敏感。

**易错**：Diffusion Policy 不是"在 BC loss 上加噪声"，是完全不同的 score-based 框架。

</details>

<details class="qa">
<summary><span class="seq">11</span> <span class="origin">卷三</span> <span class="lv lv-l2">L2</span> <span class="freq">🔥×8</span> <b>Q20</b> · Diffusion 和 Flow Matching 有什么本质区别？为什么 Flow Matching 在机器人上越来越流行？</summary>

**答**：**本质区别**：
| | Diffusion | Flow Matching |
|---|---|---|
| 数学框架 | **SDE** 前向加噪 + 反向去噪 | **ODE** 沿运输路径走 |
| 学习目标 | 噪声 $\varepsilon$ 或 score $\nabla \log p_\tau$ | **速度场** $v_\theta$ |
| 路径定义 | 由 SDE 调度（cosine/linear）决定 | **显式给出** $x_\tau = \tau x_1 + (1-\tau) x_0$ |
| 推理 | SDE 求解器（慢） | ODE 求解器（快） |

**机器人流行原因**：
1. **推理快**：10 ODE step vs 50 SDE step，高频控制可行。
2. **训练稳**：速度场数值范围紧凑，loss 不爆炸。
3. **超参少**：无需选 cosine/linear 调度。
4. **理论统一**：Diffusion 是 FM 的特例（特定路径下）。

**易错**：FM 不是 Diffusion 的"加速版"，是更通用框架；Diffusion 可看作 FM 在特定路径上的实例。

</details>

<details class="qa">
<summary><span class="seq">12</span> <span class="origin">卷三</span> <span class="lv lv-l2">L2</span> <span class="freq">🔥×10</span> <b>Q19</b> · π0 为什么用 Flow Matching 而不是 Diffusion？50 Hz 控制频率背后的工程考量是什么？</summary>

**答**：**Flow Matching 优点**：
1. **训练更稳**：学速度场 $v_\theta$ 回归 $v^* = x_1 - x_0$，数值范围紧凑；diffusion 学 $\varepsilon$ 范围大、训练易抖。
2. **推理步数少**：10 步 ODE 即可 vs DDPM 50 步；省去 cosine/linear schedule 超参。
3. **路径显式**：$x_\tau = \tau x_1 + (1-\tau) x_0$，方差 $(1-\tau)^2 I$（不是 $(1-\tau) I$，常见笔误）。

**50 Hz 工程考量**：控制频率 50 Hz（20 ms / step）由底层执行端按 chunk 消耗动作。H=50 = **覆盖时长** ≈1 秒；**重规划频率**由 execution horizon / temporal ensemble / 异步队列决定，不是固定 1 Hz。

**易错**：50 Hz = 控制频率，H=50 = 覆盖时长，两者不要混成"每秒重算一次 chunk"。

</details>

---

## 第 5 步 · 最后阅读 VLA 架构时间线

> 现在再比较 RT、OpenVLA 与 π 系列，模型名会落到已经理解的组件上。

<details class="qa">
<summary><span class="seq">13</span> <span class="origin">卷三</span> <span class="lv lv-l2">L2</span> <span class="freq">🔥×15</span> <b>Q09</b> · OpenVLA 和 RT-2 在架构上的主要区别？OpenVLA 用 7B Llama-2 凭什么打过 55B 的 RT-2-X？</summary>

**答**：
| | OpenVLA | RT-2 / RT-2-X |
|---|---|---|
| Backbone | Llama-2 **7B**（Prismatic 框架） | PaLI-X **55B** 或 PaLM-E **12B**（闭源） |
| 视觉 | **SigLIP + DINOv2 双路** | PaLI-X / PaLM-E 内置 ViT（含 ViT-22B 等） |
| 动作头 | 每维 256 bin 离散化 → 复用 LLM 词表最不常用 256 token | 同 |
| 训练数据 | Open-X-Embodiment **970K** 轨迹 | Google 内部 + Open-X |
| 开源 | ✅ 全开源 + LoRA-friendly | ❌ 闭源 |

**胜出原因**：① **DINOv2 补足空间几何**——CLIP/SigLIP 偏语义弱几何，DINOv2 自监督预训练对空间结构更敏感；② Llama-2 web 文本 + 代码预训练更稳；③ 全开源使社区微调迭代更快。

**易错**：OpenVLA 不是"小胜大"玄学——是同等 fine-tune 量上的工程整合优势；零样本新任务上 RT-2-X 仍可能更强。

</details>

<details class="qa">
<summary><span class="seq">14</span> <span class="origin">卷三</span> <span class="lv lv-l2">L2</span> <span class="freq">🔥×9</span> <b>Q10</b> · RT-2 是怎么把动作编码成 token 的？为什么这种"动作即文本 token"方案有效但效率不高？</summary>

**答**：**方案**：动作向量 **7 维 = [Δx, Δy, Δz, Δroll, Δpitch, Δyaw, gripper]**，每维正态化到 $[-1, 1]$，再离散化为 **256 个 bin**；取 LLM 词表里**最不常用的 256 个 token** 复用为"动作 token"。一步动作 = **7 个 token**，与文本 token 同混训。

**有效**：① 复用 LLM 的 token embedding + 自回归解码，直接利用 web 知识；② co-finetune 文本 + 机器人数据，VLM 的常识能迁移；③ scale up 自然。

**低效**：① **7 token 串行 AR 解码**，单步推理 = 7 forward；chunk K 步则 $7K$ forward；OpenVLA 6 Hz 慢的根源。② 动作复用 LLM token 不是"自然"的——精度不足、跨任务泛化弱。

**改进**：① OpenVLA-OFT 用**并行解码** + 连续动作头；② π0-FAST 用 DCT + BPE 把 chunk 压成更少 token。

**易错**：256 bin 不是"够细"，是 VLM 复用的权衡；高精度任务（< 0.1 mm 插针）必失效。

</details>

<details class="qa">
<summary><span class="seq">15</span> <span class="origin">卷三</span> <span class="lv lv-l3">L3</span> <span class="freq">🔥×8</span> <b>Q11</b> · π0 / π0.5 / π0.6 三个版本的核心差异？KI（Knowledge Insulation）解决了什么？</summary>

**答**：
- **π0**（2024-10）：PaliGemma 3B（VLM）+ **Action Expert 300M**（独立 Flow Matching 动作头）+ 50 Hz 控制 + chunk **H = 50**。
- **π0.5**（2025）：核心是**开放世界泛化 + 多源 co-training**，让 π0 框架在更多任务/场景/embodiment 上稳定迁移；**KI（Knowledge Insulation）是 π0.5 框架的后续扩展**，隔离 VLM 与 Action Expert 梯度防止动作训练污染语言/视觉能力。
- **π0.6 / π*0.6**（2025-11）：核心创新 **RECAP**——把示教数据当 offline RL 用，advantage-conditioned 采样，强化"好动作 token"权重。
- **π0.7**（2026-04）：最新发布。

**KI 解决什么**：早期版本动作微调梯度反传会**破坏 VLM 的语言/视觉理解**（灾难性遗忘）；KI 用 stop-gradient + 双路梯度让两个模块各学各的。

**易错**：RECAP 属于 **π0.6**，不是 π0.5；π0.5 主体是"开放世界泛化"，KI 是配套扩展工作；π0.7 是 **2026-04** 发布。

</details>

<details class="qa">
<summary><span class="seq">16</span> <span class="origin">卷三</span> <span class="lv lv-l2">L2</span> <span class="freq">🔥×6</span> <b>Q12</b> · RDT-1B、Octo、GR00T-N1 都是 VLA，它们的动作头分别长什么样？哪种结构更"重"？</summary>

**答**：
| 模型 | 总参 | 动作头 | "重量" |
|---|---|---|---|
| **RDT-1B**（2024-10） | 1.2B | 整个 1.2B Transformer 当 **diffusion denoiser** | **最重** |
| **Octo**（2024-05） | ~93M | 小 Transformer encoder + **小 diffusion head（~10M）** | **最轻** |
| **GR00T-N1**（2025） | 2.2B | VLM 1.34B + **Action Expert 0.86B**（Flow Matching） | 中重 |

**trade-off**：
- Head 太轻（Octo）→ 多模态动作分布建模能力受限，复杂任务难。
- Head 太重（RDT）→ 表达力强但推理慢、训练贵。
- GR00T-N1 中庸路线，借鉴 π0 的 backbone + expert 拆分思路。

**易错**：RDT-1B 不是"另一个 OpenVLA"——它没用 LLM token 离散化，直接 backbone 当 denoiser；这是与 OpenVLA / RT-2 范式不同的"端到端 diffusion VLA"。

</details>

<details class="qa">
<summary><span class="seq">17</span> <span class="origin">卷三</span> <span class="lv lv-l2">L2</span> <span class="freq">🔥×6</span> <b>Q13</b> · FAST tokenizer 是怎么做的？为什么 DCT + BPE 组合比传统离散化高效 10×？</summary>

**答**：**FAST = DCT → scale → round → flatten → BPE**，五步缺一不可。

1. **DCT**（Discrete Cosine Transform）：把 H 步 × D 维动作 chunk 转频域，主要能量集中低频。
2. **Scale**：把 DCT 系数缩放到合适整数范围（e.g. ±100）。
3. **Round**：离散化为整数。
4. **Flatten**：二维 (H × D) → 一维序列。
5. **BPE**：用预训练 BPE tokenizer 把常见短模式压成单 token。

**高效 10× 原因**：① DCT 集中能量，**高频系数大多 ≈ 0**，round 后变长串 0；② BPE 把这些重复模式压成 1-2 token；③ chunk 越长压缩比越高（H=50 时尤甚）。

**效果**：π0-FAST 在同样 chunk 下，token 数从 ~400 降到 ~40，推理速度 5-10× 提升。

**易错**：FAST 不是 "DCT 单独用"，BPE 是关键；少一步压缩比就不够。

</details>

<details class="qa">
<summary><span class="seq">18</span> <span class="origin">卷三</span> <span class="lv lv-l2">L2</span> <span class="freq">🔥×5</span> <b>Q14</b> · OpenVLA 的动作是怎么离散化的（每维 256 个 bin）？这种方案在多大动作精度任务上会失效？</summary>

**答**：**离散化方案**：取每维动作（7 维（6-DoF 末端位姿 + 1 维 gripper））在训练集的 1%-99% 分位数区间，等分成 **256 个 bin**；超界截断。每个 bin 复用 LLM 词表里最不常用的 256 个 token。

**失效场景**：
1. **高精度任务**（< 0.1 mm 插针、拧螺丝）：256 bin 在 ±10 cm 量程下分辨率 ≈ 0.8 mm，精度不够。
2. **极端动作**：超 99% 分位被截断，剧烈动作不能表达。
3. **多模态动作**：256 bin 是单峰离散分布，难以表达"两条专家路径"这种多模态结构。

**改进**：① **OpenVLA-OFT** 换成**连续动作头 + L1 回归**；② π0 用 **Flow Matching** 连续动作建模；③ FAST tokenizer 提高压缩比同时保精度。

**易错**：256 bin 不是 OpenVLA 独创，RT-2 也是；这是 VLM 复用方案的固有局限。

</details>

<details class="qa">
<summary><span class="seq">19</span> <span class="origin">卷三</span> <span class="lv lv-l1">L1</span> <span class="freq">🔥×4</span> <b>Q15</b> · RT-1 → RT-2 → RT-X 的演进逻辑是什么？每一代的关键创新是什么？</summary>

**答**：
- **RT-1**（2022）：EfficientNet + FiLM + Token Learner；**130K 真机数据**；首个 large-scale robot Transformer paradigm，但无 web 知识。
- **RT-2**（2023）：PaLI-X 55B / PaLM-E 12B + 动作 token + **co-finetune（web + robot data）**；**首次把 web 知识灌入 robot policy**。
- **RT-X**（2023-10）：RT-1 / RT-2 在 **Open-X-Embodiment**（~60 datasets / 22 embodiments / 1M+ trajectories）上跨形态训练（实验用 robotics mixture 子集），验证跨 embodiment 泛化。OpenVLA 后续用 OXE 中约 **970K** curated demos 微调。

**主线**：RT-1 证 paradigm → RT-2 引 web 先验 → RT-X 验证联合训练。OpenVLA 是 RT-X 路线的开源版。

**易错**：RT-2 核心是 **co-finetune** 引入 web 数据，不是"放大版 RT-1"。

</details>

<details class="qa">
<summary><span class="seq">20</span> <span class="origin">卷三</span> <span class="lv lv-l2">L2</span> <span class="freq">🔥×4</span> <b>Q16</b> · π0 用的是哪个 VLM backbone？为什么选 PaliGemma 而不是 Llama？</summary>

**答**：**π0 backbone = PaliGemma**（SigLIP-400M 视觉编码器 + **Gemma-2B** 语言模型）。

**选择原因**：
1. **已对齐的 VLM**：PaliGemma 是 Google 联合预训练好的 vision-language 模型，比 "Llama + 外挂 ViT" 拼接更稳。
2. **Gemma-2B 够小**：50 Hz 高频推理（20 ms / step）要求 backbone 轻量；Llama-2 7B 在消费级 GPU 上跑不到 50 Hz。
3. **Apache 2.0 协议**：商用友好，机器人公司容易落地。
4. **Multimodal projector 现成**：图像 → 文本 token 的投影层已训练好。

**不用 Llama**：① text-only，需要再接视觉；② 7B 太重；③ Meta 协议有限制。

**易错**：**PaliGemma ≠ Gemma**——PaliGemma 含 SigLIP 视觉；说成 "π0 用 Llama" 是常见错（OpenVLA 才用 Llama-2 7B）。

</details>

<details class="qa">
<summary><span class="seq">21</span> <span class="origin">卷三</span> <span class="lv lv-l2">L2</span> <span class="freq">🔥×4</span> <b>Q17</b> · π0 里 Action Expert 的 300M 参数为什么单独拆出来？和 backbone 怎么交互？</summary>

**答**：**π0 结构**：PaliGemma 3B（VLM，frozen 或 LoRA） + **Action Expert 300M**（独立 Flow Matching 网络）。

**拆出原因**：
1. **负载分层**：每次重算 chunk，VLM forward 一次产条件特征；Action Expert 走约 10 步 flow ODE。重算频率由 execution horizon / async 决定（不是固定 1 Hz）。
2. **训练目标不同**：VLM 是 AR 语义损失，Action Expert 是 Flow Matching 速度场回归；放一起训会互相干扰。
3. **隔离梯度**（KI 思想）：动作微调不应破坏 VLM 的语言/视觉理解。

**交互**：VLM 编码 → 条件特征 $c$ → Action Expert 接 $(c, \text{noisy chunk}, \tau)$ → 约 10 步 ODE 出干净 chunk。chunk H=50 在 50 Hz 下覆盖 ~1 秒。

**易错**：Action Expert 是 joint training（不是独立）；H=50 = **覆盖时长**，不等于"每秒重算一次"。

</details>

---

## 阶段结束时怎么复习

1. 点击“全部折叠”，只看题目口述答案。
2. 能说出答案后标记“已掌握”；不要因为“看懂了”就标记。
3. 第二天使用“只看未掌握”，第 7 天再完整复述一次。
4. 回到[总学习路线](../roadmap.html)，检查通过标准后再进入下一阶段。
