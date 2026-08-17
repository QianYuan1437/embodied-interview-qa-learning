# 阶段 1 · 机器学习共同语言

> 从训练闭环走到 Transformer，不再孤立背名词
> 本页由原八卷题库自动抽取完整问答，并严格按知识依赖排序。原卷仍是内容源。

**先修**：完成阶段 0，能解释张量、输入 / 输出和一次训练 step。

**本阶段共 16 题 · 通过标准**：能用“数据—模型—损失—更新—评测”解释分类、行为克隆和动作预测。

[← 上一步](../learning/00_prerequisites.html) · [返回总路线](../roadmap.html) · [下一步 →](02_robotics_control.html)

---

## 第 1 步 · 先理解训练为什么有效或失效

> 从梯度、损失和数据划分建立训练闭环。

<details class="qa">
<summary><span class="seq">01</span> <span class="origin">卷一</span> <span class="lv lv-l1">L1</span> <span class="freq">🔥×15</span> <b>Q02</b> · 梯度消失和梯度爆炸的原因是什么？各有哪些解决方法？</summary>

**答**：

**消失**：链式法则反传时，若激活函数（如 sigmoid）导数 < 1，多层连乘后梯度指数衰减 → 浅层几乎不更新。

**爆炸**：权重矩阵乘积特征值 > 1，梯度指数增长 → 更新步过大、训练发散。

**解决梯度消失**：① **换激活函数**：ReLU/Leaky ReLU 导数在正区间为 1；② **残差连接**（skip connection）提供梯度高速公路；③ **BatchNorm/LayerNorm** 归一化激活分布；④ **LSTM 门机制**（序列模型）。

**解决梯度爆炸**：① **梯度裁剪**（Gradient Clipping）：若 $\|g\| > \tau$ 则 $g \leftarrow g \cdot \tau / \|g\|$；② **权重初始化**（Xavier/He）；③ **BatchNorm**。

**易错**：ReLU 有 dying ReLU 问题（负值区梯度永久为 0），大批量 + 大学习率下死亡神经元显著，Leaky ReLU / ELU 可缓解。

</details>

<details class="qa">
<summary><span class="seq">02</span> <span class="origin">卷一</span> <span class="lv lv-l1">L1</span> <span class="freq">🔥×10</span> <b>Q07</b> · 交叉熵损失和 MSE 损失分别适合什么场景？用错了会怎样？</summary>

**答**：

- **交叉熵（CE）**：$L = -\sum_c y_c \log \hat{p}_c$；适合**分类**任务，与 softmax/sigmoid 配合，梯度形式简洁（$\hat{p}-y$），不会在输出层饱和时梯度消失。
- **MSE**：$L = \|y - \hat{y}\|^2$；适合**回归**任务（预测连续值，如关节角度、末端坐标）；与 sigmoid 配合时，当 $\hat{y}$ 饱和（近 0/1）梯度会消失。

**用错后果**：
- 分类用 MSE：梯度消失严重（sigmoid 饱和区），收敛慢，概率解释也不对；
- 回归用 CE：值域不匹配，CE 假设输出是概率，连续回归输出 > 1 时 log 无意义。

**延伸**：机器人连续动作回归常用 **Huber Loss**（MSE 和 MAE 的拼接），对异常值（outlier）更鲁棒。

**易错**：CE 中 $\log 0$ 需要 clip，PyTorch 的 `CrossEntropyLoss` 内部已处理，不用手动加 $\epsilon$。

</details>

<details class="qa">
<summary><span class="seq">03</span> <span class="origin">卷一</span> <span class="lv lv-l1">L1</span> <span class="freq">🔥×5</span> <b>Q19</b> · 训练集/验证集/测试集的划分原则是什么？数据泄露是什么？</summary>

**答**：**划分原则**：
- 训练集：用于学习参数
- 验证集（dev set）：用于超参调整（不能反复用来"选"模型后再报它的指标）
- 测试集：最终一次性评估，**严禁在调参中使用**

**常见比例**：数据充足时 60/20/20；数据少时用 k-fold（k=5/10）让每条数据都当过验证。

**数据泄露（Data Leakage）**：测试/验证集的信息提前"流入"训练，导致指标虚高。常见形式：① 归一化用全量（含测试集）的均值/方差；② 时序数据随机打乱（未来信息混入历史）；③ 图像增强用了测试集样本。

**机器人场景**：演示数据来自同一任务实例时，必须按**任务/场景**划分而非随机划帧（同场景的帧高度相关，随机划分严重高估泛化）。

**易错**：sklearn 的 StandardScaler 必须在训练集 `.fit()`，测试集只 `.transform()`，用 `.fit_transform()` 对全量是数据泄露。

</details>

<details class="qa">
<summary><span class="seq">04</span> <span class="origin">卷一</span> <span class="lv lv-l1">L1</span> <span class="freq">🔥×12</span> <b>Q04</b> · Adam 优化器原理是什么？和 SGD、AdamW 的区别？</summary>

**答**：**Adam** = 一阶矩（梯度 EMA）+ 二阶矩（梯度平方 EMA），各参数有独立自适应学习率；更新：$\theta \leftarrow \theta - \alpha \hat{m}/(\sqrt{\hat{v}}+\epsilon)$（偏差修正后），$\beta_1=0.9, \beta_2=0.999$。

**vs SGD**：SGD 用统一学习率，收敛稳但慢；Adam 自适应、前期快，但大规模视觉任务泛化有时弱于 SGD+momentum。

**vs AdamW**：Adam 加 L2 正则后 weight decay 强度被 $\hat{v}$ 缩放（不均匀）；AdamW 把 weight decay 直接加在权重更新上（解耦），效果一致且可控——VLA 微调几乎都用 AdamW。

**易错**：Adam + L2 ≠ AdamW，两者在自适应学习率下行为不同；LLM/VLA 微调必须用 AdamW，否则 weight decay 强度因参数而异。

</details>

<details class="qa">
<summary><span class="seq">05</span> <span class="origin">卷一</span> <span class="lv lv-l2">L2</span> <span class="freq">🔥×9</span> <b>Q10</b> · 学习率调度（LR Schedule）有哪些常用策略？Warmup 为什么重要？</summary>

**答**：

- **Cosine Annealing**：LR 按余弦从 $\eta_{max}$ 降到 $\eta_{min}$，后期细粒度收敛；最常见。
- **Step Decay**：每 N epoch 乘以 decay 因子（如 0.1）；简单但台阶式，可能跳过最优。
- **Linear Decay**：线性下降；简单，GPT 类常用。
- **Warmup + Cosine**（主流组合）：先从 0 线性升到 $\eta_{max}$（Warmup），再 cosine 衰减。

**Warmup 为什么重要**：训练初期权重随机，梯度方向不稳；大学习率直接更新会破坏预训练权重（fine-tune 场景）或让 Adam 的二阶矩估计（$v_t$）在统计不稳时误导更新方向。Warmup 让模型先"摸清地形"再大步更新。

**易错**：Warmup 步数一般是总 steps 的 1-5%；太长 warmup 浪费训练；微调大模型（如 VLA）几乎必须用 warmup，否则容易灾难性遗忘。

</details>

<details class="qa">
<summary><span class="seq">06</span> <span class="origin">卷一</span> <span class="lv lv-l2">L2</span> <span class="freq">🔥×8</span> <b>Q12</b> · 权重初始化为什么重要？Xavier 和 He 初始化各适合什么激活函数？</summary>

**答**：**为什么重要**：全 0 初始化 → 所有神经元梯度相同（对称性破坏失败）；过大初始值 → 激活饱和+梯度消失；过小 → 梯度消失+信号衰减。好的初始化让各层激活和梯度的方差在正向/反向传播中保持稳定。

**Xavier（Glorot）初始化**：$\text{Var}(W) = \frac{2}{n_{in} + n_{out}}$；假设激活函数**线性（near zero）**，适合 **tanh / sigmoid**（在零点近似线性）。

**He（Kaiming）初始化**：$\text{Var}(W) = \frac{2}{n_{in}}$；考虑 ReLU 把一半神经元置 0，方差要加倍补偿，适合 **ReLU / Leaky ReLU**。

**易错**：PyTorch 默认初始化对大多数层已用 Kaiming Uniform，但自定义层/Embedding 等要手动检查；使用 SELU 激活时有专门的 LeCun 初始化。

</details>

<details class="qa">
<summary><span class="seq">07</span> <span class="origin">卷一</span> <span class="lv lv-l1">L1</span> <span class="freq">🔥×8</span> <b>Q13</b> · 什么是 L1 正则和 L2 正则？它们对权重的影响有何不同？</summary>

**答**：

- **L2 正则**（权重衰减）：$L_{total} = L + \lambda \|w\|_2^2$；梯度 $\partial/\partial w = \partial L/\partial w + 2\lambda w$，效果是每次更新时权重**等比例收缩**（权重趋于小而稠密）。
- **L1 正则**：$L_{total} = L + \lambda \|w\|_1$；梯度为 $\pm\lambda$（恒定），将小权重推为精确 **0**（稀疏权重），等效特征选择。

**实践差异**：L2 在深度学习中更常用（weight decay）；L1 在稀疏特征选择（如 Lasso 回归）中有用；Elastic Net = L1 + L2 组合。

**机器人策略网络**：通常用 L2/weight decay + Dropout，L1 导致的权重稀疏不利于连续动作的平滑输出。

**易错**：Adam 下直接加 L2 不等于 weight decay（二阶矩缩放了梯度），要用 AdamW 才是真正解耦的 weight decay。

</details>

---

## 第 2 步 · 再理解深层网络如何稳定训练

> 残差、归一化和 Dropout 分别处理不同问题。

<details class="qa">
<summary><span class="seq">08</span> <span class="origin">卷一</span> <span class="lv lv-l1">L1</span> <span class="freq">🔥×11</span> <b>Q06</b> · ResNet 的残差连接解决了什么问题？为什么不是直接加深网络？</summary>

**答**：**问题背景**：直接堆叠深层网络（如 56 层）训练误差反而高于浅层（20 层）——不是过拟合，是**网络退化**（degradation）：优化器难以找到恒等映射。

**残差连接**：$H(x) = F(x) + x$，让网络学习残差 $F(x) = H(x) - x$ 而非直接学 $H(x)$。当最优映射接近恒等时，$F(x) \approx 0$ 比让所有层学恒等映射容易得多。

**附加好处**：① Skip connection 为梯度提供直通路径（等效更短的梯度路径），缓解梯度消失；② 实现了深度 scalable（ResNet-50/101/152 都可用）；③ 残差块输出方差较稳定，训练更容易。

**易错**：残差连接不是"自动防止过拟合"，过拟合靠 Dropout/L2/数据增强；残差解决的是**优化难度**（欠拟合+退化），不是泛化。

</details>

<details class="qa">
<summary><span class="seq">09</span> <span class="origin">卷一</span> <span class="lv lv-l1">L1</span> <span class="freq">🔥×14</span> <b>Q03</b> · BatchNorm 和 LayerNorm 的区别？Transformer 为什么用 LayerNorm？</summary>

**答**：

- **BatchNorm（BN）**：沿 batch 维归一化，即对所有样本的同一特征位置计算均值/方差；训练时用 batch 统计量，推理时用 running 均值/方差（全局估计）。**适合 CV/CNN**，batch 大时稳定。
- **LayerNorm（LN）**：沿特征维（同一样本内所有通道）归一化，每个样本独立计算，**不依赖 batch size**，训练/推理行为一致。

**Transformer 用 LN 的原因**：① 序列长度不等，batch 统计不稳定；② NLP 任务 batch 小时 BN 方差估计噪声大；③ 推理时单条序列（batch=1）BN 退化，LN 完全不受影响。

**易错**：BN 在推理期用的是训练期积累的 running mean/var，不是当前 batch 统计量；小 batch 时 BN 抖动大、LN 更稳。

</details>

<details class="qa">
<summary><span class="seq">10</span> <span class="origin">卷一</span> <span class="lv lv-l1">L1</span> <span class="freq">🔥×12</span> <b>Q05</b> · Dropout 的原理是什么？训练和推理阶段有何不同？</summary>

**答**：**训练时**：每个神经元以概率 $p$ 被随机置 0（"丢弃"），保留的神经元输出乘以 $1/(1-p)$ 缩放（Inverted Dropout），使期望与完整网络一致。

**推理时**：所有神经元保留，**不做 Dropout**，直接用完整网络输出。（如果训练时没用 Inverted Dropout，推理时需将输出乘以 $(1-p)$。）

**作用**：① 减少神经元共适应（co-adaptation），相当于隐式集成多个子网络；② 正则化，防止过拟合。

**易错**：model.eval() 会自动关 Dropout；忘调会导致推理时随机性——**这是 PyTorch 面试高频陷阱**。BatchNorm 在 eval() 也切换到 running stats，两者必须同时切换。

</details>

---

## 第 3 步 · 最后进入 Transformer 与视觉 token

> 先有优化直觉，再理解 Attention、位置、Softmax 和 ViT。

<details class="qa">
<summary><span class="seq">11</span> <span class="origin">卷一</span> <span class="lv lv-l1">L1</span> <span class="freq">🔥×18</span> <b>Q01</b> · Transformer Self-Attention 的计算流程是什么？复杂度是多少？</summary>

**答**：输入序列 $X \in \mathbb{R}^{n \times d}$ 分别乘三个权重矩阵得到 $Q, K, V$，然后计算：

$$\text{Attention}(Q, K, V) = \text{softmax}\!\left(\frac{QK^\top}{\sqrt{d_k}}\right)V$$

步骤：① 线性投影得 $Q, K, V$；② 计算相似度矩阵 $QK^\top$（$n \times n$）并除以 $\sqrt{d_k}$ 缩放；③ softmax 归一化；④ 加权求和 $V$。

**复杂度**：时间 $O(n^2 d)$，空间 $O(n^2)$（注意力矩阵是瓶颈），序列长时计算量爆炸。多头注意力是 $h$ 个小头并行，总参数量不变。

**易错**：除以 $\sqrt{d_k}$ 不是"随便加的"——防止点积过大导致 softmax 梯度消失；去掉 scale 训练会明显变差。

</details>

<details class="qa">
<summary><span class="seq">12</span> <span class="origin">卷一</span> <span class="lv lv-l2">L2</span> <span class="freq">🔥×10</span> <b>Q08</b> · Transformer 的位置编码（Positional Encoding）为什么必要？常见方案有哪些？</summary>

**答**：Self-Attention 的计算对序列顺序**天然无感**（permutation equivariant）——打乱 token 顺序，attention 输出值相同（只是对应位置互换）。对于语言/时序，顺序信息极关键，必须额外注入。

**方案对比**：
| 方案 | 原理 | 优缺点 |
|---|---|---|
| 正弦位置编码（原始 Transformer） | 固定公式 $\sin/\cos$ | 无需训练，可外推到更长序列；但绝对位置，相对位置弱 |
| 可学习位置嵌入（BERT/GPT） | 每个位置有可训练向量 | 简单有效，不可外推（超训练长度退化） |
| RoPE（LLaMA / VLA） | 旋转矩阵编码**相对**位置 | 天然外推、相对位置敏感，目前 LLM 主流 |
| ALiBi | 在 attention score 上加线性偏置 | 极简、外推好，速度快 |

**易错**：原始 Transformer 和 BERT 的位置编码方案不同；RoPE 不是加在 embedding 上，而是在 Q/K 乘以旋转矩阵。

</details>

<details class="qa">
<summary><span class="seq">13</span> <span class="origin">卷一</span> <span class="lv lv-l2">L2</span> <span class="freq">🔥×7</span> <b>Q14</b> · 为什么 Softmax 输出可以当作概率？数值稳定性如何保证？</summary>

**答**：**概率解释**：Softmax 把实值 logit 向量 $z$ 映射到 $(0,1)$ 且和为 1：

$$\hat{p}_i = \frac{e^{z_i}}{\sum_j e^{z_j}}$$

连接到最大熵原理：当约束为期望值已知时，Softmax 是最大熵分布；结合交叉熵损失等价于最大化对数似然（MLE），有良好的概率理论支撑。

**数值稳定**：直接计算 $e^{z_i}$ 会在 $z_i$ 很大时溢出 → 实践中用 **Stable Softmax**：先减最大值 $c = \max_j z_j$，即 $\hat{p}_i = e^{z_i - c} / \sum_j e^{z_j - c}$，数学等价但数值无溢出。

**易错**：PyTorch 的 `F.cross_entropy` 内部等价于 LogSoftmax + NLLLoss（数值稳定）。**不要**先手动 softmax 再喂给 NLLLoss——NLLLoss 直接把输入当 log-prob 取负求均值，若输入是概率（非 log 域），loss 和梯度都会错误。正确做法：直接 `F.cross_entropy(logits, labels)`，不需要手动 softmax。

</details>

<details class="qa">
<summary><span class="seq">14</span> <span class="origin">卷一</span> <span class="lv lv-l2">L2</span> <span class="freq">🔥×5</span> <b>Q18</b> · ViT（Vision Transformer）与 CNN 的本质区别是什么？在机器人视觉中各有什么优劣？</summary>

**答**：

| | ViT | CNN |
|---|---|---|
| 感受野 | 全局（每层 token 互相 attend） | 局部（逐层扩大） |
| 归纳偏置 | 弱（无平移等变性假设） | 强（平移等变、局部性） |
| 参数效率 | 数据少时差（需大量数据弥补归纳偏置缺失） | 数据少时好 |
| 可扩展性 | 强（patch 数量可变、序列建模自然） | 弱（固定感受野，改分辨率麻烦） |

**机器人视觉**：
- **ViT 优势**：抓全局空间关系（末端 vs 目标位置远处相关），适合 VLA（视觉 + 语言 + 动作联合建模）；SigLIP / DINOv2 预训练的 ViT 在 OpenVLA 表现超越 CLIP-only；
- **CNN 优势**：小数据集（真机 50 demos）、实时推理（低延迟）；局部纹理/接触检测（细粒度操作）。
- 实务：VLA 主流用 ViT 作视觉 backbone + Transformer LM；实时控制头（非语言部分）可用小 CNN。

**易错**：DINOv2 虽是 ViT，但自监督预训练让它比监督 ViT 更有空间几何感；不要混淆预训练方式和架构选择。

</details>

---

## 第 4 步 · 最小手撕练习

> 只实现最能检验理解的 LayerNorm 与 scaled dot-product attention。

<details class="qa qa-handcoding">
<summary><span class="seq">15</span> <span class="origin">卷一</span> <span class="lv lv-l1">L1</span> <span class="freq">🔥×10</span> <b>✍ H04</b> · 手撕 LayerNorm</summary>

**考察点**：沿最后特征维 norm；γ/β 形状等于 `normalized_shape`；LN 不依赖 batch，batch=1 也稳（vs BN）。

**实现**：

```python
import torch
import torch.nn as nn

class LayerNorm(nn.Module):
    def __init__(self, d, eps=1e-5):
        super().__init__()
        self.gamma = nn.Parameter(torch.ones(d))
        self.beta = nn.Parameter(torch.zeros(d))
        self.eps = eps

    def forward(self, x):  # x: [..., d]
        mean = x.mean(-1, keepdim=True)
        # 用有偏方差 (unbiased=False)，与 PyTorch nn.LayerNorm 一致
        var = x.var(-1, keepdim=True, unbiased=False)
        return (x - mean) / torch.sqrt(var + self.eps) * self.gamma + self.beta
```

**易错**：var 写成 std；忘 `eps` 导致除零；用 `unbiased=True`（默认）与官方实现差异；与 BN 的归一化维度记混。

</details>

<details class="qa qa-handcoding">
<summary><span class="seq">16</span> <span class="origin">卷一</span> <span class="lv lv-l2">L2</span> <span class="freq">🔥×15</span> <b>✍ H01</b> · 手撕 scaled dot-product attention</summary>

**考察点**：`Attention(Q,K,V) = softmax(QK^T/√d_k) V` 公式；为何要除 √d_k（防 softmax 饱和、梯度消失）。

**实现**：

```python
import math
import torch
import torch.nn.functional as F

def sdpa(q, k, v, mask=None):
    # q,k,v: [B, ..., L, d_k]；mask: True 处屏蔽
    d_k = q.size(-1)
    scores = q @ k.transpose(-2, -1) / math.sqrt(d_k)  # 缩放避免 softmax 饱和
    if mask is not None:
        scores = scores.masked_fill(mask, float('-inf'))  # 加性 -inf 而非乘 0
    attn = F.softmax(scores, dim=-1)
    return attn @ v  # [B, ..., L, d_v]
```

**易错**：忘 transpose；scale 用 `d_k` 而非 `√d_k`；mask 用乘性 0/1（softmax 后非 0 项不为 0）。

</details>

---

## 阶段结束时怎么复习

1. 点击“全部折叠”，只看题目口述答案。
2. 能说出答案后标记“已掌握”；不要因为“看懂了”就标记。
3. 第二天使用“只看未掌握”，第 7 天再完整复述一次。
4. 回到[总学习路线](../roadmap.html)，检查通过标准后再进入下一阶段。
