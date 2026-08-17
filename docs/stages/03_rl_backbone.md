# 阶段 3 · 强化学习骨架

> 从 MDP 与 Bellman 方程走到 PPO、SAC 和 DQN
> 本页由原八卷题库自动抽取完整问答，并严格按知识依赖排序。原卷仍是内容源。

**先修**：理解状态、动作、轨迹、概率和梯度。

**本阶段共 33 题 · 通过标准**：能解释 PPO 与 SAC 的数据来源、更新方式和数据复用差异。

[← 上一步](02_robotics_control.html) · [返回总路线](../roadmap.html) · [下一步 →](04_vla_il.html)

---

## 第 1 步 · 先定义问题与长期价值

> MDP 定义任务，折扣与 Bellman 方程定义如何评价未来。

<details class="qa">
<summary><span class="seq">01</span> <span class="origin">卷一</span> <span class="lv lv-l1">L1</span> <span class="freq">🔥×14</span> <b>Q21</b> · 什么是 MDP（马尔可夫决策过程）？五元组分别是什么？</summary>

**答**：MDP 是强化学习的数学框架：$\langle S, A, P, R, \gamma \rangle$

- $S$：状态空间（机器人关节角度、视觉观测等）
- $A$：动作空间（连续关节速度/位置，或离散动作）
- $P(s' \mid s, a)$：状态转移概率（环境动力学）
- $R(s, a, s')$：即时奖励函数
- $\gamma \in [0,1)$：折扣因子，权衡即时 vs 长期奖励

**Markov 性质**：$P(s_{t+1} \mid s_t, a_t, s_{<t}) = P(s_{t+1} \mid s_t, a_t)$，下一状态只依赖当前状态和动作，与历史无关。

**机器人现实**：几乎都是 POMDP（观测不完整），但以 MDP 作近似或用历史帧 stack 来还原 Markov 性。

**易错**：Markov 性是对**状态**的假设，不是对**观测**的假设；如果状态包含足够历史信息（如 RNN 隐状态），POMDP 也可被 MDP 框架处理。

</details>

<details class="qa">
<summary><span class="seq">02</span> <span class="origin">卷一</span> <span class="lv lv-l1">L1</span> <span class="freq">🔥×7</span> <b>Q28</b> · 折扣因子 gamma 的作用是什么？设置过大/过小会怎样？</summary>

**答**：$\gamma \in [0,1)$ 对未来奖励的权重指数衰减：$G_t = \sum_{k=0}^\infty \gamma^k r_{t+k}$。

**直觉**：① 数学上保证无限 horizon 的回报收敛（$\gamma < 1$）；② 语义上表示"对未来不确定性的折价"，近期奖励更可靠。

**$\gamma$ 太大（如 → 1）**：对遥远未来奖励权重高，bootstrap 误差远程传播，训练不稳定；长期规划强但 credit assignment 难（某奖励追溯很多步前的动作）。

**$\gamma$ 太小（如 → 0）**：只看即时奖励，变成贪心策略（myopic）；长程任务中错过关键延迟奖励。

**机器人取值**：通常 $\gamma \in [0.95, 0.99]$；稀疏奖励长程任务（200步以上）用 0.99；短程密集奖励（10步内）可用 0.95。

**易错**：$\gamma = 1$ 仅在有限 horizon + episode 一定结束的场景才可用；无限 horizon 时 $\gamma = 1$ 导致 return 不收敛。

</details>

<details class="qa">
<summary><span class="seq">03</span> <span class="origin">卷一</span> <span class="lv lv-l1">L1</span> <span class="freq">🔥×13</span> <b>Q22</b> · Bellman 方程是什么？V 和 Q 的关系？</summary>

**答**：**Bellman 期望方程**（某策略 $\pi$ 下）：

$$V^\pi(s) = \sum_a \pi(a \mid s) \sum_{s'} P(s' \mid s,a)[R(s,a,s') + \gamma V^\pi(s')]$$

$$Q^\pi(s, a) = \sum_{s'} P(s' \mid s,a)[R(s,a,s') + \gamma \sum_{a'} \pi(a' \mid s') Q^\pi(s', a')]$$

**关系**：$V^\pi(s) = \sum_a \pi(a \mid s) Q^\pi(s,a)$（对动作的加权期望）；$Q^\pi(s,a) = R + \gamma \mathbb{E}_{s'}[V^\pi(s')]$（即时奖励 + 折扣后继状态值）。

**最优 Bellman**：$V^*(s) = \max_a Q^*(s,a)$；$Q^*(s,a) = R + \gamma \mathbb{E}_{s'}[\max_{a'} Q^*(s', a')]$。

**易错**：Bellman 方程是递推定义（自洽方程），不是显式解；Q-learning 正是通过 TD 更新迭代逼近 $Q^*$，无需知道 $P$。

</details>

<details class="qa">
<summary><span class="seq">04</span> <span class="origin">卷一</span> <span class="lv lv-l1">L1</span> <span class="freq">🔥×10</span> <b>Q24</b> · Monte Carlo 和 TD 方法的区别？各自适合什么情况？</summary>

**答**：

| | Monte Carlo (MC) | TD (Temporal Difference) |
|---|---|---|
| 更新时机 | Episode 结束后（用完整回报 $G_t$） | 每步（用下一状态估计 bootstrap） |
| 方差 | 高（完整轨迹噪声叠加） | 低 |
| 偏差 | 无偏（真实样本 return） | 有偏（bootstrap 引入估计误差） |
| 适合场景 | 回合制、非 Markov 环境 | 持续交互、长 episode |

**联系**：TD($\lambda$) 通过 $\lambda$ 在 MC 和 TD 之间插值；GAE 是 TD($\lambda$) 在 advantage 估计中的应用（PPO 的核心组件）。

**易错**：MC 不需要 Markov 假设（用真实 return），但 variance 太高、数据利用率低；TD 需要 bootstrap（依赖 Markov 性），但在线学习效率高。机器人长任务（500步以上）用 TD 而非 MC。

</details>

---

## 第 2 步 · 沿值函数与策略两条路线前进

> 先分别理解 Q-learning 与 Policy Gradient，再在 Actor-Critic 合流。

<details class="qa">
<summary><span class="seq">05</span> <span class="origin">卷一</span> <span class="lv lv-l1">L1</span> <span class="freq">🔥×11</span> <b>Q23</b> · Q-learning 的更新公式是什么？DQN 相比 Q-learning 加了哪些改进？</summary>

**答**：**Q-learning 更新**（off-policy TD）：

$$Q(s_t, a_t) \leftarrow Q(s_t, a_t) + \alpha \underbrace{\big[r_t + \gamma \max_{a'} Q(s_{t+1}, a') - Q(s_t, a_t)\big]}_{\text{TD error}}$$

**DQN 三大改进**：
1. **Experience Replay**：将 $(s, a, r, s')$ 存入 replay buffer，随机采样打破样本相关性，提升数据效率
2. **Target Network**：用参数 $\theta^-$（定期硬拷贝或软更新）计算 $\max_{a'} Q(s', a'; \theta^-)$，稳定训练目标（否则目标也在变动 → 振荡）
3. **函数近似（神经网络）**：用 CNN 直接从像素输入端到端估计 $Q$ 值

**易错**：Q-learning 是 off-policy（目标用 max，不管行为策略）；SARSA 是 on-policy（用实际选择的 $a'$）；区别在 TD target 的动作来源。

</details>

<details class="qa">
<summary><span class="seq">06</span> <span class="origin">卷一</span> <span class="lv lv-l1">L1</span> <span class="freq">🔥×10</span> <b>Q25</b> · 策略梯度（Policy Gradient）的核心思想是什么？REINFORCE 算法怎么工作？</summary>

**答**：**核心**：直接参数化策略 $\pi_\theta(a \mid s)$，对 $J(\theta) = \mathbb{E}_\tau[G_0]$ 做梯度上升。策略梯度定理：$\nabla J = \mathbb{E}[\sum_t \nabla \log \pi_\theta(a_t|s_t) \cdot G_t]$。

**REINFORCE**：① 采样完整轨迹；② 计算 $G_t = \sum_{k \geq t}\gamma^{k-t}r_k$；③ 用 $\nabla \log \pi_\theta \cdot G_t$ 更新参数（on-policy）。

**直觉**：$G_t$ 大 → 增大 $a_t$ 的概率；$G_t$ 小 → 减小概率。等同于"奖励加权的最大似然"。

**易错**：REINFORCE 方差极高（$G_t$ 是完整轨迹的累积奖励，噪声大）→ 引入 baseline $b(s_t) = V(s_t)$，用 $A_t = G_t - V(s_t)$ 替代 $G_t$。Baseline 不改变期望梯度（$\mathbb{E}[\nabla \log \pi \cdot b] = 0$），但大幅降方差。这就是 Actor-Critic 的起点。

</details>

<details class="qa">
<summary><span class="seq">07</span> <span class="origin">卷一</span> <span class="lv lv-l1">L1</span> <span class="freq">🔥×9</span> <b>Q26</b> · Actor-Critic 是什么？为什么它结合了 PG 和值函数估计？</summary>

**答**：**Actor-Critic** = Actor（策略网络 $\pi_\theta$）+ Critic（值函数估计器 $V_\phi$ 或 $Q_\phi$）。

**Actor**：用策略梯度更新，目标是选更好的动作；
**Critic**：用 TD 误差训练，目标是准确估计 $V(s)$ 或 $Q(s,a)$；
**Critic 作 baseline**：$A_t = r_t + \gamma V_\phi(s_{t+1}) - V_\phi(s_t)$（TD advantage）直接作 Actor 的加权项，替代 REINFORCE 中的高方差 $G_t$。

**优势**：① 比纯 MC（REINFORCE）方差低（用 $A_t$）；② 比纯值方法（DQN）可以处理连续动作；③ 在线学习（不需要等 episode 结束）。

**延伸路径**：A2C（同步）→ A3C（异步）→ PPO（clip 截断比例）→ SAC（max-entropy AC）。

**易错**：Actor 和 Critic 可以共享主干（节省参数），也可以完全分开；机器人长程任务通常分开，防止两个目标梯度互相干扰。

</details>

---

## 第 3 步 · 建立算法选择坐标系

> on/off-policy、Advantage、PPO、SAC 与 Offline RL 是后续算法的定位骨架。

<details class="qa">
<summary><span class="seq">08</span> <span class="origin">卷一</span> <span class="lv lv-l1">L1</span> <span class="freq">🔥×8</span> <b>Q27</b> · On-policy 和 Off-policy 的区别？各自典型算法是什么？</summary>

**答**：

- **On-policy**：行为策略 = 目标策略（用来采样的策略就是正在优化的策略）。数据必须来自当前策略，旧数据无效。典型：**PPO, A3C, TRPO, SARSA**。
- **Off-policy**：行为策略 ≠ 目标策略（可以用其他策略（含过去旧策略）采样的数据来训练）。数据可复用（replay buffer）。典型：**Q-learning, DQN, SAC, TD3, DDPG**。

**权衡**：
- On-policy 样本效率低（用完即扔），但稳定、收敛保证好；
- Off-policy 样本效率高（replay buffer 重复用），但需处理重要性采样 / 分布偏移。

**机器人选择**：真机采样贵 → 首选 off-policy（SAC）；仿真大规模可重置 → on-policy（PPO）也可接受；RLHF 微调 LLM/VLA 语言部分常用 PPO；VLA 的动作策略本身更多用 BC/LoRA/flow-matching 等监督学习方式。

**易错**：PPO 看似可以用旧数据（clip 范围内），但理论上仍是 on-policy（clip 是近似约束，偏离太多就不行）；**PPO 不是 off-policy**。

</details>

<details class="qa">
<summary><span class="seq">09</span> <span class="origin">卷一</span> <span class="lv lv-l2">L2</span> <span class="freq">🔥×7</span> <b>Q30</b> · 什么是 Advantage 函数？它为什么比直接用 Q 值更好？</summary>

**答**：**Advantage 函数**：$A^\pi(s, a) = Q^\pi(s, a) - V^\pi(s)$，表示在状态 $s$ 执行动作 $a$ 相对于"平均水平"的超额价值。

**为什么更好**：
- 纯用 $Q(s,a)$ 作 PG 的权重：量纲大（$Q$ 的绝对值可能很大），方差高；
- $A(s,a)$ 零中心化（某些动作正、某些负），梯度信号更清晰——好于平均的动作被强化，差于平均的被抑制；
- 方差显著降低（baseline = $V(s)$ 的效果）；
- PPO 的 clip 目标就是 $\hat{A}_t$，没有 advantage 就没有 PPO。

**GAE（广义优势估计）**：$\hat{A}_t^{\text{GAE}} = \sum_{l \geq 0} (\gamma\lambda)^l \delta_{t+l}$（TD 残差加权求和），$\lambda$ 在低方差 TD 和低偏差 MC 之间插值，实务 $\lambda \approx 0.95$。

**易错**：理论上 $\mathbb{E}_{a \sim \pi}[A^\pi(s,a)] = 0$（对任意状态 $s$ 成立），但实践中 Critic 的 $V$ 是估计值，批量计算的 $\hat{A}_t$ 不一定严格零均值；对 mini-batch 内 advantage 做归一化（减均值除标准差）是常见 trick，可稳定训练但不等同于真实 advantage 值。

</details>

<details class="qa">
<summary><span class="seq">10</span> <span class="origin">卷一</span> <span class="lv lv-l2">L2</span> <span class="freq">🔥×6</span> <b>Q31</b> · PPO 的 Clip 机制是什么？为什么比 TRPO 更实用？</summary>

**答**：$L^{CLIP} = \mathbb{E}_t[\min(r_t \hat{A}_t,\ \text{clip}(r_t, 1\!-\!\epsilon, 1\!+\!\epsilon)\hat{A}_t)]$，其中 $r_t = \pi_\theta(a_t|s_t)/\pi_{\theta_{old}}(a_t|s_t)$，$\epsilon \approx 0.1$-$0.2$。

**直觉**：$\hat{A}_t > 0$（好动作）时增大 $r_t$，但截到 $1+\epsilon$；$\hat{A}_t < 0$ 时减小 $r_t$，但截到 $1-\epsilon$。防止更新幅度过大，新旧策略保持接近。

**关键对比**：
- **TRPO**：KL 散度硬约束 + 共轭梯度二阶优化，理论严格但计算复杂；
- **PPO**：clip 是软约束，一阶梯度即可，实现简单，是 RLHF 偏好对齐的工程主流；VLA 动作策略本身更多用 BC/flow-matching 监督学习。

**易错**：PPO 不保证真正的 trust region（多次 mini-epoch 后 $r_t$ 可能超出 clip 范围）；clip 是启发式，不是严格约束。

</details>

<details class="qa">
<summary><span class="seq">11</span> <span class="origin">卷一</span> <span class="lv lv-l2">L2</span> <span class="freq">🔥×6</span> <b>Q32</b> · SAC（Soft Actor-Critic）的最大熵框架是什么？为什么它在机器人真机训练中更受青睐？</summary>

**答**：**最大熵 RL**：目标从最大化期望 return 改为同时最大化期望 return 和策略熵：

$$J(\pi) = \mathbb{E}\left[\sum_t \gamma^t (r_t + \alpha \mathcal{H}(\pi(\cdot \mid s_t)))\right]$$

$\alpha$ 为温度参数（自动调整），$\mathcal{H}$ 为策略熵。

**好处**：① **探索内化**：高熵策略自然探索多种动作，不易陷入局部最优；② **鲁棒性**：同时优化多种良策略，对环境扰动（真机噪声）更鲁棒；③ **off-policy + replay buffer**：样本效率高，真机数据贵时可多次复用。

**自动温度**：$\alpha$ 自动调节让熵约束在目标熵附近，无需手调——这是 SAC 工程上比 TD3 友好的关键。

**易错**：SAC 的"soft"是指软 Q-learning（熵正则化），不是"软"更新（虽然 SAC 也用软更新 target network）；两个概念不同。

</details>

<details class="qa">
<summary><span class="seq">12</span> <span class="origin">卷一</span> <span class="lv lv-l3">L3</span> <span class="freq">🔥×5</span> <b>Q33</b> · Offline RL 与 Online RL 的核心区别？为什么 Offline RL 有分布偏移问题？</summary>

**答**：

- **Online RL**：边训练边与环境交互，数据来自当前策略；可以探索、纠错。
- **Offline RL**：完全从固定数据集（历史演示/日志）中学习，**不与环境交互**；数据集可能来自多种行为策略。

**分布偏移（Distribution Shift）**：学到的策略可能访问数据集中从未出现的 $(s,a)$ 对 → Q 函数对这些 OOD（out-of-distribution）动作的估计极不准确（往往过高，因为神经网络外推不可靠）→ 策略被错误高估的动作引导走错。

**对策**：
- **CQL（Conservative Q-Learning）**：在 Q 值优化中额外惩罚 OOD 动作的 Q 值，强制保守估计；
- **IQL（Implicit Q-Learning）**：避免直接对 OOD 动作查 Q，只在数据集内做 expectile 回归；
- **BC 约束**：限制策略不偏离行为策略太远（与 KL 正则类似）。

**机器人应用**：真机无法探索时（危险/昂贵）必须 offline RL；离线预训练 + 少量在线 fine-tune 是常见组合。

**易错**：Offline RL 不是"有数据就行"——数据覆盖度和质量极关键；覆盖差+高 OOD 比率时 CQL 等方法也会失效。

</details>

---

## 第 4 步 · 深入策略优化基础

> 用 TD、GAE、重要性采样和多步回报理解 PPO 的来源。

<details class="qa">
<summary><span class="seq">13</span> <span class="origin">卷二</span> <span class="lv lv-l1">L1</span> <span class="freq">🔥×15</span> <b>Q01</b> · on-policy 和 off-policy 的区别？各自有哪些代表算法？</summary>

**答**：
- **on-policy**：用**当前策略** $\pi_\theta$ 收集的数据训练，数据用完即丢；策略每次更新后必须重新采样。代表：REINFORCE / A2C / A3C / **PPO**（严格说 PPO 通过重要性采样做 mini off-policy，但仍属 on-policy 范畴）。
- **off-policy**：可以用**任意策略**（如旧策略、人类演示）收集的数据训练，借助经验回放重复利用；探索策略与优化策略可分离。代表：Q-learning / DQN / DDPG / **TD3** / **SAC**。

**关键区别**：on-policy 样本效率低但稳定；off-policy 样本效率高但收敛难（Q 值过估计、分布漂移）。

**易错**：SAC 是 off-policy，PPO 虽然用了重要性采样，但用旧数据的 epoch 数很少（通常 3-10 epoch），学术上仍归 on-policy；不要说"PPO 是 off-policy"。

</details>

<details class="qa">
<summary><span class="seq">14</span> <span class="origin">卷二</span> <span class="lv lv-l1">L1</span> <span class="freq">🔥×12</span> <b>Q02</b> · 策略梯度定理是什么？为什么要减去 baseline？</summary>

**答**：**策略梯度定理**：$\nabla_\theta J(\theta) = \mathbb{E}_{\tau \sim \pi_\theta}\!\left[\sum_t \nabla_\theta \log \pi_\theta(a_t|s_t) \cdot G_t\right]$，其中 $G_t$ 是从时刻 $t$ 起的累积回报。

**为什么减 baseline**：$G_t$ 方差极大（随机轨迹可达 $\pm$几百），导致梯度噪声大、收敛慢。减去与动作无关的 baseline $b(s_t)$（常取 $V^\pi(s_t)$）后：
- **不影响期望**（$b$ 与动作无关，减去后梯度期望不变）
- **方差显著降低**：$G_t - V(s_t) = A_t$（优势函数），只保留"这个动作比平均好多少"的信号

**易错**：baseline 必须与动作 $a_t$ 无关，否则会引入 bias；用 $V(s_t)$ 作 baseline 是最常见选择。

</details>

<details class="qa">
<summary><span class="seq">15</span> <span class="origin">卷二</span> <span class="lv lv-l1">L1</span> <span class="freq">🔥×12</span> <b>Q03</b> · Actor-Critic 框架是什么？与纯 Policy Gradient 的区别？</summary>

**答**：**Actor-Critic (AC)** 同时维护两个网络：
- **Actor**（策略网络）：$\pi_\theta(a|s)$，负责选动作；
- **Critic**（值函数网络）：$V_\phi(s)$ 或 $Q_\phi(s,a)$，负责评估动作好坏。

Actor 用 Critic 的输出（advantage 或 TD 误差）代替 MC 累积回报 $G_t$ 来更新，**把 baseline 从 V 变成实时 TD 估计**，大幅降低方差。

**vs 纯 PG（REINFORCE）**：
- REINFORCE 需等轨迹结束才能计算 $G_t$，高方差、慢收敛；
- AC 可在线（每步）更新，方差更低，但 Critic 引入 bias（若 $V_\phi$ 估不准）。

**易错**：AC 的"两网络"说法是概念层面；实际实现中 Actor 和 Critic 常共享前几层特征，只在输出头分叉。

</details>

<details class="qa">
<summary><span class="seq">16</span> <span class="origin">卷二</span> <span class="lv lv-l2">L2</span> <span class="freq">🔥×10</span> <b>Q04</b> · GAE（Generalized Advantage Estimation）是什么？λ 怎么控制 bias-variance 权衡？</summary>

**答**：**GAE** 在 MC 高方差 ($\lambda=1$) 与 TD 低方差但有 bias ($\lambda=0$) 之间用指数加权插值：

$$\hat{A}_t^{\text{GAE}(\gamma,\lambda)} = \sum_{l=0}^{\infty}(\gamma\lambda)^l \delta_{t+l}, \quad \delta_t = r_t + \gamma V(s_{t+1}) - V(s_t)$$

- $\lambda \to 1$：接近 MC，方差大、bias 小；
- $\lambda \to 0$：接近单步 TD，方差小、bias 大；
- 实务甜区：**$\lambda \approx 0.95$, $\gamma \approx 0.99$**。

**PPO 与 GAE**：PPO 的策略梯度目标 $\mathbb{E}[\min(r_t\hat{A}_t, \text{clip}(r_t,1\pm\varepsilon)\hat{A}_t)]$ 需要 $\hat{A}_t$，GAE 提供低方差的 $\hat{A}_t$ 估计，是 PPO 稳定收敛的关键。

**易错**：GAE 不是 PPO 专属，TRPO/A3C 也用；但 PPO + GAE 是当前最常见组合。

</details>

<details class="qa">
<summary><span class="seq">17</span> <span class="origin">卷二</span> <span class="lv lv-l2">L2</span> <span class="freq">🔥×8</span> <b>Q05</b> · A3C 和 A2C 的区别？为什么 A3C 提出时被认为是突破？</summary>

**答**：
- **A3C（Asynchronous Advantage Actor-Critic, 2016）**：多个**异步** worker 各自与独立环境交互，将梯度推送给全局网络，不需要经验回放；去相关化的异步更新相当于天然正则。DeepMind 原作在 CPU 集群上效果极好。
- **A2C**：**同步**版本，等所有 worker 完成一批再统一更新；实现更简单，在 GPU 上 batch 更友好，实际性能常与 A3C 持平或略强。

**A3C 突破点**：① 证明异步并行可替代经验回放去相关化；② 无 replay buffer 降低内存；③ on-policy 不需要重要性采样。

**当前地位**：A3C/A2C 已基本被 PPO 取代，但仍是理解 Actor-Critic 并行训练的经典范例。

**易错**：A3C 不是 off-policy，仍是 on-policy；它的"异步"指的是数据收集异步，不是说能复用旧数据。

</details>

<details class="qa">
<summary><span class="seq">18</span> <span class="origin">卷二</span> <span class="lv lv-l1">L1</span> <span class="freq">🔥×10</span> <b>Q06</b> · TD 误差（TD error）是什么？和 Bellman 方程有什么关系？</summary>

**答**：**TD 误差**（时序差分误差）：$\delta_t = r_t + \gamma V(s_{t+1}) - V(s_t)$，表示"实际得到的 bootstrap 估计"与"当前估计"之差。

**与 Bellman 方程的关系**：Bellman 期望方程 $V^\pi(s) = \mathbb{E}[r + \gamma V^\pi(s')]$，若 $V$ 满足 Bellman 方程，则 $\mathbb{E}[\delta_t] = 0$；TD 学习就是用随机梯度把 $\delta_t$ 向 0 推。

**核心作用**：① 提供单步可计算的 critic 更新信号（不需等轨迹结束）；② 等于 GAE 公式里的 $\delta_{t+l}$ 基本单元；③ Prioritized Replay 用 $|\delta_t|$ 衡量样本重要性。

**易错**：$\delta_t$ 是带符号的误差，正值表示"实际比预期好"、负值表示"实际比预期差"；直接用 $\delta_t^2$ 做损失就是 critic 的 MSE loss。

</details>

<details class="qa">
<summary><span class="seq">19</span> <span class="origin">卷二</span> <span class="lv lv-l2">L2</span> <span class="freq">🔥×7</span> <b>Q07</b> · 重要性采样（Importance Sampling）在 RL 中的作用？PPO 怎么用的？</summary>

**答**：**重要性采样（IS）**：当数据分布 $q$ 与目标分布 $p$ 不一致时，用比值 $w = p(x)/q(x)$ 纠正：$\mathbb{E}_p[f(x)] = \mathbb{E}_q[w \cdot f(x)]$。

**RL 中的用途**：① 允许 on-policy 算法用旧策略数据做多轮 mini-batch 更新（提升数据效率）；② off-policy 评估（用行为策略数据评估目标策略）。

**PPO 怎么用**：定义比值 $r_t(\theta) = \pi_\theta(a|s) / \pi_{\theta_{\text{old}}}(a|s)$，梯度目标变为：
$$L^{\text{CLIP}} = \mathbb{E}_t\!\left[\min\!\left(r_t \hat{A}_t, \text{clip}(r_t, 1-\varepsilon, 1+\varepsilon)\hat{A}_t\right)\right]$$
**Clip 机制**不是 IS 本身，而是限制 $r_t$ 偏离 1 太远（$\varepsilon$ 通常 0.2），防止比值失控、方差爆炸。

**易错**：PPO 的 clip 只影响梯度计算，不是完整 IS 校正；当 $r_t$ 被 clip 后梯度等效为 0，策略不会继续沿该方向走远。

</details>

<details class="qa">
<summary><span class="seq">20</span> <span class="origin">卷二</span> <span class="lv lv-l2">L2</span> <span class="freq">🔥×6</span> <b>Q08</b> · 多步回报（n-step return）是什么？和 TD(0) / MC 的关系？</summary>

**答**：**n-step return**：$G_t^{(n)} = r_t + \gamma r_{t+1} + \ldots + \gamma^{n-1}r_{t+n-1} + \gamma^n V(s_{t+n})$，即向前展 n 步后接 bootstrap。

**关系**：
- $n=1$：单步 TD（TD(0)）；低方差、高 bias（V 估计不准影响大）
- $n \to \infty$：蒙特卡洛（MC）；高方差、零 bias（用真实 G）
- 中间值：bias-variance 权衡；$\lambda$-return（GAE 是其指数加权版本）

**实务选 n 的经验**：短任务（episode < 50 步）可用较大 n；长任务（> 500 步）n 过大会导致方差爆炸，通常 n=3-10 + GAE。

**易错**：TD(λ) 和 GAE 的关系——GAE 是从 offline 轨迹计算的 λ-return advantage；TD(λ) 是 online 更新规则；计算方法不同，但在正向累积 δ 的公式上等价。

</details>

<details class="qa">
<summary><span class="seq">21</span> <span class="origin">卷二</span> <span class="lv lv-l1">L1</span> <span class="freq">🔥×18</span> <b>Q09</b> · PPO 的 Clip 机制是什么？为什么 ε 通常取 0.2？</summary>

**答**：**PPO（Proximal Policy Optimization, Schulman 2017）**的核心是 Clip 目标：

$$L^{\text{CLIP}}(\theta) = \mathbb{E}_t\!\left[\min\!\left(r_t\hat{A}_t,\ \text{clip}(r_t, 1-\varepsilon, 1+\varepsilon)\hat{A}_t\right)\right]$$

其中 $r_t = \pi_\theta / \pi_{\theta_\text{old}}$。

**直觉**：advantage 为正时想升高 $r_t$，但若 $r_t > 1+\varepsilon$ 已涨太多，clip 截断梯度，防止过激更新；advantage 为负时同理，$r_t < 1-\varepsilon$ 则截断。"先设上下限、再取 min"确保保守更新。

**ε = 0.2**：Schulman 原论文实验甜区；太小更新保守、样本浪费；太大接近无约束 PG。RLHF 常用 0.1-0.2。

**易错**：PPO-Clip ≠ PPO-KL；后者在损失里显式加 KL penalty；前者更常用且稳定。

</details>

<details class="qa">
<summary><span class="seq">22</span> <span class="origin">卷二</span> <span class="lv lv-l1">L1</span> <span class="freq">🔥×14</span> <b>Q10</b> · TRPO 和 PPO 的联系与区别？为什么 PPO 更流行？</summary>

**答**：**TRPO（Trust Region PO, Schulman 2015）**：用二阶优化（共轭梯度 + Hessian-vector 乘积）在**KL 约束** $D_\text{KL}(\pi_{\theta_\text{old}} \| \pi_\theta) \le \delta$（旧策略到新策略的 KL）下求最优更新；理论保证单调策略改进。

**PPO**：TRPO 的轻量化替代，用 clip 机制隐式限制策略变化，**不需要共轭梯度**，一阶优化（Adam）即可；代码量从数百行降到数十行。

| | TRPO | PPO-Clip |
|---|---|---|
| 约束方式 | 显式 KL 约束 | Clip ratio |
| 优化器 | 二阶（CG+线搜） | 一阶（Adam） |
| 代码复杂度 | 高 | 低 |
| 效果 | 理论保证单调 | 实务近似等效 |
| 分布式 | 难 | 容易 |

**PPO 更流行的原因**：① 实现简单；② GPU batch 友好；③ 效果接近 TRPO；④ 与 LLM RLHF 对齐流程无缝集成（VLA 微调主流仍是 BC/flow matching）。

**易错**：TRPO 的"单调改进"在神经网络参数化下只是近似保证（Fisher 矩阵近似），并非绝对。

</details>

<details class="qa">
<summary><span class="seq">23</span> <span class="origin">卷二</span> <span class="lv lv-l2">L2</span> <span class="freq">🔥×9</span> <b>Q11</b> · PPO 的 entropy bonus 是什么？什么时候需要加？</summary>

**答**：**Entropy bonus**：在 PPO 目标里加 $\beta \cdot \mathcal{H}[\pi_\theta(\cdot|s)]$（策略熵），鼓励策略保持随机性。

**直觉**：若策略过早收敛（熵趋 0），actor 只会走一条路，探索停止——这在稀疏奖励 / 多峰任务中灾难性。熵 bonus 提供额外梯度驱动策略"多尝试几种动作"。

**什么时候用**：① 奖励稀疏（初期没信号，需探索维持）；② 离散动作空间（熵易计算 $-\sum p \log p$）；③ 任务有多条最优路径（不想早期锁死一条）。

**什么时候不加**：连续控制精细任务（机械臂插针）——过多探索引入噪声反而有害；SAC 已内置熵最大化，不需要额外加。

**超参 $\beta$ 建议**：通常 0.01-0.05；RLHF 场景有时用 0.001 以下（微调阶段需保守）。

**易错**：entropy bonus 是可选项，PPO 原论文的联合目标中包含该项，但实验中系数可设为 0；SAC 的熵机制来自 max-entropy RL 框架（正则化目标），与 PPO 的 entropy bonus（探索辅助）不要混淆。

</details>

<details class="qa">
<summary><span class="seq">24</span> <span class="origin">卷二</span> <span class="lv lv-l2">L2</span> <span class="freq">🔥×8</span> <b>Q12</b> · PPO 训练的完整流程是什么（采样 → 优势估计 → 多轮更新 → 截断）？</summary>

**答**：**PPO 一个迭代周期**：

1. **Rollout**：用 $\pi_{\theta_\text{old}}$ 交互 T 步，存 $(s_t, a_t, r_t, s_{t+1}, \log\pi_\text{old})$。
2. **GAE**：计算 $\hat{A}_t$ + target value $\hat{V}_t = \hat{A}_t + V_\phi(s_t)$。
3. **多 epoch 更新**：mini-batch 采样 K 次（K=3-10），计算 Actor $L^{\text{CLIP}}$ + Critic MSE + entropy bonus（可选）。
4. **Early stopping**：KL 超阈值时提前退出 epoch。
5. 更新 $\theta_\text{old} \leftarrow \theta$，重复。

**关键超参**：T（256-2048）、batch（32-256）、K（3-10）、ε（0.2）、λ（0.95）。

**易错**：多 epoch 是 PPO 核心优势；但 K 太大 → IS ratio 失控；K 通常不超过 10。

</details>

<details class="qa">
<summary><span class="seq">25</span> <span class="origin">卷二</span> <span class="lv lv-l3">L3</span> <span class="freq">🔥×6</span> <b>Q13</b> · PPO 在机器人连续控制中常见的失败模式有哪些？如何诊断？</summary>

**答**：
**常见失败模式**：

1. **Reward hacking / mode collapse**：奖励函数有漏洞，agent 找到"不物理"的高分动作（如原地振荡换高速度奖励）。诊断：reward 高但实际任务失败；对策：奖励工程审查 + 额外约束项。

2. **训练不稳定（loss 剧烈震荡）**：学习率或 clip ε 太大；Critic 估计跟不上 Actor 更新节奏。诊断：entropy 先升后崩、KL 突增；对策：降 lr、减 epoch 数、共享 encoder 冻层。

3. **过早收敛到次优策略**：entropy 过快降至接近 0，探索停止。对策：增大 entropy bonus $\beta$ 或使用 curriculum。

4. **仿真 sim2real gap**：仿真里 PPO 高分，真机泛化差。诊断：Domain Randomization 覆盖不足；对策：增大 DR 范围 + 感知扰动。

5. **稀疏奖励不收敛**：长期无信号，梯度消失。对策：奖励 shaping（如势能函数）+ HER（Hindsight Experience Replay）。

**易错**：PPO 失败首先看 entropy 曲线——熵崩塌是早期预警信号；不要先调 clip ε，先检查奖励函数和数据分布。

</details>

---

## 第 5 步 · 补齐连续与离散动作算法

> 按 DDPG → TD3 / SAC、Q-learning → DQN 的问题改进链阅读。

<details class="qa">
<summary><span class="seq">26</span> <span class="origin">卷二</span> <span class="lv lv-l1">L1</span> <span class="freq">🔥×14</span> <b>Q14</b> · SAC 是什么？max-entropy 框架的直觉是什么？temperature α 怎么自动调？</summary>

**答**：**SAC（Soft Actor-Critic, Haarnoja 2018）**：最大熵 RL 框架下的 off-policy Actor-Critic，目标不是最大化期望回报，而是：

$$J(\pi) = \mathbb{E}\!\left[\sum_t r(s_t, a_t) + \alpha \cdot \mathcal{H}[\pi(\cdot|s_t)]\right]$$

**Max-entropy 直觉**：最大化奖励 + 策略熵 → 策略在等效动作间均匀分布。好处：探索强、多峰奖励自然处理、扰动后鲁棒恢复。

**Temperature α 自动调节**（SAC v2）：设目标熵 $\bar{\mathcal{H}} = -|\mathcal{A}|$，优化 $\min_\alpha \mathbb{E}[-\alpha(\log\pi_\theta + \bar{\mathcal{H}})]$。熵低 → α 升（多探索）；熵高 → α 降（多利用）。初始 α ≈ 0.2，之后自适应。

**易错**：α 不是"探索率"，是正则权重；SAC 无 ε-greedy，策略随机性即探索来源；自动调 α 远优于手调，不要固定 α。

</details>

<details class="qa">
<summary><span class="seq">27</span> <span class="origin">卷二</span> <span class="lv lv-l1">L1</span> <span class="freq">🔥×12</span> <b>Q15</b> · TD3 相比 DDPG 做了哪三点改进？分别解决什么问题？</summary>

**答**：**TD3（Twin Delayed DDPG, Fujimoto 2018）**针对 DDPG，做了 3 点改进：

1. **双 Q 网络**：维护 $Q_{\phi_1}, Q_{\phi_2}$，取 min：$y = r + \gamma \min_i Q_{\phi_i}(s', \pi(s'))$ → 解决过估计。

2. **Actor 延迟更新**：Actor 每 d 步更新一次（d=2），Critic 每步更新 → 防止 Actor 过快追高估 Q 值。

3. **Target Policy Smoothing**：target action 加裁剪高斯噪声 $\tilde{a} = \pi(s') + \text{clip}(\mathcal{N}(0,\sigma), -c, c)$ → 平滑 Q 面，防止在 Q 峰值上过拟合。

**易错**：TD3 是确定性策略，SAC 是随机策略；3 个改进必须**全部组合**才达到论文效果，缺一不可。

</details>

<details class="qa">
<summary><span class="seq">28</span> <span class="origin">卷二</span> <span class="lv lv-l1">L1</span> <span class="freq">🔥×9</span> <b>Q16</b> · DDPG 是什么？为什么在实务中不稳定？</summary>

**答**：**DDPG（Deep Deterministic Policy Gradient, Lillicrap 2016）**：off-policy Actor-Critic，专为连续动作设计：
- Actor 输出**确定性动作** $\mu_\theta(s)$（不是概率分布）
- Critic 用 Q-learning 更新：$y = r + \gamma Q_{\phi'}(s', \mu_{\theta'}(s'))$
- 使用**经验回放 + target 网络**（从 DQN 借来）

**实务不稳定的原因**：
1. **Q 值过估计**：actor 持续追最大 Q，Q 值单调高估，最终 NaN；
2. **超参极度敏感**：batch size / lr / 噪声 σ 调错就崩；
3. **探索困难**：确定性策略靠人为加 Ornstein-Uhlenbeck 噪声，效果有限；
4. **Critic 和 Actor 互相污染**：Q 估计不准 → 策略更新方向错 → Q 更不准（恶性循环）。

**TD3 / SAC 的出现**基本淘汰了裸 DDPG 的实际使用。

**易错**：DDPG 的"确定性"是指策略不是概率分布——推理时输出是单个动作；探索靠加外部噪声，不是策略本身的随机性。

</details>

<details class="qa">
<summary><span class="seq">29</span> <span class="origin">卷二</span> <span class="lv lv-l2">L2</span> <span class="freq">🔥×9</span> <b>Q17</b> · replay buffer（经验回放）的作用？uniform 采样有什么缺陷？PER 怎么改进？</summary>

**答**：**Replay buffer**：存储历史 $(s, a, r, s', \text{done})$ 元组，off-policy 算法随机采样训练。

**作用**：① **去相关**：相邻时间步高度相关，随机采样打破 temporal correlation；② **数据复用**：每条数据可被多次学习，提升 sample efficiency；③ **稳定分布**：避免 online 数据分布漂移太快导致不稳定。

**均匀采样缺陷**：TD 误差大的（难学、重要的）样本和 TD 误差小的（已学好的）样本同等概率采到 → 训练低效。

**PER（Prioritized Experience Replay, Schaul 2016）**：用 $|\delta_t|^\alpha$（TD 误差绝对值的 α 次方）设优先级，高 TD 误差样本更频繁采样；同时用**重要性采样权重** $w_i = (1/N \cdot 1/p_i)^\beta$ 纠正采样 bias（$\beta$ 从 0.4 退火到 1.0）。

**易错**：PER 不是"总采最难的样本"——是概率高，不是必然采；重要性权重不是可选项，缺失会引入 bias 导致价值函数偏移。

</details>

<details class="qa">
<summary><span class="seq">30</span> <span class="origin">卷二</span> <span class="lv lv-l2">L2</span> <span class="freq">🔥×8</span> <b>Q18</b> · target network 是什么？为什么不直接用当前网络做 TD 目标？</summary>

**答**：**Target network**：维护一份主网络的**软拷贝** $\phi'$，用于计算 TD 目标 $y = r + \gamma Q_{\phi'}(s', a')$；通过指数移动平均（EMA）缓慢更新：$\phi' \leftarrow \tau \phi + (1-\tau)\phi'$，通常 $\tau = 0.005$。

**为什么需要**：若 TD 目标用当前网络 $Q_\phi$ 计算，损失为：
$$L = (Q_\phi(s,a) - (r + \gamma Q_\phi(s',a')))^2$$
被拟合的目标 $r + \gamma Q_\phi$ **随着 $\phi$ 更新而移动**，形成"追逐运动目标"的循环——网络调一步，目标跟着变，容易发散（"自举问题"）。

**EMA 更新 vs 硬拷贝**：DQN 原版每 C 步硬拷贝；DDPG/TD3/SAC 用 EMA，更平滑、实务更稳定。

**易错**：$\tau$ 越小目标越稳，但学习越慢；$\tau = 1$ 等价于没有 target 网络（不稳定）。target 网络不是 Critic 专属，部分算法 Actor 也有 target 网络。

</details>

<details class="qa">
<summary><span class="seq">31</span> <span class="origin">卷二</span> <span class="lv lv-l1">L1</span> <span class="freq">🔥×10</span> <b>Q19</b> · DQN 在 Q-learning 基础上做了哪两大改进？分别解决什么问题？</summary>

**答**：**DQN（Deep Q-Network, Mnih 2015）**在朴素 Q-learning（表格/线性）基础上：

**改进 1：经验回放（Experience Replay）**
- 问题：online 样本时间相关 → 神经网络训练不稳定
- 解法：随机从 buffer 采样，打破 temporal correlation + 重复使用数据

**改进 2：Target Network**
- 问题：TD 目标 $r + \gamma \max_{a'} Q_\phi(s',a')$ 与被拟合的 $Q_\phi(s,a)$ 用同一网络，移动目标 → 发散
- 解法：单独维护 $\phi'$（每 C 步从 $\phi$ 硬拷贝），让目标在短期内固定

**关键数字**：Atari 实验中 replay buffer 大小 10^6，target 更新频率 10^4 步，batch 32，epsilon-greedy 从 1.0 线性退火到 0.1。

**易错**：DQN 的神经网络替代的是 Q-table，不是策略；DQN 输出所有动作的 Q 值（离散动作），不输出动作概率；不能直接用于连续动作空间（DDPG 才能）。

</details>

<details class="qa">
<summary><span class="seq">32</span> <span class="origin">卷二</span> <span class="lv lv-l2">L2</span> <span class="freq">🔥×7</span> <b>Q20</b> · Double DQN / Dueling DQN / Noisy Nets：各自解决什么问题？</summary>

**答**：
- **Double DQN（van Hasselt 2016）**：解决 Q 值**过估计**（max 操作对估计误差有正偏差）。改法：选动作用当前网络 $\phi$，计算 Q 值用 target 网络 $\phi'$：$y = r + \gamma Q_{\phi'}(s', \arg\max_{a'} Q_\phi(s', a'))$。解耦"选哪个动作"与"评估这个动作"。

- **Dueling DQN（Wang 2016）**：解决 Q 值的**状态无关冗余**。把 Q 分解为：$Q(s,a) = V(s) + A(s,a)$（state value + advantage）。好处：能同时更新所有动作的 V 值（即使该 step 没采到某个动作），更新效率高。

- **Noisy Nets（Fortunato 2018）**：解决 $\varepsilon$-greedy **探索低效**问题（均匀随机探索浪费）。把网络权重换成带可学噪声的参数 $\mu + \sigma \cdot \varepsilon$（参数化探索），探索自适应地集中在不确定动作上。

**易错**：三者可叠加（Rainbow DQN = 六种改进叠加）；Dueling 的标准归一化为减**均值**：$Q(s,a) = V(s) + A(s,a) - \frac{1}{|A|}\sum_{a'} A(s,a')$，保证 V/A 分解唯一且梯度覆盖所有动作；不减任何量 → V/A 分解不唯一、不稳定。

</details>

<details class="qa">
<summary><span class="seq">33</span> <span class="origin">卷二</span> <span class="lv lv-l2">L2</span> <span class="freq">🔥×5</span> <b>Q21</b> · HER（Hindsight Experience Replay）是什么？为什么对稀疏奖励机器人任务特别有效？</summary>

**答**：**HER（Andrychowicz 2017）**：将失败的轨迹"回头重写目标"为实际达到的结果，从而产生有效学习信号。

**流程**：机械臂试图把方块推到位置 $g$ 但失败（最终停在 $g'$），HER 将该 episode 的目标 $g$ 替换为 $g'$，**逐 transition 重新计算奖励**（$r = \mathbb{1}[\|s - g'\| < \delta]$，仅最后几步为 +1）→ 这段失败轨迹变成"成功到达 $g'$"的有效经验加入 buffer。

**为什么有效**：① 稀疏奖励下 agent 几乎得不到任何正信号，HER 把每次失败都变成"成功到达某个地方"的经验，信号密度大幅提升；② 不需要改奖励函数；③ 与任何 off-policy 算法（DDPG/TD3/SAC）无缝组合。

**适用场景**：目标条件策略（Goal-conditioned RL），如机器人 pick-and-place、推物体到目标位置等。

**易错**：HER 用的不是任意随机目标，而是从同 episode 实际达到的状态中重标（strategy = "future" / "final" / "episode"），语义上是"已经发生的真实结果"；若奖励不是 goal-conditioned（如 $r = \mathbb{1}[s=g]$），HER 无法应用。

</details>

---

## 阶段结束时怎么复习

1. 点击“全部折叠”，只看题目口述答案。
2. 能说出答案后标记“已掌握”；不要因为“看懂了”就标记。
3. 第二天使用“只看未掌握”，第 7 天再完整复述一次。
4. 回到[总学习路线](../roadmap.html)，检查通过标准后再进入下一阶段。
