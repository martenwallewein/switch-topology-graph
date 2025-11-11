Of course. Here is a detailed mathematical formulation of the `solve_latency_lp` model, suitable for inclusion in a research paper or for documentation.

***

### Mathematical Formulation: Latency-Optimal Traffic Allocation LP Model

This document outlines the Linear Programming (LP) model used to determine the optimal traffic allocation from the perspective of end-hosts aiming to minimize latency. The model distributes total traffic demand across a network by prioritizing paths with the lowest latency. When a low-latency path becomes saturated, traffic automatically "spills over" to the next-best available path.

---

#### 1. Sets and Indices

We define the following sets to structure the model:

*   **H**: The set of all end-hosts, indexed by `h`.
*   **D**: The set of all traffic destinations, indexed by `d`.
*   **E**: The set of all egress interfaces, indexed by `e`.
*   **P**: The set of all possible paths from any host, indexed by `p`.
*   **P<sub>h</sub>**: A subset of P, representing all available paths originating from a specific host `h ∈ H`.

---

#### 2. Parameters

The model uses the following input parameters, which are assumed to be known constants:

*   **T<sub>d</sub>**: The total traffic demand (in Mbps) destined for destination `d ∈ D`.
*   **U<sub>h</sub>**: The maximum uplink capacity (in Mbps) of the end-host `h ∈ H`.
*   **C<sub>e</sub>**: The maximum egress capacity (in Mbps) of the egress interface `e ∈ E`.
*   **L<sub>e</sub>**: The latency (e.g., in ms) associated with using the egress interface `e ∈ E`.
*   **M<sub>pe</sub>**: A binary mapping function indicating if path `p ∈ P` uses egress `e ∈ E`.
    *   `M_pe = 1` if path `p` routes through egress `e`.
    *   `M_pe = 0` otherwise.
*   **R<sub>ed</sub>**: A binary reachability function indicating if egress `e ∈ E` can route traffic to destination `d ∈ D`.
    *   `R_ed = 1` if egress `e` can reach destination `d`.
    *   `R_ed = 0` otherwise.

---

#### 3. Decision Variable

The model's primary goal is to determine the optimal value for the following continuous decision variable:

*   **x<sub>hpd</sub>**: The amount of traffic (in Mbps) sent from host `h ∈ H`, over path `p ∈ P_h`, to destination `d ∈ D`. The variable is defined for all valid combinations of `(h, p, d)`.

---

#### 4. Objective Function

The objective is to **minimize the total latency-weighted traffic** across the entire network. This is achieved by minimizing the sum of the product of the traffic on each path and the latency of that path's egress interface.

**Minimize Z:**
```
Z = ∑_{h∈H} ∑_{p∈P_h} ∑_{d∈D} (x_hpd * L_e)
```
*subject to the condition that path `p` uses egress `e` and `e` can reach `d`.*

By minimizing this function, the LP solver is incentivized to assign traffic (`x_hpd`) to paths associated with the lowest latency (`L_e`) first.

---

#### 5. Constraints

The allocation of traffic is subject to the following operational and physical constraints:

**a) Traffic Demand Satisfaction**
The total traffic sent from all hosts to a specific destination `d` must equal the total demand for that destination.

```
∀d ∈ D:   ∑_{h∈H} ∑_{p∈P_h} x_hpd = T_d
```
*(Note: If total capacity is insufficient to meet demand, this constraint can be relaxed to `<= T_d` to find a feasible solution for the maximum traffic that can be sent).*

**b) End-Host Uplink Capacity**
The total outbound traffic from any given end-host `h` cannot exceed its available uplink capacity.

```
∀h ∈ H:   ∑_{p∈P_h} ∑_{d∈D} x_hpd ≤ U_h
```

**c) Egress Interface Capacity**
The total traffic flowing through any given egress interface `e` cannot exceed its capacity. This is calculated by summing the traffic from all paths that utilize that egress.

```
∀e ∈ E:   ∑_{h∈H} ∑_{p∈P_h} ∑_{d∈D} (x_hpd * M_pe) ≤ C_e
```

**d) Path Reachability**
Traffic can only be sent on a path `p` from host `h` to destination `d` if the egress `e` used by that path can actually reach the destination. This is implicitly handled by defining the `x_hpd` variables only for valid, reachable paths.

```
∀(h, p, d): x_hpd = 0 if R_ed = 0 for the egress `e` used by path `p`.
```

**e) Non-Negativity**
The amount of traffic on any path cannot be negative.

```
∀(h, p, d): x_hpd ≥ 0
```