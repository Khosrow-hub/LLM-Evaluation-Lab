# Evaluation & Statistical Methodology

Evaluating Large Language Models (LLMs) requires moving beyond "vibes" and point estimates. This document outlines the mathematical and experimental methodology powering **LLM Evaluation Lab**.

---

## 1. The Point-Estimate Fallacy

In traditional prompt tuning, engineers often compare two prompts $A$ and $B$ by calculating raw average accuracy:
$$\bar{x}_A = 74.2\% \quad \text{vs} \quad \bar{x}_B = 76.5\%$$
Concluding that prompt $B$ is superior based solely on a $+2.3\%$ difference is dangerous for several reasons:
1. **Case-Level Stochasticity:** Test datasets exhibit high variance across test cases. A model might perform better on simple cases while catastrophically failing on safety-critical edge cases.
2. **Sampling Uncertainty:** On small or moderate datasets ($n < 500$), an apparent $+2.3\%$ lift can easily arise from pure chance.
3. **Paired Structure Ignored:** Because both models are evaluated on the **exact same test cases**, treating them as independent two-sample distributions discards critical covariance information.

---

## 2. Why Paired Bootstrap Resampling?

**LLM Evaluation Lab** uses **Paired Non-Parametric Bootstrap Resampling** as its primary inference method.

### 2.1 The Mathematics of Paired Differences
For each test case $i \in \{1, \dots, n\}$ evaluated by both Baseline ($B$) and Candidate ($C$), let:
$$d_i = \text{score}(C_i) - \text{score}(B_i)$$
The observed mean difference is:
$$\bar{d} = \frac{1}{n} \sum_{i=1}^n d_i$$

Rather than assuming $d_i$ follows a Gaussian distribution (which is almost always violated because metrics like Exact Match are binary $\{0, 1\}$ and F1 scores cluster at boundaries), we bootstrap the differences:

1. For iteration $b = 1, \dots, B$ (default $B = 2,000$):
   - Sample $n$ differences with replacement: $\{d_1^{*(b)}, \dots, d_n^{*(b)}\}$.
   - Compute the bootstrap sample mean:
     $$\bar{d}^{*(b)} = \frac{1}{n} \sum_{i=1}^n d_i^{*(b)}$$
2. Sort all bootstrap sample means: $\bar{d}^{*(1)} \le \bar{d}^{*(2)} \le \dots \le \bar{d}^{*(B)}$.
3. For confidence level $1 - \alpha$ (default $\alpha = 0.05$ for a 95% CI):
   $$\text{CI}_{\text{lower}} = \text{percentile}\left(100 \cdot \frac{\alpha}{2}\right) = \text{percentile}(2.5\%)$$
   $$\text{CI}_{\text{upper}} = \text{percentile}\left(100 \cdot \left(1 - \frac{\alpha}{2}\right)\right) = \text{percentile}(97.5\%)$$

### 2.2 Advantages over Student's Paired $t$-Test
| Property | Student's $t$-test | Paired Bootstrap |
|---|---|---|
| **Normality Assumption** | Requires normal distribution of differences | **No distributional assumptions** |
| **Discrete/Bounded Data** | Distorted by $\{0, 1\}$ binary and bounded scores | **Exact empirical percentiles** |
| **Auditability** | Abstract $p$-values often misunderstood | **Concrete confidence interval in metric units** |
| **Robustness** | Sensitive to outliers | **Robust under non-standard distributions** |

---

## 3. Practical Significance vs. Statistical Significance

A model change might produce a statistically significant lift that is practically meaningless (e.g. $+0.001$ F1 on $n = 100,000$ cases). Conversely, on smaller datasets, a large observed mean difference might not be statistically reliable.

### 3.1 Units of Measurement & Terminology
It is critical to distinguish between different measurements:
1. **Absolute Change ($\Delta$):**
   $$\Delta = \bar{x}_{\text{cand}} - \bar{x}_{\text{base}}$$
   Measured in the metric's natural units. For bounded $[0, 1]$ metrics like Exact Match or F1, an absolute change of $+0.02$ represents **$+2$ percentage points** (not a 2% relative change).
2. **Relative Change ($\Delta\%$):**
   $$\Delta\% = \frac{\Delta}{|\bar{x}_{\text{base}}|} \times 100\%$$
   Defined only when the baseline mean is non-zero. If baseline mean is $0.0$, relative change is mathematically undefined and reported as `None`.
3. **Statistical Significance:**
   Achieved when the empirical bootstrap confidence interval does not contain zero ($0 \notin [\text{CI}_{\text{lower}}, \text{CI}_{\text{upper}}]$).
4. **Practical Significance Threshold ($\tau$):**
   A minimum effect size specified in **absolute metric units**. The default in `RegressionConfig` is **$\tau = 0.0$** (pure statistical significance). Users may configure $\tau > 0$ (e.g., $\tau = 0.02$ for a $+0.02$ absolute score point threshold).

### 3.2 Decision Rules
The decision engine applies conservative rules evaluated against the **confidence interval bounds** rather than point estimates:

For higher-is-better metrics:
- **`IMPROVED`**: The lower bound of the CI strictly exceeds the threshold:
  $$\text{CI}_{\text{lower}} > \tau$$
  *(With default $\tau = 0.0$, this simplifies to $\text{CI}_{\text{lower}} > 0$.)*
- **`REGRESSED`**: The upper bound of the CI strictly falls below the negative threshold:
  $$\text{CI}_{\text{upper}} < -\tau$$
  *(With default $\tau = 0.0$, this simplifies to $\text{CI}_{\text{upper}} < 0$.)*
- **`INCONCLUSIVE`**: The confidence interval crosses zero ($0 \in [\text{CI}_{\text{lower}}, \text{CI}_{\text{upper}}]$) or fails to clear the practical significance threshold $\tau$.
- **`INSUFFICIENT_DATA`**: The number of aligned, valid paired samples $n < \text{min\_samples}$ (default 5).

---

## 4. Directionality & Inverted Metrics

Not all metrics are "higher is better". For metrics where lower values represent superior performance (e.g., `latency_ms`, token usage, error rate):
- The difference vector is inverted: $d_i = \text{score}(B_i) - \text{score}(C_i)$ or evaluated such that candidate latency lower than baseline yields an `IMPROVED` verdict.

---

## 5. Methodological Assumptions & Disclaimers

1. **Exchangeability:** The test cases must be independent and identically distributed (i.i.d.) draws from the target distribution. If all test cases share strong latent correlation (e.g., all 50 cases are slight variations of the same prompt), the bootstrap interval may underestimate true variance.
2. **Sample Size:** When $n < 10$, a warning is logged. When $n < 5$, the decision engine defaults to `INSUFFICIENT_DATA`.
3. **Multiple Testing:** Comparing dozens of metrics simultaneously inflates family-wise error rate. Treat secondary metrics as exploratory unless corrected.
